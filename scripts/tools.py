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
from utils.format import format_listing_item

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

# ── Helpers ───────────────────────────────────────────────────────────────────


STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "when",
    "at",
    "from",
    "by",
    "for",
    "with",
    "about",
    "against",
    "between",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "to",
    "up",
    "down",
    "in",
    "out",
    "on",
    "off",
    "over",
    "under",
    "again",
    "further",
    "once",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "having",
    "do",
    "does",
    "did",
    "doing",
    "of",
    "some",
    "any",
    "this",
    "that",
    "these",
    "those",
}


def _tokenize(text: str) -> list[str]:
    # return a list of tokens (preserves duplicates for counting)
    # remove apostrophes: "Levi's" -> "Levis"
    normalized = re.sub(r"'", "", text.lower())
    # punctuation to whitespace: "word - word" -> "word   word"; "word/word" -> "word word"
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return [token for token in normalized.split() if token and token not in STOP_WORDS]


def _normalize_size(size_value: str) -> set[str]:
    cleaned = re.sub(r"[()\[\],]", "", size_value.lower())
    cleaned = cleaned.replace("/", " ")
    return set(token.strip() for token in cleaned.split() if token.strip())


# ── Tool 1: search_listings ───────────────────────────────────────────────────


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> dict[str, list[dict] | bool | str]:  # ☑️
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling. Multiple retries are performed:
    no size, no price, no size nor price before finally returning an empty list
    if no results are found.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
         A dict of the form:
         { "content": str, "success": bool, "message": str }

        `content`: A list of matching listing dicts, sorted by relevance (best
                   match first). Returns an empty list if nothing matches — does
                   NOT raise an exception.
        `info`:    A dictionary containing loosened constraints.
        `success`: Whether the function succeeded without errors.
        `message`: An error message if `success` is `False`.


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
        msg = "provide a description against which to find relevant items."
        print(f"[ERROR] search_listings: {msg}")
        return {
            "success": False,
            "message": f"Error: {msg}",
        }

    # query tokens should be unique
    query_tokens = set(_tokenize(description))

    # 1. Load all listings with load_listings().
    listings = load_listings()
    # tuples of (original listing, tokenized listing)
    tokenized_listings: list[tuple[dict, dict]] = []

    for listing in listings:
        tok_listing = dict(listing)
        del tok_listing["condition"]  # search by condition not supported
        del tok_listing["platform"]  # search by platform not supported
        tok_listing["size"] = _normalize_size(listing.get("size", ""))
        tok_listing["price"] = listing.get("price")

        # 3. Score each remaining listing by keyword overlap with `description`.
        # Use token lists (not sets) for listing fields so repeated matches count.
        tok_listing["title"] = _tokenize(listing.get("title") or "")
        tok_listing["description"] = _tokenize(listing.get("description") or "")
        tok_listing["category"] = _tokenize(listing.get("category") or "")
        tok_listing["brand"] = _tokenize(listing.get("brand") or "")

        tok_listing["style_tags"] = []
        for t in listing.get("style_tags") or []:
            tok_listing["style_tags"].extend(_tokenize(str(t)))

        tok_listing["colors"] = []
        for c in listing.get("colors") or []:
            tok_listing["colors"].extend(_tokenize(str(c)))

        tokenized_listings.append((listing, tok_listing))

    def _search(
        constrain_by_price: bool, constrain_by_size: bool
    ) -> list[tuple[int, dict]]:
        filtered_listings: list[tuple[int, dict]] = []

        for listing, tok_listing in tokenized_listings:

            # 2. Filter by max_price and size (if provided).
            if (
                constrain_by_price
                and max_price is not None
                and tok_listing["price"] is not None
            ):
                if tok_listing["price"] > max_price:
                    continue

            if constrain_by_size:
                search_size_tokens = _normalize_size(size) if size else None
                listing_size_tokens = tok_listing["size"]
                if (
                    search_size_tokens
                    and listing_size_tokens
                    and not (search_size_tokens & listing_size_tokens)
                ):
                    continue

            score = 0
            for token in query_tokens:
                score += tok_listing["title"].count(token)
                score += tok_listing["description"].count(token)
                score += tok_listing["category"].count(token)
                score += tok_listing["brand"].count(token)
                score += sum(t == token for t in tok_listing["style_tags"])
                score += sum(c == token for c in tok_listing["colors"])

            # 4. Drop any listings with a score of 0 (no relevant matches).
            if score == 0:
                continue

            # Preserve score for sorting, then discard before return.
            filtered_listings.append((score, listing))
        return filtered_listings

    constrain_by_price, constrain_by_size = True, True
    filtered_listings = _search(constrain_by_price, constrain_by_size)

    if not filtered_listings:
        constrain_by_price, constrain_by_size = False, True
        filtered_listings = _search(constrain_by_price, constrain_by_size)

    if not filtered_listings:
        constrain_by_price, constrain_by_size = True, False
        filtered_listings = _search(constrain_by_price, constrain_by_size)

    if not filtered_listings:
        constrain_by_price, constrain_by_size = False, False
        filtered_listings = _search(constrain_by_price, constrain_by_size)

    # 5. Sort by score, highest first, and return the listing dicts.
    # sort by id (secondary key) in ascending order
    filtered_listings.sort(key=lambda item: item[1]["id"])
    # sort by score (primary key) in descending order
    filtered_listings.sort(key=lambda item: item[0], reverse=True)

    return {
        "content": filtered_listings,
        "info": {
            "loosened_constraints": {
                "price": not (not (max_price and not constrain_by_price)),
                "size": not (not (size and not constrain_by_size)),
            }
        },
        "success": True,
    }


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────


def suggest_outfit(new_item: dict, wardrobe: dict) -> dict[str, str | bool]:  # ☑️
    """
    Given a thrifted item and the user's wardrobe, suggest a complete outfit.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A dict of the form:
        { "content": str, "success": bool, "message": str }

        `content`: A non-empty string with outfit suggestions. If the wardrobe
                   is empty, offers general styling advice for the item rather
                   than raising an exception or returning an empty string.
        `success`: Whether the function succeeded without errors.
        `message`: An error message if `success` is `False`.

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
    def _format_wardrobe_item(item: dict) -> str:
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

    new_item_block = format_listing_item(new_item)

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
        formatted = [_format_wardrobe_item(it) for it in picks]
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


def create_fit_card(outfit: str, new_item: dict) -> dict[str, str | bool]:  # ☑️
    """
    Generates a short, shareable outfit caption for the thrifted find.

    Args:
        `outfit`:   The outfit suggestion string from suggest_outfit().
        `new_item`: The listing dict for the thrifted item.

    Returns:
        A dict of the form:
        { "content": str, "success": bool, "message": str }

        `content`: A 2-4 sentence string usable as an Instagram/TikTok caption.
                   If outfit is empty or missing, return a descriptive error
                   message string — does NOT raise an exception.
        `success`: Whether the function succeeded without errors.
        `message`: An error message if `success` is `False`.

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
        msg = "outfit suggestion is empty; cannot generate caption."
        print(f"[ERROR] create_fit_card: {msg}")
        return {
            "success": False,
            "message": f"Error: {msg}",
        }

    # 2. Build a prompt that gives the LLM the item details and the outfit,
    #    and asks for a caption matching the style guidelines above.
    new_item_block = format_listing_item(new_item)
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


# ── Tool 4: compare_price ─────────────────────────────────────────────────────


def compare_price(new_item: dict) -> dict[str, str | bool | dict]:
    """
    Determines the price quality of the given item based on comparable listings
    in the database, returning aggregate stats as reasoning.

    Args:
        new_item: The listing dict for the thrifted item.

    Returns:
         A dict of the form:
         { "content": str, "success": bool, "message": str }

        `content`: A dictionary with the price quality and the averages (both
                   weighted and unweighted) of the rest of the items' prices.
        `success`: Whether the function succeeded without errors.
        `message`: An error message if `success` is `False`.

    1. Tokenizes the titles, descriptions, and sizes of `new_item` and all the
       other items in the database.
    2. Scores each other item by relevance to `new_item`: token-matching for
       titles, descriptions, and sizes; set intersection for colors and style
       tags; exact matching for platforms, brands, conditions, and categories.
    3. Calculates the unweighted price average.
    4. Calculates the weighted price average by score percent (score / sum).
    5. Determines `new_item`'s price quality: "steal" (below 25% of weighted),
       "fair" (within +-25%), "rip-off" (above 25%)
    6. Returns the price quality and both averages.
    """
    # 1. Tokenize the titles, descriptions, and sizes of new_item and all the
    #    other items in the database.
    listings = load_listings()
    other_items = [item for item in listings if item["id"] != new_item["id"]]

    if not other_items:
        return {
            "message": "Error: no other items found",
            "success": False,
        }

    new_title_toks = _tokenize(new_item.get("title") or "")
    new_desc_toks = _tokenize(new_item.get("description") or "")
    new_size_toks = _normalize_size(new_item.get("size") or "")
    new_colors = set(new_item.get("colors") or [])
    new_styles = set(new_item.get("style_tags") or [])

    # 2. Score each other item by relevance to new_item: token-matching for
    #    titles, descriptions, and sizes; set intersection for colors and style
    #    tags; exact matching for platforms, brands, conditions, and categories.
    prices = []
    scores = []

    for item in other_items:
        score = 0
        # Token matching
        other_title = _tokenize(item.get("title") or "")
        other_desc = _tokenize(item.get("description") or "")
        other_size = _normalize_size(item.get("size") or "")

        for t in set(new_title_toks):
            score += other_title.count(t)
        for t in set(new_desc_toks):
            score += other_desc.count(t)
        score += len(new_size_toks & other_size)

        # Set intersection
        score += len(new_colors & set(item.get("colors") or []))
        score += len(new_styles & set(item.get("style_tags") or []))

        # Exact matching
        if item.get("platform") == new_item.get("platform"):
            score += 1
        if item.get("brand") == new_item.get("brand") and new_item.get("brand"):
            score += 1
        if item.get("condition") == new_item.get("condition"):
            score += 1
        if item.get("category") == new_item.get("category"):
            score += 1

        if item.get("price") is not None and score > 0:
            prices.append(item["price"])
            scores.append(score)

    # 3. Calculate the unweighted price average.
    avg = sum(prices) / len(prices)

    # 4. Calculate the weighted price average by score percent (score / sum).
    sum_scores = sum(scores)
    weighted_avg = (
        sum(p * s for p, s in zip(prices, scores)) / sum_scores
        if sum_scores > 0
        else avg
    )

    # 5. Determine new_item's price quality: "steal" (below 25% of weighted),
    #    "fair" (within +-25%), "rip-off" (above 25%)
    current_price = new_item["price"]
    if current_price < weighted_avg * 0.75:
        quality = "steal"
    elif current_price > weighted_avg * 1.25:
        quality = "rip-off"
    else:
        quality = "fair"

    # 6. Return the price quality and both averages.
    return {
        "content": {
            "price_quality": quality,
            "weighted_avg": round(weighted_avg, 2),
            "avg": round(avg, 2),
            "fraction": current_price / weighted_avg,
        },
        "success": True,
    }
