# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: `search_listings`

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

Searches through a database to find a list of clothing items that match the description as well as size and price constraints (if any), sorted in ascending order by relevance.

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

- `description` (`str`): Short descriptive phrase extracted from the user query to match against.
- `size` (`str` | `None`): The size of the clothing. Valid formats: "S", "S/M", "US 9", "W28", "One Size" with some having paretheses (e.g. "One Size (adjustable)" or "XL (oversized)").
- `max_price` (`float` | `None`): The user's desired maximum price for the new clothing.

**What it returns:**

<!-- Describe the return value — what fields does a result contain? -->

Type: `list[dict]`

Each `dict` contains:

```py
{
     "id": str,               # unique clothing item ID, e.g. "lst_001"
     "title": str,            # user-friendly item title, e.g. "Y2K Baby Tee — Butterfly Print"
     "description": str,      # short description (~150 chars max)
     "category": str,         # item category, e.g. "tops", "bottoms", "outerwear", "shoes", "accessories"
     "style_tags": list[str], # list of style descriptors, e.g. ["vintage", "grunge", "90s"]
     "size": str,             # size of piece; formats: "S", "S/M", "US 9", "W28", "One Size"
                              # some have paretheses (e.g. "One Size (adjustable)" or "XL (oversized)")
     "condition": str,        # condition of item; one of: "fair", "good", "excellent"
     "price": float,          # price of item, e.g. 18.00
     "colors": list[str],     # list of colors item has, e.g. ["white", "pink", "purple"]
     "brand": str | None,     # item brand (if known), e.g. "Levi's"
     "platform": str          # platform on which item is listed, e.g. "depop"
}
```

**What happens if it fails or returns nothing:**

<!-- What should the agent do if no listings match? -->

In the case of an error or no-result-found return, the agent should alert the user but also gracefully salvage the situation by offering a helpful response. For example:

> Unfortunately, I couldn't find any clothing in my database matching your descriptions and constraints. But here are a few tips: check your description for spelling, use a higher price, or try a different size.

---

### Tool 2: suggest_outfit

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

Suggests 1-2 complete outfits given the thrifted item (the top from `search_listings`) and the user's wardrobe.

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

- `new_item` (`dict`): The newly thrifted clothing item.
- `wardrobe` (`dict`): Contains a list of clothing in the user's wardrobe under an "items" key, which may be an empty list.

**What it returns:**

<!-- Describe the return value -->

Type: `str`

A non-empty string with outfit suggestions. If the wardrobe is empty, general styling advice instead.

**What happens if it fails or returns nothing:**

<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

If the tool's own fallback mechanism of offering general advice fails due to an empty wardrobe, the tool returns no suggestions. Handle this edge case in the main agent loop by retrying once, and if it still doesn't work, resorting to the next relevant item from the call to `search_listings`. If in the rare case that no suggestion can be found for _all_ the matched items (or a specific max amount of them), the agent can offer helpful tips on getting a better answer, e.g.:

> Sadly, I couldn't come up with an outfit suggestion for any of the items I found matching your constraints. Try adding items to your wardrobe, or tweaking or original constraints.

---

### Tool 3: create_fit_card

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

Generates a short, social-media-shareable outfit caption for the newly thrifted item from `search_listings` and the outfit suggestion from `suggest_outfit`.

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

- `outfit` (`str`): The outfit suggestion matching the user's wardrobe.
- `new_item` (`dict`): The newly thrifted clothing item.

**What it returns:**

<!-- Describe the return value -->

Type: `str`

A 2-4 sentence Instagram/TikTok-style caption, or an error message if the caption could not be generated.

**What happens if it fails or returns nothing:**

<!-- What should the agent do if the outfit data is incomplete? -->

Given the previous tool calls succeeded (otherwise, the agent should not reach this tool call), the agent can show the some of the items it found and the outfit suggestion(s), giving the user the material necessary to craft the caption on their own without leaving them emptyhanded. For example:

> I can't seem to generate a caption at this moment. But look what I found that matched your constraints:
>
> \<items listed with name, size, cost, description, etc.>
>
> And I can offer you my suggestion for a great outfit that pairs well with that \<top-most item>:
>
> \<outfit suggesstion>

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**

<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool            | Failure mode                          | Agent response |
| --------------- | ------------------------------------- | -------------- |
| search_listings | No results match the query            |                |
| suggest_outfit  | Wardrobe is empty                     |                |
| create_fit_card | Outfit input is missing or incomplete |                |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**

<!-- What does the agent do first? Which tool is called? With what input? -->

Find the desired clothing, if it exists, via a call to the tool `search_listings`:

```py
search_listings(
     description="vintage graphic tee",
     size=None,                            # user doesn't mention size
     max_price=30.0
)
```

Result (assuming matches are found), sorted by relevance in descending order:

```
[
     { <top result - most relevant clothing item> },
     {     <2nd most relevant clothing item>      },
                         ...
     {      <least relevant clothing item>        },
]
```

Example top result:

```
<Faded Band Tee — $22, Depop, Good condition>
```

**Step 2:**

<!-- What happens next? What was returned from step 1? What tool is called now? -->

Suggest an outfit via a tool call to `suggest_outfit`:

```py
suggest_outfit(
     new_item=<top result>
     wardrobe=<wardrobe>
)
```

- `<top result>` comes directly from the `search_listings` tool call in Step 1
- `<wardrobe>` is loaded from the helper function `get_example_wardrobe` in `utils/data_loader.py`

Result:

```
<outfit suggestion in natural language>
```

Example:

```
Pair this with your wide-leg jeans and platform Docs for a classic 90s grunge look. Roll the sleeves once and tuck the front corner slightly for shape.
```

**Step 3:**

<!-- Continue until the full interaction is complete -->

```py
create_fit_card(
     new_item=<top result>,
     outfit=<suggestion>,
)
```

- `<top result>` comes from `search_listings` in Step 1
- `<suggestion>` comes from `suggest_outfit` in Step 2

Result:

```
<short social-media-friendly caption about the new item and outfit>
```

Example:

```
thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look in my stories
```

**Final output to user:**

<!-- What does the user actually see at the end? -->

The user sees the final TikTok/Instagram-friendly caption describing the newly acquired item and how it fits into their current wardrobe and outfit.
