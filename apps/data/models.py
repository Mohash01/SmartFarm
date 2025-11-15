from apps import db
from datetime import datetime

class SoilData(db.Model):
    __tablename__ = 'soil_data'

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    nitrogen = db.Column(db.Float, nullable=False)  # N
    phosphorus = db.Column(db.Float, nullable=False)  # P
    potassium = db.Column(db.Float, nullable=False)  # K
    ph = db.Column(db.Float, nullable=False)
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)

    location = db.relationship('Location', backref=db.backref('soil_records', lazy=True))

    def __repr__(self):
        return f"<SoilData location={self.location_id} N={self.nitrogen}>"

class WeatherData(db.Model):
    __tablename__ = 'weather_data'

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)

    location = db.relationship('Location', backref=db.backref('weather_records', lazy=True))

    def __repr__(self):
        return f"<WeatherData location={self.location_id} Temp={self.temperature}>"
