
from apps.home import blueprint
from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
from apps.data.models import SoilData, WeatherData
from apps.crop.models import Location
from apps.model.models import Prediction

@blueprint.route('/index')
@login_required
def index():
    # Additional check: only admins can access dashboard
    print(f"DEBUG: Index route accessed")
    print(f"DEBUG: current_user.is_authenticated: {current_user.is_authenticated}")
    print(f"DEBUG: current_user.id: {current_user.id if current_user.is_authenticated else 'Not authenticated'}")
    print(f"DEBUG: current_user.username: {current_user.username if current_user.is_authenticated else 'Not authenticated'}")
    print(f"DEBUG: current_user.is_admin: {current_user.is_admin if current_user.is_authenticated else 'Not authenticated'}")
    
    if not current_user.is_admin:
        print(f"DEBUG: User is not admin, redirecting to predictions")
        print(f"DEBUG: current_user object: {current_user}")
        print(f"DEBUG: type of current_user: {type(current_user)}")
        return redirect(url_for('data_blueprint.prediction'))
    
    print(f"DEBUG: User is admin, loading dashboard")
    total_locations = Location.query.count()
    total_predictions = Prediction.query.count()
    total_soil_records = SoilData.query.count()
    total_weather_records = WeatherData.query.count()
    recent_predictions = Prediction.query.order_by(Prediction.timestamp.desc()).limit(5).all()

    from collections import Counter
    crop_counts = Counter([p.crop_recommended for p in Prediction.query.all()])
    labels = list(crop_counts.keys())
    data = list(crop_counts.values())

    return render_template(
        'home/index.html',
        segment='index',
        total_locations=total_locations,
        total_predictions=total_predictions,
        total_soil_records=total_soil_records,
        total_weather_records=total_weather_records,
        recent_predictions=recent_predictions,
        labels=labels,
        data=data
    )



@blueprint.route('/<template>')
def route_template(template):
    # Only require login for protected templates
    protected_templates = ['index', 'billing', 'profile', 'tables', 'rtl', 'virtual-reality']
    
    try:
        if not template.endswith('.html'):
            template += '.html'
        
        # Check if template requires authentication
        template_name = template.replace('.html', '')
        if template_name in protected_templates:
            from flask_login import current_user
            from flask import redirect, url_for
            if not current_user.is_authenticated:
                return redirect(url_for('authentication_blueprint.login'))

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
