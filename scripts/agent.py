"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from scripts.tools import search_listings, suggest_outfit, create_fit_card
from utils.llm import get_groq_client, MODEL as LLM_MODEL

MAX_OUTFIT_RETRIES = 5

PARSE_QUERY_SYS_PMT = "You are given a natural-langauge query about thrifting a new clothing item under some optional price and size constraints. Parse the query to extract a short description, max price, and size. The short description does not need to be a full sentence - just a phrase describing an item. The size must be in letter format (e.g. 'S' for small, 'M' for medium, 'S/M' for small/medium, etc.) if explicit sizes are given. If the query does not contain an explicit size, rather an implicit size (like 'adjustable', 'one size', etc.), just return that implicit size. The three items must be returned in a strict format shown below (each item must be in its own line):"
'DESCRIPTION: "<description>"'
"MAX PRICE: $<max price to the hundredths place>"
"SIZE: <size>"

# ── session state ─────────────────────────────────────────────────────────────


def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.
    """
    return {
        "query": query,  # original user query
        "parsed": {},  # extracted description / size / max_price
        "search_results": [],  # list of matching listing dicts
        "selected_item": None,  # top result, passed into suggest_outfit
        "wardrobe": wardrobe,  # user's wardrobe dict
        "outfit_suggestion": None,  # string returned by suggest_outfit
        "fit_card": None,  # string returned by create_fit_card
        "error": None,  # set if the interaction ended early
    }


def _normalize_size_token(size_text: str) -> str | None:
    cleaned = (size_text or "").strip()
    if not cleaned:
        return None

    normalized = re.sub(r"[\s_-]+", "/", cleaned)
    if re.fullmatch(
        r"(?i:one/size|adjustable|osfa|free/size|free-size|free size)", normalized
    ):
        return normalized.replace("/", " ").lower()

    return normalized.upper()


def _parse_llm_response(response: str) -> tuple[str, str | None, float | None]:
    description = ""
    size = None
    max_price = None

    desc_pattern = r'^(?:DESCRIPTION:)?\s*"?(?P<description>.*?)"?\s*$'
    price_pattern = r"^(?:MAX PRICE:)?\s*\$?(?P<max_price>[0-9]+(?:\.[0-9]{1,2})?)\s*$"
    size_pattern = r"^(?:SIZE:)?\s*(?P<size>.+?)\s*$"

    lines = response.split("\n")

    desc_match = re.search(
        desc_pattern,
        lines[0] if lines else "",
        flags=re.I,
    ) or re.search(
        desc_pattern,
        response,
        flags=re.I | re.M,
    )
    if desc_match:
        description = desc_match.group("description").strip()

    no_price_match = re.search(
        r"no(?:ne)?", lines[1] if len(lines) > 1 else "", flags=re.I
    )

    if not no_price_match:
        price_match = re.search(
            price_pattern,
            lines[1] if len(lines) > 1 else "",
            flags=re.I,
        ) or re.search(
            price_pattern,
            response,
            flags=re.I | re.M,
        )
        if price_match:
            max_price = float(price_match.group("max_price"))

    no_size_match = re.search(
        r"no(?:ne)?", lines[2] if len(lines) > 2 else "", flags=re.I
    )

    if not no_size_match:
        size_match = (
            re.search(r"no(?:ne)", lines[2], flags=re.I)
            or re.search(
                size_pattern,
                lines[2] if len(lines) > 2 else "",
                flags=re.I,
            )
            or re.search(
                size_pattern,
                response,
                flags=re.I | re.M,
            )
        )
        if size_match:
            size = _normalize_size_token(size_match.group("size").strip())

    return description, size, max_price


def _extract_price_from_query(query: str) -> float | None:
    if not query:
        return None

    price_patterns = [
        r"\b(?:under|below|less than|no more than|up to|max(?:imum)?|for)\s*\$?(?P<price>[0-9]+(?:\.[0-9]{1,2})?)\b",
        r"\$\s*(?P<price>[0-9]+(?:\.[0-9]{1,2})?)\b",
    ]

    for pattern in price_patterns:
        price_match = re.search(pattern, query, flags=re.I)
        if price_match:
            return float(price_match.group("price"))

    return None


def _extract_size_from_query(query: str) -> str | None:
    if not query:
        return None

    explicit_size = re.search(
        r"\bsize\s*(?:is|=|:)?\s*(?P<size>[A-Za-z0-9/ +_-]+)\b",
        query,
        flags=re.I,
    )
    if explicit_size:
        return _normalize_size_token(explicit_size.group("size"))

    token_match = re.search(
        r"\b(?P<size>XXXS|XXS|XS|S/M|S|M/L|M|L/XL|L|XL|XXL|XXXL|one size|adjustable|osfa|free size|free-size)\b",
        query,
        flags=re.I,
    )
    if token_match:
        return _normalize_size_token(token_match.group("size"))

    return None


def _fallback_description(query: str) -> str:
    if not query:
        return ""

    cleaned = query
    cleaned = re.sub(
        r"\b(?:looking for|looking to|want(?:ing)?|need(?:ing)?|search(?:ing)? for|find(?:ing)?|for|a|an|the|new)\b",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        r"\b(?:under|below|less than|no more than|up to|max(?:imum)?|for)\s*\$?[0-9]+(?:\.[0-9]{1,2})?\b",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        r"\bsize\s*(?:is|=|:)?\s*[A-Za-z0-9/ +_-]+\b",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        r"\b(XXXS|XXS|XS|S/M|S|M/L|M|L/XL|L|XL|XXL|XXXL|one size|adjustable|osfa|free size|free-size)\b",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"[^A-Za-z0-9/ ]", " ", cleaned)
    cleaned = " ".join(cleaned.split())

    return cleaned.strip() or query.strip()


def _parse_query(query: str) -> dict:
    parsed = {"description": "", "size": None, "max_price": None}
    llm_output = ""

    try:
        client = get_groq_client()
        result = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": PARSE_QUERY_SYS_PMT},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
        )
        llm_output = result.choices[0].message.content
    except Exception:
        llm_output = ""

    description, size, max_price = _parse_llm_response(llm_output)

    if not description:
        description = _fallback_description(query)

    if size is None:
        size = _extract_size_from_query(query)

    if max_price is None:
        max_price = _extract_price_from_query(query)

    parsed["description"] = description.strip()
    parsed["size"] = size
    parsed["max_price"] = max_price
    return parsed


# ── planning loop ─────────────────────────────────────────────────────────────


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # 1. Initialize the session with _new_session().
    session = _new_session(query, wardrobe)

    # 2. Parse the user's query to extract a description, size, and max_price.
    session["parsed"] = _parse_query(query)

    # 3. Call search_listings() with the parsed parameters.
    search_results = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )

    if not search_results["success"]:
        session["error"] = "Error: unable to search items"
        return session
    if not search_results["content"]:
        session["error"] = (
            "⛔ Search results returned empty! Perhaps we don't have that item "
            "in our database.\n\n💡 Pro tip: provide a short description of the "
            'clothing you want, and clearly mark your size (e.g. with "size") and '
            ' price (e.g. with "$", "bucks", etc.)!'
        )
        return session

    session["search_results"] = search_results["content"]

    # 4. Select the item to use (e.g., the top result).
    i = 0
    success = False

    while not success and i < min(len(session["search_results"]), MAX_OUTFIT_RETRIES):
        session["selected_item"] = session["search_results"][i]
        # 5. Call suggest_outfit() with the selected item and wardrobe.
        outfit_suggestion = suggest_outfit(
            new_item=session["selected_item"], wardrobe=wardrobe
        )

        # retry once upon failure
        if not outfit_suggestion["success"]:
            outfit_suggestion = suggest_outfit(
                new_item=session["selected_item"], wardrobe=wardrobe
            )

        if outfit_suggestion["success"]:
            success = True
            session["outfit_suggestion"] = outfit_suggestion["content"]

        i += 1

    if not success:
        session["error"] = "Error: unable to generate outfit suggestion"
        return session

    # 6. Call create_fit_card() with the outfit suggestion and selected item.
    fit_card = create_fit_card(
        outfit=session["outfit_suggestion"], new_item=session["selected_item"]
    )

    # retry once upon failure
    if not fit_card["success"]:
        fit_card = create_fit_card(
            outfit=session["outfit_suggestion"], new_item=session["selected_item"]
        )

        if not fit_card["success"]:
            session["error"] = "Error: unable to generate fit card"
            return session

    session["fit_card"] = fit_card["content"]
    # 7. Return the session.
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
