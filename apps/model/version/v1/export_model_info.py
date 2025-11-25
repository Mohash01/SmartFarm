import joblib
import json
import numpy as np
import os

MODEL_PATH = "random_forest_crop_rec_tuned.joblib"
ENCODER_PATH = "label_encoder.joblib"

def safe(obj):
    """Convert NumPy types to Python types for JSON."""
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Could not find model at {MODEL_PATH}")
        return
    if not os.path.exists(ENCODER_PATH):
        print(f"ERROR: Could not find label encoder at {ENCODER_PATH}")
        return

    print("Loading model...")
    model = joblib.load(MODEL_PATH)

    print("Loading label encoder...")
    encoder = joblib.load(ENCODER_PATH)

    print("Extracting model info...")
    info = {}

    # Model basics
    info["model_type"] = str(type(model))
    info["n_estimators"] = safe(getattr(model, "n_estimators", None))

    # Feature names
    try:
        info["feature_names"] = model.feature_names_in_.tolist()
    except:
        info["feature_names"] = "NOT EXPOSED"

    # Classes (encoded integers)
    info["model_classes"] = safe(model.classes_)

    # Encoder classes (decoded strings)
    info["encoder_classes"] = safe(encoder.classes_)

    # Feature importances
    info["feature_importances"] = safe(model.feature_importances_)

    # Test prediction behavior
    test_input = np.array([[50, 50, 50, 20, 50, 6, 10]])  # random balanced input
    try:
        probs = model.predict_proba(test_input)[0]
        info["test_probabilities"] = safe(probs)
        pred = model.predict(test_input)[0]
        info["test_prediction"] = safe(pred)
    except Exception as e:
        info["test_prediction_error"] = str(e)

    # JSON output
    with open("model_info.json", "w") as f:
        json.dump(info, f, indent=4)

    print("\n✅ model_info.json has been generated successfully!")
    print("Upload it to ChatGPT so we can analyze the root cause.")

if __name__ == "__main__":
    main()
