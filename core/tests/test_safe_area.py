"""Safe-area geometry and the Visual Layout Agent — the headline upgrade.

These tests prove the deterministic geometry that stops captions landing on faces,
under the platform UI, or off the edge.
"""

import pytest

from invisable_os.media.safe_area import (
    Aspect,
    Box,
    Region,
    RegionKind,
    Surface,
    VisualLayoutAgent,
    get_template,
    matches_aspect,
)
from invisable_os.models.content import Platform

# --- Box geometry -----------------------------------------------------------


def test_box_rejects_degenerate():
    with pytest.raises(ValueError):
        Box(0.5, 0.0, 0.4, 1.0)


def test_box_intersection_and_overlap():
    a = Box(0.0, 0.0, 0.5, 0.5)
    b = Box(0.25, 0.25, 0.75, 0.75)
    inter = a.intersection(b)
    assert inter == Box(0.25, 0.25, 0.5, 0.5)
    assert a.intersects(b)
    assert a.overlap_fraction(b) == pytest.approx(0.25)  # quarter of a covered
    assert not a.intersects(Box(0.6, 0.6, 0.9, 0.9))


def test_box_contains():
    outer = Box(0.0, 0.0, 1.0, 1.0)
    assert outer.contains(Box(0.1, 0.1, 0.9, 0.9))
    assert not Box(0.2, 0.2, 0.8, 0.8).contains(Box(0.1, 0.1, 0.9, 0.9))


# --- Aspect ratios ----------------------------------------------------------


def test_aspect_matching():
    assert matches_aspect(1080, 1920, Aspect.VERTICAL_9_16)
    assert matches_aspect(1080, 1080, Aspect.SQUARE_1_1)
    assert matches_aspect(1080, 1350, Aspect.PORTRAIT_4_5)
    assert not matches_aspect(1080, 1080, Aspect.VERTICAL_9_16)


# --- Templates --------------------------------------------------------------


def test_every_template_title_safe_clears_its_exclusions():
    for (platform, surface), template in _all_templates():
        for zone in template.exclusions:
            # The title-safe area must not poke into any UI zone (allowing tangency).
            assert template.title_safe.overlap_fraction(zone.box) < 0.02, (
                f"{platform}/{surface} title-safe overlaps {zone.name}"
            )


def test_tiktok_reel_has_the_expected_ui_zones():
    t = get_template(Platform.TIKTOK, Surface.REEL)
    names = {z.name for z in t.exclusions}
    assert {"top_ui", "right_rail", "bottom_caption_cta"} <= names


def _all_templates():
    from invisable_os.media.safe_area import SAFE_AREAS

    return list(SAFE_AREAS.items())


# --- Visual Layout Agent ----------------------------------------------------


def test_places_caption_in_lower_third_on_clear_frame():
    t = get_template(Platform.TIKTOK, Surface.REEL)
    p = VisualLayoutAgent().place_caption(t, height=0.12)
    assert p.ok and p.box is not None
    assert t.is_clear(p.box)
    assert p.box.y0 >= 0.5  # prefers the lower third where viewers expect captions


def test_caption_moves_off_the_founders_face():
    t = get_template(Platform.TIKTOK, Surface.REEL)
    face = Region(RegionKind.FOUNDER_FACE, Box(0.25, 0.55, 0.75, 0.85), label="stephen")
    p = VisualLayoutAgent().place_caption(t, height=0.12, regions=[face])
    assert p.ok and p.box is not None
    assert not p.box.intersects(face.box), "caption must not cover the founder's face"
    assert t.is_clear(p.box)


def test_reports_when_no_clear_band_exists():
    t = get_template(Platform.TIKTOK, Surface.REEL)
    # A face spanning the whole title-safe height leaves nowhere clear.
    wall = Region(RegionKind.FACE, Box(0.0, 0.12, 1.0, 0.80))
    p = VisualLayoutAgent().place_caption(t, height=0.12, regions=[wall])
    assert not p.ok
    assert p.blocked_by  # names what it collided with


def test_check_overlay_flags_logo_over_ui_and_edge():
    t = get_template(Platform.TIKTOK, Surface.REEL)
    # Overlay sitting in the bottom CTA band and off the title-safe edge.
    bad = Box(0.05, 0.90, 0.95, 0.99)
    p = VisualLayoutAgent().check_overlay(t, bad)
    assert not p.ok
    assert "bottom_caption_cta" in p.blocked_by
