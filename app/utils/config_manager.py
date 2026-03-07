from __future__ import annotations

import json
from app.db.database import get_app_data_dir

_DEFAULTS = {
    "empresa_nombre": "Inventario JH",
    "empresa_telefono": "",
    "empresa_direccion": "",
}


def _path():
    return get_app_data_dir() / "config.json"


def cargar_config() -> dict:
    p = _path()
    if not p.exists():
        guardar_config(_DEFAULTS.copy())
        return _DEFAULTS.copy()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        for k, v in _DEFAULTS.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return _DEFAULTS.copy()


def guardar_config(config: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def get(key: str):
    return cargar_config().get(key, _DEFAULTS.get(key, ""))


def set(key: str, value) -> None:
    config = cargar_config()
    config[key] = value
    guardar_config(config)
