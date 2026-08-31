"""Sync the browser's LDraw part library with what the backend can actually emit.

THE BUG THIS EXISTS TO PREVENT

`public/ldraw/` is a hand-picked subset of the official library — the full one is
600 MB and the viewer needs a few hundred kilobytes of it. Hand-picked worked
while the generator only ever placed eleven brick sizes. The moment the parts
catalogue grew, the viewer started failing on parts the backend was perfectly
happy to write:

    THREE.LDrawLoader: Subobject "60477.dat" could not be loaded.

and it fails the whole model, not the one part. Nothing in the backend notices,
because the .ldr it produced is valid; the file is only wrong relative to a
library on the other side of the wire. So the subset is computed here, from the
catalogues themselves, and `--check` turns the mismatch into a failing command
instead of a broken render.

WHAT GETS COPIED

Every part any code path can place, plus the transitive closure of what those
parts reference. An LDraw part is not one file: 60477 is a shell that references
`s\\60477s01.dat`, which references primitives in `p/`, which reference each
other. Miss one leaf and the render fails exactly as loudly as missing the part.

    python scripts/build_viewer_library.py --ldraw .data/ldraw            # sync
    python scripts/build_viewer_library.py --ldraw .data/ldraw --check    # verify
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import lego_catalogue as cat  # noqa: E402
from app.services import legolize  # noqa: E402
from app.services import solid_plan  # noqa: E402
from app.services.ldraw import LDRAW_PART  # noqa: E402

# Type-1 lines are the ones that reference another file; the name is the last
# token and may carry a subdirectory in DOS separators.
REF = re.compile(r"^\s*1\s+\S+(?:\s+\S+){12}\s+(\S+)\s*$")


def emittable() -> set[str]:
    """Every part number any code path can place.

    Discovered by introspection over the catalogue module rather than listed,
    because a list goes stale silently. The first version named three tables and
    missed TILES, so the tiles the relief path caps its walls with were reported
    as *unused* — the checker would have signed off on a library that could not
    draw them. Anything the catalogue exposes as a sequence of parts is fair
    game, which also means a family added later is covered without editing this.
    """
    parts: set[str] = set()
    for name in dir(cat):
        value = getattr(cat, name)
        if isinstance(value, (list, tuple)) and value:
            if all(hasattr(v, "part_num") for v in value):
                parts |= {v.part_num for v in value}
    parts |= {s.part_num for s in solid_plan.SLOPES.values()}  # solid roofline
    parts |= set(legolize.ROOF_SLOPES.values())  # relief roofline
    # The writer substitutes a few numbers on the way out; ship what it writes.
    return {LDRAW_PART.get(p, p) for p in parts}


def resolve(ref: str, root: Path) -> str | None:
    """An LDraw reference -> its path relative to the library root."""
    rel = ref.replace("\\", "/").lower()
    for base in ("parts", "p"):
        if (root / base / rel).exists():
            return f"{base}/{rel}"
    return None


def closure(seeds: set[str], root: Path) -> tuple[set[str], set[str]]:
    """Every file needed to draw `seeds`, and the references that did not resolve."""
    found: set[str] = set()
    missing: set[str] = set()
    queue: deque[str] = deque(f"{p}.dat" for p in seeds)
    while queue:
        ref = queue.popleft()
        rel = resolve(ref, root)
        if rel is None:
            missing.add(ref)
            continue
        if rel in found:
            continue
        found.add(rel)
        for line in (root / rel).read_text(errors="replace").splitlines():
            m = REF.match(line)
            if m:
                queue.append(m.group(1))
    return found, missing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ldraw", required=True, type=Path, help="unpacked LDraw library")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "nebular-design/public/ldraw",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="report what is missing and exit non-zero; copy nothing",
    )
    args = ap.parse_args()

    seeds = emittable()
    needed, missing = closure(seeds, args.ldraw)
    if missing:
        print(f"UNRESOLVED in the LDraw library: {sorted(missing)}", file=sys.stderr)
        raise SystemExit(1)

    have = {
        str(p.relative_to(args.out))
        for p in args.out.rglob("*.dat")
    }
    absent = needed - have
    stale = have - needed

    print(f"{len(seeds)} placeable parts -> {len(needed)} files with dependencies")
    print(f"  viewer has {len(have)}, missing {len(absent)}, unused {len(stale)}")

    if args.check:
        if absent:
            print("MISSING from the viewer library:", file=sys.stderr)
            for rel in sorted(absent):
                print(f"  {rel}", file=sys.stderr)
            raise SystemExit(1)
        print("viewer library is complete")
        return

    for rel in sorted(absent):
        dest = args.out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.ldraw / rel, dest)
    # LDConfig carries the colour definitions. Copied wholesale: it is 30 KB and
    # a missing colour is the same class of silent failure as a missing part.
    shutil.copyfile(args.ldraw / "LDConfig.ldr", args.out / "LDConfig.ldr")
    print(f"copied {len(absent)} file(s)")


if __name__ == "__main__":
    main()
