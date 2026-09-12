"""Insert the AI-usage slide into an existing deck, touching nothing else.

build_deck.py regenerates all fourteen slides from the template and writes
them over its output file, which destroys any edit made by hand in
PowerPoint. Once a deck has been hand-finished - a real portrait in place of
the template's sample, a reworded line, a resized box - that script must not
be run against it again.

This one is additive. It opens a deck, clones its own Introduction slide to
inherit whatever styling that deck already has, fills the clone with the AI
content, drops it after the Abilities slide, and saves to a NEW file. The
input is opened read-only and is never written to, so a mistake here costs a
re-run, not the deck.

    python docs/portfolio/add_ai_slide.py 데이터분석_포트폴리오_정연웅.pptx

Writes '<name> +AI.pptx' next to the input unless -o says otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pptx import Presentation

import build_deck
from build_deck import ai_usage, duplicate_slide, load_profile, relax_tracking

# Slides are located by their text rather than by index: a hand-edited deck
# may have had slides added, removed or reordered, and inserting the page in
# the wrong place is the kind of silent wrong answer worth failing over.
#
# ai_usage() strips its clone down to the header and redraws the body from
# that slide's own donors, so the source has to be a result slide - the
# Introduction page has no lime numeral or hairline to borrow. All three
# result slides carry the Rule/Result label pair; any of them will do.
RESULT_MARKS = ("Rule", "Result", "Title", "Date")
ABILITIES_MARKS = ("BigQuery", "PostgreSQL", "Tableau")


def slide_text(slide) -> str:
    return "\n".join(sh.text_frame.text for sh in slide.shapes if sh.has_text_frame)


def find_slide(prs, marks: tuple[str, ...], what: str, *, first: bool = False) -> int:
    hits = [i for i, s in enumerate(prs.slides) if all(m in slide_text(s) for m in marks)]
    if len(hits) == 1 or (hits and first):
        return hits[0]
    sys.exit(
        f"could not identify the {what} slide: {len(hits)} of {len(prs.slides)} slides "
        f"match {marks}.\n"
        f"Pass it explicitly - see --help for --clone-from and --after."
    )


def move_slide(prs, src: int, dest: int) -> None:
    """Move the slide at `src` so it ends up at position `dest`."""
    id_list = prs.slides._sldIdLst
    entries = list(id_list)
    entries.insert(dest, entries.pop(src))
    for entry in list(id_list):
        id_list.remove(entry)
    for entry in entries:
        id_list.append(entry)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", type=Path, help="existing .pptx to read (never modified)")
    ap.add_argument("-o", "--output", type=Path, help="where to write (default: '<deck> +AI.pptx')")
    ap.add_argument(
        "--clone-from",
        type=int,
        metavar="N",
        help="1-based slide to borrow type styles from (default: the first result slide)",
    )
    ap.add_argument(
        "--after",
        type=int,
        metavar="N",
        help="1-based slide to insert after (default: the Abilities slide)",
    )
    ap.add_argument("-f", "--force", action="store_true", help="overwrite the output file")
    args = ap.parse_args()

    if not args.deck.exists():
        sys.exit(f"no such deck: {args.deck}")

    output = args.output or args.deck.with_name(f"{args.deck.stem} +AI.pptx")
    if output.resolve() == args.deck.resolve():
        sys.exit("refusing to write over the input deck - choose a different -o")
    if output.exists() and not args.force:
        sys.exit(f"{output} already exists; pass --force to replace it")

    # stamp_header(), called from ai_usage(), reads the profile globals.
    build_deck.P = load_profile()

    prs = Presentation(args.deck)

    source = (
        args.clone_from - 1
        if args.clone_from
        else find_slide(prs, RESULT_MARKS, "result", first=True)
    )
    anchor = args.after - 1 if args.after else find_slide(prs, ABILITIES_MARKS, "Abilities")
    for idx, what in ((source, "--clone-from"), (anchor, "--after")):
        if not 0 <= idx < len(prs.slides):
            sys.exit(f"{what}: slide {idx + 1} is outside this deck's 1..{len(prs.slides)}")

    slide = duplicate_slide(prs, source)
    ai_usage(slide)
    relax_tracking(slide)
    move_slide(prs, len(prs.slides) - 1, anchor + 1)

    prs.save(output)
    print(
        f"copied slide {source + 1}'s layout, inserted the AI slide at {anchor + 2} "
        f"of {len(prs.slides)}\nwrote {output}  (input untouched)"
    )


if __name__ == "__main__":
    main()
