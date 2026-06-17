# tests/test_tools.py
import pytest
from tools import search_listings, suggest_outfit, create_fit_card


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_substring_match():
    # "M" should match "S/M", "M/L", "M" exactly — per planning.md spec
    results = search_listings("tee", size="M", max_price=None)
    assert all("m" in item["size"].lower() for item in results)


def test_search_no_exception_on_impossible_constraints():
    # Should never raise, even with constraints that match nothing
    results = search_listings("nonexistent unicorn jacket", size="XXXL", max_price=1)
    assert isinstance(results, list)


# ── suggest_outfit ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_item():
    return {
        "id": "lst_006",
        "title": "Graphic Tee — 2003 Tour Bootleg Style",
        "description": "Vintage-style bootleg tee with faded graphic.",
        "category": "tops",
        "style_tags": ["graphic tee", "vintage", "grunge"],
        "price": 24.00,
        "colors": ["black"],
        "platform": "depop",
    }


def test_suggest_outfit_empty_wardrobe_does_not_crash(sample_item):
    empty_wardrobe = {"items": []}
    result = suggest_outfit(sample_item, empty_wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_with_wardrobe_items(sample_item):
    wardrobe = {
        "items": [
            {"name": "Baggy jeans", "category": "bottoms", "color": "blue"},
            {"name": "Chunky sneakers", "category": "shoes", "color": "white"},
        ]
    }
    result = suggest_outfit(sample_item, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_missing_items_key_does_not_crash(sample_item):
    # wardrobe dict without an 'items' key at all
    result = suggest_outfit(sample_item, {})
    assert isinstance(result, str)
    assert len(result) > 0


# ── create_fit_card ───────────────────────────────────────────────────────────

def test_create_fit_card_empty_outfit_returns_error_message(sample_item):
    result = create_fit_card("", sample_item)
    assert result == "Oops, looks like the outfit context got lost. Try again!"


def test_create_fit_card_whitespace_outfit_returns_error_message(sample_item):
    result = create_fit_card("   ", sample_item)
    assert result == "Oops, looks like the outfit context got lost. Try again!"


def test_create_fit_card_valid_input_returns_caption(sample_item):
    outfit = "Pair with baggy jeans and chunky white sneakers for a grunge look."
    result = create_fit_card(outfit, sample_item)
    assert isinstance(result, str)
    assert len(result) > 0


def test_create_fit_card_output_varies():
    # Same input called multiple times should not produce identical output,
    # since temperature=0.9 is meant to introduce variation.
    item = {"title": "Test Tee", "price": 10.00, "platform": "depop"}
    outfit = "Style with jeans and sneakers."

    outputs = {create_fit_card(outfit, item) for _ in range(3)}
    assert len(outputs) > 1, "Expected varied captions across calls, got identical output"