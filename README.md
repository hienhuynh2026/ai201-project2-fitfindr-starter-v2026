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
| `mcp_server.py` | Unit 4: `search_listings` registered as an MCP tool |
| `trace.py` | Unit 4: trace steps only print once a trace is started |
| `run_eval.py` | Unit 4: also saves raw sessions as JSON for scoring |
| `score_run.py` | Unit 4: marks each try PASS or FAIL against `criteria.md`, with a reason |

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

I asked Claude to write search_listings to filter by size, price, and keywords. It noted that raw sizes like "S/M" or "US 8.5" cause simple string checks to fail, so it switched to token matching. I tested cases like "M" vs "XL" and "8" vs "US 8.5" myself, then cleaned up an unnecessary synonym list it added.



**Moment 2**

I asked Claude to generate a helpful message when a search finds no results. Its first code hardcoded "jacket" and "ballgown" for every query. I had it use the user's actual search terms instead, so the message gives tailored feedback based on their real budget, size, and query.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

Made with `python run_eval.py --label before` (cache off, temperature 0.9, five
tries per scenario). I marked each try with `python score_run.py`, which checks
the criteria exactly as they are worded in `criteria.md` and prints a reason
next to every PASS and FAIL. The full output is in
`results/run_2026-10-09_1933_before.md`, and the scored version is in
`results/run_2026-10-09_1933_before_scored.txt`.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item found is the item styled and captioned | 5 of 5 | PASS | PASS | FAIL | FAIL | PASS | MISSED (3/5) |
| 4. The fit card reads like a real post | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Search never breaks the price cap or the size | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

The empty wardrobe scenario also ran five times as a diagnostic (it isn't one of
my five criteria). All five tries finished and showed the empty wardrobe note.

**A mistake in my own scoring, caught before I trusted it.** The first time I
scored this run, criterion 2 came out 0 of 5. That looked wrong for a branch
with no model in it, so I opened a try. The run had stopped after search every
time, and `outfit_suggestion` and `fit_card` were both `None`. My scorer was
searching the trace for the word `suggest_outfit`, and it found it inside my
own branch note ("stopping before suggest_outfit"). I changed the check to look
for an actual `[n] suggest_outfit` step line. The criterion didn't change, only
the code that reads it. The fix is in its own commit.

**Real output from one try.** This is criterion 3, try 4, one of the two misses.
It was produced by `agent.py::run_agent` (the outfit text comes from
`tools.py::suggest_outfit` and the caption from `tools.py::create_fit_card`)
and written to the log by `run_eval.py::write_report`:

- stopped early: no
- selected_item: 90s Track Jacket — Navy/White Stripe ($45.0, poshmark)
- search_results: 5

Outfit suggestion:

```
Hey there! That 90s Track Jacket is an absolute steal, and you are going to get so much wear out of it. 

Outfit one leans into that effortless streetwear vibe. Layer the 90s Track Jacket over your white ribbed tank top, and pair them with your baggy straight-leg jeans, dark wash. Slip on your chunky white sneakers, and throw on your black crossbody bag to keep your hands free. 

Outfit two is a fun mix of prep and sport. Pair the 90s Track Jacket with your wide-leg khaki trousers, cinched at the waist with your brown leather belt. Wear your white ribbed tank top underneath, and finish the look with your black combat boots for a cool, edgy contrast.
```

Fit card:

```
Scored this vintage Champion track jacket for just $45 on Poshmark and I'm obsessed. Paired it with baggy denim and chunky sneakers for the ultimate 90s streetwear fit. 🤌✨ #thrifty
```

Trace:

```
[1] parse_query
      in:  90s track jacket in size M
      out: description='90s track jacket', size='M', max_price=None
[2] search_listings (via MCP)
      in:  description='90s track jacket', size='M', max_price=None
      out: 5 items: 90s Track Jacket — Navy/White Stripe, 90s Leather Bomber — Black, Bucket Hat — Reversible, Brown Plaid … +2 more
      →    branch: results found, taking the first one
[3] suggest_outfit
      in:  new_item=lst_004 '90s Track Jacket — Navy/White Stripe', wardrobe=10 items
      out: Hey there! That 90s Track Jacket is an absolute steal, and you are going to get so much wear out of it.   Outf…
[4] create_fit_card
      in:  new_item=lst_004 '90s Track Jacket — Navy/White Stripe', outfit=657 chars
      out: Scored this vintage Champion track jacket for just $45 on Poshmark and I'm obsessed. Paired it with baggy deni…
```

---

## Verdicts and Diagnoses

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | Every try had search results, an outfit and a fit card, with no error and no crash. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | Every try set `error`, left the outfit and fit card as `None`, had no `suggest_outfit` step in the trace, and the message named something to change. |
| 3 | The item found is the item styled and captioned | 5 of 5 | MISSED (3/5) | The id check passed 5 of 5. The full title showed up in the outfit only 3 times, and in the fit card 0 times. |
| 4 | The fit card reads like a real post | 4 of 5 | MET (5/5) | All five cards had 2 or 3 sentences, ran 167 to 201 characters, and named $42 and Poshmark. Hashtags and emoji don't count as sentences. |
| 5 | Search never breaks the price cap or the size | 5 of 5 | MET (5/5) | All 10 results in every try were $30 or less and size M under my rule. I rechecked the sizes with separate code, not the function being tested. |

**Diagnoses**

Criterion 3 was the only miss. It happened in **the model's output** from
`suggest_outfit`. It was not a state problem.

- **The session was fine.** In all five tries `selected_item` was `lst_004`,
  the same as `search_results[0]`, and the trace shows `lst_004` going into
  both `suggest_outfit` and `create_fit_card`. The right item reached every
  tool.
- **The mechanism is in the prompt.** The title is
  "90s Track Jacket — Navy/White Stripe". Like many titles in this data, it is
  a name followed by a detail after a dash. My `suggest_outfit` prompt only
  said "Mention the new item by its title", so the model treated the part after
  the dash as optional. In try 3 it wrote "90s Track Jacket in navy and white",
  and in try 4 just "90s Track Jacket". Both are the right item, but neither is
  the title.
- **Why the fit card couldn't make up for it.** The `create_fit_card` prompt
  says to "mention the item", not its title, and it asks for a casual caption.
  So the captions all said things like "vintage Champion track jacket". Not one
  of the 10 captions across both runs had the full title. That leaves criterion
  3 resting on the outfit text alone.

One thing I noticed that isn't a miss: for `vintage graphic tee under $30,
size M`, results 2 and 3 are a braided belt and a bucket hat. They are One Size
and match only the word "vintage". They pass criterion 5, because One Size fits
any size under my rule. They aren't what anyone asking for a tee wants, though,
and the agent only got the right item because the tee happened to score
highest.

---

## Loop Trace

Each line is one step in `agent.py::run_agent`. Step 2 is the MCP call.

**Happy path**

```
$ python app.py ask 'vintage graphic tee under $30, size M' --trace
[1] parse_query
      in:  vintage graphic tee under $30, size M
      out: description='vintage graphic tee', size='M', max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size='M', max_price=30.0
      out: 10 items: Y2K Baby Tee — Butterfly Print, Leather Belt — Brown, Braided, Bucket Hat — Reversible, Brown Plaid … +7 more
      →    branch: results found, taking the first one
[3] suggest_outfit
      in:  new_item=lst_002 'Y2K Baby Tee — Butterfly Print', wardrobe=10 items
      out: Hey babe, $18 for that Y2K Baby Tee — Butterfly Print is an absolute steal! Here are two ways to style your ne…
[4] create_fit_card
      in:  new_item=lst_002 'Y2K Baby Tee — Butterfly Print', outfit=645 chars
      out: Scored this adorable Y2K butterfly baby tee for just $18 on depop! Paired it with baggy denim and chunky sneak…

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Hey babe, $18 for that Y2K Baby Tee — Butterfly Print is an absolute steal! Here are two ways to style your new treasure using what you already own.

Outfit One: Lean into the retro vibes. Pair the baby tee with your baggy straight-leg jeans, dark wash and the chunky white sneakers. Throw your vintage black denim jacket on top and grab your black crossbody bag. It is the ultimate effortless 2000s look!

Outfit Two: Mix your aesthetics by pairing the baby tee with the wide-leg khaki trousers and your black combat boots. Cinch the waist with the brown leather belt and layer the black cropped zip hoodie loosely over your shoulders. So cute!

  Fit card: Scored this adorable Y2K butterfly baby tee for just $18 on depop! Paired it with baggy denim and chunky sneakers today for the ultimate 2000s off-duty vibe. 🦋✨

2 model calls this session, 592 prompt + 189 output tokens
```

**Empty search**

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit

  No listings matched "designer ballgown" in size XXS under $5. Try to raise your budget above $5, drop the size or try one near XXS, or use fewer or more general words than "designer ballgown".

0 model calls this session
```

The empty search stops after two steps. The happy path takes four.

**The three failure modes, triggered on purpose**

1. *Empty search results.* The trace is above. The message names the budget,
   the size and the wording as things to change, and no model call is made.
2. *Empty wardrobe.* `suggest_outfit` falls back to general styling advice, and
   the agent now tells the user that's what they're getting and what to do
   about it.

```
$ python app.py ask 'denim jacket under $50' --empty-wardrobe --trace
(running with an empty wardrobe)
[1] parse_query
      in:  denim jacket under $50
      out: description='denim jacket', size=None, max_price=50.0
[2] search_listings (via MCP)
      in:  description='denim jacket', size=None, max_price=50.0
      out: 7 items: Denim Jacket — Light Wash, Cropped, High-Waisted Denim Shorts — Cutoff, Denim Vest — Medium Wash, Studded … +4 more
      →    branch: results found, taking the first one
[3] suggest_outfit
      in:  new_item=lst_007 'Denim Jacket — Light Wash, Cropped', wardrobe=0 items
      out: Oh, a vintage Wrangler denim jacket is such a golden find! That cropped light wash has major effortless energy…
      →    empty wardrobe: general advice
[4] create_fit_card
      in:  new_item=lst_007 'Denim Jacket — Light Wash, Cropped', outfit=621 chars
      out: Score this vintage Wrangler denim jacket for just $42 on Poshmark and I'm obsessed with the cropped light wash…

  Note:     Your wardrobe is empty, so these are general styling ideas rather than outfits built from pieces you own. Add a few items to your wardrobe for suggestions that use your own closet.

  Found:    Denim Jacket — Light Wash, Cropped — $42.0 on poshmark

  Outfit:   Oh, a vintage Wrangler denim jacket is such a golden find! That cropped light wash has major effortless energy. 

Here are two easy ways to style it:

First, lean into streetwear by pairing it with baggy black parachute pants, a fitted white baby tee, and chunky retro sneakers. Add a silver chain necklace to tie the look together.

Second, go for a classic casual vibe over a black ribbed maxi dress, paired with worn-in canvas high-top sneakers and a canvas tote bag. 

Because the jacket is cropped, it naturally balances out high-waisted bottoms and loose silhouettes. You will get so much mileage out of this piece!

  Fit card: Score this vintage Wrangler denim jacket for just $42 on Poshmark and I'm obsessed with the cropped light wash. It adds the best effortless streetwear energy to baggy black pants or a simple maxi dress. Such a good find! 🤠 #thrifted

2 model calls this session, 455 prompt + 187 output tokens
```

3. *The model can't be reached.* I changed the last character of my API key for
   this one run only, by setting `GEMINI_API_KEY` on the command line so `.env`
   stayed untouched. `run_agent` catches `ModelUnavailable` and tells the user
   what was found, what broke and what to fix. There is no stack trace.

```
$ python app.py ask 'vintage graphic tee under $30' --trace    # last character of GEMINI_API_KEY changed
[1] parse_query
      in:  vintage graphic tee under $30
      out: description='vintage graphic tee', size=None, max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: results found, taking the first one
[3] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh k…
      →    model unreachable, stopping

  Found Y2K Baby Tee — Butterfly Print ($18 on depop), but couldn't write the outfit or the caption: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. Fix that and ask again; the search itself worked.

1 model calls this session
```

I also added a handler for the MCP server being unreachable. I tested it by
pointing the client at a server file that doesn't exist, and the agent replied
"The listings search couldn't be reached, so nothing was searched. Run
`python mcp_server.py` on its own to see why it won't start, then try again."

**On the MCP move:** `search_listings` is now registered in `mcp_server.py`,
with a description written for someone who can't see my code. It covers units
(US dollars, inclusive), how sizes match, every field in a result, and the
fact that it returns `[]` when nothing matches. In `agent.py::run_agent` the
direct call became `call_tool("search_listings", {...})`, and `agent.py` no
longer imports `search_listings` at all. Nothing behaved differently. Over MCP
the same query returned the same 10 listings as the direct call (I compared
them with `==`), an impossible query still came back as `[]` and not `None` or
a string, and my first happy-path run after the switch was served entirely
from cache. That last part means the prompts were byte for byte the same as
before, so the same item reached the model. The only real cost is speed. Every
search now starts a new Python process for the server, which adds about a
second.

---

## The Improvement

**What I changed:** One sentence in the `suggest_outfit` prompt in `tools.py`.
"Mention the new item by its title." became "Mention the new item at least once
by its full title, copied exactly: <the title>." The title is filled in from
the listing, so the model sees exactly what to write. Nothing else changed.

**Which failure it was meant to fix:** criterion 3. The diagnosis showed the
right item was always reaching the tool, but the model was shortening its name
because the prompt never asked for the exact title.

### Run Log — After

Made with `python run_eval.py --label after`, same scenarios and settings. See
`results/run_2026-10-09_1937_after.md` and
`results/run_2026-10-09_1937_after_scored.txt`.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item found is the item styled and captioned | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card reads like a real post | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Search never breaks the price cap or the size | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Side by side**

| Criterion | Before | After |
|---|---|---|
| 1 | 5/5 MET | 5/5 MET |
| 2 | 5/5 MET | 5/5 MET |
| 3 | 3/5 MISSED | 5/5 MET |
| 4 | 5/5 MET | 5/5 MET |
| 5 | 5/5 MET | 5/5 MET |

**Did it help, and how do I know:** Yes for criterion 3, which went from 3 of 5
to 5 of 5. In every after try, the outfit text uses the full title
"90s Track Jacket — Navy/White Stripe". The other four criteria didn't move,
which makes sense, since the change only touched one prompt.

I'd still be careful about how much this proves. It's five tries on one item,
and before the fix the model got the title right 3 times out of 5 anyway, so
5 of 5 could partly be luck. It also cost something. The outfits got longer:
before the change they ran 97 to 136 words, and after it 116 to 149, even
though the prompt asks for under 120. No criterion measures length, but it's a
real side effect.

---

## What's Still Broken

All five criteria are met after the fix, but some things are still weak.

- **Criterion 3 depends on one tool.** The fit card never uses the full title
  (0 of 10 captions). If the outfit prompt ever slips, nothing backs it up. The
  next step would be to test the title check on several different items,
  especially ones with long two-part titles, not just the track jacket. I
  stopped at one item because the unit allows one improvement, and I wanted the
  before and after to be a fair comparison.
- **Outfits run past their own word limit.** The prompt says under 120 words,
  and the after run went up to 149. Since no criterion checks this, I'd write
  it up as a new criterion first, so a fix could be measured.
- **Search ranks accessories above what was asked for.** One Size belts and
  hats that only match "vintage" come before real tees in the results. Under
  `criteria.md` that isn't a miss. The fix would be to weight words like "tee"
  that name the kind of item more than adjectives like "vintage", or to skip
  One Size accessories when the query names a clothing type. I left it alone
  because this unit only allows one change, and it wasn't failing a criterion.
- **The empty wardrobe path has no exact-title rule.** The fix only changed the
  prompt for a wardrobe with items. I left the empty wardrobe prompt as it was,
  so it could still shorten the title. It's only tested as a diagnostic right
  now.

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

       [x] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [x] Run Log — Before, five criteria, five tries each
       [x] Real output pasted underneath, naming file and function
       [x] A verdict on every criterion
       [x] A diagnosis for every miss, naming a place AND a mechanism
       [x] Loop Trace, with the MCP call visible in it
       [x] All three failure modes triggered and handled
       [x] One improvement, with Run Log — After in the same format
       [x] What's Still Broken
       [x] At least four new commits
       [x] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
