from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, validators
from wtforms.validators import Email, DataRequired, Length, Optional, EqualTo
from apps.authentication.models import Users

class UserForm(FlaskForm):
    username = StringField('Username', [
        DataRequired(),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    email = StringField('Email', [
        DataRequired(),
        Email(message='Please enter a valid email address'),
        Length(max=64)
    ])
    password = PasswordField('Password', [
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', [
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    is_admin = BooleanField('Admin User', default=False)
    
    def validate_username(self, username):
        user = Users.query.filter_by(username=username.data).first()
        if user:
            raise validators.ValidationError('Username already exists. Choose a different one.')
    
    def validate_email(self, email):
        user = Users.query.filter_by(email=email.data).first()
        if user:
            raise validators.ValidationError('Email already registered. Choose a different one.')

class EditUserForm(FlaskForm):
    username = StringField('Username', [
        DataRequired(),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    email = StringField('Email', [
        DataRequired(),
        Email(message='Please enter a valid email address'),
        Length(max=64)
    ])
    password = PasswordField('New Password (leave blank to keep current)', [
        Optional(),
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', [
        EqualTo('password', message='Passwords must match')
    ])
    is_admin = BooleanField('Admin User', default=False)
    
    def __init__(self, *args, **kwargs):
        self.original_user = kwargs.pop('original_user', None)
        super(EditUserForm, self).__init__(*args, **kwargs)
    
    def validate_username(self, username):
        if self.original_user and username.data == self.original_user.username:
            return
        user = Users.query.filter_by(username=username.data).first()
        if user:
            raise validators.ValidationError('Username already exists. Choose a different one.')
    
    def validate_email(self, email):
        if self.original_user and email.data == self.original_user.email:
            return
        user = Users.query.filter_by(email=email.data).first()
        if user:
            raise validators.ValidationError('Email already registered. Choose a different one.')