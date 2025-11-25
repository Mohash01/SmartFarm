import pandas as pd
import collections

# Replace with your actual training data CSV path
TRAINING_DATA_PATH = 'data/training_data.csv'

# Load the training data
try:
    df = pd.read_csv(TRAINING_DATA_PATH)
except Exception as e:
    print(f'Error loading training data: {e}')
    exit(1)

# Replace 'crop_label' with the actual column name for crop classes in your dataset
distribution = collections.Counter(df['crop_label'])

print('Crop class distribution:')
for crop, count in distribution.items():
    print(f'{crop}: {count}')

print('\nTotal samples:', sum(distribution.values()))
print('Unique crop classes:', len(distribution))
