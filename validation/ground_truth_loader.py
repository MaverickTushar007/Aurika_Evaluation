import json

def load_ground_truth(path="configs/ground_truth.json"):
    """Loads manual annotations of business truth."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[GroundTruthLoader] Warning: {path} not found.")
        return []
