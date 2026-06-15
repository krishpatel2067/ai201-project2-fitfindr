import pytest

from scripts.tools import search_listings


def test_search_listings_():
    levis = search_listings("Levi's", _with_score=True)

    assert levis["success"] == True  # non-empty matches
    assert len(levis["relevant_items"]) == 3  # 3 results returned
    assert levis["relevant_items"][0][0] == 2  # first result has 2 matched occurences
