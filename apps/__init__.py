from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from importlib import import_module

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Configure login manager to redirect to login page instead of showing 403
    login_manager.login_view = 'authentication_blueprint.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'


def register_blueprints(app):
    # Add all your modules here
    for module_name in ('authentication', 'home', 'crop', 'data', 'model','user'):
        module = import_module(f'apps.{module_name}.routes')
        app.register_blueprint(module.blueprint)
    
    # Exempt the predict endpoint from CSRF protection
    try:
        csrf.exempt('data_blueprint.predict')
        print("CSRF exemption for data_blueprint.predict applied successfully")
    except Exception as e:
        print(f"Failed to apply CSRF exemption: {e}")
        # Alternative method to exempt the view
        with app.app_context():
            csrf.exempt(app.view_functions.get('data_blueprint.predict'))


def configure_database(app):
    @app.before_request
    def initialize_database():
        if not hasattr(app, '_database_initialized'):
            try:
                with app.app_context():
                    db.create_all()
                    app._database_initialized = True
            except Exception as e:
                print('> Error: DBMS Exception: ' + str(e))
                raise e 

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    return app
