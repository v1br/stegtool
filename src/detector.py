import os
import time
import joblib
from imageio.v2 import imread

from src.features.feature_extractor import extract_feature_breakdown
from src.analysis.baseline_stats import FeatureBaseline
from src.analysis.progress import print_progress

MODEL_DIR = "models"

MODEL_FILES = {
    "0.1": "rf_0.1bpp.joblib",
    "0.2": "rf_0.2bpp.joblib",
    "0.3": "rf_0.3bpp.joblib",
    "0.4": "rf_0.4bpp.joblib",
    "0.5": "rf_0.5bpp.joblib",
}

# Detection thresholds
STEGO_THRESHOLD = 0.65
SUSPICIOUS_THRESHOLD = 0.45


class SteganalysisTool:

    def __init__(self):

        print("Loading steganalysis models...")

        self.models = {}

        for bpp, filename in MODEL_FILES.items():

            path = os.path.join(MODEL_DIR, filename)

            if os.path.exists(path):
                self.models[bpp] = joblib.load(path)
                print(f"Loaded model for {bpp} bpp")

        if len(self.models) == 0:
            raise RuntimeError("No models found in models/ directory")

        self.baseline = FeatureBaseline()

        # Feature importance (use highest payload model)
        model = self.models.get("0.5")

        if model and hasattr(model, "feature_importances_"):
            self.feature_importance = model.feature_importances_
        else:
            self.feature_importance = None

        print("Models loaded\n")

    def analyze_image(self, image_path):

        if not os.path.exists(image_path):
            print("File not found:", image_path)
            return None

        try:
            img = imread(image_path)
        except Exception as e:
            print("Failed to load image:", image_path)
            print(e)
            return None

        h, w = img.shape[:2]

        data = extract_feature_breakdown(img)

        features = data["features"].reshape(1, -1)

        model_probs = {}

        for bpp, model in self.models.items():

            prob = model.predict_proba(features)[0][1]
            model_probs[bpp] = prob

        # Average probability across models
        avg_prob = sum(model_probs.values()) / len(model_probs)

        # Consensus count
        stego_votes = sum(1 for p in model_probs.values() if p >= 0.5)

        # Estimate embedding payload
        estimated_bpp = max(model_probs, key=model_probs.get)

        # Threshold-based classification
        if avg_prob >= STEGO_THRESHOLD:
            label = "STEGO"
        elif avg_prob >= SUSPICIOUS_THRESHOLD:
            label = "SUSPICIOUS"
        else:
            label = "COVER"

        return {
            "file": image_path,
            "width": w,
            "height": h,
            "label": label,
            "probability": avg_prob,
            "entropy": data["entropy"],
            "glcm": data["glcm"],
            "spam": data["spam"],
            "model_probabilities": model_probs,
            "estimated_payload": estimated_bpp,
            "consensus": stego_votes
        }

    def analyze_folder(self, folder):

        if not os.path.exists(folder):
            print("Folder not found:", folder)
            return []

        files = sorted(os.listdir(folder))

        images = [
            f for f in files
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".pgm"))
        ]

        if len(images) == 0:
            print("No supported images found in folder.")
            return []

        print("\nScanning images...\n")

        results = []

        start = time.time()

        for i, file in enumerate(images, start=1):

            path = os.path.join(folder, file)

            result = self.analyze_image(path)

            if result:
                results.append(result)

            print_progress(i, len(images))

        duration = time.time() - start

        print("\n\nScan complete.")

        if duration > 0:
            speed = len(images) / duration
        else:
            speed = 0

        print("Scan time:", round(duration, 2), "seconds")
        print("Processing speed:", round(speed, 2), "images/sec\n")

        return results