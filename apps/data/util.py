import os
import requests
import time
import logging
from typing import Dict, Optional
import json
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()  # <-- ensure environment variables are loaded

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WeatherAPI key
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY", "a8f656b81fb548bf82c125713251705")
# Cache file for soil data
CACHE_FILE = "soil_data_cache.json"

# iSDAsoil API credentials
ISDA_API_USERNAME = os.getenv("ISDA_API_USERNAME", "YOUR_EMAIL")
ISDA_API_PASSWORD = os.getenv("ISDA_API_PASSWORD", "YOUR_PASSWORD")
ISDA_API_BASE_URL = "http://test-api.isda-africa.com/isdasoil/v2"

# Grok  API key
#GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")



def get_lat_lon(address: str, retries: int = 3, delay: int = 2, timeout: int = 15) -> Optional[Dict[str, any]]:
    """
    Fetch latitude and longitude for a given address using Nominatim with retries.
    """
    address_lower = address.lower().strip()
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': address,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'SmartFarmApp/1.0 (muhammadhamdun19@gmail.com)'
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            results = response.json()
            if results:
                result = {
                    'lat': float(results[0]['lat']),
                    'lon': float(results[0]['lon']),
                    'display_name': results[0].get('display_name', address),
                    'name': address  # Include original address for location storage
                }
                logger.info(f"Fetched coordinates for {address}: {result}")
                return result
            logger.warning(f"No geocoding result for address: {address} (attempt {attempt}/{retries})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Geocoding error for {address} (attempt {attempt}/{retries}): {str(e)}")
            if attempt < retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)

    logger.error(f"Failed to fetch coordinates for {address} after {retries} attempts")
    return None

def fetch_weather_data(city_name: str) -> Dict[str, Optional[float]]:
    """
    Fetch weather data (temperature, humidity, rainfall) from WeatherAPI.
    """
    url = "http://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": WEATHERAPI_KEY,
        "q": city_name,
        "days": 1,
        "aqi": "no",
        "alerts": "no"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data['current']
        forecast = data['forecast']['forecastday'][0]['day']

        weather = {
            "temperature": float(current['temp_c']),  # °C
            "humidity": float(current['humidity']),   # %
            "rainfall": float(forecast.get('totalprecip_mm', 0.0))  # mm
        }
        logger.info(f"Fetched weather data for {city_name}: {weather}")
        return weather

    except Exception as e:
        logger.error(f"Error fetching weather data for {city_name}: {str(e)}")
        return {
            "temperature": 25.0,  # °C
            "humidity": 60.0,     # %
            "rainfall": 100.0     # mm
        }

def load_cache() -> Dict:
    """Load cached soil data from file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache: Dict) -> None:
    """Save soil data to cache file."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def get_isda_token() -> str | None:
    """
    Authenticate with iSDAsoil production API and return a JWT token.
    """
    url = "https://api.isda-africa.com/login"
    data = {
        "grant_type": "password",
        "username": ISDA_API_USERNAME,
        "password": ISDA_API_PASSWORD,
        "scope": "",
        "client_id": "string",
        "client_secret": "string"
    }
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        token = response.json().get("access_token")
        if token:
            logger.info("✅ Successfully obtained iSDAsoil API token")
            return token
        else:
            logger.error("❌ No token in response")
            return None
    except Exception as e:
        logger.error(f"❌ Error obtaining iSDAsoil API token: {str(e)}")
        return None

    
def fetch_soil_data(lat: float, lon: float, retries: int = 3, delay: int = 2) -> dict:
    url = "https://api.isda-africa.com/isdasoil/v2/soilproperty"
    params = {
        "lon": lon,
        "lat": lat,
        "depth": "0-20"
        # omit property filter, fetch all
    }

    for attempt in range(1, retries + 1):
        try:
            token = get_isda_token()
            if not token:
                raise Exception("No token available")

            headers = {
                "Authorization": f"Bearer {token}",
                "accept": "application/json"
            }
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            props = data.get("property", {})

            # Safely extract values
            def extract(prop_name, default):
                try:
                    return float(props[prop_name][0]["value"]["value"])
                except Exception:
                    return default

            soil = {
                "N": extract("nitrogen_total", 100.0),
                "P": extract("phosphorous_extractable", 30.0),
                "K": extract("potassium_extractable", 300.0),
                "ph": extract("ph", 6.5)
            }
            logger.info(f"✅ Soil data fetched (attempt {attempt}): {soil}")
            return soil

        except Exception as e:
            logger.error(f"⚠️ API error (attempt {attempt}/{retries}): {str(e)}")
            if attempt < retries:
                time.sleep(delay)

    logger.warning("⚠️ Failed after retries, using fallback soil data")
    return {"N": 100.0, "P": 30.0, "K": 300.0, "ph": 6.5}




def get_model_input_features(location_name: str) -> Optional[Dict[str, float]]:
    """
    Fetch and combine soil and weather data for model input.
    """
    location = get_lat_lon(location_name)
    if not location or 'lat' not in location or 'lon' not in location:
        logger.error(f"Could not retrieve coordinates for {location_name}")
        return None

    lat = location['lat']
    lon = location['lon']

    soil_data = fetch_soil_data(lat, lon)
    weather_data = fetch_weather_data(location_name)

    model_input = {
        "N": soil_data["N"],
        "P": soil_data["P"],
        "K": soil_data["K"],
        "ph": soil_data["ph"],
        "temperature": weather_data["temperature"],
        "humidity": weather_data["humidity"],
        "rainfall": weather_data["rainfall"]
    }

    if any(v is None for v in model_input.values()):
        logger.error(f"Incomplete model input for {location_name}: {model_input}")
        return None

    logger.info("\n✅ Model Input Features")
    logger.info("========================")
    for k, v in model_input.items():
        logger.info(f"{k}: {v}")

    return model_input

def standardize_model_inputs(features: Dict[str, float]) -> Dict[str, float]:
    """
    Disable ALL standardization.
    The Random Forest model was trained on raw Kaggle values,
    so altering them (clamping/min/max) breaks predictions.
    """
    return features



def print_standardization_summary(original: Dict[str, float], standardized: Dict[str, float]) -> None:
    """
    Print a summary of the standardization process.
    """
    logger.info("\n📊 Standardization Summary")
    logger.info("=========================")
    for key in original:
        logger.info(f"{key}: {original[key]} -> {standardized[key]}")

def get_grok_crop_recommendation(soil_data, weather_data, crop=None, location_name=None):
    """
    Use Grok API to generate farmer-friendly crop insights.
    """

    if not GROK_API_KEY:
        return "Grok API key not configured."

    url = "https://api.x.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROK_API_KEY}"
    }

    prompt = f"""
You are an agricultural expert.
Provide SIMPLE, PRACTICAL farming recommendations for farmers in {location_name}.

Crop: {crop}

Soil:
- Nitrogen: {soil_data.get('n')}
- Phosphorus: {soil_data.get('p')}
- Potassium: {soil_data.get('k')}
- pH: {soil_data.get('ph')}

Weather:
- Temperature: {weather_data.get('temperature')}°C
- Humidity: {weather_data.get('humidity')}%
- Rainfall: {weather_data.get('rainfall')} mm

Return:
1. Best planting time
2. Soil preparation tips
3. Optimal fertilizer schedule
4. Watering/irrigation guidance
5. Pests & disease alerts
6. Expected growth timeline
7. Harvesting tips
"""

    payload = {
        "model": "grok-2-latest",
        "messages": [
            {"role": "system", "content": "You are a helpful agricultural advisor."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 600
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()

        # Extract text
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Error contacting Grok API: {str(e)}"


def test_grok_connection():
    """
    Test Grok API connectivity
    """
    if not GROK_API_KEY:
        return "Grok API key is not set. Please configure it in your environment."

    url = "https://api.x.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROK_API_KEY}"
    }

    payload = {
        "model": "grok-2-latest",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Respond with: Connection successful"}
        ],
        "max_tokens": 10,
        "temperature": 0
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code != 200:
            return f"Error: {response.status_code}, {response.text}"

        return response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Error testing Grok connection: {str(e)}"
