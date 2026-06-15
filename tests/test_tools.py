from scripts.tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

new_item = {
    "id": "lst_029",
    "title": "Silk Button-Down — Sage Green",
    "description": "Loose silk (feel) button-down in sage green. Long sleeve, can be worn open as a layer or fully buttoned. Very flowy.",
    "category": "tops",
    "style_tags": ["vintage", "minimal", "earth tones", "cottagecore"],
    "size": "M",
    "condition": "excellent",
    "price": 28.00,
    "colors": ["sage", "green"],
    "brand": None,
    "platform": "depop",
}

# ── Tool 1: search_listings ───────────────────────────────────────────────────


def test_search_listings_non_empty_results():
    results = search_listings("Levi's")
    assert results["success"] == True  # no errors
    assert len(results["content"]) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results["success"] == True  # no errors
    assert results["content"] == []  # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=40)
    assert results["success"] == True  # no errors
    # all items at most $40
    assert all(item["price"] <= 40 for item in results["content"])


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────


def test_suggest_outfit_response_non_empty_wardrobe():
    results = suggest_outfit(new_item, get_example_wardrobe())
    assert results["success"] == True  # no errors
    assert len(results["content"]) > 0  # non-empty string


def test_suggest_outfit_response_empty_wardrobe():
    results = suggest_outfit(new_item, get_empty_wardrobe())
    assert results["success"] == True  # no errors
    assert len(results["content"]) > 0  # non-empty string


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────


def test_create_fit_card_non_empty_response():
    results = create_fit_card(
        "Pair the new sage green silk button-down with the wide-leg khaki trousers and black combat boots for a chic, earthy look that's perfect for a casual day out. The flowy silk top will add a touch of elegance to the overall outfit, while the boots will ground it with a cool, grunge-inspired vibe.",
        new_item,
    )
    assert results["success"] == True  # no errors
    assert len(results["content"]) > 0  # non-empty string
