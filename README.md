# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

FitFindr is a small thrifting agent. You tell it what you want in plain words,
like `vintage graphic tee under $30, size M`, and it searches 40 secondhand
listings from Depop, thredUp and Poshmark for the best match. If it finds
something, it looks at your wardrobe and suggests a couple of outfits built
around the new piece, then writes a short caption you could post with the fit.
If nothing matches, it stops right there and tells you what to change (your
budget, your size, or your wording) instead of making something up.

**What I noticed in the data (Milestone 1):** sizes are not uniform. Tops use
letters (`S`, `M/L`, `XL (oversized)`), pants use waist sizes (`W30 L30`),
shoes use `US 8.5`, and accessories are `One Size`. Most listings have no
brand. That shaped how the search tool matches sizes.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Loads every listing with `load_listings()`, drops anything over the price cap or in the wrong size, and ranks the rest by how many of the user's keywords show up in the listing.
- **Inputs:** `description` (str, keywords like "vintage graphic tee"), `size` (str or None, None skips the size filter), `max_price` (float or None, inclusive, None skips the price filter).
- **Returns:** `list[dict]`, best match first, at most `config.SEARCH_RESULT_LIMIT` (10). Each dict is a full listing: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str or None), `platform` (str).
- **When it has nothing:** returns `[]`, an empty list. Never None and never an exception.
- **What counts as a size match:** sizes are compared as whole tokens, never substrings, so `M` matches `M`, `S/M` and `M/L` but not `XL`, and `S` does not match `US 9`. A number matches shoe and waist sizes (`8` matches `US 8` but not `US 8.5`, `30` matches `W30`). `One Size` listings match any size.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new item, naming pieces the user already owns.
- **Inputs:** `new_item` (dict, one listing from `search_listings`), `wardrobe` (dict with an `items` key holding a list of wardrobe item dicts, which may be empty).
- **Returns:** `str`, a non-empty block of outfit suggestions written by the model.
- **When it has nothing:** if `wardrobe["items"]` is empty, it does not fail. It asks the model for general styling advice for the item instead (what kinds of pieces pair well with it) and returns that string.

### `create_fit_card`

- **What it does:** Asks the model for a short social media caption about the find, mentioning the item, its price and its platform once each.
- **Inputs:** `outfit` (str, the text from `suggest_outfit`), `new_item` (dict, the same listing that went into `suggest_outfit`).
- **Returns:** `str`, a caption of two to four sentences.
- **When it has nothing:** if `outfit` is empty or only whitespace, it skips the model call and returns the string `"No outfit to caption yet. Run suggest_outfit first."`

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, write a message
to `session["error"]` that names what the user could change (raise the budget,
drop or change the size, or use broader words) and return the session right
away, without calling `suggest_outfit` or `create_fit_card`. Otherwise take
the first result as `session["selected_item"]` and go on to `suggest_outfit`,
then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::parse_query`. It looks for a
price after words like "under" or a `$` sign, then a size after the word "size"
(or a capitalized letter size like `M` on its own). Whatever is left, minus
filler like "looking for", becomes the description. Anything the user didn't
mention comes back as `None`, so the search skips that filter. No model call is
used for parsing, which keeps the empty-search path free of model calls.

**What moves through the session:** Every tool reads its inputs from the
session and writes its result back before the next step runs.

1. `query` and `wardrobe` are stored when the session is created.
2. `parsed` gets `{description, size, max_price}` from `parse_query`.
3. `search_results` gets the list from `search_listings`, called with the three
   values read out of `parsed`.
4. If that list is empty, `error` gets the message and the run ends here.
   `selected_item`, `outfit_suggestion` and `fit_card` stay `None`.
5. Otherwise `selected_item` gets `search_results[0]`.
6. `outfit_suggestion` gets the text from `suggest_outfit(selected_item, wardrobe)`.
7. `fit_card` gets the caption from `create_fit_card(outfit_suggestion, selected_item)`.

Each step also calls `trace.check_iterations()`, so a broken branch can never
loop forever.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30, size M'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Hey friend! That Y2K Baby Tee — Butterfly Print is an absolute steal for $18 and so versatile. Let's style it with pieces you already own!

Outfit 1: Play up that nostalgic 2000s vibe by pairing the Y2K Baby Tee — Butterfly Print with your Baggy straight-leg jeans, dark wash. Cinch the waist with the Brown leather belt, slip on your Chunky white sneakers, and throw your Black cropped zip hoodie over your shoulders just in case. Finish the look with the Black crossbody bag. 

Outfit 2: For an effortless mix of sweet and edgy, tuck the Y2K Baby Tee — Butterfly Print into your Wide-leg khaki trousers. Add the Black combat boots to anchor the pastel butterfly print, and layer the Vintage black denim jacket on top.

  Fit card: Scored this cute butterfly baby tee on Depop for just $18! Loving it dressed down with baggy denim and sneakers for major 2000s vibes. 🦋 #y2kstyle

2 model calls this session, 619 prompt + 212 output tokens
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]

```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
$38 for vintage Levi's 501s is a total score! Here are two fun ways to style them using pieces you already own.

Outfit One: Casual Streetwear
Pair the Vintage Levi's 501 Jeans — Medium Wash with your white ribbed tank top and black cropped zip hoodie layered on top. Add your chunky white sneakers and the black crossbody bag for an effortless, comfy vibe. 

Outfit Two: Edgy Denim on Denim
Rock the Vintage Levi's 501 Jeans — Medium Wash with your oversized grey crewneck sweatshirt and the vintage black denim jacket thrown over it. Cinch your waist with the brown leather belt, and finish the look with your black combat boots for some serious attitude.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Nothing beats a classic pair of vintage Levi's 501s for that effortless off-duty look. Snagged these on depop for just $38 and I'm obsessed with the wash. Paired them with fresh white sneakers for running errands today. 👖✨
```

**The empty search branch**

```
$ python app.py ask 'designer ballgown size XXS under $5'

  No listings matched "designer ballgown" in size XXS under $5. Try to raise your budget above $5, drop the size or try one near XXS, or use fewer or more general words than "designer ballgown".

0 model calls this session
```

It stops before `suggest_outfit`, so no model calls are made.

---

## Overview / Usage

**Setup (macOS or Linux):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your GEMINI_API_KEY into .env
python test.py                # checks Python, packages, key and one model call
```

**Running it:**

```bash
python app.py ask 'vintage graphic tee under $30, size M'   # one query
python app.py ask                                         # keep asking until you press Enter on a blank line
python app.py ask 'denim jacket under $50' --empty-wardrobe
python app.py ask 'designer ballgown size XXS under $5'    # the early exit
python agent.py                                           # runs a matching and a non-matching query
```

Use single quotes around the query. In PowerShell, `$30` inside double quotes
gets read as a variable and quietly disappears.

**How a query is understood:** you can mention a price (`under $30`, `$30`),
a size (`size M`, `size 8`, `size 30`, or a capital `M` on its own) and
describe the item in your own words. Leave any of them out and that filter is
skipped.

**Files I changed:**

| File | What's in it |
|---|---|
| `tools.py` | The three tools and the size and keyword matching helpers |
| `agent.py` | `run_agent` (the loop and the branch) and `parse_query` |
| `criteria.md` | The five acceptance criteria |
| `scenarios.py` | Eval scenarios for criteria 3, 4 and 5 |

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
