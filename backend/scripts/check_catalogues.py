"""Check the invariants that only break at render time. Run before deploying.

Everything here is a rule the code relies on and never states. Break one and
nothing fails where the mistake was made: the backend writes a perfectly valid
.ldr, stores it, returns 201, and the browser gives up on the whole model with

    THREE.LDrawLoader: Subobject "60477.dat" could not be loaded.

which is how a one-line change to the parts catalogue took the viewer down
without a single error on the server. The rules:

    A  Anything the writer places with an explicit turn is measured against
       lego_shapes.BY_PART. A part in a catalogue but not in the shape library
       is a KeyError inside the request.
    B  Every colour needs an LDraw code, and that code has to exist in
       LDConfig.ldr. A missing one does not fail — the viewer draws the part in
       the wrong colour, silently.
    C  The writer substitutes a few part numbers on the way out (3023 -> 3023b).
       The number it looks geometry up by has to be in the shape library; the
       number it *writes* has to be a file the viewer can fetch. These are two
       different sets and it is easy to check the wrong one.
    D  A slope replaces the course it sits in, so it has to be exactly one
       course tall. A shorter one leaves a gap that nothing reports.
    E  Every part any code path can place has to be in the viewer's library
       along with its whole dependency tree.

Runs against the library the repository actually ships — `public/ldraw` — and
needs nothing else. That is deliberate: the 745 MB LDraw download lives in
.data/ and is not committed, so a check that required it could only ever run on
a machine that had already done the work. This one runs anywhere the repo does.

    python scripts/check_catalogues.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import lego_catalogue as cat  # noqa: E402
from app.services import lego_shapes as shapes  # noqa: E402
from app.services import legolize  # noqa: E402
from app.services import solid_plan  # noqa: E402
from app.services.ldraw import LDRAW_PART  # noqa: E402
from app.services.lego_colours import LDRAW_CODE  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_viewer_library import closure, emittable  # noqa: E402

BRICK_LDU = 24.0


class Report:
    def __init__(self) -> None:
        self.failures = 0

    def __call__(self, label: str, offenders) -> None:
        offenders = sorted(offenders)
        if offenders:
            self.failures += 1
            shown = ", ".join(str(o) for o in offenders[:8])
            more = f" … and {len(offenders) - 8} more" if len(offenders) > 8 else ""
            print(f"  FAIL  {label}: {shown}{more}")
        else:
            print(f"  ok    {label}")


def part_tables() -> dict[str, list]:
    """Every sequence of parts the catalogue module exposes."""
    out = {}
    for name in dir(cat):
        value = getattr(cat, name)
        if isinstance(value, (list, tuple)) and value:
            if all(hasattr(v, "part_num") for v in value):
                out[name] = list(value)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--viewer",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "nebular-design/public/ldraw",
    )
    args = ap.parse_args()
    check = Report()

    tables = part_tables()
    every_part = {p.part_num for t in tables.values() for p in t}

    print(f"A. geometry ({len(tables)} catalogue tables, {len(every_part)} parts)")
    check("every catalogued part is in the shape library", every_part - set(shapes.BY_PART))
    check(
        "relief roofline slopes are in the shape library",
        set(legolize.ROOF_SLOPES.values()) - set(shapes.BY_PART),
    )
    check(
        "solid roofline slopes are in the shape library",
        {s.part_num for s in solid_plan.SLOPES.values()} - set(shapes.BY_PART),
    )

    print("B. colours")
    colour_ids = {c.colour_id for c in cat.COLOURS + cat.GLAZING}
    check("every colour has an LDraw code", colour_ids - set(LDRAW_CODE))
    config = (args.viewer / "LDConfig.ldr").read_text(errors="replace")
    defined = {int(m.group(1)) for m in re.finditer(r"CODE\s+(\d+)\s+VALUE", config)}
    check(
        "every LDraw code is defined in LDConfig",
        {LDRAW_CODE[i] for i in colour_ids if i in LDRAW_CODE} - defined,
    )
    check(
        "the fill and glazing defaults are in the palette",
        {cat.FILL_COLOUR_ID, cat.DEFAULT_GLAZING_ID} - set(cat.COLOURS_BY_ID),
    )

    print("C. part-number substitution")
    check("substituted-from numbers are in the shape library", set(LDRAW_PART) - set(shapes.BY_PART))
    check(
        "substituted-to numbers are files the viewer has",
        {p for p in LDRAW_PART.values() if not (args.viewer / "parts" / f"{p}.dat").exists()},
    )

    print("D. slopes")
    check(
        "every placeable slope is exactly one course tall",
        {s.part_num for s in solid_plan.SLOPES.values() if abs(s.height - BRICK_LDU) > 0.01},
    )

    print("E. viewer library")
    # Resolved against the shipped library rather than the full one, so this is
    # the same question the browser asks: can it fetch every file it will be
    # told to fetch, and every file those files reference in turn.
    needed, missing = closure(emittable(), args.viewer)
    check(f"every placeable part resolves ({len(needed)} files walked)", missing)

    print()
    if check.failures:
        print(f"{check.failures} check(s) failed")
        raise SystemExit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
