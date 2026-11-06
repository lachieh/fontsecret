"""Exercise patch defaults and feature selection through the public CLI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from fontsecret import font as patcher
from fontsecret.patterns import load

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "fonts" / "in"


def patch_cli(source, output, *options):
    return subprocess.run(
        [sys.executable, "-m", "fontsecret", "patch", str(source), str(output), *options],
        cwd=ROOT, capture_output=True, text=True,
    )


def tags(font):
    return {r.FeatureTag for r in font["GSUB"].table.FeatureList.FeatureRecord}


@pytest.mark.parametrize("name", ["CascadiaCode.ttf", "SourceCodePro-Regular.otf"])
@pytest.mark.parametrize("options, suffix", [((), " Masked"), (("--suffix", ""), "")])
def test_patch_defaults(name, options, suffix, tmp_path):
    source = INPUTS / name
    output = tmp_path / name
    result = patch_cli(source, output, *options)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["feature"] == "MASK"
    with TTFont(source) as original, TTFont(output) as patched:
        assert tags(patched) - tags(original) == {"MASK"}
        assert patched["name"].getBestFamilyName() == original["name"].getBestFamilyName() + suffix


def test_feature_override(tmp_path):
    output = tmp_path / "custom.ttf"
    result = patch_cli(INPUTS / "CascadiaCode.ttf", output, "--feature", "TEST")
    assert result.returncode == 0, result.stderr
    with TTFont(output) as font:
        assert "TEST" in tags(font)
        assert "MASK" not in tags(font)


@pytest.mark.parametrize("options, tag", [((), "MASK"), (("--feature", "ss19"), "ss19")])
def test_existing_feature_is_rejected(options, tag, tmp_path):
    source = tmp_path / "existing.ttf"
    with TTFont(INPUTS / "CascadiaCode.ttf") as font:
        # Give an original feature the requested tag without adding any masking glyphs.
        next(r for r in font["GSUB"].table.FeatureList.FeatureRecord
             if r.FeatureTag == "ss19").FeatureTag = tag
        font.save(source)
    output = tmp_path / "patched.ttf"
    result = patch_cli(source, output, *options)
    assert result.returncode != 0
    assert f"feature {tag!r} already exists" in result.stderr
    assert not output.exists()


def test_always_on_and_feature_are_mutually_exclusive(tmp_path):
    result = patch_cli(INPUTS / "CascadiaCode.ttf", tmp_path / "patched.ttf",
                       "--always-on", "--feature", "MASK")
    assert result.returncode != 0
    assert "not allowed with argument" in result.stderr


def test_patch_api_defaults_to_mask():
    with TTFont(INPUTS / "CascadiaCode.ttf") as font:
        report = patcher.patch(font, load())
        assert report["feature"] == "MASK"
        assert "MASK" in tags(font)
