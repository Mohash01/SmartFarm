import os
import requests

# Replace with your actual WeatherAPI key
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY", "a8f656b81fb548bf82c125713251705")


def get_lat_lon(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': address,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'SmartFarmApp/1.0 (mainamanasseh02@gmail.com)'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        results = response.json()
        if results:
            return results[0]
        else:
            print(f"No geocoding result for address: {address}")
            return {}
    except Exception as e:
        print(f"Geocoding error: {e}")
        return {}


def fetch_soil_data(lat, lon):
    SOILGRID_API_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    
    try:
        headers = {
            'Accept': 'application/json'
        }

        response = requests.get(
            SOILGRID_API_URL,
            params={
                "lat": lat,
                "lon": lon,
                "depths": "0-5cm",
                "properties": "bdod,soc,phh2o,cec"
            },
            headers=headers
        )

        if response.status_code != 200:
            print("SoilGrids API Error:", response.status_code)
            print("Response body:", response.text[:500])
            return None

        data = response.json()
        properties = data.get("properties", {})
        soil = {}

        def extract_value(prop_name):
            try:
                for layer in properties.get("layers", []):
                    if layer["name"] == prop_name:
                        return layer["depths"][0]["values"]["mean"]
                return None
            except (KeyError, TypeError, IndexError) as e:
                print(f"Error extracting {prop_name}: {e}")
                return None

        soil["N"] = extract_value("bdod")
        soil["P"] = extract_value("soc")
        soil["K"] = extract_value("cec")
        soil["pH"] = extract_value("phh2o")

        return soil

    except Exception as e:
        print(f"Error fetching soil data: {e}")
        return None


def fetch_weather_data(city_name):
    url = f"http://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": WEATHERAPI_KEY,
        "q": city_name,
        "days": 1,
        "aqi": "no",
        "alerts": "no"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        current = data['current']
        forecast = data['forecast']['forecastday'][0]['day']

        temperature = current['temp_c']
        humidity = current['humidity']
        rainfall = forecast.get('totalprecip_mm', 0.0)

        return {
            "temperature": temperature,
            "humidity": humidity,
            "rainfall": rainfall
        }

    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return {
            "temperature": None,
            "humidity": None,
            "rainfall": None
        }


def get_model_input_features(location_name):
    location = get_lat_lon(location_name)
    if not location:
        print("Could not retrieve coordinates.")
        return None

    lat = location['lat']
    lon = location['lon']

    soil_data = fetch_soil_data(lat, lon)
    weather_data = fetch_weather_data(location_name)

    if not soil_data or not weather_data:
        print("Failed to fetch complete data.")
        return None

    model_input = {
        "N": soil_data["N"],
        "P": soil_data["P"],
        "K": soil_data["K"],
        "pH": soil_data["pH"],
        "temperature": weather_data["temperature"],
        "humidity": weather_data["humidity"],
        "rainfall": weather_data["rainfall"]
    }

    print("\n✅ Model Input Features")
    print("========================")
    for k, v in model_input.items():
        print(f"{k}: {v}")

    return model_input







from flask import Blueprint, render_template, request, jsonify
from apps.data.util import get_lat_lon, fetch_soil_data,get_model_input_features,fetch_weather_data


blueprint = Blueprint('data_blueprint', __name__, url_prefix='/data')


@blueprint.route('/chat')
def chat():
    return render_template('home/virtual-reality.html')

@blueprint.route('/location')
def locations():
    return render_template('locations/view_locations.html')

@blueprint.route('/soil')
def soil():
    return render_template('soil/view_soil.html')

@blueprint.route('/weather')
def weather():
    return render_template('weather/view_weather.html')


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
    if not geo_data:
        return jsonify({'error': 'Failed to get geolocation data'}), 500

    lat = geo_data.get('lat')
    lon = geo_data.get('lon')
    if not lat or not lon:
        return jsonify({'error': 'Latitude and longitude could not be found'}), 500

    soil_data = fetch_soil_data(lat, lon)
    if soil_data is None:
        return jsonify({'error': 'Failed to fetch soil data from SoilGrids'}), 500

    response_data = {
        'location': {
            'address': geo_data.get('display_name'),
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
    
    weather = fetch_weather_data(city)
    if all(value is None for value in weather.values()):
        return jsonify({"error": "Failed to fetch weather data"}), 500
    
    return jsonify({
        "city": city,
        "weather": weather
    })


@blueprint.route('/model-input', methods=['GET'])
def model_input():
    location = request.args.get('location')
    if not location:
        return jsonify({'error': 'Location parameter is required'}), 400

    features = get_model_input_features(location)
    if not features:
        return jsonify({'error': 'Failed to fetch complete model input features'}), 500

    return jsonify({
        'location': location,
        'features': features
    }), 200
