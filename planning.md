# FitFindr — planning.md

---

## Tools

<!-- List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them. -->

Each tool returns a consistent structured output containing not just the main result but also the success and errors (if any). Tool return value schema:

```py
{
     "content": "any | None - If `success` is `True`, the main tool result",
     "info": "dict | None - Metadata or other info related to the content",
     "success": "bool - Whether the tool executed without any errors",
     "message": "str | None - If `success` is `False`, the error message"
}
```

Due to this shared format, each tool description below specifies the _content_ (and sometimes _info_) returned upon success, not the actual structured dictionary outlined above. For example, if a tool returns an LLM response as content, then the return type and description for that tool would be `str` and about the LLM response.

### Tool 1: `search_listings`

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

Searches through the listings database to find a list of clothing items that match the description as well as size and price constraints (if any), sorted in ascending order by relevance. The search is performed in this order, repeating with looser constraints if results are empty:

1. Keep price and size constraints
2. Drop price constraint, keep size constraint
3. Keep price constraint, drop size constraint
4. Drop price and size constraints

The search stops as soon as at least one result is retrieved or the four steps above are completed, whichever is sooner.

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

- `description` (`str`): Short descriptive phrase extracted from the user query to match against.
- `size` (`str` | `None`): Desired size of clothing, matching the format in the listing dataset.
- `max_price` (`float` | `None`): desired maximum price for the new clothing.

**What content it returns:**

<!-- Describe the return value — what fields does a result contain? -->

Type: `list[dict]`

Each `dict` is a listing item, containing:

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

**What info it returns**:

Type: `dict`

Whether any constraints were loosened to help retrieve results.

Schema:

```py
"loosened_constraints": {
     "price": bool,       # Whether price constraint existed and was loosened
     "size": bool,        # Whether size constraint existed and was loosened
}
```

**What happens if it fails or returns nothing:**

<!-- What should the agent do if no listings match? -->

In the case of an error or no-result-found return, the agent should alert the user but also gracefully salvage the situation by offering a helpful response. For example:

> Unfortunately, I couldn't find any clothing in my database matching your descriptions and constraints. But here are a few tips: check your description for spelling, use a higher price, or try a different size.

---

### Tool 2: `suggest_outfit`

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

Suggests a complete outfit given the thrifted item (the top result from `search_listings`) and the user's wardrobe.

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

- `new_item` (`dict`): The newly thrifted clothing item.
- `wardrobe` (`dict`): Contains a list of wardrobe items under an "items" key, which may be an empty list.

`new_item` example:

```json
{
  "id": "lst_028",
  "title": "Suede Chelsea Boots — Tan",
  "description": "Tan suede Chelsea boots with elastic side panels. Stacked heel. Some scuffing on the toe — can be brushed out with suede cleaner.",
  "category": "shoes",
  "style_tags": ["vintage", "classic", "western", "earth tones"],
  "size": "US 8.5",
  "condition": "fair",
  "price": 44.0,
  "colors": ["tan", "camel"],
  "brand": null,
  "platform": "poshmark"
}
```

`wardrobe` schema (the format of each item inside the key "items"):

```json
{
  "id": "string — unique identifier for this item",
  "name": "string — short description of the piece",
  "category": "string — one of: tops, bottoms, outerwear, shoes, accessories",
  "colors": ["string — list of colors this item contains"],
  "style_tags": ["string — list of style descriptors"],
  "notes": "string (optional) — any notes about fit, how the user styles it, etc."
}
```

**What content it returns:**

<!-- Describe the return value -->

Type: `str`

An outfit suggestion; if wardrobe is empty, general styling advice instead.

**What happens if it fails or returns nothing:**

<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

If the tool's own conditional mechanism of offering general advice fails due to an empty wardrobe, the tool returns no suggestions - an empty string (for example, in the event of a 400 error in the Groq API). Handle this edge case in the main agent loop by retrying once, and if it still doesn't work, resorting to the next relevant item from the call to `search_listings`. If in the rare case that no suggestion can be found for _all_ the matched items (or a specific max amount of them), a helpful error message is returned.

---

### Tool 3: `create_fit_card`

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

Generates a social media outfit caption for the newly thrifted item from `search_listings`, incorporating elements from the outfit suggestion returned by `suggest_outfit`.

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

- `outfit` (`str`): The outfit suggestion for the newly thrifted item.
- `new_item` (`dict`): The newly thrifted clothing item.

`new_item` example:

```json
{
  "id": "lst_028",
  "title": "Suede Chelsea Boots — Tan",
  "description": "Tan suede Chelsea boots with elastic side panels. Stacked heel. Some scuffing on the toe — can be brushed out with suede cleaner.",
  "category": "shoes",
  "style_tags": ["vintage", "classic", "western", "earth tones"],
  "size": "US 8.5",
  "condition": "fair",
  "price": 44.0,
  "colors": ["tan", "camel"],
  "brand": null,
  "platform": "poshmark"
}
```

**What content it returns:**

<!-- Describe the return value -->

Type: `str`

A 2-4 sentence social-media-style caption about the thrifted item.

**What happens if it fails or returns nothing:**

<!-- What should the agent do if the outfit data is incomplete? -->

Given the previous tool calls succeeded (otherwise, the agent should not reach this tool call), the agent can retry. If that doesn't work, it can show the some of the items it found and the outfit suggestion(s), giving the user the material necessary to craft the caption on their own without leaving them emptyhanded. For example:

> I can't seem to generate a caption at this moment. But look what I found that matched your constraints:
>
> \<items listed with name, size, cost, description, etc.>
>
> And I can offer you my suggestion for a great outfit that pairs well with that \<top-most item>:
>
> \<outfit suggesstion>

---

### Tool 4: `compare_price`

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

Determines the price quality of the given item based on comparable listings in the database, returning aggregate stats as reasoning.

**Input parameters:**

- `new_item` (`dict`): The newly thrifted item whose price to compare

<!-- List each parameter, its type, and what it represents -->

`new_item` example:

```json
{
  "id": "lst_028",
  "title": "Suede Chelsea Boots — Tan",
  "description": "Tan suede Chelsea boots with elastic side panels. Stacked heel. Some scuffing on the toe — can be brushed out with suede cleaner.",
  "category": "shoes",
  "style_tags": ["vintage", "classic", "western", "earth tones"],
  "size": "US 8.5",
  "condition": "fair",
  "price": 44.0,
  "colors": ["tan", "camel"],
  "brand": null,
  "platform": "poshmark"
}
```

**What content it returns:**

<!-- Describe the return value -->

Type: `dict[str, bool | float]`

A dictionary of schema:

```py
{
     "price_quality": "str - One of 'steal' (low price), 'fair' (similar "
                      "price), 'rip-off' (high price)",
     "weighted_avg":  "float - The weighed average of the prices of the other "
                      "similar items",
     "avg":           "float - The unweighted average of the prices of all the "
                      "other similar items",
     "fraction":      "float - The item's price divided by the weighted average"
}
```

**What happens if it fails or returns nothing:**

<!-- What should the agent do if the outfit data is incomplete? -->

The tool itself will never return nothing, but it can fail in the sense that the given item doesn't match with any of the other items in the database, leading to an inconclusive price comparison. The agent will report this in the session, but it will continue the planning loop since price comparison is an extra feature - not an integral part of the app.

---

## Planning Loop

**How does your agent decide which tool to call next?**

<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

The general order should be the following (the numbered steps are the happy path, and the bulleted / lettered steps are the exit conditions upon failure modes):

1. Parse the natural-language query to extract the description, size (if any), and max price (if any). Use a low-temperature LLM call first, then fall back to direct regex if response is malformatted.
2. Call `search_listings` with the extracted clothing description, size (if any), and max price (if any).
   - If the returned list is empty, mention to the user that no matching items could be found in the database, and offer tips for a successful match next time (such as correct spelling and clearly marked size and price).
3. Call `suggest_outfit` with the selected clothing item and the user's wardrobe. Initially, this selected clothing item is the first one in the list returned from `search_listings`.
   a. If suggestion returned is an empty string, retry once by calling `suggest_outfit` again with the same parameters.
   b. If that result is also empty, choose the next clothing item in the list returned from `search_listings`.
   c. Go to Step 3. The newly thrifted item is the first one whose outfit suggestion is non-empty. Repeat until the specified max fallback item count is reached or all the list items run out, whichever is first.
   d. If all fails, return a helpful error message that a suggestion cannot be made.
4. Call `create_fit_card` with the suggested outfit and newly thrifted item.
   a. If the returned caption is empty, retry once with the same exact call.
   b. If that fails, return a helpful error message stating that the outfit caption could not be generated.
5. Output the final caption to the user.

---

## State Management

**How does information from one tool get passed to the next?**

<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

A session dictionary will be used to enforce a single source of truth. The prominent keys are:

| Session Key         | Initial Value | Description                                                              |
| ------------------- | ------------- | ------------------------------------------------------------------------ |
| `search_results`    | `[]`          | Stores the list of items returned by `search_listings`                   |
| `selected_item`     | `{}`          | Set to `search_results[i]`, starting with `i=0` (the most relevant item) |
| `outfit_suggestion` | `""`          | Stores the outfit suggestion returned by `suggest_outfit`                |
| `fit_card`          | `""`          | Stores the final social media caption returned by `create_fit_card`      |
| `price_comparison`  | `{}`          | Price comparison details returned by `compare_price`                     |

General state management (some steps hidden for concision):

1. Call `search_listings`. Store return value in `search_results`.
2. While `outfit_suggestion` is empty and iteration count is below a certain max:
   a. Set `selected_item` to `search_results[i]` (`i` starting at `0`).
   b. Call `suggest_outfit` with `selected_item` a param. Store return value in `outfit_suggestion`.
3. Call `create_fit_card` with `selected_item` and `outfit_suggestion` as params. Store return value in `fit_card`.
4. Call `compare_price` with `selected_item`. Store return value in `price_comaparison`.

---

## Error Handling

<!-- For each tool, describe the specific failure mode you're handling and what the agent does in response. -->

The agent's error handling is graceful - the tools won't throw exceptions. Rather, they will return error messags as strings.

| Tool              | Failure Mode                    | Agent Response                                                                           |
| ----------------- | ------------------------------- | ---------------------------------------------------------------------------------------- |
| `search_listings` | No results match the query      | Auto-retry with looser constraints; give user tips for a better match next time          |
| `suggest_outfit`  | Wardrobe is empty               | Give general styling advice                                                              |
| `suggest_outfit`  | Outfit is missing or incomplete | Retry once; go to next relevant item; repeat; if all fails, return helpful error message |
| `create_fit_card` | Caption returned is empty       | Retry once; return helpful error message                                                 |
| `compare_price`   | No comparable items             | Return helpful error message                                                             |

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

```
User query
    │
    v
Planning Loop
    |
    |--> search_listings(description, size, max_price)
    │       │  FAILURE: search_results=[]
    │       |---> Remove price --|--> Remove size --|--> Remove both ----|
    |       |     constraint     |    constraint    |     constraints    |
    │       │                    |                  |                    |
    |       |            SUCCESS |          SUCCESS |            SUCCESS |
    |       |---------<----------|--------<---------|---------<----------|
    |       |                                                            |
    |       |                                             RETURN <-------| FAIL
    │       v                                             (Give user tips
    │   Session: selected_item=search_results[0];         for better result)
    |       |    search_results=[item0, item1, ...]
    │       │
    |--> suggest_outfit(selected_item, wardrobe) <--------|
    |       |                                             |
    |       |                                    i += 1;
    |   Session: outfit_suggestion="..."         selected_item=search_results[i]
    |       |  FAILURE                                    |
    |       |                                 FAIL        |
    |       |---> Retry once -----------------------------|
    |       |     | |                          Items left in search_results, AND
    |       |     | |  FAIL                    Iter count below max
    |       |     | |
    |       |     | |  Depleted search_results, OR
    |       |     | |  Iter count hit max
    |       |     | |----------------------------> RETURN helpful error message
    |       |-----|
    |       |  SUCCESS
    │       |
    |--> create_fit_card(outfit_suggestion, selected_item)
    |       │
    |   Session: fit_card="..."
    |       |  FAILURE
    |       │--> Retry once ---------------------> RETURN helpful error message
    |       |       |                FAIL
    |       |-------|
    |       |  SUCCESS
    |       |
    |--> compare_price(selected_item)
            |  FAILURE
            |------------------------------------> RETURN helpful error message
            |       |                FAIL
            |-------|
            |  SUCCESS
            v
        RETURN session
```

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

I plan to use GitHub Copilot and Gemini Code Assist for this milestone. I'll give it the "Tools" section of `planning.md`, which spells out the implementation details of each tool and will help the AI to generate the code I intend. When I prompt the AI one-by-one, I expect it to produce the implementations of each tool in separate phases, allowing me to test and bebug each one before starting a new one. I'll verify that the output matches my spec by performing line-by-line review of the code, asking the AI any questions about the code if I have any. Then, I'll test each tool to see that it works as intended, reprompting the AI if necessary.

**Milestone 4 — Planning loop and state management:**

I'll again use GitHub Copilot and Gemini Code Assist for this milestone. But this time, I'll give it the "State Management", "Error Handling", and "Architecture" sections of `planning.md`, which will help the AI properly understand my expectations and generate the planning loop with proper state management. I expect it to produce code that contains a robust agentic planning loop using Groq's tool API as well as the appropriately variables to manage state. To verify the AI's output, I will scan the code generated line-by-line to pick out any glaring deviations, then test the whole system multiple times for a final sanity check. I will reprompt the AI if any adjustments are necessary.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under \$30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

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

**Step 4**:

```py
compare_price(
     new_item=<top result>,
)
```

- `<top result>` comes from `search_listings` in Step 1

Result:

```
<short price comparison result>
```

Example:

```
{
     "price_quality": "fair",
     "weighted_avg": 0.0,
     "avg": 0.0
}
```

**Final output to user:**

<!-- What does the user actually see at the end? -->

The user sees the final TikTok/Instagram-friendly caption and price comparison result.
