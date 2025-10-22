# crm/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from models import db, User, Customer, Device  # reuse your central models
from .models import Lead, LeadNote, LeadTimeline, FollowUp
from .forms import LeadForm, LeadNoteForm, FollowUpForm

crm_bp = Blueprint('crm', __name__, template_folder='templates/crm')

# Dashboard
@crm_bp.route('/crm')
@crm_bp.route('/crm/dashboard')
@login_required
def crm_dashboard():
    total = Lead.query.count()
    new = Lead.query.filter_by(status='New').count()
    converted = Lead.query.filter_by(status='Converted').count()
    overdue = Lead.query.filter(Lead.next_follow_up != None,
                                Lead.next_follow_up < datetime.utcnow(),
                                Lead.status != 'Converted').count()
    sources = db.session.query(Lead.source, db.func.count(Lead.id)).group_by(Lead.source).all()
    return render_template('crm/dashboard.html', total=total, new=new, converted=converted, overdue=overdue, sources=sources)

# List leads with filters
@crm_bp.route('/crm/leads')
@login_required
def list_leads():
    status = request.args.get('status')
    assigned = request.args.get('assigned')
    search = request.args.get('q')
    query = Lead.query

    if status:
        query = query.filter_by(status=status)
    if assigned == 'me':
        query = query.filter_by(assigned_to=current_user.id)
    if search:
        like = f"%{search}%"
        query = query.filter((Lead.name.ilike(like)) | (Lead.phone.ilike(like)) | (Lead.company.ilike(like)))

    leads = query.order_by(Lead.created_at.desc()).all()
    users = User.query.all()
    return render_template('crm/list_leads.html', leads=leads, users=users)

# Add lead
@crm_bp.route('/crm/leads/add', methods=['GET', 'POST'])
@login_required
def add_lead():
    form = LeadForm()
    if form.validate_on_submit():
        lead = Lead(
            name=form.name.data,
            phone=form.phone.data.strip(),
            email=form.email.data,
            company=form.company.data,
            source=form.source.data,
            priority=form.priority.data,
            estimated_value=float(form.estimated_value.data or 0),
            next_follow_up=form.next_follow_up.data
        )
        db.session.add(lead)
        db.session.commit()
        # initial note and timeline
        if form.note.data:
            note = LeadNote(lead_id=lead.id, user_id=current_user.id, note=form.note.data)
            db.session.add(note)
            tl = LeadTimeline(lead_id=lead.id, event_type='note', meta={'text': form.note.data}, created_by=current_user.id)
            db.session.add(tl)
            db.session.commit()
        flash('Lead added', 'success')
        return redirect(url_for('crm.list_leads'))
    return render_template('crm/add_lead.html', form=form)

# View lead detail
@crm_bp.route('/crm/leads/<int:lead_id>')
@login_required
def view_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    note_form = LeadNoteForm()
    followup_form = FollowUpForm()
    timeline = LeadTimeline.query.filter_by(lead_id=lead.id).order_by(LeadTimeline.created_at.desc()).all()
    notes = LeadNote.query.filter_by(lead_id=lead.id).order_by(LeadNote.created_at.desc()).all()
    followups = FollowUp.query.filter_by(lead_id=lead.id).order_by(FollowUp.followup_date.asc()).all()
    users = User.query.all()
    return render_template('crm/lead_view.html', lead=lead, notes=notes, timeline=timeline, note_form=note_form, users=users, followups=followups, followup_form=followup_form)

# Add note
@crm_bp.route('/crm/leads/<int:lead_id>/note', methods=['POST'])
@login_required
def add_note(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    note_text = request.form.get('note')
    if not note_text:
        flash('Note is required', 'error')
        return redirect(url_for('crm.view_lead', lead_id=lead.id))
    note = LeadNote(lead_id=lead.id, user_id=current_user.id, note=note_text)
    db.session.add(note)
    tl = LeadTimeline(lead_id=lead.id, event_type='note', meta={'text': note_text}, created_by=current_user.id)
    db.session.add(tl)
    db.session.commit()
    flash('Note added', 'success')
    return redirect(url_for('crm.view_lead', lead_id=lead.id))

# Add follow-up
@crm_bp.route('/crm/leads/<int:lead_id>/followup', methods=['POST', 'GET'])
@login_required
def add_followup(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if request.method == 'POST':
        note = request.form.get('note')
        followup_date_raw = request.form.get('followup_date')
        followup_date = None
        if followup_date_raw:
            try:
                followup_date = datetime.strptime(followup_date_raw, '%Y-%m-%d %H:%M')
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD HH:MM', 'error')
                return redirect(url_for('crm.view_lead', lead_id=lead.id))
        fu = FollowUp(lead_id=lead.id, note=note, followup_date=followup_date)
        db.session.add(fu)
        # update lead.next_follow_up if provided
        if followup_date:
            lead.next_follow_up = followup_date
            db.session.add(lead)
        tl = LeadTimeline(lead_id=lead.id, event_type='followup_scheduled', meta={'followup_date': str(followup_date)}, created_by=current_user.id)
        db.session.add(tl)
        db.session.commit()
        flash('Follow-up scheduled', 'success')
        return redirect(url_for('crm.view_lead', lead_id=lead.id))
    # GET: show follow-up form
    return render_template('crm/followup.html', lead=lead)

# Update status
@crm_bp.route('/crm/leads/<int:lead_id>/status', methods=['POST'])
@login_required
def update_status(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    new_status = request.form.get('status')
    if not new_status:
        flash('Status is required', 'error')
        return redirect(url_for('crm.view_lead', lead_id=lead.id))
    old = lead.status
    lead.status = new_status
    if new_status == 'Converted':
        lead.closed_at = datetime.utcnow()
    db.session.add(lead)
    tl = LeadTimeline(lead_id=lead.id, event_type='status_change', meta={'from': old, 'to': new_status}, created_by=current_user.id)
    db.session.add(tl)
    db.session.commit()
    flash('Status updated', 'success')
    return redirect(url_for('crm.view_lead', lead_id=lead.id))

# Assign lead
@crm_bp.route('/crm/leads/<int:lead_id>/assign', methods=['POST'])
@login_required
def assign_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    user_id = request.form.get('user_id')
    if not user_id:
        flash('User required', 'error')
        return redirect(url_for('crm.view_lead', lead_id=lead.id))
    old = lead.assigned_to
    lead.assigned_to = int(user_id)
    db.session.add(lead)
    tl = LeadTimeline(lead_id=lead.id, event_type='assigned', meta={'from': old, 'to': user_id}, created_by=current_user.id)
    db.session.add(tl)
    db.session.commit()
    flash('Lead assigned', 'success')
    # TODO: notify the assigned user (WhatsApp/email)
    return redirect(url_for('crm.view_lead', lead_id=lead.id))

# Convert lead to customer
@crm_bp.route('/crm/leads/<int:lead_id>/convert', methods=['POST'])
@login_required
def convert_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    existing = Customer.query.filter_by(whatsapp_number=lead.phone).first()
    if existing:
        customer = existing
    else:
        customer = Customer(name=lead.name, location=lead.company or '', whatsapp_number=lead.phone)
        db.session.add(customer)
        db.session.commit()
    lead.status = 'Converted'
    lead.closed_at = datetime.utcnow()
    db.session.add(lead)
    tl = LeadTimeline(lead_id=lead.id, event_type='converted', meta={'customer_id': customer.id}, created_by=current_user.id)
    db.session.add(tl)
    db.session.commit()
    flash('Lead converted to customer', 'success')
    return redirect(url_for('crm.view_lead', lead_id=lead.id))

# Metrics API
@crm_bp.route('/crm/metrics')
@login_required
def crm_metrics():
    by_status = db.session.query(Lead.status, db.func.count(Lead.id)).group_by(Lead.status).all()
    by_source = db.session.query(Lead.source, db.func.count(Lead.id)).group_by(Lead.source).all()
    return jsonify({'by_status': dict(by_status), 'by_source': dict(by_source)})
