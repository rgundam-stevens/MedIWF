"""Parsing and validation of model responses (moved out of scripts/generate.py on 2026-09-16 so that generation and
detection use one and the same validator).

Validation rules (v1.1): a response is usable only if it is a JSON object with a non-empty stem, an options object whose
keys normalise to exactly A-E (EXPECTED_OPTIONS = 5) without collisions, non-empty option texts, and a single-letter
answer that is one of the options. The collision rule was added after the audit of 16 Sep 2026 found two responses in
which a malformed key ("date", "ed") silently overwrote a real option after normalisation, and two with six options.
Every repair applied to a malformed response is recorded (field parse_repair) so first-attempt strict-JSON rates can
still be reported.
"""
import json, re

EXPECTED_OPTIONS = 5
JSON_RE = re.compile(r"\{.*\}", re.S)


def _validate(d):
    """Return (item, err). Accepts answer/rationale accidentally nested inside options (a missing brace)."""
    if not isinstance(d, dict): return None, "not_object"
    opts = d.get("options")
    if isinstance(opts, list): opts = {chr(65 + i): o for i, o in enumerate(opts)}   # tolerate list form
    if not isinstance(opts, dict): return None, "missing_fields"
    opts = dict(opts)
    for k in ("answer", "rationale"):
        if k not in d and k in opts: d[k] = opts.pop(k)
    if not d.get("stem") or not d.get("answer"): return None, "missing_fields"
    ans = str(d["answer"]).strip().upper()[:1]
    norm = {}
    for k, v in opts.items():
        nk = str(k).strip().upper()[:1]
        if nk in norm: return None, "duplicate_option_key"          # e.g. "D" and "date" both normalise to D
        norm[nk] = str(v).strip()
    opts = norm
    if EXPECTED_OPTIONS and (len(opts) != EXPECTED_OPTIONS or sorted(opts) != [chr(65 + i) for i in range(EXPECTED_OPTIONS)]):
        return None, "wrong_option_count"
    if ans not in opts: return None, "answer_not_in_options"
    if any(not v for v in opts.values()): return None, "empty_option"
    return {"stem": str(d["stem"]).strip(), "options": opts, "answer": ans,
            "rationale": str(d.get("rationale", "")).strip(), "n_options": len(opts)}, None


def _repairs(text):
    """Yield (repair_name, candidate_text), least invasive first."""
    t = text.strip()
    yield "none", t
    m = JSON_RE.search(t)
    if m and m.group(0) != t: yield "outer_braces", m.group(0)
    k = t.rfind('{"stem"')
    if k > 0: yield "last_object", t[k:]            # model "corrected itself" and emitted a second object
    base = t[k:] if k > 0 else t
    yield "append_brace", base + "}"                 # missing closing brace(s)
    yield "append_2braces", base + "}}"
    r = re.sub(r",\s*}", "}", base)                  # trailing comma before a closing brace
    yield "trailing_comma", r
    yield "trailing_comma+brace", r + "}"
    yield "stray_punct", re.sub(r'"\s*[:,]\s*}\s*$', '"}', base)          # '": }' or '", }' before the final brace
    yield "double_quote_key", re.sub(r'([,{]\s*)""([A-Za-z_]+)"\s*:', r'\1"\2":', base)   # ,""E":
    yield "stray_empty_value", re.sub(r'"\s*:\s*""\s*}', '"}', base)      # option text followed by ': ""'
    if base.endswith("}") and not base.rstrip("}").rstrip().endswith('"'):
        yield "close_string", base.rstrip("}").rstrip() + '"}'            # unterminated final string
    yield "newline_strip", base.replace("\r", " ").replace("\n", " ").replace("\t", " ")


def parse_item(text):
    """Return (parsed_dict_or_None, error_string_or_None, repair_name_or_None)."""
    if not text: return None, "empty", None
    last_err = "not_json"
    for name, cand in _repairs(text):
        for attempt in (cand, cand.replace("\r", " ").replace("\n", " ").replace("\t", " ")):
            try: d = json.loads(attempt, strict=False)
            except Exception: continue
            item, err = _validate(d)
            if item: return item, None, name
            last_err = err; break
    return None, last_err, None


def usable_record(rec):
    """The item to analyse for a stored generation record: the raw response re-parsed with the CURRENT validator
    (so that a record accepted by an older, looser parser is not silently reused). Returns the item or None."""
    if not rec.get("ok") or not rec.get("content"): return None
    item, err, how = parse_item(rec["content"])
    return item
