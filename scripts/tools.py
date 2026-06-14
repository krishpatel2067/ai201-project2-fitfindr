"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq
from functools import cache

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────


@cache
def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
    _with_score: bool | None = False,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    description = (description or "").strip()
    if not description:
        return []

    def _tokenize(text: str) -> set[str]:
        # remove apostrophes: "Levi's" -> "Levis"
        normalized = re.sub(r"'", "", text.lower())
        # punctuation to whitespace: "word - word" -> "word   word"; "word/word" -> "word word"
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        return set(token for token in normalized.split() if token)

    def _tokenize_list(text: str) -> list[str]:
        # return a list of tokens (preserves duplicates for counting)
        normalized = re.sub(r"'", "", text.lower())
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        return [token for token in normalized.split() if token]

    def _normalize_size(size_value: str) -> set[str]:
        cleaned = re.sub(r"[()\[\],]", "", size_value.lower())
        cleaned = cleaned.replace("/", " ")
        return set(token.strip() for token in cleaned.split() if token.strip())

    query_tokens = _tokenize(description)
    search_size_tokens = _normalize_size(size) if size else None

    # 1. Load all listings with load_listings().
    listings = load_listings()

    filtered_listings: list[tuple[int, dict]] = []
    for listing in listings:
        listing_size = listing.get("size", "")
        listing_price = listing.get("price")

        # 2. Filter by max_price and size (if provided).
        if max_price is not None and listing_price is not None:
            if listing_price > max_price:
                continue

        if search_size_tokens is not None:
            listing_size_tokens = _normalize_size(listing_size)
            if not (search_size_tokens & listing_size_tokens):
                continue

        # 3. Score each remaining listing by keyword overlap with `description`.
        # Use token lists (not sets) for listing fields so repeated matches count.
        title_tokens_list = _tokenize_list(listing.get("title") or "")
        description_tokens_list = _tokenize_list(listing.get("description") or "")
        category_tokens_list = _tokenize_list(listing.get("category") or "")
        brand_tokens_list = _tokenize_list(listing.get("brand") or "")

        style_tokens_list: list[str] = []
        for t in listing.get("style_tags") or []:
            style_tokens_list.extend(_tokenize_list(str(t)))

        color_tokens_list: list[str] = []
        for c in listing.get("colors") or []:
            color_tokens_list.extend(_tokenize_list(str(c)))

        # Count total occurrences of each query token across all fields.
        score = 0
        for token in query_tokens:
            score += title_tokens_list.count(token)
            score += description_tokens_list.count(token)
            score += category_tokens_list.count(token)
            score += brand_tokens_list.count(token)
            score += sum(t == token for t in style_tokens_list)
            score += sum(c == token for c in color_tokens_list)

        # 4. Drop any listings with a score of 0 (no relevant matches).
        if score == 0:
            continue

        # Preserve score for sorting, then discard before return.
        filtered_listings.append((score, listing))

    # 5. Sort by score, highest first, and return the listing dicts.
    # sort by id (secondary key) in ascending order
    filtered_listings.sort(key=lambda item: item[1]["id"])
    # sort by score (primary key) in descending order
    filtered_listings.sort(key=lambda item: item[0], reverse=True)

    return (
        filtered_listings
        if _with_score
        else [listing for _, listing in filtered_listings]
    )


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    # Replace this with your implementation
    return ""


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Replace this with your implementation
    return ""
