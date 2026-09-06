# Real evaluation dataset

This directory holds photos of actual hand-drawn/whiteboard architecture
diagrams for model evaluation. These are NOT used for primary training —
only for eval and optional fine-tuning.

## Structure

```
real_eval/
├── images/    # .jpg/.png photos of hand-drawn diagrams
├── labels/    # YOLO-format .txt annotation files
└── README.md
```

## How to populate

1. Draw architecture diagrams on a whiteboard or paper
2. Take clear photos (good lighting, minimal glare)
3. Place images in `images/`
4. Annotate with a tool like Label Studio or CVAT, export in YOLO format
5. Place annotation files in `labels/`

Target: 50-100 annotated images covering the 3 supported archetypes
(3-tier web app, microservices, data pipeline).
