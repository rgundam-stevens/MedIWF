"""Query OpenRouter for available models and save candidates to outputs/openrouter_models.json.
Run in Terminal:  python3 scripts/list_models.py
"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.env import load_env, require
from mediwf.openrouter import OpenRouterClient

root = load_env()
client = OpenRouterClient(require("OPENROUTER_API_KEY"))
models = client.list_models()
keys = ["openai/", "anthropic/", "google/", "meta-llama/", "qwen/", "mistralai/", "deepseek/", "microsoft/", "aaditya/", "openbio", "medit", "x-ai/"]
rows = []
for m in models:
    mid = m.get("id", "")
    if any(k in mid.lower() for k in keys):
        pr = m.get("pricing", {}) or {}
        rows.append({
            "id": mid,
            "name": m.get("name"),
            "context_length": m.get("context_length"),
            "prompt_usd_per_M": round(float(pr.get("prompt", 0) or 0) * 1e6, 3),
            "completion_usd_per_M": round(float(pr.get("completion", 0) or 0) * 1e6, 3),
            "created": m.get("created"),
        })
rows.sort(key=lambda r: r["id"])
out = root / "outputs" / "openrouter_models.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(rows, indent=1))
print(f"{len(models)} models on OpenRouter; {len(rows)} candidates saved to {out}")
