from flask import Blueprint

blueprint = Blueprint(
    'crop_blueprint',
    __name__,
    url_prefix='/crop'  
)

from . import routes  
