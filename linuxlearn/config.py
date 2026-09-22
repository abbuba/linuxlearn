import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "linuxlearn"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "provider": "ollama",
    "model": "qwen2.5-coder:1.5b",
    "ollama_base_url": "http://localhost:11434",
    "api_base_url": "https://api.groq.com/openai/v1",
    "api_key": ""
}

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {} # Triggers onboarding wizard
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            return merged
    except Exception:
        return {}

def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def reset_config() -> dict:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    return {}