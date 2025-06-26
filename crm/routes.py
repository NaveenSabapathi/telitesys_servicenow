
from flask import render_template, request, redirect, url_for, flash
from . import crm_bp
from .models import Lead, FollowUp
# from app import db
from datetime import datetime
from crm.models import Lead, FollowUp  # Only import models
from models import db  # ✅ Use shared instance


@crm_bp.route("/crm/leads")
def list_leads():
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return render_template("crm/leads.html", leads=leads)

@crm_bp.route("/crm/add", methods=["GET", "POST"])
def add_lead():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        source = request.form.get("source")
        lead = Lead(name=name, phone=phone, source=source)
        db.session.add(lead)
        db.session.commit()
        flash("Lead added successfully")
        return redirect(url_for("crm.list_leads"))
    return render_template("crm/add_lead.html")

@crm_bp.route("/crm/<int:lead_id>/followup", methods=["GET", "POST"])
def follow_up(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if request.method == "POST":
        note = request.form["note"]
        followup_date = request.form["followup_date"]
        followup = FollowUp(note=note, followup_date=followup_date, lead_id=lead.id)
        db.session.add(followup)
        db.session.commit()
        flash("Follow-up saved.")
        return redirect(url_for("crm.list_leads"))
    return render_template("crm/followup.html", lead=lead)