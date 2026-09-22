"""Tiny .env loader (no external dependency)."""
import os, pathlib, warnings
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

def load_env(path=None):
    root = pathlib.Path(__file__).resolve().parents[2]
    p = pathlib.Path(path) if path else root / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return root

def require(key):
    v = os.environ.get(key)
    if not v or v.startswith("paste-your"):
        raise SystemExit(f"Missing {key}. Put it in MedIWF/.env as {key}=...")
    return v
