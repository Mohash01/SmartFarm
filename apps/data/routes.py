from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user, login_required
from flask_wtf import CSRFProtect
from apps.data.util import get_lat_lon, fetch_soil_data, get_model_input_features, fetch_weather_data, standardize_model_inputs, print_standardization_summary, get_gemini_recommendation, test_gemini_connection
from apps.data.models import SoilData, WeatherData
from apps.crop.models import Location
from apps.model.models import Prediction
from apps import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import joblib
import os
import numpy as np
import pandas as pd
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

blueprint = Blueprint('data_blueprint', __name__, url_prefix='/data')

# Import CSRF after blueprint creation
from apps import csrf

# Calculate ROOT_DIR as the project root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MODEL_DIR = os.path.join(ROOT_DIR, 'apps', 'model', 'version', 'v1')
MODEL_PATH = os.path.join(MODEL_DIR, 'random_forest_crop_rec_tuned.joblib')
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, 'label_encoder.joblib')

# Verify paths for debugging
logger.info(f"ROOT_DIR: {ROOT_DIR}")
logger.info(f"MODEL_PATH: {MODEL_PATH}")
logger.info(f"LABEL_ENCODER_PATH: {LABEL_ENCODER_PATH}")

# Load model and label encoder
try:
    model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(LABEL_ENCODER_PATH)
    logger.info(f"Model loaded successfully from {MODEL_PATH}")
    logger.info(f"Label encoder loaded successfully from {LABEL_ENCODER_PATH}")
    logger.info(f"Label encoder classes: {list(label_encoder.classes_)}")
except Exception as e:
    logger.error(f"Error loading model or label encoder: {str(e)}")
    model = None
    label_encoder = None

@blueprint.route('/chat')
def chat():
    return render_template('home/virtual-reality.html')

@blueprint.route('/predictions')
def prediction():
    return render_template('predictions/ml_predictions_chat.html')

@blueprint.route('/user/predictions', methods=['GET'])
def get_user_predictions():
    """Get prediction history for the current logged-in user"""
    logger.info(f"User predictions request - Authenticated: {current_user.is_authenticated}")
    if current_user.is_authenticated:
        logger.info(f"Current user ID: {current_user.id}, Username: {current_user.username}")
    
    if not current_user.is_authenticated:
        logger.warning("Unauthenticated request to /user/predictions")
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        # Fetch user's predictions with location info, ordered by most recent
        predictions = db.session.query(Prediction, Location).join(
            Location, Prediction.location_id == Location.id
        ).filter(
            Prediction.user_id == current_user.id
        ).order_by(
            Prediction.timestamp.desc()
        ).limit(50).all()  # Limit to last 50 predictions
        
        predictions_list = []
        for pred, loc in predictions:
            predictions_list.append({
                'id': pred.id,
                'location_name': loc.name,
                'crop_recommended': pred.crop_recommended,
                'confidence_score': pred.confidence_score,
                'is_suitable': pred.is_suitable,
                'timestamp': pred.timestamp.strftime('%Y-%m-%d %H:%M'),
                'nitrogen': pred.nitrogen,
                'phosphorus': pred.phosphorus,
                'potassium': pred.potassium,
                'temperature': pred.temperature,
                'humidity': pred.humidity,
                'ph': pred.ph,
                'rainfall': pred.rainfall
            })
        
        return jsonify({'predictions': predictions_list}), 200
    except Exception as e:
        logger.error(f"Error fetching user predictions: {str(e)}")
        return jsonify({'error': 'Failed to fetch predictions'}), 500

@blueprint.route('/location')
def locations():
    # Fetch all locations
    locations = Location.query.all()
    
    # Prepare location data for map
    location_data = []
    for loc in locations:
        prediction_count = Prediction.query.filter_by(location_id=loc.id).count()
        location_data.append({
            'id': loc.id,
            'name': str(loc.name) if loc.name else 'Unknown',
            'latitude': float(loc.latitude) if loc.latitude is not None else 0.0,
            'longitude': float(loc.longitude) if loc.longitude is not None else 0.0,
            'description': str(loc.description) if loc.description else '',
            'prediction_count': prediction_count
        })

    # Get prediction counts per location for bar chart
    prediction_counts = db.session.query(
        Location.name,
        func.count(Prediction.id).label('count')
    ).join(Prediction, Location.id == Prediction.location_id)\
     .group_by(Location.id, Location.name)\
     .all()
    prediction_chart_data = {
        'labels': [str(row.name) if row.name else 'Unknown' for row in prediction_counts],
        'counts': [row.count for row in prediction_counts]
    }

    # Get crop distribution for pie chart
    crop_counts = db.session.query(
        Prediction.crop_recommended,
        func.count(Prediction.id).label('count')
    ).group_by(Prediction.crop_recommended).all()
    crop_chart_data = {
        'labels': [str(row.crop_recommended) if row.crop_recommended else 'Unknown' for row in crop_counts],
        'counts': [row.count for row in crop_counts]
    }

    # Get soil data for scatter plot (latest per location)
    soil_data_query = db.session.query(
        Location.id,
        Location.name,
        SoilData.nitrogen,
        SoilData.phosphorus,
        SoilData.potassium
    ).join(SoilData, Location.id == SoilData.location_id)\
     .group_by(Location.id, Location.name, SoilData.nitrogen, SoilData.phosphorus, SoilData.potassium)\
     .all()
    soil_chart_data = [
        {
            'location': str(row.name) if row.name else 'Unknown',
            'nitrogen': float(row.nitrogen) if row.nitrogen is not None else 0.0,
            'phosphorus': float(row.phosphorus) if row.phosphorus is not None else 0.0,
            'potassium': float(row.potassium) if row.potassium is not None else 0.0
        } for row in soil_data_query
    ]

    # Get most common crop per location for summary table
    most_common_crop = db.session.query(
        Location.id,
        Prediction.crop_recommended,
        func.count(Prediction.id).label('count')
    ).join(Prediction, Location.id == Prediction.location_id)\
     .group_by(Location.id, Prediction.crop_recommended)\
     .order_by(Location.id, func.count(Prediction.id).desc())\
     .distinct(Location.id)\
     .all()
    
    most_common_crop_dict = {row.id: str(row.crop_recommended) if row.crop_recommended else 'None' for row in most_common_crop}

    summary_data = []
    for loc in locations:
        summary_data.append({
            'id': loc.id,
            'name': str(loc.name) if loc.name else 'Unknown',
            'latitude': float(loc.latitude) if loc.latitude is not None else 0.0,
            'longitude': float(loc.longitude) if loc.longitude is not None else 0.0,
            'prediction_count': Prediction.query.filter_by(location_id=loc.id).count(),
            'most_common_crop': most_common_crop_dict.get(loc.id, 'None')
        })

    return render_template(
        'locations/view_locations.html',
        location_data=location_data,
        prediction_chart_data=prediction_chart_data,
        crop_chart_data=crop_chart_data,
        soil_chart_data=soil_chart_data,
        summary_data=summary_data
    )
@blueprint.route('/soil')
def soil():
    # Query all soil data records
    soil_records = SoilData.query.all()
    return render_template('soil/view_soil.html', soil_records=soil_records)

@blueprint.route('/weather')
def weather():
    # Query all weather data records
    weather_records = WeatherData.query.all()
    return render_template('weather/view_weather.html', weather_records=weather_records)

@blueprint.route('/geocode')
def geocode():
    address = request.args.get('address')
    if not address:
        return jsonify({'error': 'Address parameter is required'}), 400
    
    result = get_lat_lon(address)
    if not result:
        return jsonify({'error': 'No geocoding result found'}), 404
    
    return jsonify(result)

@blueprint.route('/soil-info', methods=['GET'])
def get_soil_info():
    address = request.args.get('address')
    if not address:
        return jsonify({'error': 'Address is required as a query parameter'}), 400

    geo_data = get_lat_lon(address)
    if not geo_data or 'lat' not in geo_data or 'lon' not in geo_data:
        return jsonify({'error': 'Failed to get geolocation data'}), 500

    lat = geo_data.get('lat')
    lon = geo_data.get('lon')
    display_name = geo_data.get('display_name', address)

    # Check if location exists, otherwise create it
    location = Location.query.filter_by(latitude=lat, longitude=lon).first()
    if not location:
        location = Location(
            name=display_name,
            latitude=lat,
            longitude=lon,
            description=f"Location for {display_name}"
        )
        try:
            db.session.add(location)
            db.session.commit()
            logger.info(f"Created new location: {display_name}")
        except IntegrityError:
            db.session.rollback()
            location = Location.query.filter_by(latitude=lat, longitude=lon).first()
            logger.info(f"Location already exists for lat={lat}, lon={lon}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving location to database: {str(e)}")
            return jsonify({'error': 'Failed to save location to database'}), 500

    soil_data = fetch_soil_data(lat, lon)
    if soil_data is None:
        return jsonify({'error': 'Failed to fetch soil data from SoilGrids'}), 500

    # Save soil data to database
    soil_record = SoilData(
        location_id=location.id,
        nitrogen=soil_data['N'],
        phosphorus=soil_data['P'],
        potassium=soil_data['K'],
        ph=soil_data['ph'],
        date_recorded=datetime.utcnow()
    )
    try:
        db.session.add(soil_record)
        db.session.commit()
        logger.info(f"Saved soil data for location_id={location.id}: {soil_data}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving soil data to database: {str(e)}")
        return jsonify({'error': 'Failed to save soil data to database'}), 500

    response_data = {
        'location': {
            'address': display_name,
            'lat': lat,
            'lon': lon
        },
        'soil': soil_data
    }
    
    return jsonify(response_data)

@blueprint.route('/weather-info', methods=['GET'])
def get_weather_info():
    city = request.args.get('city')
    if not city:
        return jsonify({"error": "City parameter is required"}), 400
    
    # Get geolocation for city
    geo_data = get_lat_lon(city)
    if not geo_data or 'lat' not in geo_data or 'lon' not in geo_data:
        return jsonify({'error': 'Failed to get geolocation data for city'}), 500

    lat = geo_data.get('lat')
    lon = geo_data.get('lon')
    display_name = geo_data.get('display_name', city)

    # Check if location exists, otherwise create it
    location = Location.query.filter_by(latitude=lat, longitude=lon).first()
    if not location:
        location = Location(
            name=display_name,
            latitude=lat,
            longitude=lon,
            description=f"Location for {display_name}"
        )
        try:
            db.session.add(location)
            db.session.commit()
            logger.info(f"Created new location: {display_name}")
        except IntegrityError:
            db.session.rollback()
            location = Location.query.filter_by(latitude=lat, longitude=lon).first()
            logger.info(f"Location already exists for lat={lat}, lon={lon}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving location to database: {str(e)}")
            return jsonify({'error': 'Failed to save location to database'}), 500

    weather = fetch_weather_data(city)
    if all(value is None for value in weather.values()):
        return jsonify({"error": "Failed to fetch weather data"}), 500
    
    # Save weather data to database
    weather_record = WeatherData(
        location_id=location.id,
        temperature=weather['temperature'],
        humidity=weather['humidity'],
        rainfall=weather['rainfall'],
        date_recorded=datetime.utcnow()
    )
    try:
        db.session.add(weather_record)
        db.session.commit()
        logger.info(f"Saved weather data for location_id={location.id}: {weather}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving weather data to database: {str(e)}")
        return jsonify({'error': 'Failed to save weather data to database'}), 500

    return jsonify({
        "city": city,
        "weather": weather
    })

@blueprint.route('/model-input', methods=['GET'])
def model_input():
    location_name = request.args.get('location')
    if not location_name:
        return jsonify({'error': 'Location parameter is required'}), 400

    # Get geolocation for location
    geo_data = get_lat_lon(location_name)
    if not geo_data or 'lat' not in geo_data or 'lon' not in geo_data:
        return jsonify({'error': 'Failed to get geolocation data'}), 500

    lat = geo_data.get('lat')
    lon = geo_data.get('lon')
    display_name = geo_data.get('display_name', location_name)

    # Check if location exists, otherwise create it
    location = Location.query.filter_by(latitude=lat, longitude=lon).first()
    if not location:
        location = Location(
            name=display_name,
            latitude=lat,
            longitude=lon,
            description=f"Location for {display_name}"
        )
        try:
            db.session.add(location)
            db.session.commit()
            logger.info(f"Created new location: {display_name}")
        except IntegrityError:
            db.session.rollback()
            location = Location.query.filter_by(latitude=lat, longitude=lon).first()
            logger.info(f"Location already exists for lat={lat}, lon={lon}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving location to database: {str(e)}")
            return jsonify({'error': 'Failed to save location to database'}), 500

    # Fetch soil and weather data
    soil_data = fetch_soil_data(lat, lon)
    weather_data = fetch_weather_data(location_name)
    
    if soil_data is None or all(value is None for value in weather_data.values()):
        return jsonify({'error': 'Failed to fetch complete model input features'}), 500

    # Save soil data to database
    soil_record = SoilData(
        location_id=location.id,
        nitrogen=soil_data['N'],
        phosphorus=soil_data['P'],
        potassium=soil_data['K'],
        ph=soil_data['ph'],
        date_recorded=datetime.utcnow()
    )
    try:
        db.session.add(soil_record)
        db.session.commit()
        logger.info(f"Saved soil data for location_id={location.id}: {soil_data}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving soil data to database: {str(e)}")
        # Continue to allow prediction even if soil save fails

    # Save weather data to database
    weather_record = WeatherData(
        location_id=location.id,
        temperature=weather_data['temperature'],
        humidity=weather_data['humidity'],
        rainfall=weather_data['rainfall'],
        date_recorded=datetime.utcnow()
    )
    try:
        db.session.add(weather_record)
        db.session.commit()
        logger.info(f"Saved weather data for location_id={location.id}: {weather_data}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving weather data to database: {str(e)}")
        # Continue to allow prediction even if weather save fails

    features = get_model_input_features(location_name)
    if not features:
        return jsonify({'error': 'Failed to fetch complete model input features'}), 500

    standardized_features = standardize_model_inputs(features)
    print_standardization_summary(features, standardized_features)

    return jsonify({
        'location': location_name,
        'location_id': location.id,
        'features': standardized_features,
        'original_features': features
    }), 200

@blueprint.route('/predict', methods=['GET', 'POST'])
@csrf.exempt
def predict():
    if request.method == 'GET':
        return jsonify({
            'message': 'Crop Prediction API Endpoint',
            'method': 'POST',
            'content_type': 'application/json',
            'required_fields': {
                'features': {
                    'n': 'Nitrogen (0-200 ppm)',
                    'p': 'Phosphorous (0-150 ppm)', 
                    'k': 'Potassium (0-200 ppm)',
                    'ph': 'Soil pH (0-14)',
                    'temperature': 'Temperature (-10 to 50°C)',
                    'humidity': 'Humidity (0-100%)',
                    'rainfall': 'Rainfall (0-1000 mm)'
                },
                'location_id': 'Location ID (integer)',
                'location': 'Location name (string)',
                'desired_crop': 'Desired crop name (optional, string)'
            },
            'example_request': {
                'features': {
                    'n': 90,
                    'p': 42,
                    'k': 43,
                    'ph': 6.5,
                    'temperature': 25,
                    'humidity': 80,
                    'rainfall': 200
                },
                'location_id': 1,
                'location': 'Sample Location',
                'desired_crop': 'wheat'
            }
        }), 200

    if not model or not label_encoder:
        return jsonify({'error': 'Model or label encoder not loaded'}), 500

    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data is required in the request body'}), 400
    
    features = data.get('features', data)
    desired_crop = data.get('desired_crop', '').lower().strip()
    location_id = data.get('location_id')
    location_name = data.get('location')

    required_features = ['n', 'p', 'k', 'ph', 'temperature', 'humidity', 'rainfall']
    
    # Normalize feature keys to lowercase
    features = {key.lower(): value for key, value in features.items()}
    
    if not all(key in features for key in required_features):
        missing = [key for key in required_features if key not in features]
        return jsonify({'error': f'Missing required features: {missing}'}), 400

    if not location_id or not location_name:
        return jsonify({'error': 'Location ID and name are required'}), 400

    feature_ranges = {
        'n': (0, 200),  # ppm
        'p': (0, 150),  # ppm
        'k': (0, 200),  # ppm
        'ph': (0, 14),  # pH
        'temperature': (-10, 50),  # Celsius
        'humidity': (0, 100),  # Percentage
        'rainfall': (0, 1000)  # mm
    }
    
    try:
        feature_values = [float(features[key]) for key in required_features]
        
        for key, value in zip(required_features, feature_values):
            min_val, max_val = feature_ranges[key]
            if not (min_val <= value <= max_val):
                return jsonify({'error': f'Value for {key} ({value}) is out of valid range [{min_val}, {max_val}]'}), 400
        
        # Verify location exists
        location = Location.query.get(location_id)
        if not location:
            # Try to create location if it doesn't exist
            geo_data = get_lat_lon(location_name)
            if not geo_data or 'lat' not in geo_data or 'lon' not in geo_data:
                return jsonify({'error': 'Failed to get geolocation data for location'}), 500

            lat = geo_data.get('lat')
            lon = geo_data.get('lon')
            display_name = geo_data.get('display_name', location_name)

            location = Location.query.filter_by(latitude=lat, longitude=lon).first()
            if not location:
                location = Location(
                    name=display_name,
                    latitude=lat,
                    longitude=lon,
                    description=f"Location for {display_name}"
                )
                try:
                    db.session.add(location)
                    db.session.commit()
                    logger.info(f"Created new location: {display_name}")
                except IntegrityError:
                    db.session.rollback()
                    location = Location.query.filter_by(latitude=lat, longitude=lon).first()
                    logger.info(f"Location already exists for lat={lat}, lon={lon}")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error saving location to database: {str(e)}")
                    return jsonify({'error': 'Failed to save location to database'}), 500

        feature_df = pd.DataFrame([feature_values], columns=required_features)
        
        logger.info(f"Processing features with shape {feature_df.shape}:")
        logger.info(f"Column order: {list(feature_df.columns)}")
        logger.info(f"Values: {feature_df.iloc[0].tolist()}")
        
        feature_array = feature_df[required_features].to_numpy()
        probabilities = model.predict_proba(feature_array)[0]
        predicted_class_idx = model.predict(feature_array)[0]
        
        if predicted_class_idx >= len(label_encoder.classes_):
            logger.error(f"Predicted class index {predicted_class_idx} is out of bounds for classes: {label_encoder.classes_}")
            return jsonify({'error': 'Invalid prediction index from model'}), 500

        predicted_crop = label_encoder.inverse_transform([predicted_class_idx])[0]
        confidence = float(probabilities[predicted_class_idx])

        top_indices = np.argsort(probabilities)[-4:][::-1]
        predictions = []
        for idx in top_indices:
            if idx < len(label_encoder.classes_):
                predictions.append({
                    'crop': label_encoder.inverse_transform([idx])[0],
                    'probability': float(probabilities[idx])
                })
            else:
                logger.warning(f"Skipping invalid class index {idx}")

        if predictions and predictions[0]['crop'] != predicted_crop:
            predictions = sorted(predictions, key=lambda x: x['crop'] == predicted_crop, reverse=True)

        suitability = None
        if desired_crop:
            try:
                if desired_crop not in label_encoder.classes_:
                    suitability = {
                        'crop': desired_crop,
                        'status': 'unknown',
                        'message': 'The specified crop is not recognized by the model.'
                    }
                else:
                    desired_class_idx = label_encoder.transform([desired_crop])[0]
                    desired_confidence = probabilities[desired_class_idx]
                    if desired_confidence >= 0.7:
                        status = 'highly suitable'
                        message = f"{desired_crop.capitalize()} is highly suitable for your location (confidence: {(desired_confidence * 100):.1f}%)."
                    elif desired_confidence >= 0.3:
                        status = 'moderately suitable'
                        message = f"{desired_crop.capitalize()} is moderately suitable for your location (confidence: {(desired_confidence * 100):.1f}%). Consider the recommended crops for better results."
                    else:
                        status = 'not suitable'
                        message = f"{desired_crop.capitalize()} is not suitable for your location (confidence: {(desired_confidence * 100):.1f}%). The recommended crops are better suited."
                    suitability = {
                        'crop': desired_crop,
                        'status': status,
                        'message': message,
                        'confidence': float(desired_confidence)
                    }
            except Exception as e:
                logger.error(f"Error checking crop suitability: {str(e)}")
                suitability = {
                    'crop': desired_crop,
                    'status': 'error',
                    'message': 'Could not evaluate suitability for this crop.'
                }

        # Save prediction to database
        from flask_login import current_user
        prediction_record = Prediction(
            location_id=location.id,
            user_id=current_user.id if current_user.is_authenticated else None,
            nitrogen=features['n'],
            phosphorus=features['p'],
            potassium=features['k'],
            ph=features['ph'],
            temperature=features['temperature'],
            humidity=features['humidity'],
            rainfall=features['rainfall'],
            crop_recommended=predicted_crop,
            is_suitable=suitability['status'] in ['highly suitable', 'moderately suitable'] if suitability else True,
            confidence_score=confidence
        )
        try:
            db.session.add(prediction_record)
            db.session.commit()
            logger.info(f"Saved prediction for location_id={location.id}: crop={predicted_crop}, confidence={confidence}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving prediction to database: {str(e)}")
            return jsonify({'error': 'Failed to save prediction to database'}), 500

        # --- Gemini Integration ---
        # Compose soil and weather data for Gemini
        soil_data = {k: features[k] for k in ['n', 'p', 'k', 'ph']}
        weather_data = {k: features[k] for k in ['temperature', 'humidity', 'rainfall']}
        
        # Only call Gemini if API key is configured
        gemini_recommendation = None
        if os.getenv('GEMINI_API_KEY'):
            try:
                gemini_recommendation = get_gemini_recommendation(soil_data, weather_data, predicted_crop)
            except Exception as e:
                logger.warning(f"Gemini API error (skipping): {str(e)}")
                gemini_recommendation = None

        response = {
            'predictions': predictions,
            'suitability': suitability,
            'openai_recommendation': gemini_recommendation
        }
        logger.info(f"Prediction successful: {response}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}. Input features: {features}")
        return jsonify({'error': f'Prediction error: {str(e)}'}), 500

@blueprint.route('/test-gemini', methods=['GET'])
def test_gemini():
    """Test route to verify Gemini API connectivity"""
    result = test_gemini_connection()
    return jsonify({"status": "success", "result": result})
