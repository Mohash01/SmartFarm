from apps import db
from datetime import datetime

class Prediction(db.Model):
    __tablename__ = 'predictions'

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for backwards compatibility

    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)

    crop_recommended = db.Column(db.String(100), nullable=False)
    is_suitable = db.Column(db.Boolean, nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    location = db.relationship('Location', backref=db.backref('predictions', lazy=True))
    user = db.relationship('Users', backref=db.backref('predictions', lazy=True))

    def __repr__(self):
        return f"<Prediction location={self.location_id} crop={self.crop_recommended} confidence={self.confidence_score}>"
