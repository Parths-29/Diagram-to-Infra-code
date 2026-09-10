import cv2
from pathlib import Path
from backend.ml.pipeline import DiagramAnalysisPipeline

p_45 = DiagramAnalysisPipeline(conf_threshold=0.45)
p_60 = DiagramAnalysisPipeline(conf_threshold=0.60)

for p in Path("data/real_eval/images").glob("*.jpeg"):
    img = cv2.imread(str(p))
    spec_45 = p_45.analyze(img)
    spec_60 = p_60.analyze(img)
    if len(spec_45.nodes) == 11:
        print(f"MATCH: {p.name}")
        print(f"  0.45: {[n.subtype for n in spec_45.nodes]}")
        print(f"  0.60: {[n.subtype for n in spec_60.nodes]}")
