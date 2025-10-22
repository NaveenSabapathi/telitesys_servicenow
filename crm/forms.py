# crm/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, TextAreaField, DateTimeField
from wtforms.validators import DataRequired, Optional

class LeadForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional()])
    company = StringField('Company', validators=[Optional()])
    source = SelectField('Source', choices=[('Website','Website'),('Justdial','Justdial'),('Walk-in','Walk-in'),('Referral','Referral'),('Other','Other')], validators=[Optional()])
    priority = SelectField('Priority', choices=[('High','High'),('Medium','Medium'),('Low','Low')], default='Medium')
    estimated_value = DecimalField('Estimated Value', places=2, validators=[Optional()])
    next_follow_up = DateTimeField('Next Follow Up', format='%Y-%m-%d %H:%M', validators=[Optional()])
    note = TextAreaField('Initial Note', validators=[Optional()])

class LeadNoteForm(FlaskForm):
    note = TextAreaField('Note', validators=[DataRequired()])

class FollowUpForm(FlaskForm):
    note = TextAreaField('Note', validators=[Optional()])
    followup_date = DateTimeField('Follow Up Date', format='%Y-%m-%d %H:%M', validators=[Optional()])
