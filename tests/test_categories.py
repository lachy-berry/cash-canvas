"""
Tests for category loading and the GET /api/categories endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from server.main import app
from server.categories import load_categories

client = TestClient(app)


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


class TestCategoriesEndpoint:
    def test_get_categories_returns_200(self):
        response = client.get("/api/categories")
        assert response.status_code == 200

    def test_get_categories_returns_layers(self):
        response = client.get("/api/categories")
        data = response.json()
        assert "layers" in data

    def test_get_categories_broad_layer_present(self):
        response = client.get("/api/categories")
        data = response.json()
        layer_ids = [l["id"] for l in data["layers"]]
        assert "broad" in layer_ids

    def test_get_categories_includes_groceries(self):
        response = client.get("/api/categories")
        data = response.json()
        broad = next(l for l in data["layers"] if l["id"] == "broad")
        cat_ids = [c["id"] for c in broad["categories"]]
        assert "groceries" in cat_ids
