"""Load and serve categories from config/categories.yaml."""
from pathlib import Path

import yaml
from fastapi import HTTPException

_CATEGORIES_PATH = Path(__file__).parent.parent / "config" / "categories.yaml"

# Simple in-process cache — invalidated whenever the file's mtime changes.
# This means local edits to categories.yaml take effect immediately without
# restarting the server.
_CATEGORIES_CACHE: dict | None = None
_CATEGORIES_MTIME: float | None = None


def load_categories() -> dict:
    """Load categories from YAML with simple mtime-based in-process caching."""
    global _CATEGORIES_CACHE, _CATEGORIES_MTIME
    mtime = _CATEGORIES_PATH.stat().st_mtime
    if _CATEGORIES_CACHE is not None and _CATEGORIES_MTIME == mtime:
        return _CATEGORIES_CACHE

    with open(_CATEGORIES_PATH) as f:
        data = yaml.safe_load(f)

    _CATEGORIES_CACHE = data
    _CATEGORIES_MTIME = mtime
    return data


def validate_category(layer_id: str, category_id: str | None) -> None:
    """Validate that layer_id and category_id exist in categories.yaml.

    Raises HTTPException 422 if either is unknown.
    When category_id is None (clear operation), only the layer is validated.
    """
    config = load_categories()
    layers = {layer["id"]: layer for layer in config.get("layers", [])}

    if layer_id not in layers:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown layer '{layer_id}'. Valid layers: {list(layers)}",
        )

    if category_id is not None:
        valid_categories = {c["id"] for c in layers[layer_id].get("categories", [])}
        if category_id not in valid_categories:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown category '{category_id}' in layer '{layer_id}'. "
                       f"Valid categories: {sorted(valid_categories)}",
            )
