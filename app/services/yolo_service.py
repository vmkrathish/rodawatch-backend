# RoadWatch – developed by M K Rathish and team
# IIT Madras CoERS Road Safety Hackathon 2026
# All rights reserved.

"""YOLOv8 Road Issue Detection Service"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

YOLO_CLASS_MAP = {
    "pothole": "Pothole",
    "waterlogging": "Waterlogging",
    "crack": "Pothole",
    "damaged_divider": "Broken Divider",
    "broken_sign": "Missing Sign Board",
    "flooding": "Waterlogging",
}

SEVERITY_MAP = [
    (0.90, "Critical"),
    (0.75, "High"),
    (0.55, "Medium"),
    (0.0,  "Low"),
]

def get_severity(conf: float) -> str:
    for threshold, sev in SEVERITY_MAP:
        if conf >= threshold:
            return sev
    return "Low"

def analyze_image(image_path: str) -> Dict[str, Any]:
    result = {
        "detections": [],
        "issue_type": "Other",
        "severity": "Medium",
        "ai_severity_score": 5.0,
        "status": "ok"
    }
    try:
        from ultralytics import YOLO
        model = YOLO(os.environ.get("YOLO_MODEL_PATH", "yolov8n.pt"))
        yolo_results = model(image_path, conf=0.4, verbose=False)
        detections = []
        for r in yolo_results:
            for box in r.boxes:
                cls_name = model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                detections.append({
                    "class": cls_name,
                    "confidence": round(conf, 3),
                    "bbox": [round(x, 1) for x in box.xyxy[0].tolist()]
                })
        result["detections"] = detections
        if detections:
            top = max(detections, key=lambda d: d["confidence"])
            result["issue_type"] = YOLO_CLASS_MAP.get(top["class"], "Other")
            result["severity"] = get_severity(top["confidence"])
            result["ai_severity_score"] = round(top["confidence"] * 10, 2)
    except ImportError:
        result["status"] = "skipped_no_ultralytics"
    except Exception as e:
        logger.error(f"YOLO error: {e}")
        result["status"] = f"error: {str(e)}"
    return result
