from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional


class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    accept_terms = BooleanField('I accept the Terms and Risk Disclosure', validators=[DataRequired()])
    submit = SubmitField('Create Account')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class DepositForm(FlaskForm):
    asset = SelectField('Asset', choices=[('USDT', 'USDT'), ('BTC', 'BTC'), ('ETH', 'ETH')], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=1)])
    network = SelectField('Network', choices=[('TRC20', 'TRC20'), ('ERC20', 'ERC20'), ('BEP20', 'BEP20')], validators=[DataRequired()])
    reference = StringField('Transaction Reference', validators=[Optional(), Length(max=120)])
    submit = SubmitField('Submit Deposit Request')


class WithdrawalForm(FlaskForm):
    asset = SelectField('Asset', choices=[('USDT', 'USDT'), ('BTC', 'BTC'), ('ETH', 'ETH')], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=1)])
    network = SelectField('Network', choices=[('TRC20', 'TRC20'), ('ERC20', 'ERC20'), ('BEP20', 'BEP20')], validators=[DataRequired()])
    wallet_address = StringField('Wallet Address', validators=[DataRequired(), Length(min=8, max=255)])
    submit = SubmitField('Request Withdrawal')


class InvestmentForm(FlaskForm):
    amount = FloatField('Investment Amount', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Start Investment')


class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    submit = SubmitField('Save Changes')


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Update Password')


class SupportForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired(), Length(min=3, max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Open Ticket')


class PlanForm(FlaskForm):
    name = StringField('Plan Name', validators=[DataRequired(), Length(min=2, max=120)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10)])
    min_amount = FloatField('Minimum Amount', validators=[DataRequired(), NumberRange(min=1)])
    duration_days = FloatField('Duration (Days)', validators=[DataRequired(), NumberRange(min=1)])
    target_return_percent = FloatField('Projected Return %', validators=[DataRequired(), NumberRange(min=0)])
    risk_level = SelectField('Risk Level', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], validators=[DataRequired()])
    submit = SubmitField('Save Plan')
