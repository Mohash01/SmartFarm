import os
import requests
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("ISDA_API_USERNAME")
password = os.getenv("ISDA_API_PASSWORD")

url = "https://api.isda-africa.com/login"
data = {
    "grant_type": "password",
    "username": username,
    "password": password,
    "scope": "",          # must be present, even if empty
    "client_id": "string",   # must be present, even if placeholder
    "client_secret": "string" # must be present, even if placeholder
}
headers = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}

response = requests.post(url, data=data, headers=headers)
print("Status:", response.status_code)
print("Response:", response.text)