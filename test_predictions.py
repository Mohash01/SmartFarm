import requests

# Test with different feature sets
test_cases = [
    {'n': 90, 'p': 42, 'k': 43, 'ph': 6.5, 'temperature': 25, 'humidity': 80, 'rainfall': 200},  # Original
    {'n': 50, 'p': 20, 'k': 100, 'ph': 5.5, 'temperature': 20, 'humidity': 60, 'rainfall': 150},  # Different
    {'n': 120, 'p': 60, 'k': 200, 'ph': 7.0, 'temperature': 30, 'humidity': 90, 'rainfall': 250},  # Another
    {'n': 20, 'p': 10, 'k': 20, 'ph': 5.0, 'temperature': 18, 'humidity': 50, 'rainfall': 100},  # Should favor rice or maize
    {'n': 100, 'p': 50, 'k': 200, 'ph': 7.5, 'temperature': 28, 'humidity': 85, 'rainfall': 300},  # Should favor banana or coconut
]

for i, features in enumerate(test_cases):
    response = requests.post('http://localhost:5002/data/predict', json={'features': features, 'location_id': 1, 'location': f'Test {i+1}'})
    if response.status_code == 200:
        data = response.json()
        predictions = data.get('predictions', [])
        if predictions:
            top_crop = predictions[0]['crop']
            top_prob = predictions[0]['probability']
            alt_crops = [f"{p['crop']} ({p['probability']:.3f})" for p in predictions[1:4]] if len(predictions) > 1 else []
            print(f'Test {i+1} - Top: {top_crop} ({top_prob:.3f})')
            if alt_crops:
                print(f'  Alternatives: {", ".join(alt_crops)}')
        else:
            print(f'Test {i+1} - No predictions')
    else:
        print(f'Test {i+1} - Error: {response.status_code}')
