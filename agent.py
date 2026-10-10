"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit, create_fit_card
from generate import ModelUnavailable
from mcp_client import call_tool, MCPError


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "notice": None,              # set when the run finished, but with less than usual
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    steps = 0

    # Step 1: parse the query into description, size and max_price.
    steps += 1
    trace.check_iterations(steps)
    session["parsed"] = parse_query(query)
    trace.step("parse_query", inputs=query, returned=_kv(session["parsed"]))

    # Step 2: search, reading the inputs back out of the session.
    steps += 1
    trace.check_iterations(steps)
    parsed = session["parsed"]
    search_args = {
        "description": parsed["description"],
        "size": parsed["size"],
        "max_price": parsed["max_price"],
    }
    # search_listings now runs behind mcp_server.py, not as a direct import.
    try:
        session["search_results"] = call_tool("search_listings", search_args)
    except MCPError as exc:
        # Failure: the MCP server didn't start or refused the call.
        session["error"] = (
            "The listings search couldn't be reached, so nothing was searched. "
            "Run `python mcp_server.py` on its own to see why it won't start, "
            "then try again."
        )
        trace.step("search_listings (via MCP)", inputs=_kv(search_args),
                   returned=f"MCPError: {str(exc).splitlines()[0]}",
                   note="search unreachable, stopping")
        return session

    # THE BRANCH. Nothing found means we stop here, before any model call.
    if not session["search_results"]:
        # Failure mode 1: an empty search.
        session["error"] = _no_results_message(session["parsed"])
        trace.step("search_listings (via MCP)", inputs=_kv(search_args),
                   returned=session["search_results"],
                   note="branch: empty, stopping before suggest_outfit")
        return session
    trace.step("search_listings (via MCP)", inputs=_kv(search_args),
               returned=session["search_results"],
               note="branch: results found, taking the first one")

    # Step 3: pick the best match and style it.
    steps += 1
    trace.check_iterations(steps)
    session["selected_item"] = session["search_results"][0]

    wardrobe_items = (session["wardrobe"] or {}).get("items") or []
    if not wardrobe_items:
        # Failure mode 2: an empty wardrobe. suggest_outfit falls back to
        # general advice; the user should know that's what they're getting.
        session["notice"] = (
            "Your wardrobe is empty, so these are general styling ideas rather "
            "than outfits built from pieces you own. Add a few items to your "
            "wardrobe for suggestions that use your own closet."
        )

    try:
        session["outfit_suggestion"] = suggest_outfit(
            session["selected_item"], session["wardrobe"]
        )
    except ModelUnavailable as exc:
        # Failure mode 3: the model can't be reached (bad key, no network).
        session["error"] = _model_down_message(session["selected_item"], exc)
        trace.step("suggest_outfit", inputs=session["selected_item"],
                   returned=f"ModelUnavailable: {exc}",
                   note="model unreachable, stopping")
        return session
    trace.step(
        "suggest_outfit",
        inputs=f"new_item={session['selected_item']['id']} "
               f"{session['selected_item']['title']!r}, wardrobe={len(wardrobe_items)} items",
        returned=session["outfit_suggestion"],
        note="empty wardrobe: general advice" if not wardrobe_items else "",
    )

    # Step 4: write the fit card from what the session now holds.
    steps += 1
    trace.check_iterations(steps)
    try:
        session["fit_card"] = create_fit_card(
            session["outfit_suggestion"], session["selected_item"]
        )
    except ModelUnavailable as exc:
        session["error"] = _model_down_message(session["selected_item"], exc)
        trace.step("create_fit_card", inputs=session["selected_item"],
                   returned=f"ModelUnavailable: {exc}",
                   note="model unreachable, stopping")
        return session
    trace.step(
        "create_fit_card",
        inputs=f"new_item={session['selected_item']['id']} "
               f"{session['selected_item']['title']!r}, "
               f"outfit={len(session['outfit_suggestion'])} chars",
        returned=session["fit_card"],
    )

    return session


# ── query parsing ─────────────────────────────────────────────────────────────

_PRICE = re.compile(
    r"(?:under|below|less than|max|up to|<)\s*\$?\s*(\d+(?:\.\d+)?)"
    r"|\$\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SIZE_WORD = re.compile(r"\b(?:in\s+)?size\s+((?:US\s+|W)?[A-Za-z0-9.]+)", re.IGNORECASE)
# A bare letter size, only when typed in capitals, so the "m" in "i'm" is not a size.
_SIZE_BARE = re.compile(r"\b(XXS|XS|S|M|L|XL|XXL)\b")
_FILLER = re.compile(
    r"\b(?:i'?m |i am )?(?:looking for|searching for|i want|i need|find me|show me)\b",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of plain text with regex.

    "vintage graphic tee under $30, size M"
        -> {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

    Anything not mentioned comes back as None, which tells search_listings to
    skip that filter.
    """
    text = query

    max_price = None
    price_match = _PRICE.search(text)
    if price_match:
        max_price = float(price_match.group(1) or price_match.group(2))
        text = text[: price_match.start()] + " " + text[price_match.end():]

    size = None
    size_match = _SIZE_WORD.search(text) or _SIZE_BARE.search(text)
    if size_match:
        size = size_match.group(1).strip()
        text = text[: size_match.start()] + " " + text[size_match.end():]

    text = _FILLER.sub(" ", text)
    text = re.sub(r"[,.;!?]", " ", text)
    text = re.sub(r"\s+(?:in|and|for)\s*$", "", text.strip(), flags=re.IGNORECASE)
    description = re.sub(r"\s+", " ", text).strip()
    description = re.sub(r"^(?:a|an|some)\s+", "", description, flags=re.IGNORECASE)

    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """Tell the user exactly which knobs they can turn, based on what they asked for."""
    words = f'"{parsed["description"]}"' if parsed["description"] else "that"
    asked = words
    if parsed["size"]:
        asked += f" in size {parsed['size']}"
    if parsed["max_price"] is not None:
        asked += f" under ${parsed['max_price']:g}"

    tips = []
    if parsed["max_price"] is not None:
        tips.append(f"raise your budget above ${parsed['max_price']:g}")
    if parsed["size"]:
        tips.append(f"drop the size or try one near {parsed['size']}")
    if parsed["description"]:
        tips.append(f"use fewer or more general words than {words}")
    else:
        tips.append("describe the item, like 'denim jacket'")

    if len(tips) > 1:
        tip_text = ", ".join(tips[:-1]) + ", or " + tips[-1]
    else:
        tip_text = tips[0]
    return f"No listings matched {asked}. Try to {tip_text}."


def _kv(values: dict) -> str:
    """A dict as one trace line, so the trace shows the values, not just the keys."""
    return ", ".join(f"{k}={v!r}" for k, v in values.items())


def _model_down_message(item: dict, exc: Exception) -> str:
    """Say what was found, what broke, and what to try, when the model is down."""
    return (
        f"Found {item.get('title')} (${item.get('price'):g} on {item.get('platform')}), "
        f"but couldn't write the outfit or the caption: {exc} "
        f"Fix that and ask again; the search itself worked."
    )


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
