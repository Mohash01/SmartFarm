import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), '../model/version/v1/random_forest_crop_rec_tuned.joblib')

model = joblib.load(MODEL_PATH)

print('Model type:', type(model))

# Print feature importances if available
if hasattr(model, 'feature_importances_'):
    print('Feature importances:')
    print(model.feature_importances_)
else:
    print('No feature importances found.')

# Print classes if available
if hasattr(model, 'classes_'):
    print('Classes:')
    print(model.classes_)
else:
    print('No classes found.')

# Print model parameters
if hasattr(model, 'get_params'):
    print('Model parameters:')
    print(model.get_params())
else:
    print('No get_params method found.')
