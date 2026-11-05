"""fontsecret: add on-screen masking of known secret tokens to a font.

    uv run python -m fontsecret IN.ttf OUT.ttf [--feature ss20 | --always-on] [--suffix "Masked"]
"""

import argparse
import json
from pathlib import Path

from fontTools.ttLib import TTFont

from . import font as patcher
from .patterns import DEFAULT_PATTERNS, load


def main() -> None:
    ap = argparse.ArgumentParser(prog="fontsecret", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--patterns", type=Path, default=DEFAULT_PATTERNS)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--feature", help="feature tag to put masking under (default: highest free ssNN)")
    group.add_argument("--always-on", action="store_true",
                       help=f"put masking in {patcher.ALWAYS_ON}, which shapers always apply")
    ap.add_argument("--suffix", help="append to the family name (needed for OFL fonts with a Reserved Font Name)")
    args = ap.parse_args()

    font = TTFont(args.input)
    report = patcher.patch(font, load(args.patterns),
                           patcher.ALWAYS_ON if args.always_on else args.feature)
    if args.suffix:
        patcher.rename(font, args.suffix)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    font.save(args.output)
    print(json.dumps({"output": str(args.output), **report}))


if __name__ == "__main__":
    main()
