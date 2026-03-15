"""
Tests for category loading from config/categories.yaml.
Categories must never be hardcoded — always loaded from YAML.
"""
import pytest
from server.categories import load_categories


class TestCategoryLoading:
    def test_loads_without_error(self):
        categories = load_categories()
        assert categories is not None

    def test_returns_layers(self):
        categories = load_categories()
        assert "layers" in categories

    def test_broad_layer_exists(self):
        categories = load_categories()
        layer_ids = [layer["id"] for layer in categories["layers"]]
        assert "broad" in layer_ids

    def test_broad_layer_has_categories(self):
        categories = load_categories()
        broad = next(l for l in categories["layers"] if l["id"] == "broad")
        assert len(broad["categories"]) > 0

    def test_each_category_has_id_and_name(self):
        categories = load_categories()
        broad = next(l for l in categories["layers"] if l["id"] == "broad")
        for cat in broad["categories"]:
            assert "id" in cat
            assert "name" in cat
