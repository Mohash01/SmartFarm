from apps.data.util import fetch_soil_data

lat = -1.2921
lon = 36.8219

soil = fetch_soil_data(lat, lon)
print("Soil data for Nairobi:", soil)