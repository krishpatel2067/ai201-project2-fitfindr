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

`new_item` example:

```
{
     "id": "lst_028",
     "title": "Suede Chelsea Boots — Tan",
     "description": "Tan suede Chelsea boots with elastic side panels. Stacked heel. Some scuffing on the toe — can be brushed out with suede cleaner.",
     "category": "shoes",
     "style_tags": ["vintage", "classic", "western", "earth tones"],
     "size": "US 8.5",
     "condition": "fair",
     "price": 44.00,
     "colors": ["tan", "camel"],
     "brand": null,
     "platform": "poshmark"
}
```

`wardrobe` schema (the format of each item inside the key "items"):

```
{
     "id": "string — unique identifier for this item",
     "name": "string — short description of the piece",
     "category": "string — one of: tops, bottoms, outerwear, shoes, accessories",
     "colors": ["string — list of colors this item contains"],
     "style_tags": ["string — list of style descriptors"],
     "notes": "string (optional) — any notes about fit, how the user styles it, etc."
}
```

**What it returns:**

<!-- Describe the return value -->

Type: `str`

A non-empty string with outfit suggestions. If the wardrobe is empty, general styling advice instead.

**What happens if it fails or returns nothing:**

<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

If the tool's own conditional mechanism of offering general advice fails due to an empty wardrobe, the tool returns no suggestions - an empty string (for example, in the event of a 400 error in the Groq API). Handle this edge case in the main agent loop by retrying once, and if it still doesn't work, resorting to the next relevant item from the call to `search_listings`. If in the rare case that no suggestion can be found for _all_ the matched items (or a specific max amount of them), the agent can offer helpful tips on getting a better answer, e.g.:

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

`new_item` example:

```
{
     "id": "lst_028",
     "title": "Suede Chelsea Boots — Tan",
     "description": "Tan suede Chelsea boots with elastic side panels. Stacked heel. Some scuffing on the toe — can be brushed out with suede cleaner.",
     "category": "shoes",
     "style_tags": ["vintage", "classic", "western", "earth tones"],
     "size": "US 8.5",
     "condition": "fair",
     "price": 44.00,
     "colors": ["tan", "camel"],
     "brand": null,
     "platform": "poshmark"
}
```

**What it returns:**

<!-- Describe the return value -->

Type: `str`

A 2-4 sentence Instagram/TikTok-style caption, or an error message if the caption could not be generated.

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

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

The general order should be the following (the numbered steps are the happy path, and the bulleted / lettered steps are the exit conditions upon failure modes):

1. Check the user's query for adequacy: the required clothing description and relevance to the app's goal.
   - Do not make any tool calls for inadequate queries. Only generate the final response, depending on the case below.
   - If the user's query is vague, ask for clarification, especially asking for a description and optionally size and maximum price.
   - If the user's query is irrelevant, state that and your domain of expertise.
2. Call `search_listings` with the extracted clothing description, size (if any), and maximum price (if any).
   - If the returned list is empty, mention to the user that no matching items could be found in the database. Additionally, offer tips for a successful match next time, e.g. correct spelling, different size and/or price, etc.
3. Call `suggest_outfit` with the chosen clothing item and the user's wardrobe. Initially, this chosen clothing item is the first one in the list returned from `search_listings`.
   a. If suggestion returned is an empty string, retry once by making the same tool call to `suggest_outfit` again.
   b. If that result is also empty, choose the next clothing item in the list returned from `search_listings`.
   c. Go to Step 3. The newly thrifted item is the first one whose outfit suggestion is non-empty. Repeat until the specified max fallback item count is reached or all the list items run out, whichever is first.
   d. Mention that you can't make an outfit suggestion. Suggest to the user ways to improve the outcome next time: adding items to their wardrobe, tweaking their original description, etc.
4. Call `create_fit_card` with the suggested outfit and newly thrifted item.
   a. If the returned caption is empty, retry once with the same exact call.
   b. If that fails, mention that you were unable to generate a social media outfit caption. In addition, reveal the newly thrifted item information and outfit suggestion to them.
5. Output the final caption to the user.

However, the system prompt shouldn't include all these details to leave the agent with some flexibility to reason.

---

## State Management

**How does information from one tool get passed to the next?**

<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

| Variable            | Initial Value | Description                                                                 |
| ------------------- | ------------- | --------------------------------------------------------------------------- |
| `relevant_listings` | `[]`          | Stores the list of items returned by `search_listings`                      |
| `selected_item`     | `{}`          | Set to `relevant_listings[i]`, starting with `i=0` (the most relevant item) |
| `outfit_suggestion` | `""`          | Set to the return value of `suggest_outfit`                                 |
| `fit_card`          | `""`          | Final social media caption returned by `create_fit_card`                    |

General state management (some steps hidden for concision):

1. Call `search_listings`. Store return value in `relevant_listings`.
2. While `outfit_suggestion` is empty and iteration count is below a certain max:
   a. Set `selected_item` to `relevant_listings[i]` (`i` starting at `0`).
   b. Call `suggest_outfit` with `selected_item` a param. Store return value in `outfit_suggestion`.
3. Call `create_fit_card` with `selected_item` and `outfit_suggestion` as params. Store return value in `fit_card`.

---

## Error Handling

<!-- For each tool, describe the specific failure mode you're handling and what the agent does in response. -->

Each failure mode is first acknowledged to the user, then the items from `Agent Response` apply.

| Tool              | Failure Mode                    | Agent Response                                                                                |
| ----------------- | ------------------------------- | --------------------------------------------------------------------------------------------- |
| `search_listings` | No results match the query      | Auto-retry with looser constraints [TODO]; give user tips for a better match next time        |
| `suggest_outfit`  | Wardrobe is empty               | Give general styling advice                                                                   |
| `suggest_outfit`  | Outfit is missing or incomplete | Retry once; go to next relevant item; repeat; if all fails, give user tips for better outcome |
| `create_fit_card` | Caption returned is empty       | Retry once; if it fails, reveal to user some relevant items and outfit suggestion             |

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
    │       │  FAILURE: search_listings=[]
    │       |------------------------------> RETURN
    │       │                                (Give user tips for better result)
    │       v
    │   Session: selected_item=search_listings[0];
    |       |    search_listings=[item0, item1, ...]
    │       │
    |--> suggest_outfit(selected_item, wardrobe) <--------|
    |       |                                             |
    |       |                                  i += 1;
    |   Session: outfit_suggestion="..."       selected_item=search_listings[i]
    |       |  FAILURE: outfit_suggestion=""              |
    |       |                                 FAIL        |
    |       |---> Retry once -----------------------------|
    |       |     | |                        Items left in search_listings, AND
    |       |     | |  FAIL                  Iter count below max
    |       |     | |
    |       |     | |  Depleted search_listings, OR
    |       |     | |  Iter count hit max
    |       |     | |---------------------------> RETURN
    |       |-----|                               (Give tips for better result)
    |       |  SUCCESS
    │       |
    |--> create_fit_card(outfit_suggestion, selected_item)
            │
        Session: fit_card="..."
            |  FAILURE: fit_card=""
            │--> Retry once -------------------> RETURN
            |       |                FAIL        (Reveal some search_listings;)
            |-------|                            (Show outfit suggestion;)
            |  SUCCESS
            v
        RETURN fit_card
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

I plan to use Claude Code for this milestone. I'll give it the "Tools" section of `planning.md`, which spells out the implementation details of each tool and will help the AI to generate the code I intend. When I prompt the AI one-by-one, I expect it to produce the implementations of each tool in separate phases, allowing me to test and bebug each one before starting a new one. I'll verify that the output matches my spec by performing line-by-line review of the code, asking the AI any questions about the code if I have any. Then, I'll test each tool to see that it works as intended, reprompting the AI if necessary.

**Milestone 4 — Planning loop and state management:**

I'll again use Claude Code for this milestone. But this time, I'll give it the "State Management", "Error Handling", and "Architecture" sections of `planning.md`, which will help the AI properly understand my expectations and generate the planning loop with proper state management. I expect it to produce code that contains a robust agentic planning loop using Groq's tool API as well as the appropriately variables to manage state. To verify the AI's output, I will scan the code generated line-by-line to pick out any glaring deviations, then test the whole system multiple times for a final sanity check. I will reprompt the AI if any adjustments are necessary.

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
