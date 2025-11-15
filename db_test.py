import requests
import json

def get_lat_lon(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': address,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'SmartFarmApp/1.0 (test@example.com)'
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
            print("Response body:", response.text[:500])  # Print first 500 chars of response for debugging
            return None

        data = response.json()
        properties = data.get("properties", {})
        soil = {}

        def extract_value(prop_name):
            try:
                # Look for the property in the layers list
                for layer in properties.get("layers", []):
                    if layer["name"] == prop_name:
                        return layer["depths"][0]["values"]["mean"]
                return None
            except (KeyError, TypeError, IndexError) as e:
                print(f"Error extracting {prop_name}: {e}")
                return None

        # These are approximate conversions for demonstration
        soil["N"] = extract_value("bdod")  # Using bulk density as proxy
        soil["P"] = extract_value("soc")   # Using soil organic carbon as proxy
        soil["K"] = extract_value("cec")   # Using cation exchange capacity as proxy
        soil["pH"] = extract_value("phh2o")

        return soil

    except Exception as e:
        print(f"Error fetching soil data: {e}")
        return None

def suggest_crops(soil_data):
    n_value = soil_data.get('N')
    p_value = soil_data.get('P')
    k_value = soil_data.get('K')
    ph_value = soil_data.get('pH')
    
    print("\nCrop Suggestions Based on Soil Data:")
    
    # These are simplified suggestions based on general soil requirements
    # In a real application, you would need more comprehensive crop data
    
    # pH-based suggestions
    if ph_value is not None:
        if ph_value < 5.5:
            print("  Acidic soil crops: Blueberries, Potatoes, Sweet Potatoes")
        elif ph_value < 6.5:
            print("  Slightly acidic soil crops: Corn, Wheat, Oats, Rye")
        elif ph_value < 7.5:
            print("  Neutral soil crops: Soybeans, Alfalfa, Vegetables, Cotton")
        else:
            print("  Alkaline soil crops: Asparagus, Beets, Cabbage")
    
    # Soil density (N proxy) based suggestions
    if n_value is not None:
        if n_value < 110:
            print("  Low density soil crops: Root vegetables like Carrots, Radishes")
        elif n_value < 140:
            print("  Medium density soil crops: Most grains and vegetables")
        else:
            print("  High density soil crops: Shallow-rooted crops like Lettuce, Spinach")
    
    # Based on combination of factors
    good_conditions = 0
    
    if p_value is not None and p_value > 15:
        good_conditions += 1
    
    if k_value is not None and k_value > 15:
        good_conditions += 1
    
    if ph_value is not None and 6.0 <= ph_value <= 7.5:
        good_conditions += 1
    
    if good_conditions >= 2:
        print("  High-value crops suitable for these soil conditions: Tomatoes, Peppers, Eggplants")
    
    return True

# Function to show raw API response
def show_raw_response(lat, lon):
    print("\nRaw API response:")
    raw_response = requests.get(
        "https://rest.isric.org/soilgrids/v2.0/properties/query",
        params={
            "lat": lat,
            "lon": lon,
            "depths": "0-5cm",
            "properties": "bdod,soc,phh2o,cec"
        },
        headers={'Accept': 'application/json'}
    )
    if raw_response.status_code == 200:
        pretty_json = json.dumps(raw_response.json(), indent=2)
        # Print just the first 1000 characters to avoid excessive output
        print(pretty_json[:1000] + "..." if len(pretty_json) > 1000 else pretty_json)
    else:
        print(f"Failed to get raw response: {raw_response.status_code}")

# Function to interpret soil data and suggest crops
def suggest_crops(soil_data):
    n_value = soil_data.get('N')
    p_value = soil_data.get('P')
    k_value = soil_data.get('K')
    ph_value = soil_data.get('pH')
    
    print("\nCrop Suggestions Based on Soil Data:")
    
    # These are simplified suggestions based on general soil requirements
    # In a real application, you would need more comprehensive crop data
    
    # pH-based suggestions
    if ph_value is not None:
        if ph_value < 5.5:
            print("  Acidic soil crops: Blueberries, Potatoes, Sweet Potatoes")
        elif ph_value < 6.5:
            print("  Slightly acidic soil crops: Corn, Wheat, Oats, Rye")
        elif ph_value < 7.5:
            print("  Neutral soil crops: Soybeans, Alfalfa, Vegetables, Cotton")
        else:
            print("  Alkaline soil crops: Asparagus, Beets, Cabbage")
    
    # Soil density (N proxy) based suggestions
    if n_value is not None:
        if n_value < 110:
            print("  Low density soil crops: Root vegetables like Carrots, Radishes")
        elif n_value < 140:
            print("  Medium density soil crops: Most grains and vegetables")
        else:
            print("  High density soil crops: Shallow-rooted crops like Lettuce, Spinach")
    
    # Based on combination of factors
    good_conditions = 0
    
    if p_value is not None and p_value > 15:
        good_conditions += 1
    
    if k_value is not None and k_value > 15:
        good_conditions += 1
    
    if ph_value is not None and 6.0 <= ph_value <= 7.5:
        good_conditions += 1
    
    if good_conditions >= 2:
        print("  High-value crops suitable for these soil conditions: Tomatoes, Peppers, Eggplants")
    
    return True

import requests
import json

def get_lat_lon(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': address,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'SmartFarmApp/1.0 (test@example.com)'
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
            print("Response body:", response.text[:500])  # Print first 500 chars of response for debugging
            return None

        data = response.json()
        properties = data.get("properties", {})
        soil = {}

        def extract_value(prop_name):
            try:
                # Look for the property in the layers list
                for layer in properties.get("layers", []):
                    if layer["name"] == prop_name:
                        return layer["depths"][0]["values"]["mean"]
                return None
            except (KeyError, TypeError, IndexError) as e:
                print(f"Error extracting {prop_name}: {e}")
                return None

        # These are approximate conversions for demonstration
        soil["N"] = extract_value("bdod")  # Using bulk density as proxy
        soil["P"] = extract_value("soc")   # Using soil organic carbon as proxy
        soil["K"] = extract_value("cec")   # Using cation exchange capacity as proxy
        soil["pH"] = extract_value("phh2o")

        return soil

    except Exception as e:
        print(f"Error fetching soil data: {e}")
        return None

# Test for Nakuru, Kenya
def test_location(location_name):
    print(f"Testing soil data for: {location_name}")

    # Step 1: Get coordinates
    geo_data = get_lat_lon(location_name)
    if not geo_data:
        print("Failed to get coordinates for location")
        return False

    lat = geo_data.get('lat')
    lon = geo_data.get('lon')
    print(f"Coordinates: Lat {lat}, Lon {lon}")

    # Step 2: Fetch soil data
    soil_data = fetch_soil_data(lat, lon)
    if not soil_data:
        print("Failed to fetch soil data")
        return False

    # Print results
    print("\nLocation information:")
    print(f"  Address: {geo_data.get('display_name')}")
    print(f"  Lat: {lat}")
    print(f"  Lon: {lon}")

    print("\nSoil data:")
    print(f"  N (proxy from bdod): {soil_data.get('N')}")
    print(f"  P (proxy from soc): {soil_data.get('P')}")
    print(f"  K (proxy from cec): {soil_data.get('K')}")
    print(f"  pH: {soil_data.get('pH')}")

    # Interpret the results
    print("\nSoil interpretation:")
    
    # Bulk density interpretation (N proxy)
    # Values based on general soil science guidelines
    bdod = soil_data.get('N')
    if bdod is not None:
        if bdod < 100:
            print(f"  N proxy (Bulk Density): {bdod} - Low density soil, generally good for root growth")
        elif bdod < 130:
            print(f"  N proxy (Bulk Density): {bdod} - Medium density soil, acceptable for most crops")
        else:
            print(f"  N proxy (Bulk Density): {bdod} - High density soil, may restrict root growth")
    
    # Organic carbon interpretation (P proxy)
    # Values based on general soil fertility guidelines
    soc = soil_data.get('P')
    if soc is not None:
        if soc < 10:
            print(f"  P proxy (Soil Organic Carbon): {soc} - Low organic carbon content")
        elif soc < 20:
            print(f"  P proxy (Soil Organic Carbon): {soc} - Medium organic carbon content")
        else:
            print(f"  P proxy (Soil Organic Carbon): {soc} - High organic carbon content")
    
    # CEC interpretation (K proxy)
    # Values based on general soil fertility guidelines
    cec = soil_data.get('K')
    if cec is not None:
        if cec < 10:
            print(f"  K proxy (Cation Exchange Capacity): {cec} - Low CEC, poor nutrient retention")
        elif cec < 20:
            print(f"  K proxy (Cation Exchange Capacity): {cec} - Medium CEC, moderate nutrient retention")
        else:
            print(f"  K proxy (Cation Exchange Capacity): {cec} - High CEC, good nutrient retention")
    
    # pH interpretation
    # Values based on standard soil pH ranges
    ph = soil_data.get('pH')
    if ph is not None:
        if ph < 5.5:
            print(f"  pH: {ph} - Acidic soil, may need liming for most crops")
        elif ph < 7.5:
            print(f"  pH: {ph} - Neutral soil, optimal for most crops")
        else:
            print(f"  pH: {ph} - Alkaline soil, may need acidification for some crops")
    
    return True

# Test multiple locations
locations_to_test = [
    "Nakuru, Kenya",
    "Nairobi, Kenya",
    "Mombasa, Kenya"
]

for location in locations_to_test:
    print("\n" + "="*60)
    test_location(location)
    print("="*60)
    
    
    
    
    
    
    
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