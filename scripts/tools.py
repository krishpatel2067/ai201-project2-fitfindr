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

import re
import random

from utils.data_loader import load_listings
from utils.llm import get_groq_client, MODEL as LLM_MODEL

# ── System prompts ────────────────────────────────────────────────────────────
NON_EMPTY_WARDROBE_OUTFIT_SYS_PMT = (
    "You are a fashion advisor. Take a newly thrifted clothing item and a "
    "wardrobe of existing clothing items, and give a 1-2 sentence outfit "
    "suggestion incorporating the new item with some wardrobe items. As a "
    "fashion advisor, use an informal, friendly, and lighthearted tone. Be "
    "creative with the suggestions, but make sure they are helpful to the "
    "user. Do NOT mention yourself (no 'I', 'me', etc.). Only give one "
    "suggestion - do NOT give alternatives or choices."
)

EMPTY_WARDROBE_OUTFIT_SYS_PMT = (
    "You are a fashion advisor. Take a newly thrifted clothing item, and give "
    "1-2 sentences of general styling advice. As a fashion advisor, use an "
    "informal, friendly, and lighthearted tone. Be creative with the "
    "suggestions, but make sure they are helpful to the user. Do NOT mention "
    "yourself (no 'I', 'me', etc.). Only give one suggestion - do NOT give "
    "alternatives or choices."
)

FIT_CARD_SYS_PMT = (
    "You are a social media caption writer. Given a newly thrifted clothing "
    "item and an outfit suggestion, produce a 2-4 sentence "
    "Instagram/TikTok-style caption. Mention the item name, price, and "
    "platform naturally (once each). Capture the outfit vibe in specific "
    "terms. As a social media caption writer, use a casual, authentic, and "
    "playful tone (like a real 'Outfit of the Day' post). Make sure to NOT "
    "sound like a product listing. Err on the side of concision rather than "
    "descriptiveness to sound like an ordinary person, not a fashion expert. "
    "For the price, just mention the dollar amount (e.g. $28 NOT $28.00). Feel "
    "free to use social media conventions like text love hearts, text emojis, "
    "lowercase, caps, etc. for an even more casual style. Use regular emojis "
    "very sparingly."
)

# ── Shared helper functions ───────────────────────────────────────────────────


def _format_new_item(new_item: dict) -> str:
    return "\n".join(
        [
            f"Item: {new_item.get('title') or "UNKNOWN"}",
            f"Category: {new_item.get('category') or "UNKNOWN"}",
            f"Colors: {', '.join(new_item.get('colors') or []) or "UNKNOWN"}",
            f"Style tags: {', '.join(new_item.get('style_tags') or []) or "NONE"}",
            f"Price: {"$" + str(new_item.get('price')) if new_item.get('price') is not None else 'UNKNOWN'}",
            f"Platform: {new_item.get('platform') or "UNKNOWN"}",
            f"Description: {new_item.get('description') or "NONE"}",
        ]
    )


# ── Tool 1: search_listings ───────────────────────────────────────────────────


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
    _with_score: bool | None = False,
) -> list[dict]:  # ☑️
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

    1. Loads all listings with load_listings().
    2. Filters by max_price and size (if provided).
    3. Scores each remaining listing by keyword overlap with `description`.
    4. Drops any listings with a score of 0 (no relevant matches).
    5. Sorts by score, highest first, and returns the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    description = (description or "").strip()
    if not description:
        return {
            "success": False,
            "message": "Error: provide a description against which to find relevant items.",
        }

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

    return {
        "content": (
            filtered_listings
            if _with_score
            else [listing for _, listing in filtered_listings]
        ),
        "success": True,
    }


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:  # ☑️
    """
    Given a thrifted item and the user's wardrobe, suggest a complete outfit.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    1. Checks whether wardrobe['items'] is empty.
    2. If empty: calls the LLM with a prompt for general styling ideas
        (what kinds of items pair well, what vibe it suits, etc.).
    3. If not empty: formats the wardrobe items into a prompt and asks
        the LLM to suggest specific outfit combinations using the new item
        and named pieces from the wardrobe.
    4. Returns the LLM's response as a string.
    """
    wardrobe_items = wardrobe.get("items")

    # Helper to format an item succinctly for the LLM prompt
    def _format_item_for_prompt(item: dict) -> str:
        parts = []
        name = item.get("name") or "UNKNOWN"
        parts.append(f"{name}")
        cat = item.get("category")
        if cat:
            parts.append(f"Category: {cat}")
        colors = item.get("colors")
        if colors:
            parts.append(f"Colors: {', '.join(colors)}")
        styles = item.get("style_tags")
        if styles:
            parts.append(f"Style tags: {', '.join(styles)}")
        notes = item.get("notes")
        if notes:
            parts.append(f"Notes: {notes}")
        return "\n".join(parts)

    new_item_block = _format_new_item(new_item)

    # 1. Check whether wardrobe['items'] is empty.
    if not wardrobe_items:
        # 2. If empty: call the LLM with a prompt for general styling ideas.
        system_prompt = EMPTY_WARDROBE_OUTFIT_SYS_PMT
        user_prompt = "NEWLY THRIFTED CLOTHING ITEM:\n\n" + new_item_block
    else:
        # 3. If not empty: format the wardrobe items into a prompt and ask
        #    the LLM to suggest specific outfit combinations using the new item
        #    and named pieces from the wardrobe.
        system_prompt = NON_EMPTY_WARDROBE_OUTFIT_SYS_PMT
        picks = random.sample(wardrobe_items, k=min(10, len(wardrobe_items)))
        formatted = [_format_item_for_prompt(it) for it in picks]
        wardrobe_block = "\n\n".join(formatted)
        user_prompt = (
            "NEWLY THRIFTED CLOTHING ITEM:\n\n"
            + new_item_block
            + "\n\nWARDROBE ITEMS:\n\n"
            + wardrobe_block
        )

    # Call Groq chat completions API and return the model text response directly
    try:
        client = get_groq_client()
        result = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
        )
        # 4. Return the LLM's response as a string.
        return {"content": result.choices[0].message.content, "success": True}
    except Exception as e:
        # potential errors like 400
        print("[ERROR] suggest_outfit:", e)
        return {
            "success": False,
            "message": "Error: failed to generate outfit suggestion: " + str(e),
        }


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────


def create_fit_card(outfit: str, new_item: dict) -> str:  # ☑️
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2-4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption:
    - Feels casual and authentic (like a real OOTD post, not a product
      description)
    - Mentions the item name, price, and platform naturally (once each)
    - Captures the outfit vibe in specific terms
    - Sounds different each time for different inputs (via a higher LLM
      temperature)

    1. Guards against an empty or whitespace-only outfit string.
    2. Builds a prompt that gives the LLM the item details and the outfit,
       and asks for a caption matching the style guidelines above.
    3. Calls the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # 1. Guard against an empty or whitespace-only outfit string.
    outfit = outfit.strip()
    if not outfit:
        return {
            "success": False,
            "message": "Error: outfit suggestion is empty; cannot generate caption.",
        }

    # 2. Build a prompt that gives the LLM the item details and the outfit,
    #    and asks for a caption matching the style guidelines above.
    new_item_block = _format_new_item(new_item)
    system_prompt = FIT_CARD_SYS_PMT
    user_prompt = (
        f"NEWLY THRIFTED CLOTHING ITEM:\n\n"
        + new_item_block
        + f"\n\nOUTFIT SUGGESTION:\n\n"
        + outfit
    )

    # 3. Call the LLM and return the response.
    try:
        client = get_groq_client()
        result = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=1.0,
        )

        return {"content": result.choices[0].message.content, "success": True}
    except Exception as e:
        print("[ERROR] create_fit_card:", e)
        return {
            "success": False,
            "message": "Error: failed to generate caption: " + str(e),
        }
