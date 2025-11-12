# app_cusdata.py (patched)
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from models import User, db, Device, Customer, SparePart, Service
from flask_wtf.csrf import CSRFProtect, validate_csrf, CSRFError, generate_csrf
from flask_migrate import Migrate
import matplotlib, os
matplotlib.use('agg')
from datetime import datetime, date
from sqlalchemy import or_, and_, cast, Date as saDate
from werkzeug.utils import secure_filename
from crm.routes import crm_bp
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register blueprints (keep CRM/inventory registration if present)
try:
    app.register_blueprint(crm_bp, url_prefix="/crm")
except Exception:
    # if blueprint not present during tests, ignore
    pass

# If you have inventory blueprint, register similarly (commented out in some copies)
# from inventory.routes import inventory_bp
# app.register_blueprint(inventory_bp, url_prefix='/inventory')

db.init_app(app)
migrate = Migrate(app, db)

# defensive blueprint registration - put near other blueprint registration code
import traceback
import logging

# ensure app.logger configured
if not app.logger.handlers:
    logging.basicConfig(level=logging.DEBUG)

# Attempt to register inventory blueprint defensively
try:
    from inventory.routes import inventory_bp
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.logger.info("inventory_bp registered successfully")
except Exception as e:
    app.logger.error("Failed to import/register inventory_bp: %s", e)
    app.logger.error(traceback.format_exc())

# dev-only endpoint to list all registered endpoints (only enable in DEBUG)
@app.route('/__debug_endpoints')
def _debug_endpoints():
    if not app.debug:
        return "Disabled", 403
    out = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        out.append(f"{rule.endpoint:40} -> {rule.rule}")
    return "<pre>" + "\n".join(out) + "</pre>"



@app.context_processor
def inject_csrf_token():
    # expose function so templates can call {{ csrf_token() }}
    return dict(csrf_token=generate_csrf)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            csrf_token = request.form.get('csrf_token')
            validate_csrf(csrf_token)
        except CSRFError:
            flash("CSRF token is missing or invalid.", "error")
            return redirect(url_for('login'))

        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    # Allow first user to be created as admin, otherwise only admins can create users
    if User.query.first() is None:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            phone_number = request.form['phone_number']
            user_level = 'admin'  # First user becomes admin

            if User.query.filter_by(phone_number=phone_number).first():
                flash('Phone number already registered', 'error')
                return redirect(url_for('register'))

            user = User(username=username, phone_number=phone_number, user_level=user_level)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Admin account created. Please login.', 'success')
            return redirect(url_for('login'))

        flash('No users found. Please create an admin account.')
        return render_template('register.html')

    # Only admin can create additional users
    if not current_user.is_authenticated or current_user.user_level != 'admin':
        flash('Only admins can register new users.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        phone_number = request.form['phone_number']
        user_level = request.form['user_level']

        if User.query.filter_by(phone_number=phone_number).first():
            flash('Phone number already registered', 'error')
            return redirect(url_for('register'))

        user = User(username=username, phone_number=phone_number, user_level=user_level)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('User registered successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/add_spare_part', methods=['POST'])
@login_required
def add_spare_part():
    data = request.json or {}
    name = data.get('name')
    cost = data.get('cost')
    service_id = data.get('service_id')

    if not name or cost is None or service_id is None:
        return jsonify({'message': 'Missing name, cost or service_id'}), 400

    try:
        new_spare_part = SparePart(spare_name=name, cost=int(cost), service_id=int(service_id))
        db.session.add(new_spare_part)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to add spare part', 'error': str(e)}), 500

    return jsonify({'message': 'Spare part added successfully'})


# --- helper funcs for dates ---
def safe_to_date(val):
    """Return a date object whether val is a date or datetime, or None."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    # unknown type (string?), try parse
    try:
        return datetime.strptime(str(val), '%Y-%m-%d').date()
    except Exception:
        return None


@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().date()

    if current_user.user_level == 'admin':
        # NOTE: cast DB datetime to date for proper comparison
        assigned_devices_count = Device.query.filter_by(assign_status='Assigned').count()
        available_devices = Device.query.filter_by(assign_status='Assigned').all()
        unassigned_devices_count = Device.query.filter_by(assign_status='Unassigned').count()
        unbilled_devices_count = Device.query.filter_by(assign_status='Delivery Pending').count()
        delivery_ready_devices = Device.query.filter_by(assign_status='Closed').count()

        # pending delivery: expected_delivery_date (date part) < today and not Delivered
        pending_delivery_count = Device.query.filter(
            and_(
                cast(Device.expected_delivery_date, saDate) < today,
                Device.device_status != 'Delivered'
            )
        ).count()

        pending_bill_amount = bill_today()

        closed_device_history = Device.query.filter_by(assign_status='Delivered').count()

        return render_template(
            'dashboard.html',
            assigned_devices_count=assigned_devices_count,
            available_devices=available_devices,
            pending_delivery_count=pending_delivery_count,
            unbilled_devices_count=unbilled_devices_count,
            unassigned_devices_count=unassigned_devices_count,
            delivery_ready_devices=delivery_ready_devices,
            bill_today=pending_bill_amount,
            closed_device_history=closed_device_history
        )
    else:
        assigned_devices_count = Device.query.filter_by(assigned_to=current_user.id).count()
        available_devices = Device.query.filter_by(assign_status='Assigned').all()
        unassigned_devices_count = 0
        unbilled_devices_count = 0
        delivery_ready_devices = Device.query.filter_by(assign_status='Closed').count()

        pending_delivery_count = Device.query.filter(cast(Device.expected_delivery_date, saDate) < today).count()

        pending_bill_amount = 0

        return render_template(
            'dashboard.html',
            assigned_devices_count=assigned_devices_count,
            available_devices=available_devices,
            pending_delivery_count=pending_delivery_count,
            unbilled_devices_count=unbilled_devices_count,
            unassigned_devices_count=unassigned_devices_count,
            delivery_ready_devices=delivery_ready_devices,
            bill_today=pending_bill_amount
        )


@app.route('/print_bill/<int:device_id>')
@login_required
def print_bill(device_id):
    device = Device.query.get_or_404(device_id)
    customer = Customer.query.get(device.customer_id)
    if not customer:
        return "Customer not found", 404
    return render_template('print_bill.html', device=device, customer=customer)


def bill_today():
    today = datetime.now().date()
    # Use assign_status 'Delivered' to get completed devices
    service_done = Device.query.filter_by(assign_status='Delivered').all()
    bill_amount = 0.0
    for service in service_done:
        proc_date = safe_to_date(service.expected_delivery_date)
        if proc_date == today:
            bill_amount += float(service.bill_value or 0)
    return bill_amount


@app.route('/section/<section_name>')
def section(section_name):
    return render_template('dashboard.html')


@app.route('/listed_device', methods=['GET', 'POST'])
@login_required
def list_device():
    # Support both GET (from search form) and POST
    q = request.values.get('q') or request.values.get('device_id') or request.form.get('device_id')
    devices = []
    c_name = ''
    if not q:
        return jsonify(error='No search query provided'), 400

    # Try finding a customer by whatsapp number first
    customer = Customer.query.filter_by(whatsapp_number=q).first()
    if customer:
        devices_list = Device.query.filter_by(customer_id=customer.id).all()
        c_name = customer.name
        for device in devices_list:
            devices.append({'device_name': device.device_name, 'customer_name': c_name, 'id': device.id})
        return render_template('list_devices.html', devices=devices, c_name=c_name)

    # If no customer, attempt to find device by service_id or serial_number or device_name
    try:
        # try numeric service id
        possible_id = int(q)
        device = Device.query.filter_by(service_id=possible_id).first()
        if device:
            cust = Customer.query.get(device.customer_id)
            devices.append({'device_name': device.device_name, 'customer_name': cust.name if cust else '', 'id': device.id})
            return render_template('list_devices.html', devices=devices, c_name=cust.name if cust else '')
    except Exception:
        # not numeric or not found — continue
        pass

    # fallback: search serial number or device_name partial match
    devices_query = Device.query.filter(
        or_(
            Device.serial_number.ilike(f"%{q}%"),
            Device.device_name.ilike(f"%{q}%")
        )
    ).all()
    for device in devices_query:
        cust = Customer.query.get(device.customer_id)
        devices.append({'device_name': device.device_name, 'customer_name': cust.name if cust else '', 'id': device.id})

    if not devices:
        return jsonify(error='No results found'), 404

    return render_template('list_devices.html', devices=devices, c_name=c_name)


@app.route('/search_customer/<whatsapp_number>', methods=['GET'])
@login_required
def search_customer(whatsapp_number):
    customer = Customer.query.filter_by(whatsapp_number=whatsapp_number).first()
    if customer:
        customer_details = {
            'name': customer.name,
            'location': customer.location
        }
        return jsonify(customer_details)
    else:
        return jsonify({'error': 'Customer not found'}), 404


@app.route('/add_device', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'POST':
        whatsapp_number = request.form['whatsapp_number']

        # Check if the customer with the given WhatsApp number exists
        customer = Customer.query.filter_by(whatsapp_number=whatsapp_number).first()

        if customer:
            customer_name = customer.name
            location = customer.location
        else:
            customer_name = request.form.get('customer_name', '').strip()
            location = request.form.get('location', '').strip()

            customer = Customer(
                name=customer_name or 'Unknown',
                location=location or '',
                whatsapp_number=whatsapp_number,
                device_count=0,
                bill_value=0
            )
            db.session.add(customer)
            db.session.commit()

        # Extract form data for device
        device_type = request.form.get('device_type')
        device_name = request.form.get('device_name')
        model = request.form.get('model')
        serial_number = request.form.get('serial_number')
        issue_description = request.form.get('issue_description')

        image_file = request.files.get('device_image')
        filename = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

        device_status = request.form.get('device_status')
        remark = request.form.get('remark')

        # Parse dates robustly
        received_date = datetime.strptime(request.form['received_date'], '%Y-%m-%d') if request.form.get('received_date') else datetime.now()
        expected_delivery_date = datetime.strptime(request.form['expected_delivery_date'], '%Y-%m-%d') if request.form.get('expected_delivery_date') else datetime.now()

        expected_budget = float(request.form.get('expected_budget') or 0.0)

        # Generate unique service ID
        last_device = Device.query.order_by(Device.id.desc()).first()
        service_id = (last_device.id + 1) if last_device else 1

        new_device = Device(
            device_type=device_type,
            device_name=device_name,
            model=model,
            serial_number=serial_number,
            issue_description=issue_description,
            image_filename=filename,
            device_status=device_status,
            remark=remark,
            service_id=service_id,
            customer_id=customer.id,
            added_by=current_user.id,
            received_date=received_date,
            expected_delivery_date=expected_delivery_date,
            expected_budget=expected_budget
        )
        db.session.add(new_device)
        db.session.commit()

        flash('Device added successfully!', 'success')
        return redirect(url_for('ack_ticket', device_id=new_device.id))

    return render_template('add_device.html')


@app.route('/ack_ticket/<int:device_id>')
@login_required
def ack_ticket(device_id):
    device = Device.query.get_or_404(device_id)
    customer = Customer.query.get_or_404(device.customer_id)
    return render_template('ack_ticket.html', device=device, customer=customer)


# @app.route('/device_time_overlap', methods=['GET'])
# @login_required
# def device_time_overlap():
#     if current_user.user_level != "admin":
#         return redirect(url_for('dashboard'))
#
#     today = datetime.now().date()
#     pending_devices = Device.query.filter(
#         and_(
#             cast(Device.expected_delivery_date, saDate) < today,
#             Device.device_status != 'Delivered'
#         )
#     ).all()
#
#     if not pending_devices:
#         return redirect(url_for('dashboard'))
#
#     # build device -> customer mapping
#     device_customer_info = {device.id: Customer.query.get(device.customer_id) for device in pending_devices}
#     # also build assigned_to map (user id -> user object lookup not necessary, template can show device.assigned_to as id)
#     # Pass the pending_devices and the device_customer_info mapping to the template
#     users = User.query.all()
#
#     return render_template(
#         'device_overlap.html',
#         pending_devices=pending_devices,
#         available_users=users,
#         device_customer_info=device_customer_info
#     )

@app.route('/device_time_overlap', methods=['GET'])
@login_required
def device_time_overlap():
    if current_user.user_level != "admin":
        return redirect(url_for('dashboard'))

    today = datetime.now().date()

    # Exclude devices already delivered/closed and ensure we compare only date part
    excluded_assign_status = ['Delivered', 'Closed']
    pending_devices = Device.query.filter(
        and_(
            cast(Device.expected_delivery_date, saDate) < today,
            ~Device.assign_status.in_(excluded_assign_status),
            Device.device_status != 'Delivered'
        )
    ).distinct(Device.id).all()

    if not pending_devices:
        return redirect(url_for('dashboard'))

    # build device -> customer mapping (one lookup per unique customer)
    customer_ids = {d.customer_id for d in pending_devices}
    customers = {c.id: c for c in Customer.query.filter(Customer.id.in_(customer_ids)).all()}

    # prepare assigned users lookup
    user_ids = {d.assigned_to for d in pending_devices if d.assigned_to}
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

    return render_template(
        'device_overlap.html',
        pending_devices=pending_devices,
        available_users=list(users.values()) or User.query.all(),
        device_customer_info=customers,
        assigned_users_map=users
    )


@app.route('/update_device_info', methods=['POST'])
@login_required
def update_device_info():
    device_id = request.form.get('device_id')
    description = request.form.get('description')
    new_date = request.form.get('new_expected_date')
    assigned_to = request.form.get('assigned_to')
    remarks = request.form.get('remarks', '')

    if not device_id:
        return jsonify({'success': False, 'message': 'device_id missing'}), 400

    device = Device.query.get(device_id)
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    # Update textual fields
    device.remark = remarks
    device.description = description if description is not None else getattr(device, 'description', '')

    # Parse and set new expected date (only if provided)
    if new_date:
        try:
            device.expected_delivery_date = datetime.strptime(new_date, '%Y-%m-%d')
        except Exception:
            return jsonify({'success': False, 'message': 'Invalid date format'}), 400

    # Resolve assigned_to (accepts numeric id or username)
    if assigned_to:
        user_obj = None
        try:
            assigned_int = int(assigned_to)
            user_obj = User.query.get(assigned_int)
        except Exception:
            user_obj = User.query.filter_by(username=assigned_to).first()

        if user_obj:
            # assign as integer id
            device.assigned_to = int(user_obj.id)
            device.assign_status = 'Assigned'
            # Optional: set device.device_status to 'In Service' or similar
            # device.device_status = 'In Service'
        else:
            # if provided value can't be resolved, keep device unassigned
            device.assigned_to = None
            device.assign_status = 'Unassigned'

    db.session.commit()

    # Return assigned_to username for UI feedback
    assigned_username = None
    if device.assigned_to:
        u = User.query.get(device.assigned_to)
        assigned_username = u.username if u else None

    return jsonify({'success': True, 'assigned_to': assigned_username})


@app.route('/device_assign')
@login_required
def device_assign():
    if current_user.user_level != "admin":
        return redirect(url_for('dashboard'))

    unassigned_devices = Device.query.filter_by(assign_status='Unassigned').all()
    if not unassigned_devices:
        return redirect(url_for('dashboard'))

    # build mapping device.id -> customer object to simplify template lookups
    device_customer_map = {device.id: Customer.query.get(device.customer_id) for device in unassigned_devices}
    users = User.query.all()

    return render_template('device_assign.html', unassigned_devices=unassigned_devices, available_users=users, device_customer_map=device_customer_map)


@app.route('/delivery_ready')
@login_required
def delivery_ready():
    if current_user.user_level == 'admin':
        delivery_devices = Device.query.filter_by(assign_status='Delivery Pending').all()
        if not delivery_devices:
            return redirect(url_for('dashboard'))

        device_service_info = {}
        for device in delivery_devices:
            # service.id is probably unique per device; model SparePart has service_id FK to Service.id
            service_parts = SparePart.query.filter_by(service_id=device.service_id).all()
            device_service_info[device.id] = service_parts

        return render_template('delivery_ready.html', delivery_devices=delivery_devices, device_service_info=device_service_info)
    return redirect(url_for('dashboard'))


@app.route('/assigning_devices', methods=['POST'])
@login_required
def assigning_devices():
    device_id = request.form.get('device_id')
    user_id = request.form.get('user_id')

    if not device_id:
        flash('Device id missing', 'error')
        return redirect(url_for('assigned_devices'))

    device = Device.query.get(device_id)
    if device:
        try:
            device.assigned_to = int(user_id) if user_id else None
        except Exception:
            # maybe username was passed
            user_obj = User.query.filter_by(username=user_id).first()
            device.assigned_to = user_obj.id if user_obj else None

        device.assign_status = "Assigned"
        db.session.commit()
        flash('Device assigned successfully!', 'success')
    else:
        flash('Device not found!', 'error')

    return redirect(url_for('assigned_devices'))


@app.route('/service/<int:device_id>')
def service(device_id):
    device = Device.query.get_or_404(device_id)

    # Pick the most recent Service for this device, if multiple exist
    service = Service.query.filter_by(device_id=device_id).order_by(Service.id.desc()).first()
    if not service:
        service = Service(device_id=device.id)
        db.session.add(service)
        db.session.commit()

    # Get spare parts for this service, dedupe by id in case of accidental duplicates
    raw_parts = SparePart.query.filter_by(service_id=service.id).all()
    seen = set()
    spare_parts = []
    for p in raw_parts:
        if p.id not in seen:
            spare_parts.append(p)
            seen.add(p.id)

    # Prevent same device repeating in templates by sending single device object
    return render_template(
        'service.html',
        device=device,
        dev_id=service.id,
        spare_parts=spare_parts,
        user_is=device.assigned_to
    )

@app.route('/assigned_devices')
@login_required
def assigned_devices():
    """
    Admin: shows a dropdown of users to filter assigned devices by selected user.
    Non-admin: shows devices assigned to current_user.

    Query param:
      - user_id (optional, int): when admin, filter assigned devices to this user.
    """
    # Non-admin users see only their assigned devices
    if current_user.user_level != 'admin':
        assigned_devices = Device.query.filter_by(assigned_to=current_user.id).all()
        # Build customer map to avoid repeated DB hits in template
        customer_ids = {d.customer_id for d in assigned_devices}
        device_customer_info = {c.id: c for c in Customer.query.filter(Customer.id.in_(customer_ids)).all()} if customer_ids else {}
        # build user map for display (only current user)
        users = {current_user.id: current_user}
        return render_template('assigned_devices.html',
                               assigned_devices=assigned_devices,
                               users=users,
                               selected_user_id=current_user.id,
                               device_customer_info=device_customer_info)

    # Admin flow
    # Get all service users (exclude admins if you prefer — adjust filter)
    users_list = User.query.filter(User.user_level != None).order_by(User.username).all()
    # Build map id -> user
    users_map = {u.id: u for u in users_list}

    # Read filter param
    selected_user_id = request.args.get('user_id', type=int)

    if selected_user_id:
        # fetch devices assigned to this user only
        assigned_devices = Device.query.filter_by(assigned_to=selected_user_id).all()
    else:
        # If no user selected, show all devices with assign_status 'Assigned'
        assigned_devices = Device.query.filter_by(assign_status='Assigned').all()

    # Prepare customer map to avoid N+1 lookups
    customer_ids = {d.customer_id for d in assigned_devices}
    device_customer_info = {c.id: c for c in Customer.query.filter(Customer.id.in_(customer_ids)).all()} if customer_ids else {}

    return render_template('assigned_devices.html',
                           assigned_devices=assigned_devices,
                           users=users_list,
                           selected_user_id=selected_user_id,
                           device_customer_info=device_customer_info)


@app.route('/finish_service', methods=['POST'])
@login_required
def finish_service():
    device_id = request.form.get('device_id')
    if not device_id:
        flash('Device id missing', 'error')
        return redirect(url_for('device_assign'))

    device = Device.query.get(device_id)
    if device:
        device.assign_status = "Delivery Pending"
        db.session.commit()
        flash('Device marked Delivery Pending', 'success')
    else:
        flash('Device not found!', 'error')

    return redirect(url_for('device_assign'))


@app.route('/close_device', methods=['POST'])
@login_required
def close_device():
    # allow any logged in user to close (previous code allowed all non-None user_level)
    device_id = request.form.get('device_id')
    bill_value = request.form.get('bill_value', 0)

    if not device_id:
        flash('Device id missing', 'error')
        return redirect(url_for('dashboard'))

    device = Device.query.get(device_id)
    if device:
        try:
            device.bill_value = float(bill_value)
        except Exception:
            device.bill_value = 0.0
        device.assign_status = "Closed"
        device.device_status = "Ready"
        # set expected_delivery_date to today (as datetime)
        device.expected_delivery_date = datetime.now()
        db.session.commit()
        flash('Device State Updated successfully!', 'success')
    else:
        flash('Device not found!', 'error')

    return redirect(url_for('dashboard'))


@app.route('/closed_devices')
@login_required
def closed_devices():
    if current_user.user_level != 'staff':
        closed_devices = Device.query.filter_by(assign_status='Closed').all()
        device_customer_info = {device.id: Customer.query.get(device.customer_id) for device in closed_devices}
        return render_template('closed_devices.html', closed_devices=closed_devices, device_customer_info=device_customer_info)
    return redirect(url_for('dashboard'))


@app.route('/close_device_all', methods=['POST'])
@login_required
def close_device_all():
    device_id = request.form.get('device_id')
    bill_status = request.form.get('bill_status')
    amount_received = request.form.get('amount_received')
    delivery_status = request.form.get('delivery_status')

    if delivery_status in ['true', 'True', 'on', '1', True]:
        delivery_status = 'Delivered'
    else:
        delivery_status = 'Undelivered'

    if (not amount_received or amount_received.strip() == '') and delivery_status != 'Delivered':
        return jsonify({'error': 'Amount received is required and delivery status must be checked'}), 400

    device = Device.query.get(device_id)
    if not device:
        return jsonify({'error': 'Device not found'}), 404

    device.bill_status = bill_status
    try:
        device.amount_received = float(amount_received) if amount_received else 0.0
    except Exception:
        device.amount_received = 0.0

    device.device_status = delivery_status
    device.assign_status = delivery_status

    if delivery_status == 'Delivered':
        device.expected_delivery_date = datetime.now()

    db.session.commit()

    return jsonify({'message': 'Device closed successfully'}), 200


@app.route('/closed_device_history', methods=['GET'])
@login_required
def closed_device_history():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Only devices with assign_status == Delivered (closed & delivered)
    query = Device.query.join(Customer).filter(Device.assign_status == "Delivered")

    if search_query:
        query = query.filter(
            or_(
                Device.device_name.ilike(f"%{search_query}%"),
                Customer.whatsapp_number.ilike(f"%{search_query}%")
            )
        )

    pagination = query.order_by(Device.expected_delivery_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    closed_devices = pagination.items

    # Build maps: device_id -> serviced_by_username, device_id -> delivery_date (safe)
    user_ids = {d.assigned_to for d in closed_devices if d.assigned_to}
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
    device_serviced_by = {}
    device_delivery_date = {}
    for d in closed_devices:
        device_serviced_by[d.id] = users.get(d.assigned_to).username if d.assigned_to and users.get(d.assigned_to) else None
        device_delivery_date[d.id] = safe_to_date(d.expected_delivery_date)

    return render_template(
        'closed_device_history.html',
        closed_devices=closed_devices,
        pagination=pagination,
        search_query=search_query,
        device_serviced_by=device_serviced_by,
        device_delivery_date=device_delivery_date
    )


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(host='0.0.0.0', debug=True)
