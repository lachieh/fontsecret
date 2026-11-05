"""Load patterns.toml into triggers: the text that, once drawn, starts a secret."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATTERNS = Path(__file__).resolve().parent.parent / "patterns.toml"


@dataclass(frozen=True)
class Kind:
    """How the characters after a trigger are masked. One marker and mask glyph per kind."""

    charset: str
    chars: str
    word_filter: bool

    @property
    def name(self) -> str:
        return f"{self.charset}.w" if self.word_filter else self.charset


@dataclass(frozen=True)
class Trigger:
    text: str
    kind: Kind
    source: str


@dataclass(frozen=True)
class Patterns:
    keep: int
    triggers: tuple[Trigger, ...]

    @property
    def kinds(self) -> tuple[Kind, ...]:
        return tuple(dict.fromkeys(t.kind for t in self.triggers))


def expand_charset(spec: str) -> str:
    """Expand `A-Za-z0-9_-` style ranges; a trailing or leading `-` is literal."""
    chars: list[str] = []
    i = 0
    while i < len(spec):
        if i + 2 < len(spec) and spec[i + 1] == "-":
            chars.extend(chr(c) for c in range(ord(spec[i]), ord(spec[i + 2]) + 1))
            i += 3
        else:
            chars.append(spec[i])
            i += 1
    return "".join(dict.fromkeys(chars))


def load(path: Path = DEFAULT_PATTERNS) -> Patterns:
    data = tomllib.loads(path.read_text())
    charsets = {name: expand_charset(spec) for name, spec in data["charsets"].items()}

    def kind(entry: dict, word_filter: bool) -> Kind:
        name = entry["charset"]
        return Kind(name, charsets[name], entry.get("word_filter", word_filter))

    triggers: list[Trigger] = []
    for entry in data.get("prefix", []):
        k = kind(entry, False)
        triggers += [Trigger(s, k, entry["issuer"]) for s in entry["starts"]]
    for entry in data.get("assignment", []):
        k = kind(entry, True)
        triggers += [
            Trigger(form.replace("{}", name), k, entry["note"])
            for name in entry["names"]
            for form in entry["forms"]
        ]

    _check(triggers)
    return Patterns(keep=data["keep"], triggers=tuple(triggers))


def _check(triggers: list[Trigger]) -> None:
    seen: dict[str, Trigger] = {}
    for t in triggers:
        if t.text in seen:
            raise ValueError(f"duplicate trigger {t.text!r}")
        if not t.text.isascii() or not t.text.isprintable():
            raise ValueError(f"trigger {t.text!r} must be printable ASCII")
        seen[t.text] = t
    for a in seen:
        for b in seen:
            # A rule that ends with a shorter trigger's text would never fire: the shorter
            # trigger's marker replaces the same last glyph first. Word-start triggers are
            # exempt when the extra text ends in a non-word character (TOKEN= inside GITHUB_TOKEN=).
            if a != b and b.endswith(a):
                prefix = b[: -len(a)]
                if not (re.match(r"\w", a) and re.search(r"[^A-Za-z0-9]$", prefix)):
                    raise ValueError(f"trigger {b!r} ends with trigger {a!r}")
