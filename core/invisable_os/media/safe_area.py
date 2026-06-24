"""Safe-area geometry and the Visual Layout Agent.

This is the upgrade that separates "AI content spam" from "proper media team
output": it stops the studio shipping captions over faces, text under the TikTok
buttons, or graphics jammed into the platform UI.

Everything here is **deterministic geometry** in normalised coordinates — fractions
of the frame in ``[0, 1]`` with the origin at the top-left. It needs no GPU and is
fully testable. The heavy detectors (OpenCV/YOLO faces, OCR text, logo detection)
feed this layer a list of :class:`Region` boxes; the placement solver then finds a
spot for each caption/overlay that clears the platform UI *and* the protected
regions, or reports exactly what it could not avoid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from invisable_os.models.content import Platform


class Surface(StrEnum):
    """The publishing surface within a platform — drives which UI overlays apply."""

    REEL = "reel"  # full-screen 9:16 short video (TikTok / Reels / Shorts)
    FEED = "feed"  # in-feed post (image / 4:5 / 1:1)
    STORY = "story"  # 9:16 ephemeral story / status
    CAROUSEL = "carousel"  # multi-slide feed post


class Aspect(StrEnum):
    VERTICAL_9_16 = "9:16"
    SQUARE_1_1 = "1:1"
    PORTRAIT_4_5 = "4:5"
    LANDSCAPE_16_9 = "16:9"


# Canonical export resolutions per aspect (width, height) — what FFmpeg targets.
ASPECT_RESOLUTION: dict[Aspect, tuple[int, int]] = {
    Aspect.VERTICAL_9_16: (1080, 1920),
    Aspect.SQUARE_1_1: (1080, 1080),
    Aspect.PORTRAIT_4_5: (1080, 1350),
    Aspect.LANDSCAPE_16_9: (1920, 1080),
}


def aspect_ratio(width: int, height: int) -> float:
    return round(width / height, 4) if height else 0.0


def matches_aspect(width: int, height: int, aspect: Aspect, *, tol: float = 0.02) -> bool:
    """Whether a (w, h) is the given aspect within a small tolerance."""
    target_w, target_h = ASPECT_RESOLUTION[aspect]
    return abs(aspect_ratio(width, height) - aspect_ratio(target_w, target_h)) <= tol


@dataclass(frozen=True)
class Box:
    """A rectangle in normalised frame coordinates, origin top-left, in ``[0, 1]``."""

    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if not (self.x0 <= self.x1 and self.y0 <= self.y1):
            raise ValueError(f"degenerate box: {self}")

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height

    def intersection(self, other: Box) -> Box | None:
        x0, y0 = max(self.x0, other.x0), max(self.y0, other.y0)
        x1, y1 = min(self.x1, other.x1), min(self.y1, other.y1)
        if x0 >= x1 or y0 >= y1:
            return None
        return Box(x0, y0, x1, y1)

    def intersects(self, other: Box, *, min_overlap: float = 0.0) -> bool:
        """True if the boxes overlap by more than ``min_overlap`` (absolute area)."""
        inter = self.intersection(other)
        return inter is not None and inter.area > min_overlap

    def overlap_fraction(self, other: Box) -> float:
        """Fraction of *this* box covered by ``other`` (0–1)."""
        inter = self.intersection(other)
        return inter.area / self.area if inter and self.area else 0.0

    def contains(self, other: Box, *, tol: float = 1e-9) -> bool:
        return (
            self.x0 - tol <= other.x0 and self.y0 - tol <= other.y0
            and self.x1 + tol >= other.x1 and self.y1 + tol >= other.y1
        )

    def as_dict(self) -> dict[str, float]:
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}


class RegionKind(StrEnum):
    """What a detector found that must not be covered."""

    FACE = "face"
    FOUNDER_FACE = "founder_face"
    COMMUNITY_FACE = "community_face"
    HAND_TOOL_PRODUCT = "hand_tool_product"
    LOGO = "logo"
    SPONSOR_PRODUCT = "sponsor_product"
    ON_SCREEN_TEXT = "on_screen_text"
    IMPORTANT_TEXT = "important_text"


@dataclass(frozen=True)
class Region:
    """A protected region the layout must not cover, from a detector or annotation."""

    kind: RegionKind
    box: Box
    confidence: float = 1.0
    label: str = ""


@dataclass(frozen=True)
class ExclusionZone:
    """A slice of the frame owned by the platform UI — keep captions/graphics out."""

    name: str
    box: Box
    reason: str


@dataclass(frozen=True)
class SafeAreaTemplate:
    """Per-platform, per-surface safe-area map."""

    platform: Platform
    surface: Surface
    aspect: Aspect
    exclusions: tuple[ExclusionZone, ...]
    title_safe: Box  # captions & important graphics should live inside this box

    def obstructed_zones(self, box: Box) -> list[str]:
        """Names of UI exclusion zones a given box collides with."""
        return [z.name for z in self.exclusions if box.intersects(z.box)]

    def within_title_safe(self, box: Box) -> bool:
        return self.title_safe.contains(box)

    def is_clear(self, box: Box) -> bool:
        """A box is clear if it sits inside the title-safe area and hits no UI zone."""
        return self.within_title_safe(box) and not self.obstructed_zones(box)


# --- Platform safe-area templates -------------------------------------------
#
# Coordinates are deliberately conservative. They model where the platform paints
# its own chrome (handle, caption, action rail, top status) over a 9:16 frame, plus
# the inner title-safe area for our own text. Tuned to public UI layouts; centralised
# here so they are easy to adjust as platforms change.


def _vertical_template(
    platform: Platform, surface: Surface, *, right_rail: Box, bottom: Box
) -> SafeAreaTemplate:
    return SafeAreaTemplate(
        platform=platform,
        surface=surface,
        aspect=Aspect.VERTICAL_9_16,
        exclusions=(
            ExclusionZone("top_ui", Box(0.0, 0.0, 1.0, 0.08), "status bar / top controls"),
            ExclusionZone("right_rail", right_rail, "like / comment / share / icons"),
            ExclusionZone("bottom_caption_cta", bottom, "creator handle / caption / CTA"),
        ),
        # Title-safe: clear of top UI, the right rail and the bottom caption band.
        title_safe=Box(0.06, 0.12, right_rail.x0 - 0.01, bottom.y0 - 0.01),
    )


SAFE_AREAS: dict[tuple[Platform, Surface], SafeAreaTemplate] = {
    (Platform.TIKTOK, Surface.REEL): _vertical_template(
        Platform.TIKTOK, Surface.REEL,
        right_rail=Box(0.84, 0.32, 1.0, 0.88),
        bottom=Box(0.0, 0.80, 1.0, 1.0),
    ),
    (Platform.INSTAGRAM, Surface.REEL): _vertical_template(
        Platform.INSTAGRAM, Surface.REEL,
        right_rail=Box(0.86, 0.40, 1.0, 0.86),
        bottom=Box(0.0, 0.78, 1.0, 1.0),
    ),
    (Platform.YOUTUBE, Surface.REEL): _vertical_template(
        Platform.YOUTUBE, Surface.REEL,
        right_rail=Box(0.85, 0.45, 1.0, 0.90),
        bottom=Box(0.0, 0.82, 1.0, 1.0),
    ),
    (Platform.INSTAGRAM, Surface.STORY): SafeAreaTemplate(
        platform=Platform.INSTAGRAM, surface=Surface.STORY, aspect=Aspect.VERTICAL_9_16,
        exclusions=(
            ExclusionZone("top_ui", Box(0.0, 0.0, 1.0, 0.10), "profile / progress bar"),
            ExclusionZone("bottom_ui", Box(0.0, 0.86, 1.0, 1.0), "reply bar / share"),
        ),
        title_safe=Box(0.06, 0.14, 0.94, 0.84),
    ),
    (Platform.INSTAGRAM, Surface.FEED): SafeAreaTemplate(
        platform=Platform.INSTAGRAM, surface=Surface.FEED, aspect=Aspect.PORTRAIT_4_5,
        exclusions=(),  # in-feed images own the whole frame; just keep a margin.
        title_safe=Box(0.05, 0.05, 0.95, 0.95),
    ),
    (Platform.INSTAGRAM, Surface.CAROUSEL): SafeAreaTemplate(
        platform=Platform.INSTAGRAM, surface=Surface.CAROUSEL, aspect=Aspect.PORTRAIT_4_5,
        exclusions=(
            ExclusionZone("dots", Box(0.30, 0.96, 0.70, 1.0), "carousel position dots"),
        ),
        title_safe=Box(0.06, 0.06, 0.94, 0.92),
    ),
}


def get_template(platform: Platform, surface: Surface) -> SafeAreaTemplate | None:
    return SAFE_AREAS.get((platform, surface))


# --- Placement result --------------------------------------------------------


@dataclass(frozen=True)
class Placement:
    """Where the Visual Layout Agent decided to put a caption/overlay (or why not)."""

    ok: bool
    box: Box | None
    blocked_by: tuple[str, ...] = ()
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "box": self.box.as_dict() if self.box else None,
            "blocked_by": list(self.blocked_by),
            "note": self.note,
        }


@dataclass
class VisualLayoutAgent:
    """Places captions and overlays where they never block what matters.

    Strategy: caption bands span a safe horizontal width and a small height. We try a
    set of vertical anchors (preferring the lower third, where viewers expect
    captions) and return the first band that sits inside the title-safe area and
    clears every UI exclusion zone *and* every protected region. If none is clear we
    return the least-bad option with the obstructions named, so a human (or the
    Content Recovery Agent) can decide.
    """

    margin: float = 0.06  # side margin inside the title-safe width

    # Vertical anchors to try, as the *top* of the caption band, preferred first.
    anchors: tuple[float, ...] = field(
        default_factory=lambda: (0.66, 0.58, 0.50, 0.42, 0.34, 0.26, 0.18)
    )

    def place_caption(
        self,
        template: SafeAreaTemplate,
        *,
        height: float = 0.12,
        regions: list[Region] | None = None,
    ) -> Placement:
        """Find a clear band for a caption of fractional ``height``."""
        regions = regions or []
        ts = template.title_safe
        x0 = ts.x0 + self.margin  # left edge inside title-safe
        x1 = ts.x1 - self.margin
        if x1 <= x0:
            x0, x1 = ts.x0, ts.x1  # title-safe too narrow for the margin; use it raw

        best: Placement | None = None
        for top in self.anchors:
            bottom = top + height
            if bottom > ts.y1 or top < ts.y0:
                continue
            band = Box(x0, top, x1, bottom)
            ui_hits = template.obstructed_zones(band)
            region_hits = tuple(
                f"{r.kind.value}:{r.label}" if r.label else r.kind.value
                for r in regions
                if band.intersects(r.box)
            )
            blocked = tuple(ui_hits) + region_hits
            if not blocked:
                return Placement(ok=True, box=band, note=f"placed at y={top:.2f}")
            # Remember the candidate with the fewest collisions as a fallback.
            if best is None or len(blocked) < len(best.blocked_by):
                best = Placement(ok=False, box=band, blocked_by=blocked,
                                 note="no fully clear band; least-obstructed shown")
        if best is not None:
            return best
        return Placement(ok=False, box=None, blocked_by=("title_safe",),
                         note="caption height does not fit the title-safe area")

    def check_overlay(
        self,
        template: SafeAreaTemplate,
        overlay: Box,
        *,
        regions: list[Region] | None = None,
    ) -> Placement:
        """Validate a *fixed* overlay box (e.g. a logo bug) against the safe area."""
        regions = regions or []
        ui_hits = template.obstructed_zones(overlay)
        edge = not template.within_title_safe(overlay)
        region_hits = tuple(
            f"{r.kind.value}:{r.label}" if r.label else r.kind.value
            for r in regions
            if overlay.intersects(r.box)
        )
        blocked = tuple(ui_hits) + (("title_safe_edge",) if edge else ()) + region_hits
        if blocked:
            return Placement(ok=False, box=overlay, blocked_by=blocked,
                             note="overlay collides with protected areas")
        return Placement(ok=True, box=overlay, note="overlay clear")
