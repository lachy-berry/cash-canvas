"""Tests for GET /api/categories and the underlying YAML loader."""
from tests.conftest import client


def test_categories_endpoint_returns_broad_layer_with_groceries():
    """Single integration test: endpoint loads YAML, returns broad layer with real categories."""
    data = client.get("/api/categories").json()
    broad = next(l for l in data["layers"] if l["id"] == "broad")
    cat_ids = [c["id"] for c in broad["categories"]]
    assert "groceries" in cat_ids

def test_each_category_has_id_and_name():
    """All categories in the broad layer must have both id and name fields."""
    data = client.get("/api/categories").json()
    broad = next(l for l in data["layers"] if l["id"] == "broad")
    for cat in broad["categories"]:
        assert "id" in cat and "name" in cat
