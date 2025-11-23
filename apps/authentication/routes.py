from flask import render_template, redirect, request, url_for, session
from flask_login import (
    current_user,
    login_user,
    logout_user
)
import logging

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm, ForgotPasswordForm, ResetPasswordForm
from apps.authentication.models import Users

from apps.authentication.util import verify_pass

logger = logging.getLogger(__name__)


@blueprint.route('/')
def route_default():
    return redirect(url_for('data_blueprint.prediction'))


# Login & Registration

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    logger.info(f"=== LOGIN ROUTE CALLED === Method: {request.method}")
    
    login_form = LoginForm(request.form)
    if 'login' in request.form:
        # If already logged in from a previous session, log them out first
        if current_user.is_authenticated:
            logger.info(f"User already authenticated: {current_user.username}, logging out first")
            logout_user()
        logger.info("Login form submitted")

        # read form data
        username = request.form['username']
        password = request.form['password']
        
        logger.info(f"Attempting login for username: {username}")

        # Locate user
        user = Users.query.filter_by(username=username).first()
        
        if user:
            logger.info(f"User found: {user.username}, is_admin: {user.is_admin}")
        else:
            logger.warning(f"User not found: {username}")

        # Check the password
        if user and verify_pass(password, user.password):
            logger.info(f"Password verified for user: {username}")
            # Regular users only - admins must use /admin/login
            if not user.is_admin:
                logger.info(f"Calling login_user for: {username}")
                session.permanent = True  # Make session persistent
                login_user(user, remember=True)
                logger.info(f"User logged in: {user.username} (ID: {user.id})")
                logger.info(f"Session after login: {dict(session)}")
                logger.info(f"current_user.is_authenticated: {current_user.is_authenticated}")
                logger.info(f"current_user.id: {current_user.id}")
                db.session.commit()  # Ensure session is saved
                return redirect(url_for('data_blueprint.prediction'))
            else:
                return render_template('accounts/login.html',
                                       msg='Admin users must login at /admin/login',
                                       form=login_form)

        # Something (user or pass) is not ok
        return render_template('accounts/login.html',
                               msg='Wrong user or password',
                               form=login_form)

    return render_template('accounts/login.html', form=login_form)


@blueprint.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # If already authenticated, check if admin
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('home_blueprint.index'))
        else:
            # Non-admin user trying to access admin page - logout and show admin login
            logout_user()
            session.clear()
    
    login_form = LoginForm(request.form)
    if 'login' in request.form:

        # read form data
        username = request.form['username']
        password = request.form['password']

        # Locate user
        user = Users.query.filter_by(username=username).first()

        # Check the password and verify user is admin
        if user and verify_pass(password, user.password):
            if user.is_admin:
                logger.info(f"Admin login attempt: {user.username} (ID: {user.id}), is_admin: {user.is_admin}")
                
                # Clear any existing session first
                session.clear()
                
                # Set session configuration
                session.permanent = True
                
                # Login the user
                login_user(user, remember=True)
                
                # Force session save
                session.modified = True
                
                logger.info(f"Admin logged in: {user.username} (ID: {user.id})")
                logger.info(f"Session after login: {dict(session)}")
                logger.info(f"current_user.is_authenticated: {current_user.is_authenticated}")
                logger.info(f"current_user.is_admin: {current_user.is_admin}")
                logger.info(f"current_user.id: {current_user.id}")
                
                # Commit any database changes
                db.session.commit()
                
                # Add a small delay to ensure session is saved
                import time
                time.sleep(0.1)
                
                return redirect(url_for('home_blueprint.index'))
            else:
                return render_template('accounts/admin-login.html',
                                       msg='Access denied. Admin credentials required.',
                                       form=login_form)

        # Something (user or pass) is not ok
        return render_template('accounts/admin-login.html',
                               msg='Wrong admin credentials',
                               form=login_form)

    return render_template('accounts/admin-login.html',
                           form=login_form)


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    create_account_form = CreateAccountForm(request.form)
    if 'register' in request.form:

        username = request.form['username']
        email = request.form['email']

        # Check usename exists
        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('accounts/register_new.html',
                                   msg='Username already registered',
                                   success=False,
                                   form=create_account_form)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('accounts/register_new.html',
                                   msg='Email already registered',
                                   success=False,
                                   form=create_account_form)

        # else we can create the user
        user = Users(**request.form)
        db.session.add(user)
        db.session.commit()

        # Delete user from session
        logout_user()
        
        return render_template('accounts/register_new.html',
                               msg='Account created successfully.',
                               success=True,
                               form=create_account_form)

    else:
        return render_template('accounts/register_new.html', form=create_account_form)


@blueprint.route('/logout')
def logout():
    logger.info(f"Logging out user: {current_user.username if current_user.is_authenticated else 'anonymous'}")
    logout_user()
    session.clear()  # Clear all session data
    return redirect(url_for('authentication_blueprint.login'))


# Errors

@login_manager.unauthorized_handler
def unauthorized_handler():
    # Redirect to login page instead of showing 403 error
    return redirect(url_for('authentication_blueprint.login'))


@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404


@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500


@blueprint.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    forgot_form = ForgotPasswordForm(request.form)
    
    if 'forgot_password' in request.form:
        email = request.form['email']
        
        # Find user by email
        user = Users.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = user.generate_reset_token()
            
            # In a production environment, you would send an email with the reset link
            # For demo purposes, we'll just show the token (remove this in production)
            reset_url = url_for('authentication_blueprint.reset_password', token=token, _external=True)
            
            return render_template('accounts/forgot_password.html',
                                   msg=f'Password reset link: {reset_url}',
                                   success=True,
                                   form=forgot_form)
        else:
            return render_template('accounts/forgot_password.html',
                                   msg='If an account with that email exists, a password reset link has been sent.',
                                   success=True,
                                   form=forgot_form)
    
    return render_template('accounts/forgot_password.html', form=forgot_form)


@blueprint.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Find user with this token
    user = Users.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        return render_template('accounts/reset_password.html',
                               msg='Invalid or expired reset token',
                               token_valid=False)
    
    reset_form = ResetPasswordForm(request.form)
    
    if 'reset_password' in request.form:
        new_password = request.form['password']
        
        # Reset the password
        user.reset_password(new_password)
        
        return render_template('accounts/reset_password.html',
                               msg='Password has been reset successfully. You can now login with your new password.',
                               success=True,
                               token_valid=True)
    
    return render_template('accounts/reset_password.html', 
                           form=reset_form, 
                           token_valid=True)
