# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

## Tool Inventory
Tool 1: search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]

Purpose: Searches the mock listings.json dataset for secondhand clothing items matching a description, optional size, and optional price ceiling.

Inputs:
- description (str) — keywords describing the item (e.g. "vintage graphic tee")
- size (str | None) — a size string to filter by, matched as a case-insensitive substring (e.g. "M" matches "S/M" and "M/L")
- max_price (float | None) — maximum price, inclusive


Output: A list of listing dicts, sorted by keyword-overlap relevance (best match first). Each dict includes id, title, description, category, style_tags, size, condition, price, colors, brand, platform.

Failure mode: Returns [] if nothing matches — never raises an exception.

Tool 2: suggest_outfit(new_item: dict, wardrobe: dict) -> str

Purpose: Uses the Groq LLM (llama-3.3-70b-versatile) to suggest 1–2 outfits pairing a newly found item with the user's existing wardrobe pieces.

Inputs:
- new_item (dict) — the selected listing dict from search_listings
- wardrobe (dict) — a dict with an items key containing a list of wardrobe item dicts; may be empty


Output: A string with one or more outfit suggestions.

Failure mode: If wardrobe["items"] is empty (or the items key is missing entirely), the function switches prompts and asks the LLM for general styling advice based only on the new item's characteristics, rather than crashing or returning an empty string.

Tool 3: create_fit_card(outfit: str, new_item: dict) -> str

Purpose: Uses the Groq LLM to generate a short, casual, shareable Instagram/TikTok-style caption for the outfit.

Inputs:
- outfit (str) — the outfit suggestion string returned by suggest_outfit
- new_item (dict) — the same listing dict used in suggest_outfit, used to pull title, price, and platform into the caption


Output: A 2–4 sentence caption string. Temperature is set to 0.9 so repeated calls with the same input produce varied wording.

Failure mode: If outfit is empty or whitespace-only, returns the fixed string "Oops, looks like the outfit context got lost. Try again!" without calling the LLM at all.

## Planning Loop
run_agent(query, wardrobe) in agent.py runs a fixed sequence of steps with one conditional branch point:


Initialize a fresh session dict.
Parse the natural language query into description, size, and max_price using an LLM call (see Spec Reflection below for why this isn't regex).
Call search_listings() with the parsed parameters.
Branch: if search_listings() returns [], set session["error"] to a fallback message and return session immediately. suggest_outfit and create_fit_card are never called on this path.
If results exist, select results[0] as session["selected_item"].
Call suggest_outfit(selected_item, wardrobe) and store the result.
Call create_fit_card(outfit, selected_item) and store the result.
Return the completed session.


The loop isn't a free-form planner that decides which tool to call next at runtime — it's a fixed pipeline with one early-exit branch. The branch is what prevents the agent from calling all three tools unconditionally: when search_listings fails to find anything, two of the three tools are skipped entirely.

## State Management
A single session dict, created by _new_session(), is the source of truth for one interaction:
{
    "query": query,
    "parsed": {},
    "search_results": [],
    "selected_item": None,
    "wardrobe": wardrobe,
    "outfit_suggestion": None,
    "fit_card": None,
    "error": None,
}

session["parsed"] is written once, right after query parsing. session["selected_item"] is written once, as results[0], and that exact same dict object is then passed as an argument into both suggest_outfit() and create_fit_card() — nothing is re-fetched or recreated between tool calls. session["outfit_suggestion"] is written by suggest_outfit's return value and immediately read back out to build the input to create_fit_card. On the no-results branch, outfit_suggestion and fit_card are left at their None defaults from _new_session(), which is how the Gradio UI and CLI test both detect that the early-exit path was taken.

## Error Handling
| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query |"I couldn't find anything matching that. Try removing the size filter or raising your budget!" — confirmed via terminal output running python agent.py with the query "designer ballgown size XXS under $5", where outfit_suggestion and fit_card stayed None.|

| suggest_outfit | Wardrobe is empty |The LLM generates general styling advice rather than forcing a match with nonexistent pieces — confirmed by toggling the "Empty wardrobe (new user)" radio button in the Gradio UI, where the outfit panel changed from naming specific items to generic categories.|

| create_fit_card | Outfit input is missing or incomplete|"Oops, looks like the outfit context got lost. Try again!" — confirmed by passing pytest tests test_create_fit_card_empty_outfit_returns_error_message and test_create_fit_card_whitespace_outfit_returns_error_message.|

## Spec Reflection
One way the spec helped: Writing out the exact session dict field names (selected_item, outfit_suggestion, fit_card, error) in planning.md before touching code meant that when I prompted Claude for the run_agent() implementation, I could require it to use those exact key names instead of letting it invent its own variable names. This made handle_query() in app.py trivial to write afterward, since the session dict's shape was already fixed and predictable.

One way implementation diverged from the spec: The original planning.md didn't specify how the query would be parsed into description/size/max_price — it only said the agent would "extract parameters." During implementation I chose an LLM-based parser (a dedicated Groq call with a strict JSON-only system prompt) over a regex/string-split approach, because example queries like "I mostly wear baggy jeans and chunky sneakers" mix unrelated wardrobe context into the same sentence as the search request, and regex would need a separate rule for every possible phrasing of price and size. The tradeoff is that run_agent() now makes three LLM calls per successful interaction instead of two, which matters for Groq's free-tier rate limits but wasn't a constraint in the original plan.

## AI Usage
Instance 1 — search_listings() implementation: I gave Claude the Tool 1 spec block from planning.md (description/size/max_price inputs, the listing dict return fields, and the "return [], never raise" failure mode), plus a sample listings.json entry so it could see exact field names like style_tags and colors. It produced a function that filtered by price and size first, then scored remaining listings by keyword overlap across the description field only. I overrode this to also search title, category, style_tags, and brand for keyword matches, because a query like "vintage graphic tee" needed to match listings where "graphic tee" appeared in style_tags rather than literally in the prose description field — testing showed the original version missed otherwise-clear matches.

Instance 2 — run_agent() planning loop: I gave Claude the Planning Loop, State Management, and Architecture sections of planning.md, including the ASCII diagram showing the branch between the error path and the success path. It produced a run_agent() that matched the session dict structure exactly, with the early return session on empty results. I revised the query-parsing step specifically: the first draft used a basic regex parser, and I directed Claude to switch it to an LLM-based JSON parser instead, after deciding that fixed regex patterns wouldn't generalize to the natural, conversational example queries from planning.md's "Complete Interaction" walkthrough.

