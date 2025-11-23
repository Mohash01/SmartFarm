import os
import requests
import time
import logging
from typing import Dict, Optional
import json
import openai
import google.generativeai as genai
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

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Generative AI API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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
    Standardize model input features to match training data ranges (in ppm/mg/kg).
    """
    standardized = features.copy()
    ranges = {
        "N": {"min": 0.0, "max": 200.0},  # ppm
        "P": {"min": 0.0, "max": 150.0},  # ppm
        "K": {"min": 0.0, "max": 200.0},  # ppm
        "ph": {"min": 3.5, "max": 10.0},  # pH units
        "temperature": {"min": 8.0, "max": 44.0},  # °C
        "humidity": {"min": 14.0, "max": 100.0},  # %
        "rainfall": {"min": 20.0, "max": 300.0}   # mm
    }
    fallback_values = {
        "N": 100.0,  # ppm
        "P": 30.0,   # ppm
        "K": 300.0,  # ppm
        "ph": 6.5,   # pH units
        "temperature": 25.0,  # °C
        "humidity": 60.0,     # %
        "rainfall": 100.0     # mm
    }
    for key, value in standardized.items():
        if key in ranges:
            min_val = ranges[key]["min"]
            max_val = ranges[key]["max"]
            if value < min_val:
                standardized[key] = min_val
            elif value > max_val:
                standardized[key] = max_val
        else:
            standardized[key] = fallback_values.get(key, value)
    return standardized

def print_standardization_summary(original: Dict[str, float], standardized: Dict[str, float]) -> None:
    """
    Print a summary of the standardization process.
    """
    logger.info("\n📊 Standardization Summary")
    logger.info("=========================")
    for key in original:
        logger.info(f"{key}: {original[key]} -> {standardized[key]}")

def get_gemini_recommendation(soil_data, weather_data, crop=None):
    """
    Use Google Generative AI (Gemini) to generate expert farming tips and recommendations based on soil, weather, and crop data.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured")
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        prompt = f"""
        Given the following soil and weather data:
        Soil: {soil_data}
        Weather: {weather_data}
        {f'Crop: {crop}' if crop else ''}
        Provide actionable, expert farming tips and recommendations for this location. Be concise and practical.
        """
        # Using gemini-2.0-flash model for faster responses
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error in Gemini API call: {str(e)}")
        return None

def test_gemini_connection():
    """
    Test function to verify Gemini API connectivity
    """
    if not GEMINI_API_KEY:
        return "Google API key is not set. Please configure it in your environment."
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Test connection - respond with 'Connection successful'")
        return response.text
    except Exception as e:
        logger.error(f"Error testing Gemini connection: {str(e)}")
        return f"Error testing Gemini connection: {str(e)}"