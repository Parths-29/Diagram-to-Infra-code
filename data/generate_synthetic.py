"""
Synthetic Architecture Diagram Generator

Generates training images for YOLOv8 object detection by programmatically
drawing architecture diagrams using OpenCV + PIL. Since we control every pixel,
bounding-box annotations in YOLO format are generated for free.

Supports 3 archetypes:
  1. 3-tier web app (ALB → EC2 → RDS, inside VPC)
  2. Microservices (multiple services with mesh connectivity)
  3. Data pipeline (S3 → compute chain → database)

Usage:
    python data/generate_synthetic.py --output data/synthetic_dataset --count 500
"""

import argparse
import os
import random
import sys
from pathlib import Path

import cv2
import numpy as np

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.utils import (
    CLASS_ID,
    BBox,
    ComponentSpec,
    COMPONENT_LABELS,
    FILL_COLORS,
    PEN_COLORS,
    BG_COLORS,
    draw_hand_drawn_rect,
    draw_hand_drawn_cylinder,
    draw_hand_drawn_arrow,
    draw_text_label,
    apply_augmentations,
    save_yolo_annotations,
)


# ── Image Configuration ─────────────────────────────────────────────────────

IMG_SIZES = [(640, 640), (800, 600), (1024, 768), (640, 480)]
DEFAULT_IMG_SIZE = (640, 640)


# ── Archetype Generators ────────────────────────────────────────────────────

def generate_three_tier_web_app(img_w: int, img_h: int) -> tuple[np.ndarray, list[BBox]]:
    """
    Generate a 3-tier web app architecture diagram.

    Layout:
        [VPC box containing everything]
            [ALB] at top
                ↓
            [EC2] [EC2] in middle (2-3 instances)
                ↓
            [RDS] at bottom
        Optional: [S3] to the side
    """
    bg_color = random.choice(BG_COLORS)
    pen_color = random.choice(PEN_COLORS)
    img = np.full((img_h, img_w, 3), bg_color, dtype=np.uint8)
    bboxes: list[BBox] = []

    # Margins and spacing
    margin = int(img_w * 0.08)
    inner_margin = int(img_w * 0.05)

    # ── VPC box (network) ──
    vpc_x1 = margin
    vpc_y1 = margin
    vpc_x2 = img_w - margin
    vpc_y2 = img_h - margin
    vpc_fill = random.choice(FILL_COLORS["network"])
    draw_hand_drawn_rect(img, vpc_x1, vpc_y1, vpc_x2, vpc_y2,
                         pen_color, thickness=2, fill_color=vpc_fill)
    vpc_bbox = BBox(vpc_x1, vpc_y1, vpc_x2, vpc_y2,
                    CLASS_ID["network"], "VPC")
    bboxes.append(vpc_bbox)

    # VPC label
    vpc_label = random.choice(COMPONENT_LABELS["network"]["vpc"])
    label_bbox = draw_text_label(img, vpc_label,
                                 vpc_x1 + 40, vpc_y1 + 15,
                                 pen_color, font_scale=0.45)
    bboxes.append(label_bbox)

    # ── Layout zones inside VPC ──
    content_x1 = vpc_x1 + inner_margin
    content_y1 = vpc_y1 + inner_margin + 15
    content_x2 = vpc_x2 - inner_margin
    content_y2 = vpc_y2 - inner_margin
    content_w = content_x2 - content_x1
    content_h = content_y2 - content_y1

    # Three tiers: top (LB), middle (compute), bottom (DB)
    tier_h = content_h // 4

    # ── Load Balancer (top tier) ──
    lb_w = min(int(content_w * 0.4), 150)
    lb_h = min(tier_h - 20, 50)
    lb_x = content_x1 + (content_w - lb_w) // 2
    lb_y = content_y1 + 10
    lb_fill = random.choice(FILL_COLORS["load_balancer"])
    draw_hand_drawn_rect(img, lb_x, lb_y, lb_x + lb_w, lb_y + lb_h,
                         pen_color, thickness=2, fill_color=lb_fill, rounded=True)
    lb_bbox = BBox(lb_x, lb_y, lb_x + lb_w, lb_y + lb_h,
                   CLASS_ID["load_balancer"], "ALB")
    bboxes.append(lb_bbox)

    lb_label = random.choice(COMPONENT_LABELS["load_balancer"]["alb"])
    lb_label_bbox = draw_text_label(img, lb_label,
                                     lb_x + lb_w // 2, lb_y + lb_h // 2,
                                     pen_color, font_scale=0.4)
    bboxes.append(lb_label_bbox)

    # ── Compute instances (middle tier) ──
    num_instances = random.choice([2, 3])
    instance_w = min(int(content_w / (num_instances + 1)), 120)
    instance_h = min(tier_h - 20, 55)
    instance_y = content_y1 + tier_h + 15
    spacing = (content_w - num_instances * instance_w) // (num_instances + 1)

    compute_centers = []
    for i in range(num_instances):
        ix = content_x1 + spacing + i * (instance_w + spacing)
        iy = instance_y
        ec2_fill = random.choice(FILL_COLORS["compute"])
        draw_hand_drawn_rect(img, ix, iy, ix + instance_w, iy + instance_h,
                             pen_color, thickness=2, fill_color=ec2_fill, rounded=True)
        ec2_bbox = BBox(ix, iy, ix + instance_w, iy + instance_h,
                        CLASS_ID["compute"], "EC2")
        bboxes.append(ec2_bbox)

        ec2_label = random.choice(COMPONENT_LABELS["compute"]["ec2"])
        ec2_label_bbox = draw_text_label(img, ec2_label,
                                          ix + instance_w // 2, iy + instance_h // 2,
                                          pen_color, font_scale=0.35)
        bboxes.append(ec2_label_bbox)
        compute_centers.append((ix + instance_w // 2, iy))

    # ── Database (bottom tier) ──
    db_w = min(int(content_w * 0.35), 130)
    db_h = min(tier_h - 10, 60)
    db_x = content_x1 + (content_w - db_w) // 2
    db_y = content_y1 + tier_h * 2 + 30
    db_fill = random.choice(FILL_COLORS["database"])
    draw_hand_drawn_cylinder(img, db_x, db_y, db_x + db_w, db_y + db_h,
                             pen_color, thickness=2, fill_color=db_fill)
    db_bbox = BBox(db_x, db_y, db_x + db_w, db_y + db_h,
                   CLASS_ID["database"], "RDS")
    bboxes.append(db_bbox)

    db_label = random.choice(COMPONENT_LABELS["database"]["rds"])
    db_label_bbox = draw_text_label(img, db_label,
                                     db_x + db_w // 2, db_y + db_h // 2,
                                     pen_color, font_scale=0.4)
    bboxes.append(db_label_bbox)

    # ── Arrows: LB → each EC2 ──
    lb_bottom = (lb_x + lb_w // 2, lb_y + lb_h)
    for cx, cy in compute_centers:
        arrow_bbox = draw_hand_drawn_arrow(
            img, lb_bottom[0], lb_bottom[1] + 3, cx, cy - 3,
            pen_color, thickness=2
        )
        bboxes.append(arrow_bbox)

    # ── Arrows: each EC2 → DB ──
    db_top = (db_x + db_w // 2, db_y)
    for cx, cy in compute_centers:
        arrow_bbox = draw_hand_drawn_arrow(
            img, cx, cy + instance_h + 3, db_top[0], db_top[1] - 3,
            pen_color, thickness=2
        )
        bboxes.append(arrow_bbox)

    # ── Optional: S3 bucket to the side ──
    if random.random() < 0.6:
        s3_w = min(int(content_w * 0.2), 90)
        s3_h = min(50, tier_h - 20)
        # Place to the right of the VPC or inside it
        s3_x = content_x2 - s3_w - 5
        s3_y = db_y
        s3_fill = random.choice(FILL_COLORS["storage"])
        draw_hand_drawn_rect(img, s3_x, s3_y, s3_x + s3_w, s3_y + s3_h,
                             pen_color, thickness=2, fill_color=s3_fill, rounded=True)
        s3_bbox = BBox(s3_x, s3_y, s3_x + s3_w, s3_y + s3_h,
                       CLASS_ID["storage"], "S3")
        bboxes.append(s3_bbox)

        s3_label = random.choice(COMPONENT_LABELS["storage"]["s3"])
        s3_label_bbox = draw_text_label(img, s3_label,
                                         s3_x + s3_w // 2, s3_y + s3_h // 2,
                                         pen_color, font_scale=0.35)
        bboxes.append(s3_label_bbox)

        # Arrow from EC2 to S3
        last_ec2_cx = compute_centers[-1][0]
        last_ec2_cy = compute_centers[-1][1] + instance_h // 2
        arrow_bbox = draw_hand_drawn_arrow(
            img, last_ec2_cx + instance_w // 2 + 3, last_ec2_cy,
            s3_x - 3, s3_y + s3_h // 2,
            pen_color, thickness=2
        )
        bboxes.append(arrow_bbox)

    return img, bboxes


def generate_microservices(img_w: int, img_h: int) -> tuple[np.ndarray, list[BBox]]:
    """
    Generate a microservices architecture diagram.

    Layout:
        [LB] at top
            ↓
        [Service A] [Service B] [Service C] (2-4 services)
            ↓ (some connect to each other)
        [Shared DB] at bottom
        Optional: [S3] to the side
    """
    bg_color = random.choice(BG_COLORS)
    pen_color = random.choice(PEN_COLORS)
    img = np.full((img_h, img_w, 3), bg_color, dtype=np.uint8)
    bboxes: list[BBox] = []

    margin = int(img_w * 0.06)

    # ── Optional VPC wrapper ──
    if random.random() < 0.5:
        vpc_fill = random.choice(FILL_COLORS["network"])
        draw_hand_drawn_rect(img, margin, margin,
                             img_w - margin, img_h - margin,
                             pen_color, thickness=2, fill_color=vpc_fill)
        vpc_bbox = BBox(margin, margin, img_w - margin, img_h - margin,
                        CLASS_ID["network"], "VPC")
        bboxes.append(vpc_bbox)
        vpc_label = random.choice(COMPONENT_LABELS["network"]["vpc"])
        bboxes.append(draw_text_label(img, vpc_label,
                                       margin + 40, margin + 15,
                                       pen_color, font_scale=0.4))
        margin = int(img_w * 0.1)

    content_w = img_w - 2 * margin
    content_h = img_h - 2 * margin

    # ── Load Balancer at top ──
    lb_w = min(int(content_w * 0.3), 130)
    lb_h = min(45, content_h // 6)
    lb_x = margin + (content_w - lb_w) // 2
    lb_y = margin + 10
    lb_fill = random.choice(FILL_COLORS["load_balancer"])
    draw_hand_drawn_rect(img, lb_x, lb_y, lb_x + lb_w, lb_y + lb_h,
                         pen_color, thickness=2, fill_color=lb_fill, rounded=True)
    bboxes.append(BBox(lb_x, lb_y, lb_x + lb_w, lb_y + lb_h,
                       CLASS_ID["load_balancer"], "ALB"))
    lb_label = random.choice(COMPONENT_LABELS["load_balancer"]["alb"])
    bboxes.append(draw_text_label(img, lb_label,
                                   lb_x + lb_w // 2, lb_y + lb_h // 2,
                                   pen_color, font_scale=0.35))

    # ── Services (middle) ──
    num_services = random.choice([2, 3, 4])
    svc_w = min(int(content_w / (num_services + 1)), 110)
    svc_h = min(50, content_h // 5)
    svc_y = lb_y + lb_h + int(content_h * 0.2)
    svc_spacing = (content_w - num_services * svc_w) // (num_services + 1)

    svc_centers = []
    service_names = ["Auth Svc", "User Svc", "Order Svc", "Payment Svc",
                     "API Svc", "Notif Svc", "Search Svc", "Cart Svc"]
    chosen_names = random.sample(service_names, min(num_services, len(service_names)))

    for i in range(num_services):
        sx = margin + svc_spacing + i * (svc_w + svc_spacing)
        sy = svc_y
        svc_fill = random.choice(FILL_COLORS["compute"])
        draw_hand_drawn_rect(img, sx, sy, sx + svc_w, sy + svc_h,
                             pen_color, thickness=2, fill_color=svc_fill, rounded=True)
        bboxes.append(BBox(sx, sy, sx + svc_w, sy + svc_h,
                           CLASS_ID["compute"], "EC2"))
        name = chosen_names[i] if i < len(chosen_names) else f"Svc {i+1}"
        bboxes.append(draw_text_label(img, name,
                                       sx + svc_w // 2, sy + svc_h // 2,
                                       pen_color, font_scale=0.3))
        svc_centers.append((sx + svc_w // 2, sy, sx, svc_w, svc_h))

    # ── Arrows: LB → each service ──
    lb_bottom_cx = lb_x + lb_w // 2
    lb_bottom_cy = lb_y + lb_h
    for (scx, sy, _, _, _) in svc_centers:
        bboxes.append(draw_hand_drawn_arrow(
            img, lb_bottom_cx, lb_bottom_cy + 3, scx, sy - 3,
            pen_color, thickness=2
        ))

    # ── Inter-service arrows (mesh) ──
    if num_services >= 2:
        # Connect some adjacent pairs
        pairs = [(0, 1)]
        if num_services >= 3:
            pairs.append((1, 2))
        if num_services >= 4 and random.random() < 0.6:
            pairs.append((0, 3))

        for i, j in pairs:
            if i < len(svc_centers) and j < len(svc_centers):
                s1 = svc_centers[i]
                s2 = svc_centers[j]
                # Horizontal arrow between services
                x1 = s1[2] + s1[3] + 3  # right edge of service i
                y1 = s1[1] + s1[4] // 2
                x2 = s2[2] - 3  # left edge of service j
                y2 = s2[1] + s2[4] // 2
                bboxes.append(draw_hand_drawn_arrow(
                    img, x1, y1, x2, y2, pen_color, thickness=1
                ))

    # ── Database at bottom ──
    db_w = min(int(content_w * 0.3), 120)
    db_h = min(55, content_h // 5)
    db_x = margin + (content_w - db_w) // 2
    db_y = svc_y + svc_h + int(content_h * 0.2)
    db_fill = random.choice(FILL_COLORS["database"])
    draw_hand_drawn_cylinder(img, db_x, db_y, db_x + db_w, db_y + db_h,
                             pen_color, thickness=2, fill_color=db_fill)
    bboxes.append(BBox(db_x, db_y, db_x + db_w, db_y + db_h,
                       CLASS_ID["database"], "RDS"))
    db_label = random.choice(COMPONENT_LABELS["database"]["rds"])
    bboxes.append(draw_text_label(img, db_label,
                                   db_x + db_w // 2, db_y + db_h // 2,
                                   pen_color, font_scale=0.4))

    # ── Arrows: services → DB ──
    db_top_cx = db_x + db_w // 2
    db_top_cy = db_y
    for (scx, sy, _, _, sh) in svc_centers:
        if random.random() < 0.7:  # Not all services need DB
            bboxes.append(draw_hand_drawn_arrow(
                img, scx, sy + sh + 3, db_top_cx, db_top_cy - 3,
                pen_color, thickness=2
            ))

    # ── Optional S3 ──
    if random.random() < 0.4:
        s3_w = min(80, int(content_w * 0.15))
        s3_h = min(45, svc_h)
        s3_x = img_w - margin - s3_w - 5
        s3_y = db_y
        s3_fill = random.choice(FILL_COLORS["storage"])
        draw_hand_drawn_rect(img, s3_x, s3_y, s3_x + s3_w, s3_y + s3_h,
                             pen_color, thickness=2, fill_color=s3_fill, rounded=True)
        bboxes.append(BBox(s3_x, s3_y, s3_x + s3_w, s3_y + s3_h,
                           CLASS_ID["storage"], "S3"))
        s3_label = random.choice(COMPONENT_LABELS["storage"]["s3"])
        bboxes.append(draw_text_label(img, s3_label,
                                       s3_x + s3_w // 2, s3_y + s3_h // 2,
                                       pen_color, font_scale=0.3))

    return img, bboxes


def generate_data_pipeline(img_w: int, img_h: int) -> tuple[np.ndarray, list[BBox]]:
    """
    Generate a data pipeline architecture diagram.

    Layout (left-to-right or top-to-bottom):
        [S3 Input] → [Compute 1] → [Compute 2] → [Database Output]
        Optional: branches, additional S3 output
    """
    bg_color = random.choice(BG_COLORS)
    pen_color = random.choice(PEN_COLORS)
    img = np.full((img_h, img_w, 3), bg_color, dtype=np.uint8)
    bboxes: list[BBox] = []

    margin = int(img_w * 0.06)

    # Decide layout direction
    horizontal = random.random() < 0.6

    if horizontal:
        # Left-to-right pipeline
        num_stages = random.choice([3, 4, 5])
        stage_w = min(int((img_w - 2 * margin) / (num_stages + 0.5)), 120)
        stage_h = min(55, int(img_h * 0.2))
        spacing = ((img_w - 2 * margin) - num_stages * stage_w) // (num_stages + 1)
        center_y = img_h // 2

        # Define stages: first is S3, middle are compute, last is DB
        stage_types = ["storage"]
        for _ in range(num_stages - 2):
            stage_types.append("compute")
        stage_types.append("database")

        prev_right = None
        prev_cy = None

        for i, stype in enumerate(stage_types):
            sx = margin + spacing + i * (stage_w + spacing)
            # Add vertical jitter
            sy_offset = random.randint(-15, 15)
            sy = center_y - stage_h // 2 + sy_offset

            fill = random.choice(FILL_COLORS[stype])

            if stype == "database":
                draw_hand_drawn_cylinder(img, sx, sy, sx + stage_w, sy + stage_h,
                                         pen_color, thickness=2, fill_color=fill)
                subtypes = list(COMPONENT_LABELS[stype].keys())
                subtype = random.choice(subtypes)
            elif stype == "storage":
                draw_hand_drawn_rect(img, sx, sy, sx + stage_w, sy + stage_h,
                                     pen_color, thickness=2, fill_color=fill, rounded=True)
                subtype = "s3"
            else:
                draw_hand_drawn_rect(img, sx, sy, sx + stage_w, sy + stage_h,
                                     pen_color, thickness=2, fill_color=fill, rounded=True)
                subtype = "ec2"

            bboxes.append(BBox(sx, sy, sx + stage_w, sy + stage_h,
                               CLASS_ID[stype]))

            labels = COMPONENT_LABELS[stype][subtype]
            label = random.choice(labels)
            bboxes.append(draw_text_label(img, label,
                                           sx + stage_w // 2, sy + stage_h // 2,
                                           pen_color, font_scale=0.3))

            # Arrow from previous stage
            if prev_right is not None:
                bboxes.append(draw_hand_drawn_arrow(
                    img, prev_right + 3, prev_cy,
                    sx - 3, sy + stage_h // 2,
                    pen_color, thickness=2
                ))

            prev_right = sx + stage_w
            prev_cy = sy + stage_h // 2

        # Optional: branch output S3 at the end
        if random.random() < 0.5 and prev_right is not None:
            out_w = min(80, stage_w)
            out_h = min(45, stage_h)
            out_x = margin + spacing + (num_stages - 1) * (stage_w + spacing)
            out_y = center_y + stage_h // 2 + 30
            out_fill = random.choice(FILL_COLORS["storage"])
            draw_hand_drawn_rect(img, out_x, out_y, out_x + out_w, out_y + out_h,
                                 pen_color, thickness=2, fill_color=out_fill, rounded=True)
            bboxes.append(BBox(out_x, out_y, out_x + out_w, out_y + out_h,
                               CLASS_ID["storage"], "S3"))
            bboxes.append(draw_text_label(img, "Output",
                                           out_x + out_w // 2, out_y + out_h // 2,
                                           pen_color, font_scale=0.3))
            # Arrow down from last compute stage
            last_stage_x = margin + spacing + (num_stages - 2) * (stage_w + spacing)
            bboxes.append(draw_hand_drawn_arrow(
                img, last_stage_x + stage_w // 2, center_y + stage_h // 2 + 3,
                out_x + out_w // 2, out_y - 3,
                pen_color, thickness=2
            ))

    else:
        # Top-to-bottom pipeline
        num_stages = random.choice([3, 4])
        stage_w = min(int(img_w * 0.35), 140)
        stage_h = min(50, int((img_h - 2 * margin) / (num_stages * 1.8)))
        spacing = ((img_h - 2 * margin) - num_stages * stage_h) // (num_stages + 1)
        center_x = img_w // 2

        stage_types = ["storage"]
        for _ in range(num_stages - 2):
            stage_types.append("compute")
        stage_types.append("database")

        prev_bottom = None
        prev_cx = None

        for i, stype in enumerate(stage_types):
            sx_offset = random.randint(-20, 20)
            sx = center_x - stage_w // 2 + sx_offset
            sy = margin + spacing + i * (stage_h + spacing)

            fill = random.choice(FILL_COLORS[stype])

            if stype == "database":
                draw_hand_drawn_cylinder(img, sx, sy, sx + stage_w, sy + stage_h,
                                         pen_color, thickness=2, fill_color=fill)
                subtype = "rds"
            elif stype == "storage":
                draw_hand_drawn_rect(img, sx, sy, sx + stage_w, sy + stage_h,
                                     pen_color, thickness=2, fill_color=fill, rounded=True)
                subtype = "s3"
            else:
                draw_hand_drawn_rect(img, sx, sy, sx + stage_w, sy + stage_h,
                                     pen_color, thickness=2, fill_color=fill, rounded=True)
                subtype = "ec2"

            bboxes.append(BBox(sx, sy, sx + stage_w, sy + stage_h,
                               CLASS_ID[stype]))

            labels = COMPONENT_LABELS[stype][subtype]
            label = random.choice(labels)
            bboxes.append(draw_text_label(img, label,
                                           sx + stage_w // 2, sy + stage_h // 2,
                                           pen_color, font_scale=0.35))

            if prev_bottom is not None:
                bboxes.append(draw_hand_drawn_arrow(
                    img, prev_cx, prev_bottom + 3,
                    sx + stage_w // 2, sy - 3,
                    pen_color, thickness=2
                ))

            prev_bottom = sy + stage_h
            prev_cx = sx + stage_w // 2

    # ── Optional VPC wrapper ──
    if random.random() < 0.3:
        vpc_pad = 15
        vpc_fill = random.choice(FILL_COLORS["network"])

        # Find extent of all existing bboxes
        all_x1 = min(b.x1 for b in bboxes) - vpc_pad
        all_y1 = min(b.y1 for b in bboxes) - vpc_pad - 15
        all_x2 = max(b.x2 for b in bboxes) + vpc_pad
        all_y2 = max(b.y2 for b in bboxes) + vpc_pad

        # Draw VPC behind everything (we'll need to redraw — but for
        # simplicity we draw it as a semi-transparent overlay instead)
        overlay = img.copy()
        draw_hand_drawn_rect(overlay, all_x1, all_y1, all_x2, all_y2,
                             pen_color, thickness=2, fill_color=vpc_fill)
        # Blend so existing content shows through
        cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)

        # Re-draw the border on top
        draw_hand_drawn_rect(img, all_x1, all_y1, all_x2, all_y2,
                             pen_color, thickness=2)
        bboxes.append(BBox(all_x1, all_y1, all_x2, all_y2,
                           CLASS_ID["network"], "VPC"))
        vpc_label = random.choice(COMPONENT_LABELS["network"]["vpc"])
        bboxes.append(draw_text_label(img, vpc_label,
                                       all_x1 + 35, all_y1 + 12,
                                       pen_color, font_scale=0.4))

    return img, bboxes


# ── Main Generator ───────────────────────────────────────────────────────────

ARCHETYPE_GENERATORS = {
    "three_tier": generate_three_tier_web_app,
    "microservices": generate_microservices,
    "data_pipeline": generate_data_pipeline,
}


def generate_dataset(
    output_dir: str,
    total_count: int = 500,
    augmented_copies: int = 1,
    seed: int = 42,
) -> None:
    """
    Generate the full synthetic dataset.

    Args:
        output_dir: Root output directory (will contain train/ and val/ splits)
        total_count: Total number of unique diagrams to generate
        augmented_copies: Number of augmented copies per clean image
        seed: Random seed for reproducibility
    """
    random.seed(seed)
    np.random.seed(seed)

    # Create directory structure
    for split in ["train", "val"]:
        os.makedirs(os.path.join(output_dir, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, split, "labels"), exist_ok=True)

    # Split: 80% train, 20% val
    val_count = max(1, total_count // 5)
    train_count = total_count - val_count

    archetype_names = list(ARCHETYPE_GENERATORS.keys())
    # Distribute evenly across archetypes
    per_archetype = total_count // len(archetype_names)
    remainder = total_count % len(archetype_names)

    idx = 0
    total_images = 0

    for arch_idx, arch_name in enumerate(archetype_names):
        gen_fn = ARCHETYPE_GENERATORS[arch_name]
        count = per_archetype + (1 if arch_idx < remainder else 0)

        for i in range(count):
            # Determine split
            split = "val" if idx >= train_count else "train"

            # Random image size
            img_w, img_h = random.choice(IMG_SIZES)

            # Generate clean diagram
            img, bboxes = gen_fn(img_w, img_h)

            # Clamp bboxes to image bounds
            for b in bboxes:
                b.x1 = max(0, min(b.x1, img_w - 1))
                b.y1 = max(0, min(b.y1, img_h - 1))
                b.x2 = max(b.x1 + 1, min(b.x2, img_w))
                b.y2 = max(b.y1 + 1, min(b.y2, img_h))

            # Filter out degenerate bboxes
            valid_bboxes = [b for b in bboxes if b.w > 3 and b.h > 3]

            # Save clean version
            name = f"{arch_name}_{idx:04d}"
            img_path = os.path.join(output_dir, split, "images", f"{name}.png")
            lbl_path = os.path.join(output_dir, split, "labels", f"{name}.txt")

            cv2.imwrite(img_path, img)
            save_yolo_annotations(valid_bboxes, lbl_path, img_w, img_h)
            total_images += 1

            # Save augmented copies
            for aug_idx in range(augmented_copies):
                aug_img = apply_augmentations(img.copy())
                aug_name = f"{arch_name}_{idx:04d}_aug{aug_idx}"
                aug_img_path = os.path.join(output_dir, split, "images", f"{aug_name}.png")
                aug_lbl_path = os.path.join(output_dir, split, "labels", f"{aug_name}.txt")

                cv2.imwrite(aug_img_path, aug_img)
                # Use same labels for augmented (rotation is small enough
                # that bboxes are still approximately correct)
                save_yolo_annotations(valid_bboxes, aug_lbl_path, img_w, img_h)
                total_images += 1

            idx += 1

            if idx % 50 == 0:
                print(f"  Generated {idx}/{total_count} diagrams "
                      f"({total_images} total with augmentations)...")

    print(f"\nDataset generation complete!")
    print(f"  Unique diagrams: {total_count}")
    print(f"  Total images (with augmentations): {total_images}")
    print(f"  Train: {output_dir}/train/")
    print(f"  Val:   {output_dir}/val/")


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic architecture diagram dataset for YOLOv8 training"
    )
    parser.add_argument(
        "--output", type=str, default="data/synthetic_dataset",
        help="Output directory for the dataset (default: data/synthetic_dataset)"
    )
    parser.add_argument(
        "--count", type=int, default=500,
        help="Number of unique diagrams to generate (default: 500)"
    )
    parser.add_argument(
        "--augmented-copies", type=int, default=1,
        help="Number of augmented copies per clean image (default: 1)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )

    args = parser.parse_args()

    print(f"Generating synthetic dataset:")
    print(f"  Output: {args.output}")
    print(f"  Count: {args.count} unique diagrams")
    print(f"  Augmented copies: {args.augmented_copies} per image")
    print(f"  Seed: {args.seed}")
    print()

    generate_dataset(
        output_dir=args.output,
        total_count=args.count,
        augmented_copies=args.augmented_copies,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
