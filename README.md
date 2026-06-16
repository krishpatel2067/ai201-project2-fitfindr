# FitFindr

It's not easy to find new clothes of the right size, price, and aesthetics - let alone know how to incorporate them with your existing clothes. Meet FitFindr, the one-stop-shop for finding the right clothes to thrift as well as getting AI-powered outfit suggestions and expressive fit cards (captions) worthy of posting on social media!

---

## Demo

---

## Tech Stack

| Component     | Technology                                                                    |
| ------------- | ----------------------------------------------------------------------------- |
| Database      | Locally stored JSON files                                                     |
| Tools         | Groq `llama-3.3-70b-versatile` LLM model; Vanilla Python (tokenization, etc.) |
| Planning loop | Vanilla Python (conditional logic)                                            |
| Interface     | Gradio                                                                        |
| Unit testing  | pytest                                                                        |

<!-- My Claude Code usage totally didn't max out... -->

**AI tools leveraged**: GitHub Copilot, Gemini Code Assist

**Tokenization**: `search_listings` and `compare_price` (described in the [Tool Inventory](#Tool-Inventory) section below) both use tokenization with stop words filtering and keyword matching to retrieve clothing item matches. This ensures a fully local, fast, and deterministic search mechanism, but it does come with its own limitations (described in the [Limitations][#Limitations] section below).

---

## Project Structure

```
root/
|-- data/
│   |-- listings.json          # 40 mock secondhand listings
│   |-- wardrobe_schema.json   # Wardrobe format + example wardrobe
|-- utils/
│   |-- data_loader.py         # Helper functions for loading the data
|   |-- format.py              # Helper functions for formatting output
|   |-- llm.py                 # Helper functions form managing the Groq LLM API
|-- tests/
|   |-- test_tools.py          # Suite of unit tests for the tools
|-- scripts/
|   |-- agent.py               # Main planning loop that executes tools
|   |-- tools.py               # Tool implementations that the agent can call
|-- app.py                     # Gradio UI manager and app driver
|-- conftest.py                # Ensure local module imports work properly in pytest
|-- planning.md                # Planning steps and specs before implementation
|-- requirements.txt           # Python dependencies
```

---

## Setup

1. Create a virtual environemnt:

```bash
python -m venv .venv
```

2. Activate the virtual environment:

```bash
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy the `.env.example` template into a `.env`, and set the Groq API key (freely available at [console.groq.com](https://console.groq.com)):

```bash
cp .env.example .env
```

```
GROQ_API_KEY=your_key_here
```

5. Run the app:

```bash
python app.py       # replace `python` with `gradio` for hot-reload
```

[Optional] Run the unit tests:

```bash
pytest tests/
```

## Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

An example listing:

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

## Wardrobe

`data/wardrobe_schema.json` defines the format that the agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items
- `empty_wardrobe`: a starting template for a new user

The wardrobe schema:

```json
"items": [
  {
    "id": "string — unique identifier for this item",
    "name": "string — short description of the piece",
    "category": "string — one of: tops, bottoms, outerwear, shoes, accessories",
    "colors": ["string — list of colors this item contains"],
    "style_tags": ["string — list of style descriptors"],
    "notes": "string (optional) — any notes about fit, how the user styles it, etc."
  }
]
```

---

## Tool Inventory

All the tools return structured dictionaries following a standard format:

| Key       | Value Type | Returned (When) | Description                                  |
| --------- | ---------- | --------------- | -------------------------------------------- |
| `content` | `any`      | `success=True`  | The main tool result                         |
| `info`    | `dict`     | Tool-dependent  | Metadata or other info related to `content`  |
| `success` | `bool`     | Always          | Whether the tool executed without any errors |
| `message` | `str`      | `success=False` | The error message                            |

Thus, each tool's output describes the `content` (and `info` when available) upon success.

### Tool 1 - `search_listings`

Searches through the listings database to find a list of clothing items that match the description as well as size and price constraints (if any), sorted in ascending order by relevance. The search is performed in this order, repeating with looser constraints if results are empty:

1. Keep price and size constraints
2. Drop price constraint, keep size constraint
3. Keep price constraint, drop size constraint
4. Drop price and size constraints

The search stops as soon as at least one result is retrieved or the four steps above are completed, whichever is sooner.

### Input

| Parameter     | Type    | Required | Description                                                          |
| ------------- | ------- | -------- | -------------------------------------------------------------------- |
| `description` | `str`   | Yes      | Short phrase extracted from the user query to match against          |
| `size`        | `str`   | No       | Desired size of clothing, matching the format in the listing dataset |
| `max_price`   | `float` | Yes      | Desired maximum price for the new clothing                           |

### Output

| Key       | Type         | Description                                                       |
| --------- | ------------ | ----------------------------------------------------------------- |
| `content` | `list[dict]` | A list of clothing items each in [this format](#Listings-Dataset) |
| `info`    | `dict`       | What constraints existed and were loosened                        |

`content` is an empty list when no matching items were found.

`info` schema:

```py
"loosened_constraints": {
     "price": bool,
     "size": bool,
}
```

### Tool 2 - `suggest_outfit`

Suggests a complete outfit given the thrifted item (the top result from `search_listings`) and the user's wardrobe.

### Input

| Parameter  | Type   | Required | Description                                                                        |
| ---------- | ------ | -------- | ---------------------------------------------------------------------------------- |
| `new_item` | `dict` | Yes      | The newly thrifted clothing item in [this format](#Listings-Dataset)               |
| `wardrobe` | `dict` | Yes      | Contains a list of wardrobe items under an "items" key, which may be an empty list |

### Output

| Key       | Type  | Description                                                                |
| --------- | ----- | -------------------------------------------------------------------------- |
| `content` | `str` | An outfit suggestion; if wardrobe is empty, general styling advice instead |

### Tool 3 - `create_fit_card`

Generates a social media outfit caption for the newly thrifted item from `search_listings`, incorporating elements from the outfit suggestion returned by `suggest_outfit`.

### Input

| Parameter  | Type   | Required | Description                                                          |
| ---------- | ------ | -------- | -------------------------------------------------------------------- |
| `outfit`   | `str`  | Yes      | The outfit suggestion for the newly thrifted item                    |
| `new_item` | `dict` | Yes      | The newly thrifted clothing item in [this format](#Listings-Dataset) |

### Output

| Key       | Type  | Description                                                       |
| --------- | ----- | ----------------------------------------------------------------- |
| `content` | `str` | A 2-4 sentence social-media-style caption about the thrifted item |

### Tool 4 - `compare_price`

Determines the price quality of the given item based on comparable listings in the database, returning aggregate stats as reasoning. More info in the [Price Comparison Tool](#Price-Comparison-Tool) section.

### Input

| Parameter  | Type   | Required | Description                                    |
| ---------- | ------ | -------- | ---------------------------------------------- |
| `new_item` | `dict` | Yes      | The newly thrifted item whose price to compare |

### Output

| Key       | Type                       | Description              |
| --------- | -------------------------- | ------------------------ |
| `content` | `dict[str, bool \| float]` | Price comparison results |

`content` schema (all keys always present):

| Key             | Type    | Description                                           |
| --------------- | ------- | ----------------------------------------------------- |
| `price_quality` | `str`   | One of "steal", "fair", "rip-off"                     |
| `weighted_avg`  | `float` | Weighed average of the other similar items' prices    |
| `avg`           | `float` | Unweighted average of the other similar items' prices |
| `fraction`      | `float` | The item's price divided by the weighted average      |

---

## Planning Loop

The planning loop does not use Groq's tool calling API because conditional logic is sufficient for the one-way tool-calling flow:

```
search_listings --> suggest_outfit --> create_fit_card --> compare_price
```

1. Parse the natural-language query to extract the description, size, and max price. Use a low-temperature LLM call first, then fall back to direct regex if the LLM response is malformatted.
2. Call `search_listings` with the extracted clothing details. If the returned list is empty, mention to the user that no matching items could be found in the database, and offer tips for a successful match next time (such as correct spelling and clearly marked size and price).
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

## State Mangement

A `session` dictionary is used to manage the storage as well as flow of state from one tool to another and to the interface. The prominent keys are:

| Session Key         | Initial Value | Description                                                              |
| ------------------- | ------------- | ------------------------------------------------------------------------ |
| `search_results`    | `[]`          | Stores the list of items returned by `search_listings`                   |
| `selected_item`     | `{}`          | Set to `search_results[i]`, starting with `i=0` (the most relevant item) |
| `outfit_suggestion` | `""`          | Stores the outfit suggestion returned by `suggest_outfit`                |
| `fit_card`          | `""`          | Stores the inal social media caption returned by `create_fit_card`       |
| `price_comparison`  | `{}`          | Price comparison details returned by `compare_price`                     |

Other keys are stored to manage input, debug info, and errors.

---

## Error Handling

The agent's error handling is graceful - the tools don't throw exceptions. Rather, they return error messages as strings.

| Tool              | Failure Mode                    | Agent Response                                                                           |
| ----------------- | ------------------------------- | ---------------------------------------------------------------------------------------- |
| `search_listings` | No results match the query      | Auto-retry with looser constraints; give user tips for a better match next time          |
| `suggest_outfit`  | Wardrobe is empty               | Give general styling advice                                                              |
| `suggest_outfit`  | Outfit is missing or incomplete | Retry once; go to next relevant item; repeat; if all fails, return helpful error message |
| `create_fit_card` | Caption returned is empty       | Retry once; return helpful error message                                                 |
| `compare_price`   | No comparable items             | Return helpful error message                                                             |

Example of the handling when no results are returned from `search_listings`:

Query:

> designer ballgown size XXS under $5

Top listing found:

> ⛔ Search results returned empty! Perhaps we don't have that item in our database.
>
> 💡 Pro tip: provide a short description of the clothing you want, check your spelling, and clearly mark your size (e.g. with "size") and price (e.g. with "$", "bucks", etc.)!

The outfit idea and fit card panels remain empty since the planning loop returns early with this error condition.

---

## Testing Failure Modes

### Empty Search Results

```bash
python -c "from scripts.tools import search_listings;
print(search_listings('designer ballgown', size='XXS', max_price=5))"
```

Structured output:

```
{
  'content': [],
  'info': {
    'loosened_constraints': {
      'price': True,
      'size': True
    }
  },
  'success': True
}
```

Even after loosening both constraints, this impossible item couldn't be found, and so an empty list was gracefully returned.

### Empty Wardrobe

```bash
python -c "from scripts.tools import search_listings, suggest_outfit
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(suggest_outfit(results['content'][0][1], get_empty_wardrobe()))"
```

Content output:

> Pair this rad vintage graphic tee with some high-waisted mom jeans and chunky sneakers for a laid-back, retro-inspired look that's perfect for a casual day out. The slightly boxy fit will add to the overall relaxed vibe, so just throw it on and rock that effortless grunge style.

When the user wardrobe is empty, `suggest_outfit` falls back to general styling advice instead of personalized wardrobe advice.

### Empty Outfit

```bash
python -c "from scripts.tools import search_listings, create_fit_card
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(create_fit_card('', results['content'][0][1]))"
```

Structured output:

```
{
  'success': False,
  'message': 'Error: outfit suggestion is empty; cannot generate caption.'
}
```

The function gracefully returns an error message without throwing an exception.

---

## Features

### Multi-Method Query Parsing

A natural language user query like "vintage graphic tee for under $30" must be parsed to extract three elements: description ("vintage graphic tee"), size (none specified), and maximum price ("$30").

The planning loop first makes an LLM call using the same model (`llama-3.3-70b-versatile`) as `suggest_outfit` and `create_fit_card`. However, this model doesn't support structured outputs, so the temperature was set to 0 for a highly deterministic and strictly formatted output. Regex is then used to extract the three elements by the expected format with some leeway.

However, if the LLM call fails completely or returns a malformatted response, the original query is parsed via regex with common indicators like "under" for price and "size" or size.

This two-method mechanism is used for one key reason: regex is rigid at parsing format-less strings (like raw user queries) and is often less accurate as a result, but LLMs are more flexible and, thus, offer more accurate parsing. There is an acceptable downside, however, which the [Limitations](#Limitations) section discusses.

A demo showing the advantage of LLM-based parsing:

Query:

> vintage graphic tee of size small under 50 bucks

LLM parsing:

Description: `"vintage graphic tee"`
Price: `50`
Size: `"S"`

Regex alone (unless overfitted) wouldn't have been able to extract "small" (instead of "S") and "bucks" (instead of "$").

---

## Bonus Features

### Price Comparison Tool

Users benefit from knowing whether the price of an item is fair compared to the prices of similar items on the market, which is what the `compare_price` tool helps accomplish.

It uses tokenization to find comparable items and additive scoring to quantify comparability. However, unlike `search_listings`, tokenization in `compare_price` is only reserved for the name, description, and size of the clothing (which don't follow a strict format). The rest of the fields rely on set intersection or direct keyword matching. The reason is that this tool benefits from stricter matching to ensure prices of only comparable items are considered the most. A more lenient matching mechanism like in `search_listings` would dilute the importance of comparable listings by introducing loosely comparable ones.

The calculated comparability score for each item is used to calculated the weighted average of all the prices: the higher the score, the higher the weight. The price quality is

- `"fair"` if the given item's price is within 25% (above or below) of the weighted average.
- a `"steal"` if the given item's price is below 25% of the weighted average.
- a `"rip-off"` if the given item's price is above 25% of the weighted average.

Finally, this price quality, weighted _and_ unweighted averages, and the fraction `given item price / weighted average` are returned. The interface only shows the price quality, but the debug logs surface the rest for sanity checks and reasoning.

### Auto-Retry with Looser Constraints in `search_listings`

Implemented into the tool `search_listings`, this mechanism simulates what shoppers already do in the real world: start off with an ideal match (tightest constraints), then slowly broaden your search (looser constraints) if you can't find anything.

The mechanism works as follows:

1. Initiate the search, applying _both_ **price** and **size** constraints.
2. If no results are found, repeat the search with _only_ the **size** constraint. Return any results found.
3. If no results are found, repeat the search with _only_ the **price** constraint. Return any results found.
4. If no results are found, repeat the search with _neither_ constraint. Return any results found.
5. If no results are found, return an empty list.

The ordering is deliberate: ideal match first, broadest search last, and favor constraint on price over size (though this depends from person to person).

The interface displays what constraints had to be loosened to get non-empty results (if any).

### Demo

Query:

> vintage graphic tee of size XS under $1

Top listing found panel:

> We loosened the price and size constraints to help with the search.
>
> 👍 This item seems like it's at a fair price!
>
> Item: Graphic Tee — 2003 Tour Bootleg Style
> Description: Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.
> Category: tops
> Style tags: graphic tee, vintage, grunge, streetwear, band tee
> Size: L
> Condition: good
> Price: $24.00
> Colors: black
> Brand: UNKNOWN
> Platform: depop

There is no clothing in the dataset that is extra small or $1, but there is a vintage graphic T-shirt, which was found due to loosening both the constraints.

---

## Spec Reflection

**Spec**: [planning.md](./planning.md)

**How the spec helped**: The spec helped me plan my individual tool implementations and their cross-wiring in the planning loop. It also helped me become deeply familiar with the project, allowing me to pick back up easily from one development session to another.

**When I diverged from the spec**: I diverged from my originally written spec in a few ways:

- I ended up using GitHub Copilot and Gemini Code Assist instead of Claude Code due to me reaching the monthly usage limit in the latter.
- I added stretch features (a price comparison tool and auto-retrying with looser constraints in `search_listings`)
- I had anticipated an agent driven by an LLM (like in [Plant Advisor](https://github.com/krishpatel2067/ai201-lab2-plantadvisor)), but I realized conditional logic was enough since this project does not involve repeated tool use.
- I had user-facing error messages for all the tools except `compare_price`, but I only needed one for `search_listings`. The rest were converted to internal error messages.
- I anticipated simpler return values for each tool, but then I realized that a structured output like in Plant Advisor was needed for consistency.

However, after these changes, I updated the spec to match the implementation.

## AI Tool Use

Due to my last-minute switch to GitHub Copilot and Gemini Code Assist, I ended up using AI generated code much less than in [The Unofficial Guide](https://github.com/krishpatel2067/ai201-project1-unofficial-guide). In fact, after writing all the spec, I also wrote some parts of the tool implementations, leaving blanks for targetting code generation when I didn't have a clear idea of the syntax or mechanism. Nonetheless, even in my limited AI use, there were some instances worth discussing.

### Instance 1

**My input**: I asked the AI tool to implement the `_tokenize` helper function in `tools.py`.

**My expectation**: I expected the AI tool to generate code to perform simple tokenization of a listing entry, taking into account edge cases.

**AI output**: The AI generated sound code, save for a small oversight that I unconvered after a manual scan of the dataset: apostrophes within words. The AI's original generation would split on all non-alphanumeric characters, causing `"Levi's"` to split into `["Levi", "s"]`, making it unmatchable against a query containing `"Levi's"` or `"Levis"`.

**My final call**: I manually added a regex substitution to simply eliminate all apostrophes, handling the above scenario perfectly without causing new issues due to the very limited use of apostrophes in the dataset.

**Conclusion**: Line-by-line review and isolated testing of AI-generated code helps ensure that overlooked edge cases get addressed. Additionally, a more comprehensive spec (especially one listing out known edge cases) helps steer an AI towards more reliable code.

### Instance 2

**My input**: I asked the AI tool to implement `search_listings` as per the docstring and my spec.

**My expectation**: I expected the AI to generate readable code that followed the docstring and my spec precisely, taking into account some edge cases with simple searching algorithms.

**AI output**: The AI got most of the implementation spot on, but I realized that it stored unique tokens only, wrongfully considering entries containing multiple instances of a matching word and entries containing just a single instance equally relevant.

**My final call**: I reprompted the AI, pointing out this issue and asking it to count duplicates when calculating the relevance score.

**Conclusion**: Even when AI can generate code, knowing the conceptual underpinnings of an algorithm helps catch and revise secretly simplistic code to ensure robustness.

### Instance 3

**My input**: I asked the AI tool to implement `suggest_outfits` as per the docstring and my spec.

**My expectation**: I expected the AI to generate readable code that specifically used the Groq LLM API correctly to implement the tool.

**AI output**: The AI got the general structure of the code right, but it failed in using the correct functions to leverage the Groq API. In fact, it seemed like it didn't know what the correct API is as per my installed version. So, it created hyper-guarded code with a lot of conditional branching to test whether the attributes and methods it wanted to use existed. This lenghtened the code significantly and added unnecessary overhead.

**My final call**: Luckily, I had experience with the Groq API from the [Plant Advisor](https://github.com/krishpatel2067/ai201-lab2-plantadvisor) project, so I reprompted the AI tool to replace its overly cautious code with the expected Groq API calls. I had to literally guide it by giving it snippets of code like `client.chat.completions.create` to prompt the LLM and `result.choices[0].message.content` to retrieve the response.

**Conclusion**: This instance was especially shocking. Perhaps GitHub Copilot used an under-equipped model for this prompt. Nonetheless, it stresses the need to still know the necessary API well enough (even in the age of AI) to catch such odd behavior and guide the AI towards fixing it.

---

## What I Learned

Though this project was basic (using mock datasets and conditional logic rather than Groq's tool calling API), I learned some important skills that are highly transferrable to a fully deployed real-world project:

- **LLM** - Design a system prompt thoroughly, execute the LLM API calls properly, handle any edge cases appropriately
- **State management** - Ensure proper storage and flow of state, enforcing a single source of truth
- **Thorough planning and specs** - Lay out app intent and logic before implementation, helping both humans and AI
- **AI-assisted software development** - Leverage AI to make targetted implementations and adjustments, review output, and take over when needed
- **Unit testing** - Use automation to ensure that the core of the app (tools) work as intended
- **Ample documentation** - Use Markdown files (like this one) to communicate effectively about the project to a new audience
- **Project organization** - Clear directory structure (e.g. `utils/`, `scripts/`, `data/`) for managing a large codebase
- **Industry conventions** - Practice and reinforce conventions such as `.env.example`, well-formatted docstrings, consistent local tool API, etc.

---

## Limitations

- Tokenized keyword-based matching in `search_listings` does not support negations in the query. For example, "NOT a vintage graphic tee" would not respect the negation and still return results with a vintage graphic tee. Some solutions:
  - Manually handle negations. However, this is not always reliable due to the flexibility of natural language.
  - Use an LLM to consolidate a list of negations to later manually remove from the results. This may work, but now the tool is not fully-local and may suffer latency issues due to an API call - not to mention possible rate limiting and potential errors.
- In the auto-retry with looser constraints mechanism in `search_listings`, returning as soon as non-empty results are found may lead to a worse match. For example, any clothing items found get returned early in the retry pipeline, but any item that may have scored higher in the next retry step never gets evaluated. Some solutions:
  - Run all the retry steps no matter what and return all the results so that the highest-ranking item out of all pairs of constraints gets chosen. However, this would make the tool run slower.
  - Use a score cutoff below which to continue to the next step in the retry pipeline even if non-empty results are found. Finding this threshold would require empirical testing and would be heavily dataset-dependent unless it's dynamically calculated.
- LLM-based query parsing, even at a low temperature, introduces a possibility of hallucination. In fact, I encountered such an instance during my testing:

Query:

> vintage graphic tee size small

LLM parsing:

Description: `"vintage graphic tee"`
Price: `20`
Size: `"S"`

The price was hallucinated! This exact query leads to the less relevant "Y2K Baby Tee — Butterfly Print" to be surfaced instead, which is $18, satisfying the faux price constraint.
