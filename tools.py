"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# Words that say nothing about the item itself. Leaving them in would let
# "looking for a tee" match every listing that uses the word "for".
_STOPWORDS = {
    "a", "an", "and", "the", "for", "in", "of", "with", "to", "on", "or",
    "i", "im", "me", "my", "want", "need", "looking", "something", "some",
    "size", "under", "below", "less", "than", "max", "around", "about",
}

# Listing text says "tee" and "t-shirt" interchangeably.
_SYNONYMS = {"tshirt": "tee"}


def _words(text: str) -> list[str]:
    """Lowercase words, with a trailing plural "s" dropped so "sneakers" finds "sneaker"."""
    out = []
    for word in re.findall(r"[a-z0-9]+", text.lower().replace("t-shirt", "tshirt")):
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        out.append(_SYNONYMS.get(word, word))
    return out


def _size_tokens(size: str) -> set[str]:
    """Split a size like "XL (fits oversized)" or "US 8.5" into whole tokens."""
    return set(re.findall(r"[A-Z]+\d*(?:\.\d+)?|\d+(?:\.\d+)?", size.upper()))


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Whole-token size match, never a substring test.

    "M" matches "M", "S/M" and "M/L" but not "XL". "8" matches "US 8" but not
    "US 8.5". "30" matches "W30". Anything sold as "One Size" fits everyone.
    """
    listing_upper = listing_size.upper()
    if listing_upper.startswith("ONE SIZE"):
        return True

    wanted = re.sub(r"^(SIZE|US)\s*", "", wanted.strip().upper())
    if not wanted:
        return True

    tokens = _size_tokens(listing_upper)
    if wanted in tokens:
        return True
    # A bare number can be a waist size, as in "W30".
    return bool(re.fullmatch(r"\d+", wanted)) and f"W{wanted}" in tokens


def _score(query_words: list[str], listing: dict) -> int:
    """Count query words found in the listing. Title and tag hits count double."""
    strong = set(_words(listing["title"] + " " + " ".join(listing["style_tags"])))
    weak = set(_words(" ".join([
        listing["description"],
        listing["category"],
        " ".join(listing["colors"]),
        listing["brand"] or "",
    ])))
    score = 0
    for word in query_words:
        if word in strong:
            score += 2
        elif word in weak:
            score += 1
    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    query_words = [w for w in _words(description or "") if w not in _STOPWORDS]
    if not query_words:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue
        score = _score(query_words, listing)
        if score > 0:
            scored.append((score, listing))

    # Highest score first. Ties go to the cheaper listing.
    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_text = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    if not items:
        prompt = (
            f"Someone is thinking about buying this secondhand piece:\n{item_text}\n\n"
            "They haven't told us what's in their closet. Give general styling "
            "advice: two outfit ideas built around this piece, naming the kinds "
            "of basics that pair well with it (for example 'straight-leg jeans' "
            "or 'white sneakers'). Keep it under 120 words. Plain text, no "
            "markdown headers."
        )
    else:
        closet = "\n".join(
            f"- {w['name']} ({w['category']}, {', '.join(w.get('colors') or [])})"
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this secondhand piece:\n{item_text}\n\n"
            f"Here is what they already own:\n{closet}\n\n"
            "Suggest one or two outfits built around the new piece. Each outfit "
            "should name specific pieces from their closet, using the names as "
            "written above. Mention the new item at least once by its full "
            f"title, copied exactly: {new_item.get('title')}. Keep it under "
            "120 words. Plain text, no markdown headers."
        )

    return generate(
        prompt,
        system="You are a friendly thrift stylist. You give practical, specific outfit ideas.",
    ).strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "No outfit to caption yet. Run suggest_outfit first."

    platform = new_item.get("platform", "a thrift app")
    price = new_item.get("price")
    price_text = f"${price:g}" if isinstance(price, (int, float)) else "a thrift price"

    prompt = (
        f"Write a caption for a social media post about this thrift find.\n\n"
        f"Item:\n{_describe_item(new_item)}\n\n"
        f"How it's being styled:\n{outfit}\n\n"
        "Rules:\n"
        "- Two to four sentences, under 350 characters total.\n"
        f"- Mention the item, the price ({price_text}) and the platform "
        f"({platform}) once each.\n"
        "- Sound like a real person posting their fit, not a product listing. "
        "Be specific about the vibe.\n"
        "- One or two emoji or hashtags at most.\n"
        "- Return only the caption."
    )

    return generate(
        prompt,
        system="You write short, casual captions for outfit posts.",
    ).strip()


def _describe_item(item: dict) -> str:
    """The listing as a few prompt lines. Brand is left out when there isn't one."""
    lines = [
        f"Title: {item.get('title')}",
        f"Category: {item.get('category')}",
        f"Colors: {', '.join(item.get('colors') or [])}",
        f"Style: {', '.join(item.get('style_tags') or [])}",
        f"Size: {item.get('size')}",
        f"Condition: {item.get('condition')}",
        f"Price: ${item.get('price')}",
        f"Platform: {item.get('platform')}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)
