from flask import Blueprint, render_template
from apps.crop.models import Location
from apps.model.models import Prediction
from apps import db

blueprint = Blueprint('model_blueprint', __name__, url_prefix='/model')

@blueprint.route('/')
def prediction():
    predictions = Prediction.query.order_by(Prediction.timestamp.desc()).all()

    serialized_predictions = []
    for p in predictions:
        serialized_predictions.append({
            'timestamp': p.timestamp.strftime('%Y-%m-%d %H:%M'),
            'location': p.location.name if p.location else "Unknown",
            'crop_recommended': p.crop_recommended,
            'is_suitable': p.is_suitable,
            'confidence_score': p.confidence_score
        })

    return render_template(
        'predictions/view_predictions.html',
        predictions=predictions,
        json_predictions=serialized_predictions
    )

