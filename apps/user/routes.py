from flask import Blueprint, render_template
from datetime import datetime, timedelta
from apps.authentication.models import Users
from sqlalchemy import func

blueprint = Blueprint('user_blueprint', __name__, url_prefix='/users')

@blueprint.route('/')
def users():
    # Fetch all users
    all_users = Users.query.all()
    
    
    return render_template(
        'users/view_users.html',
        users=all_users,
    )