from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, Float
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import enum
from sqlalchemy import JSON

db = SQLAlchemy()

class AssignStatus(enum.Enum):
    UNASSIGNED = 'unassigned'
    ASSIGNED = 'assigned'
    SERVICED = 'serviced'
    UNDELIVERED = 'undelivered'
    DELIVERED = 'delivered'
# ------------------------------
# User Model
# ------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)  # Increased size for secure hashes
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    user_level = db.Column(db.String(128), default="admin")

    # Devices added by this user
    devices_added = db.relationship('Device', backref='added_by_user', lazy=True, foreign_keys='Device.added_by')

    # Devices assigned to this user
    assigned_devices = db.relationship('Device', backref='assigned_user', lazy=True, foreign_keys='Device.assigned_to')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# ------------------------------
# Customer Model
# ------------------------------
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    whatsapp_number = db.Column(db.String(20), unique=True, nullable=False)
    device_count = db.Column(db.Integer, default=0)
    bill_value = db.Column(db.Float, default=0.0)


    # Relationship to Device
    devices = db.relationship('Device', backref='customer', lazy=True)

    def __repr__(self):
        return f"Customer('{self.name}', '{self.location}', '{self.whatsapp_number}')"

# models.py
class BillStatus(enum.Enum):
    UNPAID = 'unpaid'
    PARTIAL = 'partial'
    PAID = 'paid'

# ------------------------------
# Device Model
# ------------------------------
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.String(50), unique=True, nullable=False)
    device_type = db.Column(db.String(100), nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100), nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    device_status = db.Column(db.String(100), nullable=False)
    # --- UPDATED FIELD ---
    assign_status = db.Column(
        db.Enum(AssignStatus),
        default=AssignStatus.UNASSIGNED,
        nullable=False
    )
    remark = db.Column(db.Text)
    service_id = db.Column(db.String, unique=True, nullable=False)
    image_filename = db.Column(db.String(255))  # NEW

    total_cost = db.Column(db.Float, default=0.0)
    # Foreign keys
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))  # Refers to assigned technician
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Refers to creator
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)

    # Billing and time
    bill_value = db.Column(db.Float, default=0.0)
    # models.py
    amount_received = db.Column(db.Float, default=0.0)

    bill_status = db.Column(db.Enum(BillStatus), default=BillStatus.UNPAID, nullable=False)
    received_date = db.Column(DateTime, nullable=False)
    expected_delivery_date = db.Column(DateTime, nullable=False)
    delivery_date = db.Column(DateTime, nullable=True)
#added delivery date
    expected_budget = db.Column(Float, nullable=False)

    # Relationships
    services = db.relationship('Service', backref='device', lazy=True)

    def __repr__(self):
        return f"Device('{self.device_name}', '{self.model}', '{self.serial_number}')"


# ------------------------------
# Service Model
# ------------------------------
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)

    # Relationship to spare parts
    spare_parts = db.relationship('SparePart', backref='service', lazy=True)

    def __repr__(self):
        return f"<Service DeviceID={self.device_id}>"


#--------------------------
#HISTORY DATA
#_----------------------


class DeviceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    device_id = db.Column(db.Integer, nullable=False)
    service_id = db.Column(db.Integer, nullable=False)

    # Snapshots
    device_snapshot = db.Column(JSON, nullable=False)
    customer_snapshot = db.Column(JSON, nullable=False)
    assigned_user_snapshot = db.Column(JSON)
    spare_parts_snapshot = db.Column(JSON)

    # Financials
    total_cost = db.Column(db.Float, nullable=False)
    bill_value = db.Column(db.Float)
    expected_budget = db.Column(db.Float)

    delivered_at = db.Column(DateTime, nullable=False)
    created_at = db.Column(DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<DeviceHistory device_id={self.device_id} delivered_at={self.delivered_at}>"

# ------------------------------
# SparePart Model
# ------------------------------
class SparePart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spare_name = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Integer, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)

    def __repr__(self):
        return f"SparePart('{self.spare_name}', Cost: {self.cost})"

class DeviceUpdateLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    device_id = db.Column(db.Integer, nullable=False, index=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # What changed
    old_description = db.Column(db.Text)
    new_description = db.Column(db.Text)

    old_expected_delivery_date = db.Column(DateTime)
    new_expected_delivery_date = db.Column(DateTime)

    old_assigned_to = db.Column(db.Integer)
    new_assigned_to = db.Column(db.Integer)

    update_reason = db.Column(db.Text)  # 🔑 IMPORTANT

    updated_at = db.Column(DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<DeviceUpdateLog device={self.device_id} at={self.updated_at}>"