import joblib

model_path = r"C:\Users\User\smart-farma\apps\model\version\v1\random_forest_crop_rec_tuned.joblib"
model = joblib.load(model_path)

print("MODEL FEATURES:", model.feature_names_in_)
