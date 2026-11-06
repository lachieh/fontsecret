"""fontsecret: draw known secret tokens as dots in any OpenType font.

    uv run python -m fontsecret patch IN.ttf OUT.ttf [--feature MASK | --always-on] [--suffix Masked]
    uv run python -m fontsecret verify ORIGINAL.ttf PATCHED.ttf

By default, masking is opt-in under MASK and the family name gets a Masked suffix.
Use --always-on for ccmp masking, or --suffix "" to keep the original family name.
"""

import argparse
import json
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

from . import font as patcher
from .patterns import DEFAULT_PATTERNS, load
from .verify import verify


def main() -> None:
    ap = argparse.ArgumentParser(prog="fontsecret", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("patch", help="write a copy of a font that masks secrets")
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--patterns", type=Path, default=DEFAULT_PATTERNS)
    group = p.add_mutually_exclusive_group()
    group.add_argument("--feature", default=patcher.DEFAULT_FEATURE,
                       help=f"feature tag to put masking under (default: {patcher.DEFAULT_FEATURE})")
    group.add_argument("--always-on", action="store_true",
                       help=f"put masking in {patcher.ALWAYS_ON}, which shapers always apply")
    p.add_argument("--suffix", default="Masked",
                   help='append to the family name (default: Masked); use "" to keep the original name')

    v = sub.add_parser("verify", help="check a patched font differs from its original only by masking")
    v.add_argument("original", type=Path)
    v.add_argument("patched", type=Path)

    args = ap.parse_args()
    if args.command == "patch":
        font = TTFont(args.input)
        try:
            report = patcher.patch(font, load(args.patterns),
                                   patcher.ALWAYS_ON if args.always_on else args.feature)
        except patcher.Unsupported as error:
            p.error(str(error))
        if args.suffix:
            patcher.rename(font, args.suffix)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        font.save(args.output)
        print(json.dumps({"output": str(args.output), **report}))
    else:
        result = verify(TTFont(args.original), TTFont(args.patched))
        for note in result.notes:
            print(f"note: {note}")
        for error in result.errors:
            print(f"FAIL: {error}")
        print("OK: only masking was added" if result.ok else f"{len(result.errors)} problems")
        sys.exit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
