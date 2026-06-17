"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

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
import json
import os
 
from dotenv import load_dotenv
from groq import Groq

from tools import search_listings, suggest_outfit, create_fit_card

# Load environment variables from the .env file!
load_dotenv()

# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }

 
 
# ── query parsing (LLM-based) ─────────────────────────────────────────────────
 
def _parse_query(query: str) -> dict:
    """
    Use the LLM to extract description, size, and max_price from a natural
    language query. Returns a dict: { description, size, max_price }.
 
    size and max_price are None if not mentioned in the query.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")
 
    client = Groq(api_key=api_key)
 
    system_prompt = (
        "You extract structured search parameters from a clothing search query. "
        "Respond with ONLY a JSON object, no other text, no markdown fences. "
        "The JSON object must have exactly these keys:\n"
        '  "description": string — the core item keywords (e.g. "vintage graphic tee")\n'
        '  "size": string or null — a size string if mentioned (e.g. "M", "S/M", "W30"), else null\n'
        '  "max_price": number or null — the maximum price as a number if mentioned, else null\n\n'
        'Example query: "vintage graphic tee under $30, size M"\n'
        'Example output: {"description": "vintage graphic tee", "size": "M", "max_price": 30}'
    )
 
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        temperature=0,
        max_tokens=150,
    )
 
    raw = response.choices[0].message.content.strip()
 
    # Strip markdown fences if the model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
 
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: treat the whole query as the description if parsing fails
        parsed = {"description": query, "size": None, "max_price": None}
 
    return {
        "description": parsed.get("description") or query,
        "size": parsed.get("size"),
        "max_price": parsed.get("max_price"),
    }

# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    """
    # Step 1: initialize session
    session = _new_session(query, wardrobe)
 
    # Step 2: parse the query into description / size / max_price
    parsed = _parse_query(query)
    session["parsed"] = parsed
 
    # Step 3: search for listings
    results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results
 
    if not results:
        session["error"] = (
            "I couldn't find anything matching that. Try removing the size "
            "filter or raising your budget!"
        )
        return session  # branch: stop here, do NOT call suggest_outfit or create_fit_card
 
    # Step 4: select the top result
    session["selected_item"] = results[0]
 
    # Step 5: suggest an outfit using the selected item + wardrobe
    outfit = suggest_outfit(session["selected_item"], wardrobe)
    session["outfit_suggestion"] = outfit
 
    # Step 6: generate the fit card caption
    fit_card = create_fit_card(outfit, session["selected_item"])
    session["fit_card"] = fit_card
 
    # Step 7: return the completed session
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
