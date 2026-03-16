"""Load and serve categories from config/categories.yaml."""
from pathlib import Path
import yaml

_CATEGORIES_PATH = Path(__file__).parent.parent / "config" / "categories.yaml"


def load_categories() -> dict:
    """Load categories from the YAML config file."""
    with open(_CATEGORIES_PATH) as f:
        return yaml.safe_load(f)
