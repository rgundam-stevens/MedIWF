"""Minimal OpenRouter chat-completions client with retries, provider pinning and cost capture."""
import json, time, requests, threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from typing import Optional

_deadline_pool = ThreadPoolExecutor(max_workers=64)

class RequestDeadline(Exception):
    pass

def _post_with_deadline(session, url, data, deadline_s):
    """POST with an absolute wall-clock deadline. Slow keep-alive streams cannot defeat it: if the reply has not
    fully arrived by the deadline, the attempt is abandoned and retried on a fresh connection."""
    fut = _deadline_pool.submit(session.post, url, data=data, timeout=(20, 120))
    try:
        return fut.result(timeout=deadline_s)
    except FutTimeout:
        raise RequestDeadline("no complete response within %ds" % deadline_s)

BASE = "https://openrouter.ai/api/v1"

class OpenRouterClient:
    def __init__(self, api_key: str, app_title: str = "MedIWF research pipeline"):
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": app_title,
        })

    def list_models(self):
        r = self.s.get(f"{BASE}/models", timeout=60)
        r.raise_for_status()
        return r.json()["data"]

    def chat(self, model: str, system: str, user: str, temperature: float = 0.7,
             max_tokens: int = 4000, seed: Optional[int] = None,
             provider_order: Optional[list] = None, json_mode: bool = True,
             retries: int = 7, disable_reasoning: bool = True,
             attempt_deadline_s: int = 300, job_deadline_s: int = 1200, reasoning: Optional[dict] = None):
        """reasoning: an explicit OpenRouter reasoning object (e.g. {"effort": "high"} or {"max_tokens": 2048}) that ENABLES
        hidden reasoning; when given it overrides disable_reasoning and is never dropped on a rejected request (Amendment 6, A28)."""
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "usage": {"include": True},
        }
        if reasoning:
            body["reasoning"] = dict(reasoning)
        elif disable_reasoning:
            # Ask reasoning-capable models to answer directly. Reasoning tokens otherwise consume the
            # completion budget and leave the visible answer empty (seen in pilot 1).
            body["reasoning"] = {"enabled": False}
        reasoning_on = bool(reasoning); dropped = []
        if seed is not None:
            body["seed"] = seed
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if provider_order:
            body["provider"] = {"order": provider_order, "allow_fallbacks": False}
        last_err = None
        job_t0 = time.time()
        for attempt in range(retries + 3):  # extra attempts cover parameter-dropping retries
            if time.time() - job_t0 > job_deadline_s:
                return {"ok": False, "error": f"job deadline exceeded ({job_deadline_s}s): {last_err}"}
            try:
                t0 = time.time()
                r = _post_with_deadline(self.s, f"{BASE}/chat/completions", json.dumps(body), attempt_deadline_s)
                latency = time.time() - t0
                if r.status_code in (429, 500, 502, 503, 504):
                    last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                    # rate limits: back off progressively (3, 6, 12, 24, 48, 60, 60 s)
                    time.sleep(min(60, 3 * (2 ** attempt)))
                    continue
                if r.status_code == 400:
                    # Drop optional parameters one at a time (some models reject them), then give up. With reasoning
                    # enabled the reasoning object is never dropped: temperature goes first (Anthropic requires the
                    # default temperature when thinking is on), then response_format, then seed.
                    msg = r.text[:300]
                    order = ("temperature", "response_format", "seed") if reasoning_on else ("reasoning", "response_format", "seed")
                    for opt in order:
                        if opt in body:
                            body.pop(opt, None); dropped.append(opt)
                            if opt == "response_format": json_mode = False
                            last_err = f"HTTP 400 (dropped {opt}): {msg}"
                            break
                    else:
                        return {"ok": False, "error": f"HTTP 400: {msg}"}
                    continue
                if r.status_code != 200:
                    return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}
                data = r.json()
                choice = data["choices"][0]
                usage = data.get("usage", {}) or {}
                if choice.get("finish_reason") == "length" and body["max_tokens"] < 16000:
                    # truncated (usually hidden reasoning); retry once with a larger budget
                    body["max_tokens"] = 16000
                    continue
                return {
                    "ok": True,
                    "content": choice["message"]["content"],
                    "finish_reason": choice.get("finish_reason"),
                    "generation_id": data.get("id"),
                    "model_returned": data.get("model"),
                    "provider": data.get("provider"),
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "cost_usd": usage.get("cost"),
                    "latency_s": round(latency, 2),
                    "json_mode_used": json_mode,
                    "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                    "max_tokens_used": body["max_tokens"],
                    "seed_used": body.get("seed"),
                    "reasoning_param_used": "reasoning" in body,
                    "reasoning_request": body.get("reasoning"),
                    "temperature_sent": body.get("temperature"),
                    "dropped_params": dropped,
                }
            except (requests.RequestException, RequestDeadline) as e:
                last_err = str(e)[:300]
                time.sleep(min(30, 2 ** attempt + 1))
        return {"ok": False, "error": last_err}
