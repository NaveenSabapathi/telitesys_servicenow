# crm/models.py
from datetime import datetime
from sqlalchemy import JSON
from models import db  # use shared db instance from your project

class Lead(db.Model):
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(40), nullable=False, index=True)
    email = db.Column(db.String(120))
    company = db.Column(db.String(150))
    source = db.Column(db.String(80))
    status = db.Column(db.String(50), default='New')          # New / Contacted / Quoted / Negotiation / Converted / Lost
    priority = db.Column(db.String(20), default='Medium')     # High / Medium / Low
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    estimated_value = db.Column(db.Float, default=0.0)
    next_follow_up = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    notes = db.relationship('LeadNote', backref='lead', lazy=True, cascade='all, delete-orphan')
    timeline = db.relationship('LeadTimeline', backref='lead', lazy=True, cascade='all, delete-orphan')
    followups = db.relationship('FollowUp', backref='lead', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Lead {self.name} ({self.phone})>"

class LeadNote(db.Model):
    __tablename__ = 'lead_note'
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', foreign_keys=[user_id])

class LeadTimeline(db.Model):
    __tablename__ = 'lead_timeline'
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    event_type = db.Column(db.String(50))   # note, status_change, assigned, message_sent, converted
    meta = db.Column(JSON, nullable=True)   # e.g., {"from":"New","to":"Contacted"}
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by])

class FollowUp(db.Model):
    __tablename__ = 'followup'
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'))
    note = db.Column(db.Text)
    followup_date = db.Column(db.DateTime)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
