import json


def load_config(path):
    """Load configuration from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    return {
        "listen_addr": cfg.get("listen_addr", "0.0.0.0"),
        "listen_port": int(cfg.get("listen_port", 2101)),
        "max_client": int(cfg.get("max_client", 0)),
        "max_source": int(cfg.get("max_source", 0)),
        "max_pending": int(cfg.get("max_pending", 10)),
        "tokens_client": cfg.get("tokens_client", {}),
        "tokens_source": cfg.get("tokens_source", {}),
        "log_level": cfg.get("log_level", "INFO"),
        "log_file": cfg.get("log_file"),
    }
