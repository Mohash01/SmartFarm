from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from apps.authentication.models import Users
from apps.user.forms import UserForm, EditUserForm
from apps import db, csrf
from apps.authentication.util import hash_pass
from sqlalchemy.exc import IntegrityError

blueprint = Blueprint('user_blueprint', __name__, url_prefix='/admin/users')

@blueprint.route('/')
@login_required
def users():
    # Only admins can access user management
    if not current_user.is_admin:
        return redirect(url_for('data_blueprint.prediction'))
    
    # Get search and pagination parameters
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Build query with search
    query = Users.query
    if search:
        query = query.filter(
            (Users.username.ilike(f'%{search}%')) |
            (Users.email.ilike(f'%{search}%'))
        )
    
    # Paginate results
    users_pagination = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template(
        'users/view_users.html',
        users=users_pagination.items,
        pagination=users_pagination,
        search=search,
        segment='users'
    )

@blueprint.route('/create', methods=['GET', 'POST'])
@login_required
def create_user():
    # Only admins can create users
    if not current_user.is_admin:
        return redirect(url_for('data_blueprint.prediction'))
    
    form = UserForm()
    if form.validate_on_submit():
        try:
            user = Users(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,  # Will be hashed in model __init__
                is_admin=form.is_admin.data
            )
            db.session.add(user)
            db.session.commit()
            flash(f'User {user.username} created successfully!', 'success')
            return redirect(url_for('user_blueprint.users'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
    
    return render_template(
        'users/create_user.html',
        form=form,
        segment='users'
    )

@blueprint.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    # Only admins can edit users
    if not current_user.is_admin:
        return redirect(url_for('data_blueprint.prediction'))
    
    user = Users.query.get_or_404(user_id)
    form = EditUserForm(obj=user)
    
    if form.validate_on_submit():
        try:
            # Prevent admins from removing their own admin status
            if user.id == current_user.id and not form.is_admin.data:
                flash('You cannot remove your own admin privileges!', 'error')
                return render_template('users/edit_user.html', form=form, user=user, segment='users')
            
            user.username = form.username.data
            user.email = form.email.data
            user.is_admin = form.is_admin.data
            
            # Only update password if provided
            if form.password.data:
                user.password = hash_pass(form.password.data)
            
            db.session.commit()
            flash(f'User {user.username} updated successfully!', 'success')
            return redirect(url_for('user_blueprint.users'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template(
        'users/edit_user.html',
        form=form,
        user=user,
        segment='users'
    )

@blueprint.route('/<int:user_id>/delete', methods=['POST'])
@login_required
@csrf.exempt
def delete_user(user_id):
    # Only admins can delete users
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    user = Users.query.get_or_404(user_id)
    
    # Prevent admins from deleting themselves
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'You cannot delete your own account!'}), 400
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': f'User {username} deleted successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting user: {str(e)}'}), 500

@blueprint.route('/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@csrf.exempt
def toggle_admin(user_id):
    # Only admins can toggle admin status
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    user = Users.query.get_or_404(user_id)
    
    # Prevent admins from removing their own admin status
    if user.id == current_user.id and user.is_admin:
        return jsonify({'success': False, 'message': 'You cannot remove your own admin privileges!'}), 400
    
    try:
        user.is_admin = not user.is_admin
        db.session.commit()
        status = 'Admin' if user.is_admin else 'User'
        return jsonify({'success': True, 'message': f'{user.username} is now a {status}', 'is_admin': user.is_admin})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating user: {str(e)}'}), 500