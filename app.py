import traceback
import logging
from logging.handlers import RotatingFileHandler
import os
import matplotlib
from datetime import datetime, date

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect, validate_csrf, CSRFError, generate_csrf
from flask_migrate import Migrate
from sqlalchemy import or_, and_, cast, Date as saDate
from werkzeug.utils import secure_filename

# Import models and the Enum
from models import User, db, Device, Customer, SparePart, Service, AssignStatus
from crm.routes import crm_bp
from config import Config

# Configure Matplotlib backend
matplotlib.use('agg')

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
# Create a file handler that logs to 'app.log'
file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)

# Apply handler to the Flask App
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Application startup detected')

if not app.logger.handlers:
    logging.basicConfig(level=logging.DEBUG)

# ------------------------------------------------------------------------------
# Blueprint Registration
# ------------------------------------------------------------------------------
try:
    app.register_blueprint(crm_bp, url_prefix="/crm")
except Exception:
    pass

db.init_app(app)
migrate = Migrate(app, db)

try:
    from inventory.routes import inventory_bp

    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.logger.info("inventory_bp registered successfully")
except Exception as e:
    app.logger.error("Failed to import/register inventory_bp: %s", e)
    app.logger.error(traceback.format_exc())


# Dev-only endpoint
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


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

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
    if User.query.first() is None:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            phone_number = request.form['phone_number']
            user_level = 'admin'

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


# --- Helper functions ---
def safe_to_date(val):
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        return datetime.strptime(str(val), '%Y-%m-%d').date()
    except Exception:
        return None


def bill_today():
    today = datetime.now().date()
    # Corrected: Filter by Enum 'DELIVERED'
    service_done = Device.query.filter_by(assign_status=AssignStatus.DELIVERED).all()
    bill_amount = 0.0
    for service in service_done:
        proc_date = safe_to_date(service.expected_delivery_date)
        if proc_date == today:
            bill_amount += float(service.bill_value or 0)
    return bill_amount


@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().date()

    if current_user.user_level == 'admin':
        # 1. Assigned Devices (Technician working)
        assigned_devices_count = Device.query.filter_by(assign_status=AssignStatus.ASSIGNED).count()
        available_devices = Device.query.filter_by(assign_status=AssignStatus.ASSIGNED).all()

        # 2. Unassigned Devices (New intake)
        unassigned_devices_count = Device.query.filter_by(assign_status=AssignStatus.UNASSIGNED).count()

        # 3. Unbilled / Delivery Awaiting (Work done, waiting for pickup/payment)
        # Using SERVICED status for both conceptual buckets unless differentiated by bill_status
        unbilled_devices_count = Device.query.filter_by(assign_status=AssignStatus.SERVICED).count()

        # 4. Delivery Ready (In template this often mirrors 'Delivery Awaiting')
        # We map this to SERVICED (Ready to go)
        delivery_ready_devices = Device.query.filter_by(assign_status=AssignStatus.SERVICED).count()

        # 5. Pending Delivery (Overdue check)
        # Check devices that are NOT Delivered yet, but date is passed
        pending_delivery_count = Device.query.filter(
            and_(
                cast(Device.expected_delivery_date, saDate) < today,
                Device.assign_status != AssignStatus.DELIVERED
            )
        ).count()

        pending_bill_amount = bill_today()

        # 6. Closed History (Actually delivered/Gone)
        closed_device_history = Device.query.filter_by(assign_status=AssignStatus.DELIVERED).count()

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
        # Staff View
        # assigned_devices_count = Device.query.filter_by(assigned_to=current_user.id).count()
        assigned_devices_count = Device.query.filter_by(
            assigned_to=current_user.id,
            assign_status=AssignStatus.ASSIGNED
        ).count()
        available_devices = Device.query.filter_by(assign_status=AssignStatus.ASSIGNED).all()
        unassigned_devices_count = 0
        unbilled_devices_count = 0

        # For staff, delivery ready might mean things they finished
        delivery_ready_devices = Device.query.filter_by(assign_status=AssignStatus.SERVICED).count()

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


@app.route('/section/<section_name>')
def section(section_name):
    return render_template('dashboard.html')


@app.route('/listed_device', methods=['GET', 'POST'])
@login_required
def list_device():
    q = request.values.get('q') or request.values.get('device_id') or request.form.get('device_id')
    devices = []
    c_name = ''
    if not q:
        return jsonify(error='No search query provided'), 400

    customer = Customer.query.filter_by(whatsapp_number=q).first()
    if customer:
        devices_list = Device.query.filter_by(customer_id=customer.id).all()
        c_name = customer.name
        for device in devices_list:
            devices.append({'device_name': device.device_name, 'customer_name': c_name, 'id': device.id})
        return render_template('list_devices.html', devices=devices, c_name=c_name)

    try:
        possible_id = int(q)
        device = Device.query.filter_by(service_id=possible_id).first()
        if device:
            cust = Customer.query.get(device.customer_id)
            devices.append(
                {'device_name': device.device_name, 'customer_name': cust.name if cust else '', 'id': device.id})
            return render_template('list_devices.html', devices=devices, c_name=cust.name if cust else '')
    except Exception:
        pass

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

        received_date = datetime.strptime(request.form['received_date'], '%Y-%m-%d') if request.form.get(
            'received_date') else datetime.now()
        expected_delivery_date = datetime.strptime(request.form['expected_delivery_date'],
                                                   '%Y-%m-%d') if request.form.get(
            'expected_delivery_date') else datetime.now()
        expected_budget = float(request.form.get('expected_budget') or 0.0)

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
            expected_budget=expected_budget,
            assign_status=AssignStatus.UNASSIGNED  # Explicit default
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


# -----------------------------------------------------------------
@app.route('/generate_bill', methods=['POST'])
@login_required
def generate_bill():
    device_id = request.form.get('device_id')
    bill_value = request.form.get('bill_value')

    if not device_id or not bill_value:
        flash('Please enter a bill value.', 'error')
        return redirect(url_for('delivery_ready'))

    device = Device.query.get(device_id)
    if device:
        # Save Bill Value
        device.bill_value = float(bill_value)
        # Change Status to UNDELIVERED (Bill Ready, waiting for customer)
        device.assign_status = AssignStatus.UNDELIVERED
        device.device_status = "Billed"
        db.session.commit()
        flash('Bill Generated. Device moved to Closed Devices (Undelivered).', 'success')

    return redirect(url_for('delivery_ready'))

@app.route('/device_time_overlap', methods=['GET'])
@login_required
def device_time_overlap():
    if current_user.user_level != "admin":
        return redirect(url_for('dashboard'))

    today = datetime.now().date()

    # Updated: use Enums for exclusion
    pending_devices = Device.query.filter(
        and_(
            cast(Device.expected_delivery_date, saDate) < today,
            Device.assign_status != AssignStatus.DELIVERED
        )
    ).distinct(Device.id).all()

    if not pending_devices:
        return redirect(url_for('dashboard'))

    customer_ids = {d.customer_id for d in pending_devices}
    customers = {c.id: c for c in Customer.query.filter(Customer.id.in_(customer_ids)).all()}

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

    device.remark = remarks
    device.description = description if description is not None else getattr(device, 'description', '')

    if new_date:
        try:
            device.expected_delivery_date = datetime.strptime(new_date, '%Y-%m-%d')
        except Exception:
            return jsonify({'success': False, 'message': 'Invalid date format'}), 400

    if assigned_to:
        user_obj = None
        try:
            assigned_int = int(assigned_to)
            user_obj = User.query.get(assigned_int)
        except Exception:
            user_obj = User.query.filter_by(username=assigned_to).first()

        if user_obj:
            device.assigned_to = int(user_obj.id)
            device.assign_status = AssignStatus.ASSIGNED
        else:
            device.assigned_to = None
            device.assign_status = AssignStatus.UNASSIGNED

    db.session.commit()

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

    # Corrected: Use Enum
    unassigned_devices = Device.query.filter_by(assign_status=AssignStatus.UNASSIGNED).all()
    if not unassigned_devices:
        return redirect(url_for('dashboard'))

    device_customer_map = {device.id: Customer.query.get(device.customer_id) for device in unassigned_devices}
    users = User.query.all()

    return render_template('device_assign.html', unassigned_devices=unassigned_devices, available_users=users,
                           device_customer_map=device_customer_map)


# -----------------------------------------------------------------
@app.route('/delivery_ready')
@login_required
def delivery_ready():
    # Only show devices where technician is done (SERVICED) but bill is not made
    if current_user.user_level == 'admin':
        unbilled_devices = Device.query.filter_by(assign_status=AssignStatus.SERVICED).all()

        # Get spare parts for display
        device_service_info = {}
        for device in unbilled_devices:
            service = Service.query.filter_by(device_id=device.id).order_by(Service.id.desc()).first()
            if service:
                parts = SparePart.query.filter_by(service_id=service.id).all()
                device_service_info[device.id] = parts
            else:
                device_service_info[device.id] = []

        return render_template('delivery_ready.html',
                               delivery_devices=unbilled_devices,
                               device_service_info=device_service_info)
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
            user_obj = User.query.filter_by(username=user_id).first()
            device.assigned_to = user_obj.id if user_obj else None

        device.assign_status = AssignStatus.ASSIGNED
        db.session.commit()
        flash('Device assigned successfully!', 'success')
    else:
        flash('Device not found!', 'error')

    return redirect(url_for('assigned_devices'))


@app.route('/service/<int:device_id>')
def service(device_id):
    device = Device.query.get_or_404(device_id)
    service = Service.query.filter_by(device_id=device_id).order_by(Service.id.desc()).first()
    if not service:
        service = Service(device_id=device.id)
        db.session.add(service)
        db.session.commit()

    raw_parts = SparePart.query.filter_by(service_id=service.id).all()
    seen = set()
    spare_parts = []
    for p in raw_parts:
        if p.id not in seen:
            spare_parts.append(p)
            seen.add(p.id)

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
    # --- Helper Class for Privacy ---
    class RedactedCustomer:
        """Placeholder to hide details from Staff"""
        name = "NA"
        whatsapp_number = "NA"
        location = "NA"

    # ---------------------------------------------------------
    # 1. NON-ADMIN VIEW (Staff & Managers)
    # ---------------------------------------------------------
    if current_user.user_level != 'admin':
        # Fetch devices assigned to this user that are currently 'ASSIGNED'
        # Note: Using AssignStatus.ASSIGNED enum for safety
        assigned_devices = Device.query.filter_by(
            assigned_to=current_user.id,
            assign_status=AssignStatus.ASSIGNED
        ).all()

        customer_ids = {d.customer_id for d in assigned_devices}

        # --- PRIVACY LOGIC START ---
        if current_user.user_level == 'staff':
            # IF STAFF: Replace real data with "NA" dummy objects
            device_customer_info = {cid: RedactedCustomer() for cid in customer_ids}
        else:
            # IF MANAGER: Fetch and show real customer details
            real_customers = Customer.query.filter(Customer.id.in_(customer_ids)).all() if customer_ids else []
            device_customer_info = {c.id: c for c in real_customers}
        # --- PRIVACY LOGIC END ---

        users = {current_user.id: current_user}

        return render_template('assigned_devices.html',
                               assigned_devices=assigned_devices,
                               users=users,
                               selected_user_id=current_user.id,
                               device_customer_info=device_customer_info)

    # ---------------------------------------------------------
    # 2. ADMIN VIEW (Full Access)
    # ---------------------------------------------------------
    users_list = User.query.filter(User.user_level != None).order_by(User.username).all()
    selected_user_id = request.args.get('user_id', type=int)

    if selected_user_id:
        assigned_devices = Device.query.filter_by(assigned_to=selected_user_id).all()
    else:
        assigned_devices = Device.query.filter_by(assign_status=AssignStatus.ASSIGNED).all()

    customer_ids = {d.customer_id for d in assigned_devices}

    # Admins always see real data
    real_customers = Customer.query.filter(Customer.id.in_(customer_ids)).all() if customer_ids else []
    device_customer_info = {c.id: c for c in real_customers}

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
        # Corrected: Delivery Pending -> SERVICED
        device.assign_status = AssignStatus.SERVICED
        db.session.commit()
        flash('Device marked Delivery Pending', 'success')
    else:
        flash('Device not found!', 'error')

    return redirect(url_for('device_assign'))


@app.route('/close_device', methods=['POST'])
@login_required
def close_device():
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

        # Corrected: Closed -> DELIVERED
        device.assign_status = AssignStatus.DELIVERED
        device.device_status = "Ready"
        device.expected_delivery_date = datetime.now()
        db.session.commit()
        flash('Device State Updated successfully!', 'success')
    else:
        flash('Device not found!', 'error')

    return redirect(url_for('dashboard'))

#
# @app.route('/closed_devices')
# @login_required
# def closed_devices():
#     if current_user.user_level != 'staff':
#         closed_devices = Device.query.filter_by(assign_status=AssignStatus.DELIVERED).all()
#         device_customer_info = {device.id: Customer.query.get(device.customer_id) for device in closed_devices}
#         return render_template('closed_devices.html', closed_devices=closed_devices,
#                                device_customer_info=device_customer_info)
#     return redirect(url_for('dashboard'))
#
#
#
# #profit calc
#
#
# @app.route('/close_device_all', methods=['POST'])
# @login_required
# def close_device_all():
#     # Only Admin/Manager should close devices
#     if current_user.user_level == "staff":
#         return jsonify({'error': 'Access Denied: Staff cannot close devices.'}), 403
#
#     device_id = request.form.get('device_id')
#     bill_status = request.form.get('bill_status')
#     amount_received = request.form.get('amount_received')
#     raw_delivery_status = request.form.get('delivery_status')
#
#     app.logger.info(f"Attempting to close device {device_id} | User: {current_user.username}")
#
#     # 1. Determine Status
#     if raw_delivery_status in ['true', 'True', 'on', '1', True]:
#         final_assign_status = AssignStatus.DELIVERED
#         final_device_status_str = 'Delivered'
#     else:
#         final_assign_status = AssignStatus.SERVICED
#         final_device_status_str = 'Ready'
#
#     # 2. Validation
#     if (not amount_received or amount_received.strip() == '') and final_assign_status != AssignStatus.DELIVERED:
#         return jsonify({'error': 'Amount received is required and delivery status must be checked'}), 400
#
#     device = Device.query.get(device_id)
#     if not device:
#         return jsonify({'error': 'Device not found'}), 404
#
#     try:
#         # 3. Calculate Internal Cost (Spare Parts)
#         # Find the most recent service for this device
#         service = Service.query.filter_by(device_id=device.id).order_by(Service.id.desc()).first()
#
#         calculated_cost = 0.0
#         if service:
#             # Sum up all spare parts linked to this service
#             parts = SparePart.query.filter_by(service_id=service.id).all()
#             calculated_cost = sum(part.cost for part in parts)
#
#         # SAVE the cost to the device
#         device.total_cost = calculated_cost
#
#         # 4. Update Billing & Status
#         device.bill_status = bill_status
#         try:
#             device.amount_received = float(amount_received) if amount_received else 0.0
#         except ValueError:
#             device.amount_received = 0.0
#
#         device.device_status = final_device_status_str
#         device.assign_status = final_assign_status
#
#         if final_assign_status == AssignStatus.DELIVERED:
#             device.expected_delivery_date = datetime.now()
#
#         db.session.commit()
#
#         # Log the profit for internal tracking
#         profit = device.amount_received - device.total_cost
#         app.logger.info(
#             f"Device {device.id} Closed. Revenue: {device.amount_received}, Cost: {device.total_cost}, Profit: {profit}")
#
#         return jsonify({'message': 'Device closed successfully'}), 200
#
#     except Exception as e:
#         db.session.rollback()
#         app.logger.critical(f"Database Commit Failed for device {device_id}: {str(e)}")
#         return jsonify({'error': 'Internal Server Error'}), 500

#############################new logic#####################
# app_cusdata.py

# -----------------------------------------------------------------
@app.route('/closed_devices')
@login_required
def closed_devices():
    # Fetch devices that are Billed but UNDELIVERED
    print(f"DEBUG CHECK: {AssignStatus.UNDELIVERED.value}")
    pending_pickup = Device.query.filter_by(bill_status="unpaid").all()
    device_customer_info = {device.id: Customer.query.get(device.customer_id) for device in pending_pickup}

    return render_template('closed_devices.html',
                           closed_devices=pending_pickup,
                           device_customer_info=device_customer_info)


# -----------------------------------------------------------------

# -----------------------------------------------------------------
@app.route('/close_device_all', methods=['POST'])
@login_required
def close_device_all():
    if current_user.user_level == "staff": return jsonify({'error': 'Access Denied'}), 403

    device_id = request.form.get('device_id')
    amount_received = request.form.get('amount_received')

    # We strictly expect 'delivered' here as per your workflow
    final_status = AssignStatus.DELIVERED

    device = Device.query.get(device_id)
    if not device: return jsonify({'error': 'Device not found'}), 404

    try:
        # Calculate Costs (Profit logic)
        service = Service.query.filter_by(device_id=device.id).order_by(Service.id.desc()).first()
        if service:
            parts = SparePart.query.filter_by(service_id=service.id).all()
            device.total_cost = sum(part.cost for part in parts)

        # Update Payment Info
        device.amount_received = float(amount_received) if amount_received else 0.0
        device.bill_status = "paid" if device.amount_received >= device.bill_value else "partial"

        # FINAL STATUS CHANGE
        device.assign_status = final_status
        device.device_status = "Delivered"
        device.expected_delivery_date = datetime.now()

        db.session.commit()

        # Return success AND the ID so frontend can trigger popup
        return jsonify({'message': 'Device Delivered', 'device_id': device.id}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
##########new wnd #############

#
@app.route('/closed_device_history', methods=['GET'])
@login_required
def closed_device_history():
    # Allow Admins and Managers (Block only Staff)
    if current_user.user_level == "staff":
        return redirect(url_for('dashboard'))

    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Get Delivered devices
    query = Device.query.join(Customer).filter(Device.assign_status == AssignStatus.DELIVERED)

    if search_query:
        query = query.filter(
            or_(
                Device.device_name.ilike(f"%{search_query}%"),
                Customer.whatsapp_number.ilike(f"%{search_query}%"),
                Device.serial_number.ilike(f"%{search_query}%")
            )
        )

    pagination = query.order_by(Device.expected_delivery_date.desc()).paginate(page=page, per_page=per_page,
                                                                               error_out=False)
    closed_devices = pagination.items

    # Create a dictionary to map Device ID -> Username
    # This is faster/safer than relying on lazy-loaded relationships in the loop
    user_ids = {d.assigned_to for d in closed_devices if d.assigned_to}
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

    device_serviced_by = {}
    for d in closed_devices:
        assigned_user = users.get(d.assigned_to)
        device_serviced_by[d.id] = assigned_user.username if assigned_user else 'N/A'

    return render_template(
        'closed_device_history.html',
        closed_devices=closed_devices,
        pagination=pagination,
        search_query=search_query,
        device_serviced_by=device_serviced_by  # Pass this map to the template
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