"""
app.py

Gradio interface for FitFindr.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr

from scripts.agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
from utils.format import format_listing_item

# ── helpers ───────────────────────────────────────────────────────────────────


def _format_debug(session: dict) -> str:
    parsed_txt = (
        f"Description: {session["parsed"]["description"]}\n"
        f"Max price: {session["parsed"]["max_price"]}\n"
        f"Size: {session["parsed"]["size"]}"
    )
    price_comp_txt = (
        (
            f"Weighted average: {session["price_comparison"]["weighted_avg"]}\n"
            f"Unweighted average: {session["price_comparison"]["avg"]}\n"
            f"Fraction (item prize / weighted average): {session["price_comparison"]["fraction"]:.4f}"
        )
        if session["price_comparison"] != {}
        else "None"
    )
    search_res = session["search_results_debug"]
    search_res_txt = "\n\n".join(
        [f"{len(search_res)} search results"]
        + [
            format_listing_item(res, include_id=True) + f"\n**Score**: {score}"
            for score, res in search_res
        ]
    )
    return (
        "-- PARSED TEXT -----------------------------------------------------------------\n\n"
        f"{parsed_txt}\n\n"
        "-- PRICE COMPARISON ------------------------------------------------------------\n\n"
        f"{price_comp_txt}\n\n"
        "-- SEARCH RESULTS --------------------------------------------------------------\n\n"
        f"{search_res_txt}\n\n"
    )


# ── query handler ─────────────────────────────────────────────────────────────


def handle_query(
    user_query: str, wardrobe_choice: str
) -> tuple[str, str, str, str]:  # ☑️
    """
    Called by Gradio when the user submits a query.

    Args:
        user_query:      The text the user typed into the search box.
        wardrobe_choice: Either "Example wardrobe" or "Empty wardrobe (new user)".

    Returns:
        A tuple of four strings:
            (listing_text, outfit_suggestion, fit_card, debug)
        Each string maps to one output panel in the UI.

    1. Guards against an empty query (returning early with an error message).
    2. Selects the wardrobe based on wardrobe_choice.
    3. Calls run_agent() with the query and selected wardrobe.
    4. If session["error"] is set, returns the error in the first panel
        and empty strings for the other two.
    5. Formats session["price_comparison"] into a readable string.
    6. Formats session["selected_item"] into a readable string.
    7. Format debug info to a readable string.
    8. Returns the formatted listing string, session["outfit_suggestion"],
       session["fit_card"], and the formatted price comparison.
    """
    # 1. Guard against an empty query (return early with an error message).
    if not user_query:
        return "The query cannot be empty!", "", "", ""

    # 2. Select the wardrobe based on wardrobe_choice.
    wardrobe = (
        get_example_wardrobe()
        if wardrobe_choice == "Example wardrobe"
        else get_empty_wardrobe()
    )

    # 3. Call run_agent() with the query and selected wardrobe.
    session = run_agent(user_query, wardrobe)

    # 4. If session["error"] is set, return the error in the first panel
    #    and empty strings for the other two.
    if session["error"]:
        return session["error"], "", "", _format_debug(session)

    # 5. Format session["price_comparison"] into a readable string.
    price_comparison_text = ""

    if session["price_comparison"] != {}:
        quality = session["price_comparison"]["price_quality"]
        quality_text = f"it's at a fair price" if quality == "fair" else f"a {quality}"
        emoji = "👍" if quality == "fair" else ("🤑" if quality == "steal" else "⚠️")
        price_comparison_text = f"{emoji} This item seems like {quality_text}!\n\n"

    # 6. Format session["selected_item"] into a readable string.
    loose_price = session["loosened_constraints"]["price"]
    loose_size = session["loosened_constraints"]["size"]
    loose_both = loose_price and loose_size
    both = "price and size" if loose_both else ""
    one = "price" if loose_price else "size"
    loose_msg = (
        f"We loosened the {both or one} constraint{"s" if loose_both else ""} to help with the search.\n\n"
        if loose_price or loose_size
        else ""
    )
    listing_text = (
        loose_msg
        + price_comparison_text
        + format_listing_item(session["selected_item"])
    )

    # 7. Format debug info to a readable string.
    debug = _format_debug(session)

    # 8. Return the formatted listing string, session["outfit_suggestion"],
    #    session["fit_card"], and the formatted price comparison.
    return listing_text, session["outfit_suggestion"], session["fit_card"], debug


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",  # deliberate no-results test
]


def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=1,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        with gr.Accordion("🐛 Debug Info", open=False):
            debug_output = gr.Textbox(
                label="Full Debug Dump",
                lines=15,
                interactive=False,
                visible=True,
                elem_id="debug-dump",
            )

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output, debug_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output, debug_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch(
        css="#debug-dump textarea { font-family: monospace; font-size: 0.85rem; }",
    )
