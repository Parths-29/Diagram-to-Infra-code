import json
import cv2
from backend.main import get_pipeline, get_generator

# Load image
img = cv2.imread("/Users/SHARMPX132/Downloads/Gemini_Generated_Image_k3ilzrk3ilzrk3il.png")

# Run Analyze
pipeline = get_pipeline()
spec = pipeline.analyze(img)

print("=== RAW DETECTED COMPONENTS ===")
for node in spec.nodes:
    print(f"[{node.id}] Class: {node.class_name}, Subtype: {node.subtype}, OCR Label: '{node.label}'")

print("\n=== RAW DETECTED EDGES ===")
for edge in spec.edges:
    print(f"{edge.source} -> {edge.target} ({edge.edge_type})")

print("\n=== AMBIGUITIES ===")
for amb in spec.ambiguities:
    print(amb)

# Run Generate
generator = get_generator()
tf_code = generator.generate(spec)

with open("test_tf/main.tf", "w") as f:
    f.write(tf_code)
