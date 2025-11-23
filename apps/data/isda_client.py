import time
import requests
import os
from dotenv import load_dotenv
from typing import Optional, Dict

load_dotenv()

ISDA_API_USERNAME = os.getenv("ISDA_API_USERNAME")
ISDA_API_PASSWORD = os.getenv("ISDA_API_PASSWORD")

class ISDAClient:
    def __init__(self, base_url: str = "https://api.isda-africa.com"):
        self.base_url = base_url
        self.username = ISDA_API_USERNAME
        self.password = ISDA_API_PASSWORD
        self.token: Optional[str] = None
        self.token_expiry: float = 0  # epoch time

    def _authenticate(self) -> None:
        url = f"{self.base_url}/login"
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        payload = response.json()
        self.token = payload.get("access_token")
        self.token_expiry = time.time() + 3600  # token valid for 1 hour

    def _get_token(self) -> str:
        if not self.token or time.time() >= self.token_expiry:
            self._authenticate()
        return self.token

    def fetch_soil_data(self, lat: float, lon: float, retries: int = 3, delay: int = 2) -> Dict[str, float]:
        """
        Fetch soil data with retry logic. Falls back to defaults if all attempts fail.
        """
        url = f"{self.base_url}/isdasoil/v2/soilproperty"
        params = {
            "lon": lon,
            "lat": lat,
            "depth": "0-20",
            "property": "nitrogen_total,phosphorous_extractable,potassium_extractable,ph"
        }

        for attempt in range(1, retries + 1):
            try:
                headers = {
                    "Authorization": f"Bearer {self._get_token()}",
                    "accept": "application/json"
                }
                response = requests.get(url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                props = data.get("properties", {})

                if not props:
                    print(f"Attempt {attempt}: Empty properties for lat={lat}, lon={lon}")
                    continue

                soil = {
                    "N": float(props.get("nitrogen_total", 100.0)),
                    "P": float(props.get("phosphorous_extractable", 30.0)),
                    "K": float(props.get("potassium_extractable", 300.0)),
                    "ph": float(props.get("ph", 6.5))
                }
                print(f"Fetched soil data (attempt {attempt}): {soil}")
                return soil

            except requests.exceptions.RequestException as e:
                print(f"API error (attempt {attempt}/{retries}): {str(e)}")
                if attempt < retries:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)

        print("Failed after retries, using fallback soil data")
        return {"N": 100.0, "P": 30.0, "K": 300.0, "ph": 6.5}