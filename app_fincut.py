from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, date
import logging
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Import models (define them in a separate file ideally)
from models import User, Device, Customer, Service

# Load user
def load_user(user_id):
    return User.query.get(int(user_id))

login_manager.user_loader(load_user)

# --- Routes ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if User.query.first():
        flash("Admin account already exists. Contact admin to register others.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_level = request.form.get('user_level', 'admin')
        user = User(username=username, user_level=user_level)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Admin account created. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_level == 'admin':
        devices = Device.query.all()
        pending = Device.query.filter_by(assign_status='Assigned').count()
        closed = Device.query.filter_by(assign_status='Closed').count()
        return render_template('dashboard.html', devices=devices, pending=pending, closed=closed)
    else:
        staff_devices = Device.query.filter_by(assign_to=current_user.username).all()
        return render_template('staff_dashboard.html', devices=staff_devices)

@app.route('/assign/<int:device_id>', methods=['GET', 'POST'])
@login_required
def assign_device(device_id):
    device = Device.query.get_or_404(device_id)
    if request.method == 'POST':
        issue = request.form['issue']
        expected_delivery = request.form['expected_delivery_date']
        if device.assign_status == 'Unassigned':
            service = Service(
                device_id=device.id,
                assign_date=date.today(),
                assign_to=current_user.username,
                issue=issue,
                expected_delivery_date=datetime.strptime(expected_delivery, '%Y-%m-%d')
            )
            device.assign_status = 'Assigned'
            db.session.add(service)
            db.session.commit()
            flash('Device assigned successfully', 'success')
            return redirect(url_for('dashboard'))
        flash('Device already assigned', 'warning')
    return render_template('device_assign.html', device=device)

@app.route('/ack/<int:device_id>')
@login_required
def ack_ticket(device_id):
    device = Device.query.get_or_404(device_id)
    customer = Customer.query.get_or_404(device.customer_id)
    return render_template('ack_ticket.html', device=device, customer=customer)

@app.route('/listed_device', methods=['POST'])
@login_required
def list_device():
    customer_id = request.form['customer_id']
    customer = Customer.query.filter_by(customer_id=customer_id).first()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    devices = Device.query.filter_by(customer_id=customer.id).all()
    return render_template('device_list.html', customer=customer, devices=devices)

@app.route('/update_status/<int:device_id>', methods=['POST'])
@login_required
def update_status(device_id):
    device = Device.query.get_or_404(device_id)
    if device.assign_status == 'Assigned':
        device.assign_status = 'Delivery Pending'
    elif device.assign_status == 'Delivery Pending':
        device.assign_status = 'Closed'
    db.session.commit()
    flash('Status updated', 'success')
    return redirect(url_for('dashboard'))

@app.route('/bill_today')
@login_required
def bill_today():
    today = date.today()
    services = Service.query.all()
    closed_today = [s for s in services if s.expected_delivery_date.date() == today and s.device.assign_status == 'Closed']
    return render_template('today_closures.html', services=closed_today)

if __name__ == '__main__':
    app.run(debug=True)
