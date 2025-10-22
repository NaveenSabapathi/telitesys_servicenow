# inventory/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField, DateField, DateTimeField, FieldList, FormField
from wtforms.validators import DataRequired, Optional

class SerialLineForm(FlaskForm):
    item_id = IntegerField('Item ID', validators=[DataRequired()])
    serial_number = StringField('Serial Number', validators=[DataRequired()])
    billed_to = StringField('Billed To', validators=[Optional()])

class GoodsInForm(FlaskForm):
    ref_no = StringField('Ref No', validators=[Optional()])
    vendor = StringField('Vendor', validators=[Optional()])
    arrived_date = DateTimeField('Arrived Date', format='%Y-%m-%d %H:%M', validators=[Optional()])
    lines = FieldList(FormField(SerialLineForm), min_entries=1)

class GoodsOutForm(FlaskForm):
    ref_no = StringField('Ref No', validators=[Optional()])
    to_customer = StringField('To Customer', validators=[Optional()])
    sent_via = SelectField('Sent Via', choices=[('bus','Bus'),('parcel','Parcel'),('courier','Courier')], validators=[Optional()])
    parcel_details = TextAreaField('Parcel Details', validators=[Optional()])
    sent_date = DateTimeField('Sent Date', format='%Y-%m-%d %H:%M', validators=[Optional()])
    lines = FieldList(FormField(SerialLineForm), min_entries=1)
