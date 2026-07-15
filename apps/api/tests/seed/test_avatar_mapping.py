from __future__ import annotations

import re
from pathlib import Path

from levels_api.seed.loader import SVG_REGIONS


def test_every_seeded_highlightable_muscle_has_a_rendered_svg_region() -> None:
    repository_root = Path(__file__).resolve().parents[4]
    avatar_source = (
        repository_root / "apps" / "web" / "src" / "features" / "avatar" / "Avatar.tsx"
    ).read_text(encoding="utf-8")
    rendered_regions = set(re.findall(r'\{ id: "([a-z_]+)", shapes:', avatar_source))

    seeded_regions = {region for regions in SVG_REGIONS.values() for region in regions}

    assert seeded_regions
    assert seeded_regions <= rendered_regions
    assert SVG_REGIONS["cardiovascular"] == []
    assert SVG_REGIONS["full_body"] == []
