from flask import Blueprint, render_template, request, jsonify, send_file, make_response
from flask_login import current_user, login_required
from flask_wtf import CSRFProtect
from apps.data.util import (
    get_lat_lon,
    fetch_soil_data,
    get_model_input_features,
    fetch_weather_data,
    get_grok_crop_recommendation

)
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
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO

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
    try:
        logger.info(f"Model feature names: {list(model.feature_names_in_)}")
    except Exception:
        logger.info("Model does not expose feature_names_in_")
    logger.info(f"Label encoder classes: {list(label_encoder.classes_)}")
except Exception as e:
    logger.error(f"Error loading model or label encoder: {str(e)}")
    model = None
    label_encoder = None


@blueprint.route('/chat')
def chat():
    return render_template('home/chat.html')


@blueprint.route('/chat-crop-advice', methods=['POST'])
@csrf.exempt
def chat_crop_advice():
    """Handle chatbot requests for crop growing advice"""
    try:
        data = request.get_json()
        crop = data.get('crop', '').strip()
        message = data.get('message', '').strip()
        location = data.get('location', '').strip()

        if not crop or not message:
            return jsonify({'success': False, 'error': 'Crop and message are required'}), 400

        # Import OpenAI client
        from openai import OpenAI
        import os

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OpenAI API key not configured")
            return jsonify({
                'success': False,
                'error': 'AI service not configured'
            }), 500

        client = OpenAI(api_key=api_key)

        # Build the prompt
        location_context = f" in {location}" if location else ""
        system_prompt = f"""You are an expert agricultural advisor specializing in {crop} cultivation{location_context}. 
Provide practical, actionable advice for farmers. Be specific and consider:
- Local growing conditions{location_context if location else ""}
- Best practices for planting, growing, and harvesting {crop}
- Common pests and diseases and how to manage them
- Optimal soil conditions, watering, and fertilization
- Seasonal considerations and climate requirements
- Post-harvest handling and storage

Keep responses clear, practical, and easy to understand for farmers."""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )

        advice = response.choices[0].message.content
        logger.info(f"Generated crop advice for {crop}: {message[:50]}...")

        return jsonify({
            'success': True,
            'response': advice,
            'crop': crop
        })

    except Exception as e:
        logger.error(f"Error in chat_crop_advice: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate advice. Please try again.'
        }), 500


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


@blueprint.route('/download-prediction-report/<int:prediction_id>', methods=['GET'])
@login_required
def download_prediction_report(prediction_id):
    """Generate and download PDF report for a specific prediction"""
    try:
        # Get the prediction with location info
        prediction_data = db.session.query(Prediction, Location).join(
            Location, Prediction.location_id == Location.id
        ).filter(
            Prediction.id == prediction_id,
            Prediction.user_id == current_user.id
        ).first()

        if not prediction_data:
            return jsonify({'error': 'Prediction not found or access denied'}), 404

        prediction, location = prediction_data

        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb'),
            alignment=1  # Center alignment
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#059669'),
            spaceBefore=20
        )

        # Content to add to PDF
        content = []

        # Title
        content.append(Paragraph("Smart Farma - Crop Prediction Report", title_style))
        content.append(Spacer(1, 20))

        # Prediction Summary
        content.append(Paragraph("Prediction Summary", heading_style))
        summary_data = [
            ['Field', 'Value'],
            ['Location', location.name],
            ['Recommended Crop', prediction.crop_recommended.title()],
            ['Prediction Date', prediction.timestamp.strftime('%Y-%m-%d %H:%M')],
            ['Confidence Score', f"{(prediction.confidence_score * 100):.1f}%"],
            ['Suitability', 'Suitable' if prediction.is_suitable else 'Not Suitable'],
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
        ]))
        content.append(summary_table)
        content.append(Spacer(1, 20))

        # Soil Nutrients
        content.append(Paragraph("Soil Nutrients Analysis", heading_style))
        soil_data = [
            ['Nutrient', 'Value', 'Unit'],
            ['Nitrogen (N)', f"{prediction.nitrogen:.2f}", 'ppm'],
            ['Phosphorus (P)', f"{prediction.phosphorus:.2f}", 'ppm'],
            ['Potassium (K)', f"{prediction.potassium:.2f}", 'ppm'],
            ['pH Level', f"{prediction.ph:.2f}", ''],
        ]

        soil_table = Table(soil_data, colWidths=[2*inch, 1.5*inch, 1*inch])
        soil_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
        ]))
        content.append(soil_table)
        content.append(Spacer(1, 20))

        # Weather Conditions
        content.append(Paragraph("Weather Conditions", heading_style))
        weather_data = [
            ['Parameter', 'Value', 'Unit'],
            ['Temperature', f"{prediction.temperature:.1f}", '°C'],
            ['Humidity', f"{prediction.humidity:.1f}", '%'],
            ['Rainfall', f"{prediction.rainfall:.1f}", 'mm'],
        ]

        weather_table = Table(weather_data, colWidths=[2*inch, 1.5*inch, 1*inch])
        weather_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
        ]))
        content.append(weather_table)
        content.append(Spacer(1, 20))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6b7280'),
            alignment=1  # Center alignment
        )
        content.append(Spacer(1, 40))

        # Add actionable insights from Grok API
        try:
            actionable_insights = get_grok_crop_recommendation(
                soil_data={
                    'n': prediction.nitrogen,
                    'p': prediction.phosphorus,
                    'k': prediction.potassium,
                    'ph': prediction.ph,
                },
                weather_data={
                    'temperature': prediction.temperature,
                    'humidity': prediction.humidity,
                    'rainfall': prediction.rainfall,
                },
                crop=prediction.crop_recommended,
                location_name=location.name
            )

            insights_lines = actionable_insights.split('\n')
            content.append(Paragraph("Actionable Insights from Grok API", heading_style))
            for line in insights_lines:
                if line.strip():
                    content.append(Paragraph(line.strip(), styles['Normal']))
                    
            content.append(Spacer(1, 20))
        except Exception as e:
            logger.error(f"Error fetching Grok actionable insights for PDF: {str(e)}")

        content.append(Paragraph(
            f"Report generated by Smart Farma on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            footer_style
        ))

        # Build PDF
        doc.build(content)

        # Prepare file for download
        buffer.seek(0)

        # Create response
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=prediction_report_{prediction_id}_{datetime.now().strftime("%Y%m%d")}.pdf'

        return response


    except Exception as e:
        logger.error(f"Error generating PDF report: {str(e)}")
        return jsonify({'error': 'Failed to generate PDF report'}), 500


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

    # IMPORTANT: return raw features (do NOT standardize / clamp values here)
    return jsonify({
        'location': location_name,
        'location_id': location.id,
        'features': features,
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
            }
        }), 200

    if not model or not label_encoder:
        return jsonify({'error': 'Model or label encoder not loaded'}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data is required in the request body'}), 400

        features = data.get('features', data)
        location_id = data.get('location_id')
        location_name = data.get('location')

        required_features = ['n', 'p', 'k', 'ph', 'temperature', 'humidity', 'rainfall']

        # lowercase keys
        features = {k.lower(): v for k, v in features.items()}

        if not all(k in features for k in required_features):
            missing = [k for k in required_features if k not in features]
            return jsonify({'error': f'Missing required features: {missing}'}), 400

        if not location_id or not location_name:
            return jsonify({'error': 'Location ID and name are required'}), 400

        # === BUILD INPUT FOR MODEL ===
        input_map = {
            'N': float(features['n']),
            'P': float(features['p']),
            'K': float(features['k']),
            'temperature': float(features['temperature']),
            'humidity': float(features['humidity']),
            'ph': float(features['ph']),
            'rainfall': float(features['rainfall']),
        }

        try:
            model_cols = list(model.feature_names_in_)
        except:
            model_cols = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']

        input_df = pd.DataFrame([input_map])[model_cols]
        feature_array = input_df.to_numpy()

        # --- MODEL PREDICTION ---
        probabilities = model.predict_proba(feature_array)[0]
        model_classes = model.classes_
        predicted_label = model.predict(feature_array)[0]

        # Decode label
        if isinstance(predicted_label, (int, np.integer)):
            predicted_crop = label_encoder.inverse_transform([predicted_label])[0]
        else:
            predicted_crop = str(predicted_label)

        # ----------------------------------------------------------
        # 🔥 HYBRID SMART-KENYA RULE ENGINE (Option 1 fix)
        # ----------------------------------------------------------
        corrected_scores = {}
        temp = float(features["temperature"])
        rainfall = float(features["rainfall"])
        humidity = float(features["humidity"])
        ph = float(features["ph"])

        for idx, label in enumerate(model_classes):

            # decode each crop
            if isinstance(label, (int, np.integer)):
                crop_name = label_encoder.inverse_transform([label])[0]
            else:
                crop_name = str(label)

            prob = float(probabilities[idx])
            suitability = 1.0

            # RULE 1 — Penalize apples everywhere
            if crop_name.lower() == "apple":
                prob *= 0.15

            # RULE 2 — High temperature areas
            if temp > 22:
                if crop_name.lower() in ["banana", "mango", "cassava", "pineapple", "papaya", "sugarcane"]:
                    suitability += 0.35
                if crop_name.lower() in ["maize", "sorghum", "millet"]:
                    suitability += 0.15

            # RULE 3 — Cold areas
            if temp < 18:
                if crop_name.lower() in ["tea", "potatoes", "cabbage", "peas"]:
                    suitability += 0.40
                if crop_name.lower() in ["wheat", "barley"]:
                    suitability += 0.25

            # RULE 4 — Low rainfall
            if rainfall < 5:
                if crop_name.lower() in ["sorghum", "millet", "pigeon pea", "cowpeas"]:
                    suitability += 0.40

            # RULE 5 — High rainfall
            if rainfall > 15:
                if crop_name.lower() in ["rice", "sugarcane"]:
                    suitability += 0.30

            # RULE 6 — Acidic soils
            if ph < 6:
                if crop_name.lower() in ["tea", "potatoes"]:
                    suitability += 0.25
                if crop_name.lower() in ["maize"]:
                    suitability += 0.10

            # HYBRID SCORE: 70% ML + 30% Rules
            final_score = (0.7 * prob) + (0.3 * suitability)
            corrected_scores[crop_name] = final_score

        # Sorted top-4 final recommendations
        sorted_crops = sorted(corrected_scores.items(), key=lambda x: x[1], reverse=True)
        predictions = [
            {"crop": crop, "probability": float(score)}
            for crop, score in sorted_crops[:4]
        ]

        # Save prediction
        prediction_record = Prediction(
            location_id=location_id,
            user_id=current_user.id if current_user.is_authenticated else None,
            nitrogen=float(features['n']),
            phosphorus=float(features['p']),
            potassium=float(features['k']),
            ph=float(features['ph']),
            temperature=float(features['temperature']),
            humidity=float(features['humidity']),
            rainfall=float(features['rainfall']),
            crop_recommended=predictions[0]["crop"],
            is_suitable=True,
            confidence_score=predictions[0]["probability"],
        )
        db.session.add(prediction_record)
        db.session.commit()

        # Fetch Grok actionable insights
        try:
            grok_recommendation = get_grok_crop_recommendation(
                soil_data={
                    'n': float(features['n']),
                    'p': float(features['p']),
                    'k': float(features['k']),
                    'ph': float(features['ph'])
                },
                weather_data={
                    'temperature': float(features['temperature']),
                    'humidity': float(features['humidity']),
                    'rainfall': float(features['rainfall'])
                },
                crop=predictions[0]["crop"],
                location_name=location_name
            )
        except Exception as grok_e:
            logger.error(f"Grok recommendation error: {str(grok_e)}")
            grok_recommendation = "Failed to fetch actionable insights from Grok API."

        return jsonify({
            'predictions': predictions,
            'suitability': None,
            'openai_recommendation': None,
            'grok_recommendation': grok_recommendation
        }), 200

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}. Input features: {features}")
        return jsonify({'error': f'Prediction error: {str(e)}'}), 500



