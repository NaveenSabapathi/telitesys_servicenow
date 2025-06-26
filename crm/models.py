# crm/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from models import db
# db = SQLAlchemy()

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    source = db.Column(db.String(50))
    status = db.Column(db.String(20), default="new")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FollowUp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'))
    note = db.Column(db.Text)
    followup_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, default=False)

    lead = db.relationship('Lead', backref='followups')

