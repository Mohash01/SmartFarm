import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), '../model/version/v1/random_forest_crop_rec_tuned.joblib')
LABEL_ENCODER_PATH = os.path.join(os.path.dirname(__file__), '../model/version/v1/label_encoder.joblib')

model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(LABEL_ENCODER_PATH)

print('Model classes (indices):', model.classes_)
print('Label encoder classes (names):', label_encoder.classes_)

if len(model.classes_) == len(label_encoder.classes_):
    print('Number of classes match.')
else:
    print('Number of classes do NOT match!')

print('\nMapping:')
for idx, class_idx in enumerate(model.classes_):
    crop_name = label_encoder.inverse_transform([class_idx])[0]
    print(f'Class index {class_idx}: {crop_name}')
