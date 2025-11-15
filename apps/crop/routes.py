from flask import Blueprint, render_template

blueprint = Blueprint('crop_blueprint', __name__, url_prefix='/crop')

@blueprint.route('/')
def index():
    return render_template('crop/index.html')
