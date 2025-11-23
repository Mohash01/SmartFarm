from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import Email, DataRequired, EqualTo, Length

# login and registration


class LoginForm(FlaskForm):
    username = StringField('Username',
                         id='username_login',
                         validators=[DataRequired()])
    password = PasswordField('Password',
                             id='pwd_login',
                             validators=[DataRequired()])


class CreateAccountForm(FlaskForm):
    username = StringField('Username',
                         id='username_create',
                         validators=[DataRequired()])
    email = StringField('Email',
                      id='email_create',
                      validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             id='pwd_create',
                             validators=[DataRequired()])


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email',
                       id='email_forgot',
                       validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password',
                             id='pwd_reset',
                             validators=[DataRequired(), Length(min=6)])
    password_confirm = PasswordField('Confirm Password',
                                   id='pwd_confirm',
                                   validators=[DataRequired(), EqualTo('password')])
