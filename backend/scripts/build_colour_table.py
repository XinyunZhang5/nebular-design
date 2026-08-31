"""Regenerate app/services/lego_colours.py from the Rebrickable colour table.

Run this instead of editing lego_colours.py, and instead of adding a colour from
memory. Every name and RGB below is read out of Rebrickable's public catalogue
dump, the same source the parts tables come from.

    https://rebrickable.com/downloads/  ->  colors.csv

WHY THE OLD HAND-WRITTEN LIST WAS TOO SMALL

It held 43 opaque colours, filtered to "solid, currently produced, more than 800
known parts, no metallics" so that a generated shopping list was something you
could order today. That constraint is worth dropping: the model is as likely to
be 3D printed as bought, and a colour that LEGO retired in 2010 prints exactly
as well as one it sells now. A photograph of a sandstone building has no good
match in 43 colours and four decent ones in 150.

WHAT IS STILL FILTERED, AND WHY

    id -1 / 9999   [Unknown] and [No Colour] are placeholders, not colours.
    Modulex*       A different product line — LEGO's 1:2.5 architectural
                   modelling brick, whose studs do not fit a System brick. Its
                   colours sit in the same table and are the *closest* match for
                   a lot of stonework, so left in they quietly win the palette
                   and the parts list becomes unbuildable and unprintable at the
                   model's own scale.
    num_parts < 50 A colour known from a handful of parts is usually a catalogue
                   artefact or a one-off print run. Below this threshold the
                   table fills with near-duplicates that no photograph can tell
                   apart, and every one of them is another candidate the palette
                   clustering has to consider.

EVERY COLOUR ALSO GETS AN LDRAW CODE, AND WHY THAT IS GENERATED TOO

LDraw colour codes are not Rebrickable colour IDs. Most coincide; some collide
outright, and every Rebrickable-only colour (the 1000+ IDs) has no LDraw code at
all. Widening the palette from 43 to 102 turned that from a three-line hand-kept
exception table into 34 colours with nothing to export as — including Warm Tan
and Sienna Brown, which are most of Big Ben. A part written with an unresolvable
code does not fail; the viewer just draws it in the wrong colour.

So the map is computed here, against the official LDConfig.ldr: keep the code
when the ID exists in LDraw *and* the two catalogues agree on the RGB, and
otherwise fall back to the nearest LDraw colour of the same transparency. That
also catches the collisions the hand-kept table listed one at a time — 326 is
Olive Green to Rebrickable and Yellowish Green to LDraw, and the RGB check
notices without being told.

Transparent colours are kept separate rather than dropped. They are the glazing:
a window at brick scale is an ordinary brick shape in a transparent colour, so
the geometry never changes and the wall still reads as glass.

    python scripts/build_colour_table.py --data backend/.data/rebrickable \
        --ldraw-config backend/.data/ldraw/LDConfig.ldr
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

# Below this many known parts a colour is an artefact of the catalogue rather
# than something anyone has ever built with.
MIN_PARTS = 50

# How far apart two catalogues may put the "same" colour before the shared ID is
# treated as a collision rather than a rounding difference, in redmean units.
#
# Measured rather than guessed, because the first value (60) was tight enough to
# call Black a collision and remap it away from LDraw code 0. Across every ID the
# two catalogues share, genuine matches run from 23 (Reddish Brown) to 78
# (Orange) — the same physical brick, measured twice — while the three known
# collisions sit at 197, 236 and 243, a whole hue apart. 150 is the middle of
# that gap and nothing lands near it.
SAME_COLOUR_DISTANCE = 150.0

HEADER = '''"""LEGO colours, read from the Rebrickable catalogue. GENERATED — do not edit.

Regenerate with scripts/build_colour_table.py. Names and RGB values come from
Rebrickable's colors.csv; none of it was recalled.

{opaque} opaque colours and {trans} transparent ones, each appearing on at least
{min_parts} known parts. Ordered by how much of the catalogue they cover, so the
common colours are first and a caller that truncates the list keeps the useful
half.
"""

from typing import NamedTuple


class Colour(NamedTuple):
    colour_id: int  # Rebrickable colour ID
    name: str  # official LEGO / BrickLink colour name
    rgb: tuple[int, int, int]

    @property
    def hex(self) -> str:
        """The colour as `#RRGGBB`, for clients that draw a swatch.

        Names alone are not enough on the wire: a client that keeps its own
        name-to-hex table silently falls back to grey the moment this catalogue
        gains a colour, and the drift is invisible until someone looks at a
        rendered palette. Shipping the hex from here keeps one source of truth.
        """
        return "#{{:02X}}{{:02X}}{{:02X}}".format(*self.rgb)


'''


def load(path: Path) -> tuple[list, list]:
    opaque, trans = [], []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            if row["id"] in ("-1", "9999"):
                continue
            if int(row["num_parts"] or 0) < MIN_PARTS:
                continue
            if row["name"].startswith("Modulex"):
                continue
            rgb = row["rgb"]
            entry = (
                int(row["id"]),
                row["name"],
                (int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)),
                int(row["num_parts"]),
            )
            (trans if row["is_trans"] == "True" else opaque).append(entry)
    opaque.sort(key=lambda c: -c[3])
    trans.sort(key=lambda c: -c[3])
    return opaque, trans


def _key(name: str) -> str:
    """Normalise a colour name so the two catalogues' spellings compare equal."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_ldraw(path: Path) -> dict[int, tuple[tuple[int, int, int], bool, str]]:
    """LDraw colour code -> (rgb, is_transparent, name), read from LDConfig.ldr."""
    out: dict[int, tuple[tuple[int, int, int], bool, str]] = {}
    pattern = re.compile(
        r"^0 !COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+#([0-9A-Fa-f]{6})"
    )
    for line in path.read_text(errors="replace").splitlines():
        m = pattern.match(line)
        if not m:
            continue
        # LDConfig carries the Modulex palette too, under codes in the 30000s.
        # Left in the pool it wins matches on RGB alone — Olive Green resolves to
        # Modulex_Olive_Green — and writes a code for a brick that does not fit
        # the model it is in. Same exclusion as on the Rebrickable side.
        if m.group(1).startswith("Modulex"):
            continue
        v = m.group(3)
        out[int(m.group(2))] = (
            (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)),
            "ALPHA" in line,
            m.group(1),
        )
    return out


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """Redmean, the same weighting the runtime uses to snap a pixel to a brick."""
    rmean = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return (
        (2 + rmean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rmean) / 256) * db * db
    ) ** 0.5


def ldraw_codes(entries: list, trans: bool, ldraw: dict) -> dict[int, int]:
    """Best LDraw code for each of our colours.

    Name before RGB, because RGB alone gets it wrong in exactly the cases that
    matter. Rebrickable's Olive Green is #9B9A5A and LDraw's is #77774E — the
    same colour, measured on different plastic — while LDraw's Reddish Gold sits
    30 units closer to the Rebrickable value than LDraw's own Olive Green does.
    Matching on the number alone writes a gold roof where an olive one was asked
    for, and the file is perfectly valid.
    """
    pool = [(code, rgb) for code, (rgb, is_t, _n) in ldraw.items() if is_t == trans]
    by_name = {
        _key(n): code for code, (_rgb, is_t, n) in ldraw.items() if is_t == trans
    }
    out: dict[int, int] = {}
    for cid, name, rgb, _parts in entries:
        native = ldraw.get(cid)
        if native and native[1] == trans and _distance(rgb, native[0]) <= SAME_COLOUR_DISTANCE:
            out[cid] = cid
        elif _key(name) in by_name:
            out[cid] = by_name[_key(name)]
        else:
            out[cid] = min(pool, key=lambda c: _distance(rgb, c[1]))[0]
    return out


def render(name: str, entries: list) -> str:
    lines = [f"{name}: list[Colour] = ["]
    for cid, label, (r, g, b), parts in entries:
        lines.append(
            f'    Colour({cid}, "{label}", (0x{r:02X}, 0x{g:02X}, 0x{b:02X})),'
            f"  # {parts:,} parts"
        )
    lines.append("]")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path, help="dir holding colors.csv")
    ap.add_argument(
        "--ldraw-config", required=True, type=Path, help="path to LDConfig.ldr"
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "app/services/lego_colours.py",
    )
    args = ap.parse_args()

    opaque, trans = load(args.data / "colors.csv")
    ldraw = load_ldraw(args.ldraw_config)
    codes = ldraw_codes(opaque, False, ldraw) | ldraw_codes(trans, True, ldraw)
    remapped = sum(1 for cid, code in codes.items() if cid != code)

    body = HEADER.format(opaque=len(opaque), trans=len(trans), min_parts=MIN_PARTS)
    body += render("SOLID", opaque) + "\n\n\n"
    body += render("TRANSPARENT", trans) + "\n\n\n"
    body += (
        "# Rebrickable colour ID -> LDraw colour code, matched by RGB against the\n"
        "# official LDConfig.ldr. Where the two catalogues agree the code is the\n"
        "# ID; where they collide, or where the colour is Rebrickable-only, it is\n"
        "# the nearest LDraw colour of the same transparency.\n"
        "LDRAW_CODE: dict[int, int] = {\n"
    )
    lookup = {c[0]: c[1] for c in opaque + trans}
    for cid in sorted(codes):
        mark = "" if cid == codes[cid] else f"  # {lookup[cid]} -> LDraw {codes[cid]}"
        body += f"    {cid}: {codes[cid]},{mark}\n"
    body += "}\n"
    args.out.write_text(body)
    print(
        f"{args.out}: {len(opaque)} opaque + {len(trans)} transparent, "
        f"{remapped} remapped to a different LDraw code"
    )


if __name__ == "__main__":
    main()
