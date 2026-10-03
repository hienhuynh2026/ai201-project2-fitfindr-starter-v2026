# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
My search is a plain keyword match with a regex query parser, so an unusual
phrasing can slip past it, and two of the three tools depend on a model call
that can time out or get rate limited. One miss in five leaves room for that
without excusing a search that is actually broken.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path never touches the model. It is a filter over a fixed file followed
by an `if`, so the same input should give the same result every time. Anything
less than 5 of 5 would mean the branch itself is wrong, not that something
outside my code got unlucky.

---

## 3. The item that was found is the item that gets styled and captioned

<!-- YOU WRITE THIS ONE.

     How would you know that the item your search found is the same item the
     next tool received? Name something countable or observable.

     This is the criterion people find hardest, because state failure doesn't
     look like state failure — it looks like a tool problem. Something that
     compares session["selected_item"] against what actually reached
     suggest_outfit is the shape you're after. -->

On a matching query, `session["selected_item"]["id"]` equals
`session["search_results"][0]["id"]`, and the item title from
`selected_item` appears in the outfit suggestion or the fit card, in 5 of 5
tries.

**Why this target:**

Every hand-off goes through the session dictionary, and nothing in between is
random, so the id check should never fail. The title check leans on the model,
but both tools get the title directly in their prompt, so a caption that never
mentions the item would mean the wrong thing reached the tool. That is a state
bug and I want zero of them.

---

## 4. The fit card reads like a real post

<!-- YOU WRITE THIS ONE.

     The fit card calls a model, so the same input can produce different words
     each time. That's not a bug — it's the nature of the tool. So what would
     make it acceptable?

     Think about what you'd actually be unhappy to see. A caption that never
     mentions the price? Two different items producing the same opening
     sentence? A card longer than a caption anyone would post? Any of those can
     be turned into a number. -->

For a matching query, the fit card is 2 to 4 sentences, under 400 characters,
and mentions the item's price (for example `$24`) and its platform name, in at
least 4 of 5 tries.

**Why this target:**

The caption comes from the model at temperature 0.9, so the wording will drift
from run to run and it may now and then forget the price or run long. I tell it
exactly what to include, so most tries should pass, but asking for 5 of 5 on a
creative model output would be pretending I control it more than I do.

---

## 5. Search never breaks the price cap or the size

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->

For queries that give a price cap and a size, every item in
`session["search_results"]` costs at most that price and has a size that
matches under my size rule (so asking for `M` never returns an `XL` or a
`US 9` shoe), in 5 of 5 tries.

**Why this target:**

A thrift search that shows you a $45 jacket when you said under $30, or a pair
of shoes when you asked for a medium top, feels broken even if the caption is
great. The filter is plain code with no model involved, so there is no reason
for it to ever be wrong. The data has messy sizes like `US 9` and
`XL (oversized)`, which is exactly where a substring check would slip.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
