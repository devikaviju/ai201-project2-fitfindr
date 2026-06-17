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

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
    ...
    """
    listings = load_listings()

    # Step 1: filter by max_price and size
    filtered = []
    for item in listings:
        if max_price is not None and item.get("price", float("inf")) > max_price:
            continue
        if size is not None:
            item_size = item.get("size", "") or ""
            if size.lower() not in item_size.lower():
                continue
        filtered.append(item)

    # Step 2: score by keyword overlap with description
    keywords = [kw.lower() for kw in description.split() if kw.strip()]

    scored = []
    for item in filtered:
        searchable_text = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("category", ""),
            " ".join(item.get("style_tags", [])),
            item.get("brand") or "",
        ]).lower()

        score = sum(1 for kw in keywords if kw in searchable_text)

        if score > 0:
            scored.append((score, item))

    # Step 3: sort by score, highest first
    scored.sort(key=lambda pair: pair[0], reverse=True)

    return [item for score, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
 
    If the wardrobe is empty, offers general styling advice for the item
    rather than raising an exception or returning an empty string.
    """
    client = _get_groq_client()
 
    item_desc = (
        f"{new_item.get('title', 'Unknown item')} — "
        f"{new_item.get('description', '')} "
        f"(category: {new_item.get('category', 'n/a')}, "
        f"colors: {', '.join(new_item.get('colors', []))}, "
        f"style: {', '.join(new_item.get('style_tags', []))})"
    )
 
    wardrobe_items = wardrobe.get("items", []) if wardrobe else []
 
    if not wardrobe_items:
        # Empty wardrobe → general styling advice, not a crash
        prompt = (
            f"A user just found this thrifted item:\n{item_desc}\n\n"
            f"They don't have any wardrobe items on file. Give general styling "
            f"advice: what kinds of pieces would pair well with this item, what "
            f"overall vibe/aesthetic it suits, and 1-2 example outfit ideas using "
            f"generic pieces (e.g., 'pair with straight-leg jeans and white sneakers')."
        )
    else:
        wardrobe_text = "\n".join(
            f"- {w.get('name', w.get('title', 'item'))} "
            f"({w.get('category', 'n/a')}, {w.get('color', '')})"
            for w in wardrobe_items
        )
        prompt = (
            f"A user just found this thrifted item:\n{item_desc}\n\n"
            f"Their current wardrobe includes:\n{wardrobe_text}\n\n"
            f"Suggest 1-2 complete outfits that pair the new item with specific "
            f"named pieces from their wardrobe above."
        )
 
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful fashion stylist for a thrift-shopping app."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=400,
    )
 
    return response.choices[0].message.content.strip()
 


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
 
    If outfit is empty or missing, returns a descriptive error message
    string — does NOT raise an exception.
    """
    if not outfit or not outfit.strip():
        return "Oops, looks like the outfit context got lost. Try again!"
 
    client = _get_groq_client()
 
    item_name = new_item.get("title", "this piece")
    price = new_item.get("price", "?")
    platform = new_item.get("platform", "a thrift platform")
 
    prompt = (
        f"Write a short, casual Instagram/TikTok OOTD-style caption (2-4 sentences) "
        f"for this thrifted find:\n\n"
        f"Item: {item_name}, ${price}, found on {platform}\n"
        f"Outfit styling: {outfit}\n\n"
        f"The caption should feel authentic and casual — like a real post, not a "
        f"product description. Mention the item name, price, and platform naturally "
        f"(once each), and capture the outfit vibe in specific terms."
    )
 
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You write casual, trendy social media captions for a thrift-shopping app."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,  # higher temp → varied output across calls
        max_tokens=200,
    )
 
    return response.choices[0].message.content.strip()
