from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, Float

db = SQLAlchemy()

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)  # New phone number field
    user_level = db.Column(db.String(128), default="admin")


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_type = db.Column(db.String(100), nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100), nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    device_status = db.Column(db.String(100), nullable=False)
    remark = db.Column(db.Text)
    service_id = db.Column(db.Integer, unique=True, nullable=False)
    added_by = db.Column(db.String(80))

    # New fields for date and budget
    received_date = db.Column(DateTime, nullable=False)
    expected_delivery_date = db.Column(DateTime, nullable=False)
    expected_budget = db.Column(Float, nullable=False)

    # Define the foreign key relationship with Customer
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)

    def __repr__(self):
        return f"Device('{self.device_name}', '{self.model}', '{self.serial_number}')"

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    whatsapp_number = db.Column(db.String(20), unique=True, nullable=False)
    device_count = db.Column(db.Integer, default=0)
    bill_value = db.Column(db.Float, default=0.0)

    # Define a relationship between Customer and Device
    devices = db.relationship('Device', backref='customer', lazy=True)

    def __repr__(self):
        return f"Customer('{self.name}', '{self.location}', '{self.whatsapp_number}')"
#
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False)
#     # Replace with secure password hashing logic
#     password = db.Column(db.String(128), nullable=False)
#     user_level = db.Column(db.String(128), default="admin")
#
#     def __repr__(self):
#         return f'<User {self.username}>'
