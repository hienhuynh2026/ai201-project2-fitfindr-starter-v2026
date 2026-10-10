#!/usr/bin/env python3
"""
Mark every try in a run log PASS or FAIL against criteria.md, and say why.

    python score_run.py results/run_2026-10-09_1930_before.json

run_eval.py leaves the verdicts to you. This is me doing that, written down as
code so every PASS/FAIL has a reason printed next to it and can be checked.
Each check is the criterion's wording in criteria.md, read literally, no
looser. It does not import tools.py, so the size check in criterion 5 is an
independent re-implementation of the rule, not the search grading itself.
"""

import json
import re
import sys

TARGETS = {1: 4, 2: 5, 3: 5, 4: 4, 5: 5}
NAMES = {
    1: "A matching query completes all three tools",
    2: "An impossible query stops before the second tool",
    3: "The item found is the item styled and captioned",
    4: "The fit card reads like a real post",
    5: "Search never breaks the price cap or the size",
}


def c1(s, t):
    if not s.get("search_results"):
        return False, "search returned nothing"
    if s.get("error"):
        return False, f"stopped with error: {s['error'][:60]}"
    if not (s.get("outfit_suggestion") or "").strip():
        return False, "no outfit suggestion"
    card = (s.get("fit_card") or "").strip()
    if not card or card.startswith("No outfit to caption"):
        return False, "no fit card"
    return True, "search, suggest_outfit and create_fit_card all returned"


def c2(s, t):
    if not s.get("error"):
        return False, "no error message; the run did not stop"
    if s.get("outfit_suggestion") is not None or s.get("fit_card") is not None:
        return False, "suggest_outfit or create_fit_card ran anyway"
    # A step line, "[3] suggest_outfit". Not just the word: the branch's own
    # note says "stopping before suggest_outfit".
    if re.search(r"^\[\d+\] suggest_outfit", t or "", re.M):
        return False, "a suggest_outfit step appears in the trace"
    if not re.search(r"\b(raise|drop|try|use fewer|describe)\b", s["error"], re.I):
        return False, "message doesn't name anything to change"
    return True, "stopped after search; message names what to change"


def c3(s, t):
    item, results = s.get("selected_item"), s.get("search_results") or []
    if not item or not results:
        return False, "nothing selected"
    if item["id"] != results[0]["id"]:
        return False, f"selected {item['id']} but search_results[0] is {results[0]['id']}"
    title = item["title"].lower()
    outfit = (s.get("outfit_suggestion") or "").lower()
    card = (s.get("fit_card") or "").lower()
    if title in outfit or title in card:
        where = "outfit" if title in outfit else "fit card"
        return True, f"ids match ({item['id']}); full title in {where}"
    return False, f"ids match ({item['id']}) but full title {item['title']!r} in neither outfit nor fit card"


def sentences(text):
    """Sentences in a caption. Hashtags and emoji-only tails aren't sentences."""
    text = re.sub(r"#\w+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if re.search(r"[A-Za-z]{2,}", p)]


def c4(s, t):
    card, item = s.get("fit_card") or "", s.get("selected_item") or {}
    if not card:
        return False, "no fit card"
    problems = []
    n = len(sentences(card))
    if not 2 <= n <= 4:
        problems.append(f"{n} sentences")
    if len(card) >= 400:
        problems.append(f"{len(card)} chars")
    price = item.get("price")
    price_re = rf"\${price:g}(?:\.0+)?(?!\d)" if price is not None else r"(?!)"
    if not re.search(price_re, card):
        problems.append(f"no ${price:g}")
    if (item.get("platform") or "").lower() not in card.lower():
        problems.append(f"no platform '{item.get('platform')}'")
    if problems:
        return False, "; ".join(problems)
    return True, f"{n} sentences, {len(card)} chars, price and platform present"


def size_ok(wanted, listing_size):
    up = listing_size.upper()
    if up.startswith("ONE SIZE"):
        return True
    return wanted.upper() in re.split(r"[^A-Z0-9.]+", up)


def c5(s, t, cap, size):
    results = s.get("search_results") or []
    if not results:
        return False, "no results to check"
    bad = [f"{r['id']} ${r['price']} size {r['size']!r}" for r in results
           if r["price"] > cap or not size_ok(size, r["size"])]
    if bad:
        return False, "breaks the filter: " + ", ".join(bad)
    one = sum(r["size"].upper().startswith("ONE SIZE") for r in results)
    return True, f"all {len(results)} ≤ ${cap:g} and size {size} ({one} are One Size)"


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    table = {}
    for row in data:
        sc = row["scenario"]
        num = sc.get("criterion")
        label = f"{num}. {NAMES[num]}" if num else f"(diagnostic) {sc['name']}"
        print(f"\n{label}\n  query: {sc['query']}  ({sc['wardrobe']} wardrobe)")
        marks = []
        for i, tr in enumerate(row["tries"], 1):
            s, t = tr["session"] or {}, tr["trace"] or ""
            if tr["crashed"]:
                ok, why = False, f"CRASHED: {tr['crashed']}"
            elif num == 1:
                ok, why = c1(s, t)
            elif num == 2:
                ok, why = c2(s, t)
            elif num == 3:
                ok, why = c3(s, t)
            elif num == 4:
                ok, why = c4(s, t)
            elif num == 5:
                p = s["parsed"]
                ok, why = c5(s, t, p["max_price"], p["size"])
            else:
                ok = not s.get("error") and bool(s.get("fit_card"))
                why = ("completed" if ok else f"stopped: {s.get('error')}") + \
                      (f"; notice: {s['notice'][:50]}…" if s.get("notice") else "; NO notice")
            marks.append(ok)
            print(f"  try {i}: {'PASS' if ok else 'FAIL'}: {why}")
        if num:
            table[num] = marks

    print("\n| Criterion | Target | " + " | ".join(f"Try {i}" for i in range(1, 6)) + " | Verdict |")
    print("|---|---|---|---|---|---|---|---|")
    for num in sorted(table):
        marks, target = table[num], TARGETS[num]
        passed = sum(marks)
        verdict = f"{'MET' if passed >= target else 'MISSED'} ({passed}/{len(marks)})"
        cells = " | ".join("PASS" if m else "FAIL" for m in marks)
        print(f"| {num}. {NAMES[num]} | {target} of 5 | {cells} | {verdict} |")


if __name__ == "__main__":
    main(sys.argv[1])
