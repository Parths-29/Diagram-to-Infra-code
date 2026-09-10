"""
Utility functions for synthetic dataset generation.

Handles YOLO annotation formatting, bounding-box normalization,
and image augmentation transforms.
"""

import random
import math
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np


# ── Class IDs (must match dataset.yaml) ──────────────────────────────────────
CLASS_NAMES = [
    "compute",        # 0
    "database",       # 1
    "storage",        # 2
    "load_balancer",  # 3
    "network",        # 4
    "arrow",          # 5
    "text_label",     # 6
]

CLASS_ID = {name: idx for idx, name in enumerate(CLASS_NAMES)}


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class BBox:
    """Axis-aligned bounding box in pixel coordinates."""
    x1: int
    y1: int
    x2: int
    y2: int
    class_id: int
    label: str = ""

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def w(self) -> int:
        return self.x2 - self.x1

    @property
    def h(self) -> int:
        return self.y2 - self.y1

    def to_yolo(self, img_w: int, img_h: int) -> str:
        """Convert to YOLO format: <class_id> <cx> <cy> <w> <h> (normalized)."""
        cx = self.cx / img_w
        cy = self.cy / img_h
        w = self.w / img_w
        h = self.h / img_h
        # Clamp to [0, 1]
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        w = max(0.001, min(1.0, w))
        h = max(0.001, min(1.0, h))
        return f"{self.class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


@dataclass
class ArrowSpec:
    """Specification for an arrow connecting two components."""
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    bbox: Optional[BBox] = None


@dataclass
class ComponentSpec:
    """Specification for a diagram component."""
    class_name: str
    subtype: str
    label: str
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    bbox: Optional[BBox] = None


# ── Color Palettes (hand-drawn style) ───────────────────────────────────────

# Background colors (whiteboard / paper)
BG_COLORS = [
    (255, 255, 255),  # white
    (245, 245, 240),  # off-white
    (250, 248, 230),  # cream
    (240, 240, 245),  # light gray-blue
    (248, 248, 248),  # very light gray
]

# Augmented paper style tags — used by draw_paper_background()
PAPER_STYLES = ["plain", "lined", "grid", "plain"]  # plain weighted 2x intentionally

# Pen colors for drawing shapes
PEN_COLORS = [
    (0, 0, 0),        # black
    (30, 30, 80),     # dark blue-black
    (0, 0, 180),      # blue marker
    (180, 0, 0),      # red marker
    (0, 120, 0),      # green marker
    (50, 50, 50),     # dark gray
]

# Fill colors for component boxes (lighter, like whiteboard fills)
FILL_COLORS = {
    "compute": [(200, 220, 255), (180, 210, 255), (220, 230, 250)],
    "database": [(255, 220, 200), (255, 210, 180), (250, 225, 210)],
    "storage": [(200, 255, 200), (180, 240, 190), (210, 250, 210)],
    "load_balancer": [(255, 255, 200), (255, 250, 180), (250, 245, 210)],
    "network": [(240, 240, 255), (230, 230, 250), (235, 235, 245)],
}

# Labels per component type
COMPONENT_LABELS = {
    "compute": {
        "ec2": ["Web Server", "App Server", "API Server", "Worker",
                "Backend", "Server", "EC2", "Instance", "Compute",
                "Web App", "Service", "Node"],
        "eks": ["K8s Cluster", "EKS", "Container", "Kubernetes",
                "K8s", "Cluster"],
    },
    "database": {
        "rds": ["Database", "DB", "RDS", "MySQL", "PostgreSQL",
                "Postgres", "SQL DB", "Main DB", "User DB", "Data Store"],
    },
    "storage": {
        "s3": ["S3 Bucket", "Storage", "S3", "Bucket", "Files",
               "Assets", "Static Files", "Object Store", "Data Lake"],
    },
    "load_balancer": {
        "alb": ["Load Balancer", "ALB", "LB", "ELB", "Balancer",
                "Gateway", "Entry Point", "Ingress"],
    },
    "network": {
        "vpc": ["VPC", "Network", "Subnet", "Private Net",
                "Public Subnet", "Private Subnet", "Cloud Network"],
    },
}


# ── Drawing Helpers ──────────────────────────────────────────────────────────

def jitter_point(x: int, y: int, amount: int = 3) -> tuple[int, int]:
    """Add small random jitter to a point to simulate hand-drawn imperfection."""
    return (
        x + random.randint(-amount, amount),
        y + random.randint(-amount, amount),
    )


def draw_hand_drawn_rect(
    img: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    color: tuple[int, int, int],
    thickness: int = 2,
    fill_color: Optional[tuple[int, int, int]] = None,
    rounded: bool = False,
) -> None:
    """Draw a rectangle with slight hand-drawn wobble."""
    if fill_color is not None:
        if rounded:
            # Rounded rectangle fill
            radius = min(10, (x2 - x1) // 8, (y2 - y1) // 8)
            _draw_rounded_rect_filled(img, x1, y1, x2, y2, radius, fill_color)
        else:
            cv2.rectangle(img, (x1, y1), (x2, y2), fill_color, -1)

    # Draw edges with slight wobble
    points = [
        jitter_point(x1, y1), jitter_point(x2, y1),
        jitter_point(x2, y2), jitter_point(x1, y2),
    ]
    for i in range(4):
        p1 = points[i]
        p2 = points[(i + 1) % 4]
        cv2.line(img, p1, p2, color, thickness, cv2.LINE_AA)


def _draw_rounded_rect_filled(
    img: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    radius: int, color: tuple[int, int, int],
) -> None:
    """Draw a filled rounded rectangle."""
    # Center rectangle
    cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1)
    cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1)
    # Corner circles
    cv2.circle(img, (x1 + radius, y1 + radius), radius, color, -1)
    cv2.circle(img, (x2 - radius, y1 + radius), radius, color, -1)
    cv2.circle(img, (x1 + radius, y2 - radius), radius, color, -1)
    cv2.circle(img, (x2 - radius, y2 - radius), radius, color, -1)


def draw_hand_drawn_cylinder(
    img: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    color: tuple[int, int, int],
    thickness: int = 2,
    fill_color: Optional[tuple[int, int, int]] = None,
) -> None:
    """Draw a cylinder shape (for databases) with hand-drawn wobble."""
    cx = (x1 + x2) // 2
    w = x2 - x1
    h = y2 - y1
    ellipse_h = max(h // 6, 8)

    if fill_color is not None:
        # Fill body
        cv2.rectangle(img, (x1, y1 + ellipse_h // 2),
                       (x2, y2 - ellipse_h // 2), fill_color, -1)
        # Fill top/bottom ellipses
        cv2.ellipse(img, (cx, y1 + ellipse_h // 2),
                    (w // 2, ellipse_h // 2), 0, 0, 360, fill_color, -1)
        cv2.ellipse(img, (cx, y2 - ellipse_h // 2),
                    (w // 2, ellipse_h // 2), 0, 0, 360, fill_color, -1)

    # Draw outline
    # Top ellipse (full)
    cv2.ellipse(img, jitter_point(cx, y1 + ellipse_h // 2, 1),
                (w // 2, ellipse_h // 2), 0, 0, 360, color, thickness, cv2.LINE_AA)
    # Bottom ellipse (front half only)
    cv2.ellipse(img, jitter_point(cx, y2 - ellipse_h // 2, 1),
                (w // 2, ellipse_h // 2), 0, 0, 180, color, thickness, cv2.LINE_AA)
    # Side lines
    cv2.line(img, jitter_point(x1, y1 + ellipse_h // 2),
             jitter_point(x1, y2 - ellipse_h // 2), color, thickness, cv2.LINE_AA)
    cv2.line(img, jitter_point(x2, y1 + ellipse_h // 2),
             jitter_point(x2, y2 - ellipse_h // 2), color, thickness, cv2.LINE_AA)


def draw_hand_drawn_arrow(
    img: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    color: tuple[int, int, int],
    thickness: int = 2,
) -> BBox:
    """Draw an arrow with slight hand-drawn wobble. Returns the bounding box."""
    # Add a mid-point with jitter for natural curve
    mx = (x1 + x2) // 2 + random.randint(-5, 5)
    my = (y1 + y2) // 2 + random.randint(-5, 5)

    # Draw line segments
    p1 = jitter_point(x1, y1, 2)
    pm = (mx, my)
    p2 = jitter_point(x2, y2, 2)
    cv2.line(img, p1, pm, color, thickness, cv2.LINE_AA)
    cv2.line(img, pm, p2, color, thickness, cv2.LINE_AA)

    # Draw arrowhead
    angle = math.atan2(y2 - my, x2 - mx)
    arrow_len = random.randint(10, 18)
    arrow_angle = math.radians(random.randint(25, 40))

    ax1 = int(x2 - arrow_len * math.cos(angle - arrow_angle))
    ay1 = int(y2 - arrow_len * math.sin(angle - arrow_angle))
    ax2 = int(x2 - arrow_len * math.cos(angle + arrow_angle))
    ay2 = int(y2 - arrow_len * math.sin(angle + arrow_angle))

    cv2.line(img, p2, jitter_point(ax1, ay1, 1), color, thickness, cv2.LINE_AA)
    cv2.line(img, p2, jitter_point(ax2, ay2, 1), color, thickness, cv2.LINE_AA)

    # Compute bounding box for the arrow (including arrowhead)
    all_x = [x1, x2, mx, ax1, ax2]
    all_y = [y1, y2, my, ay1, ay2]
    pad = thickness + 3
    bbox = BBox(
        x1=max(0, min(all_x) - pad),
        y1=max(0, min(all_y) - pad),
        x2=max(all_x) + pad,
        y2=max(all_y) + pad,
        class_id=CLASS_ID["arrow"],
    )
    return bbox


def draw_text_label(
    img: np.ndarray,
    text: str,
    x: int, y: int,
    color: tuple[int, int, int],
    font_scale: float = 0.5,
    thickness: int = 1,
) -> BBox:
    """Draw a text label and return its bounding box."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)

    # Center the text at (x, y)
    tx = x - tw // 2
    ty = y + th // 2

    cv2.putText(img, text, (tx, ty), font, font_scale, color,
                thickness, cv2.LINE_AA)

    pad = 3
    bbox = BBox(
        x1=max(0, tx - pad),
        y1=max(0, ty - th - pad),
        x2=tx + tw + pad,
        y2=ty + baseline + pad,
        class_id=CLASS_ID["text_label"],
        label=text,
    )
    return bbox


# ── Augmentation ─────────────────────────────────────────────────────────────

# ── New Background & Ink Helpers ────────────────────────────────────────────

def draw_paper_background(
    img: np.ndarray,
    style: str = "plain",
    bg_color: Optional[tuple] = None,
) -> np.ndarray:
    """
    Draw a paper background onto `img` in-place.

    Styles:
        'plain'  - solid fill (original behaviour)
        'lined'  - ruled horizontal lines (thin, light gray)
        'grid'   - grid lines (thin, light gray)

    Ruled-line design constraints:
        - 1px stroke, color is bg_color darkened by 10-15 DN — NOT drawn at
          handwriting contrast so the model doesn't fire text_label on them.
        - Spacing is 18-22px, consistent per image.
        - Lines start and end slightly inside the canvas edge so they don't
          form a bounding box that confuses the arrow detector.
    """
    h, w = img.shape[:2]
    if bg_color is None:
        bg_color = random.choice(BG_COLORS)
    img[:] = bg_color

    if style in ("lined", "grid"):
        # Line color: darken the bg by ~12-18 DN in each channel, clamp to 0
        darken = random.randint(12, 18)
        line_color = tuple(max(0, c - darken) for c in bg_color)
        spacing = random.randint(18, 22)
        margin_x = 8

        if style in ("lined", "grid"):
            # Horizontal lines
            y = spacing
            while y < h - spacing:
                cv2.line(img, (margin_x, y), (w - margin_x, y),
                         line_color, 1, cv2.LINE_AA)
                y += spacing

        if style == "grid":
            # Vertical lines
            x = spacing
            while x < w - spacing:
                cv2.line(img, (x, margin_x), (x, h - margin_x),
                         line_color, 1, cv2.LINE_AA)
                x += spacing

    return img


def draw_strokes_with_variable_thickness(
    img: np.ndarray,
    pen_color: tuple,
    thickness: int,
) -> tuple:
    """
    Return a (possibly-modified) pen_color and thickness pair that simulates
    ink variation within realistic bounds.

    - Thickness: 1-4px uniform random per image
    - Color: darken or lighten by up to 30 DN per channel so the pen looks
      like it's running dry (lighter) or freshly inked (darker).
    """
    t = random.randint(1, 4)
    shift = random.randint(-30, 30)
    varied = tuple(int(max(0, min(255, c + shift))) for c in pen_color)
    return varied, t


def augment_perspective_warp(
    img: np.ndarray,
    max_offset_frac: float = 0.12,
) -> np.ndarray:
    """
    Apply a bounded perspective warp to simulate an angled phone photo.

    Each corner is displaced by up to `max_offset_frac` * dimension in X and Y.
    Capped at 12% by default so component aspect ratios stay recognisable
    (a square EC2 box warped >30% starts looking like a parallelogram the
    model has never seen).

    The warped output is the same size as the input (canvas-fit).
    """
    h, w = img.shape[:2]
    max_dx = int(w * max_offset_frac)
    max_dy = int(h * max_offset_frac)

    def rnd(maxv):
        return random.randint(-maxv, maxv)

    src = np.float32([
        [0,     0    ],
        [w - 1, 0    ],
        [w - 1, h - 1],
        [0,     h - 1],
    ])
    dst = np.float32([
        [0     + rnd(max_dx), 0     + rnd(max_dy)],
        [w - 1 + rnd(max_dx), 0     + rnd(max_dy)],
        [w - 1 + rnd(max_dx), h - 1 + rnd(max_dy)],
        [0     + rnd(max_dx), h - 1 + rnd(max_dy)],
    ])

    M = cv2.getPerspectiveTransform(src, dst)
    bg = random.choice(BG_COLORS)
    warped = cv2.warpPerspective(
        img, M, (w, h),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=bg,
    )
    return warped


def augment_rotation(img: np.ndarray, max_angle: float = 5.0) -> np.ndarray:
    """Rotate image by a small random angle to simulate imperfect photos."""
    angle = random.uniform(-max_angle, max_angle)
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    bg = random.choice(BG_COLORS)
    return cv2.warpAffine(img, M, (w, h), borderValue=bg)


def augment_blur(img: np.ndarray, max_ksize: int = 3) -> np.ndarray:
    """Apply slight Gaussian blur to simulate camera blur."""
    ksize = random.choice([1, 3])
    if ksize > 1:
        img = cv2.GaussianBlur(img, (ksize, ksize), 0)
    return img


def augment_noise(img: np.ndarray, intensity: float = 10.0) -> np.ndarray:
    """Add Gaussian noise."""
    noise = np.random.normal(0, intensity, img.shape).astype(np.float32)
    noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy


def augment_brightness(img: np.ndarray, range_pct: float = 0.15) -> np.ndarray:
    """Randomly adjust brightness."""
    factor = random.uniform(1.0 - range_pct, 1.0 + range_pct)
    return np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def apply_augmentations(
    img: np.ndarray,
    force_perspective: bool = False,
) -> np.ndarray:
    """
    Apply a random subset of augmentations to simulate hand-drawn / phone-photo noise.

    Original pipeline (always available):
        rotation, blur, noise, brightness

    New axes (enabled probabilistically or forced):
        perspective warp
    """
    if random.random() < 0.7:
        img = augment_rotation(img)
    if random.random() < 0.5:
        img = augment_blur(img)
    if random.random() < 0.6:
        img = augment_noise(img)
    if random.random() < 0.5:
        img = augment_brightness(img)
    # Perspective warp: 40% chance normally, 100% if forced
    if force_perspective or random.random() < 0.4:
        img = augment_perspective_warp(img)
    return img


# ── Annotation I/O ───────────────────────────────────────────────────────────

def save_yolo_annotations(bboxes: list[BBox], filepath: str,
                          img_w: int, img_h: int) -> None:
    """Save bounding boxes in YOLO format to a text file."""
    with open(filepath, "w") as f:
        for bbox in bboxes:
            f.write(bbox.to_yolo(img_w, img_h) + "\n")


def boxes_overlap(b1: BBox, b2: BBox, margin: int = 5) -> bool:
    """Check if two bounding boxes overlap (with margin)."""
    return not (
        b1.x2 + margin < b2.x1 or
        b2.x2 + margin < b1.x1 or
        b1.y2 + margin < b2.y1 or
        b2.y2 + margin < b1.y1
    )
