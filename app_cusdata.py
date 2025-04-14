from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from models import User, db, Device, Customer, SparePart, Service
from functools import partial
from flask_migrate import Migrate
from flask import jsonify
import matplotlib
matplotlib.use('agg')
from datetime import datetime

app = Flask(__name__)

# Replace with a strong secret key for production
app.config['SECRET_KEY'] = 'your_strong_secret_key'

# Adjust database URI as needed. Consider using an environment variable.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'  # Or other database connection details
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:12345@localhost/breezedb'


db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page on unauthorized access

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password):  # Use verify_password from User model
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

# Registration route (similar to login route)

@app.route('/register', methods=['GET', 'POST'])
#todo need to find some alternate ways for setting up new users
#ss @login_required
def register():
    #todo need to setup  so if theres no registered user in db, i will redirect to registration page ,
    # or else it will pop up ask admin account to create a login with admin names
    if User.query.first() is not None:
        print("Need to create a account")
    else:
        print("GO HERE")
        if current_user.user_level != 'admin':
            print("yes")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        phone_number = request.form['phone_number']
        user_level = request.form['user_level']
        print(phone_number)
        if User.query.filter_by(phone_number=phone_number).first():
            flash('Phone number already registered', 'error')
            return redirect(url_for('register'))
        user = User(username=username, phone_number=phone_number, user_level=user_level)
        user.set_password(password)  # Use set_password from User model
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/add_spare_part', methods=['POST'])
@login_required
def add_spare_part():
    data = request.json
    name = data.get('name')
    cost = data.get('cost')
    service_id = data.get('service_id')

    # Insert spare part data into the database
    # Example using SQLAlchemy
    print("trying to add spare part")
    new_spare_part = SparePart(spare_name=name, cost=cost, service_id = service_id)
    db.session.add(new_spare_part)
    db.session.commit()
    print("Spare added successfully")

    return jsonify({'message': 'Spare part added successfully'})

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_level == 'admin':
        assigned_devices_count = Device.query.filter_by(assign_status='Assigned').count()
        print(assigned_devices_count)
        available_devices = Device.query.filter_by(assign_status='Assigned').all()
        unassigned_devices_count = Device.query.filter_by(assign_status='Unassigned').count()
        unbilled_devices_count = Device.query.filter_by(assign_status='Delivery Pending').count()
        delivery_ready_devices = Device.query.filter_by(assign_status='Closed').count()
        # print(delivery_ready_devices)
        today = datetime.now().date()
        pending_delivery_count = Device.query.filter(Device.expected_delivery_date < today).count()
        pending_bill_amount = bill_today()
        return render_template('dashboard.html', assigned_devices_count=assigned_devices_count,available_devices=available_devices,pending_delivery_count=pending_delivery_count,unbilled_devices_count=unbilled_devices_count,unassigned_devices_count=unassigned_devices_count, delivery_ready_devices=delivery_ready_devices, bill_today = pending_bill_amount )
        # plot_data=plot_data)
    else:
        assigned_devices_count = Device.query.filter_by(assigned_to=current_user.id).count()
        available_devices = Device.query.filter_by(assign_status='Assigned').all()
        unassigned_devices_count = 0
        unbilled_devices_count = 0
        delivery_ready_devices = Device.query.filter_by(assign_status='Closed').count()
        today = datetime.now().date()
        pending_delivery_count = Device.query.filter(Device.expected_delivery_date < today).count()
        pending_bill_amount = 0

        return render_template('dashboard.html', assigned_devices_count=assigned_devices_count,available_devices=available_devices,pending_delivery_count=pending_delivery_count,unbilled_devices_count=unbilled_devices_count,unassigned_devices_count=unassigned_devices_count, delivery_ready_devices=delivery_ready_devices, bill_today = pending_bill_amount )



def bill_today():
    today = datetime.now().date()
    service_done = Device.query.filter_by(assign_status='Delivered').all()
    # print(service_done)
    bill_amount = 0

    for service in service_done:
        process_date = service.expected_delivery_date.date()
        # print("process,",process_date)
        # print("today =", today)
        if process_date == today:
            # print("processed today",service.bill_value)
            bill_amount += service.bill_value
    return bill_amount


@app.route('/section/<section_name>')
def section(section_name):
    # Your logic for the section endpoint
    return render_template('dashboard.html')
    pass

@app.route('/listed_device', methods=['POST'])  # Corrected route name
@login_required
def list_device():
    search_filter = request.form.get('device_id')
    customer = Customer.query.filter_by(whatsapp_number=search_filter).first()
    devices = []

    if customer:
        devices_list = Device.query.filter_by(customer_id=customer.id).all()
        c_name = customer.name
        for device in devices_list:
            devices.append({'device_name': device.device_name, 'customer_name': c_name})
            # print("if rules")
        return render_template('list_devices.html', devices=devices, c_name=c_name)
    else:
        return jsonify(error='Customer not found'), 404

    return render_template('list_devices.html', devices=devices, c_name=c_name)




@app.route('/search_customer/<whatsapp_number>', methods=['GET'])
@login_required
def search_customer(whatsapp_number):
    customer = Customer.query.filter_by(whatsapp_number=whatsapp_number).first()
    if customer:
        customer_details = {
            'name': customer.name,
            'location': customer.location
            # Add more customer details here if needed
        }
        print(customer_details['name'])
        return jsonify(customer_details)
    else:
        return jsonify({'error': 'Customer not found'})

@app.route('/add_device', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'POST':
        whatsapp_number = request.form['whatsapp_number']

        # Check if the customer with the given WhatsApp number exists
        customer = Customer.query.filter_by(whatsapp_number=whatsapp_number).first()

        if customer:
            # Customer exists, autopopulate customer details
            customer_name = customer.name
            location = customer.location
        else:
            # Customer doesn't exist, collect customer data
            customer_name = request.form['customer_name']
            location = request.form['location']

            # Create a new customer object and add it to the database
            customer = Customer(
                name=customer_name,
                location=location,
                whatsapp_number=whatsapp_number,
                device_count=0,  # Initialize device count to 0
                bill_value=0  # Initialize bill value to 0
            )
            db.session.add(customer)
            db.session.commit()

        # Extract form data for device
        device_type = request.form['device_type']
        device_name = request.form['device_name']
        model = request.form['model']
        serial_number = request.form['serial_number']
        issue_description = request.form['issue_description']
        device_status = request.form['device_status']
        remark = request.form['remark']

        received_date = datetime.strptime(request.form['received_date'], '%Y-%m-%d')
        expected_delivery_date = datetime.strptime(request.form['expected_delivery_date'], '%Y-%m-%d')
        expected_budget = float(request.form['expected_budget'])

        # Generate unique service ID
        last_device = Device.query.order_by(Device.id.desc()).first()
        if last_device:
            service_id = last_device.id + 1
        else:
            service_id = 1

        # Create a new device object and add it to the database
        new_device = Device(
            device_type=device_type,
            device_name=device_name,
            model=model,
            serial_number=serial_number,
            issue_description=issue_description,
            device_status=device_status,
            remark=remark,
            service_id=service_id,
            customer_id=customer.id,
            added_by=current_user.id,  # Assuming you're tracking the user who added the device
            received_date=received_date,
            expected_delivery_date=expected_delivery_date,
            expected_budget=expected_budget
        )
        db.session.add(new_device)
        db.session.commit()

        # whatsapp_message_body = f"New device added:\nDevice Type: {device_type}\nDevice Name: {device_name}\nModel: {model}\nSerial Number: {serial_number}\nIssue Description: {issue_description}\nDevice Status: {device_status}\nRemark: {remark}\nReceived Date: {received_date}\nExpected Delivery Date: {expected_delivery_date}\nExpected Budget: {expected_budget}"
        # send_whatsapp_message(whatsapp_number, whatsapp_message_body)

        # flash('Device added successfully!', 'success')
        # return redirect(url_for('dashboard'))
        flash('Device added successfully!', 'success')
        return redirect(url_for('ack_ticket', device_id=new_device.id))

    # If the request method is GET, render the add_device template
    return render_template('add_device.html')
# Section route (similar to login and dashboard routes)

# todo rename keyword as per its use case
# todo login check for pages
###################################################Print ack#########################

@app.route('/ack_ticket/<int:device_id>')
@login_required
def ack_ticket(device_id):
    device = Device.query.get_or_404(device_id)
    customer = Customer.query.get_or_404(device.customer_id)
    return render_template('ack_ticket.html', device=device, customer=customer)



######################################################################



####################################SECTION WHERE ADMIN ASSIGN THE UNASSIGNED DEVICES TO SERVICE TEAM#######################################
@app.route('/device_assign')
@login_required
def device_assign():
    if current_user.user_level != "admin":
        return redirect(url_for('dashboard'))
    unassigned_devices = Device.query.filter_by(assign_status='Unassigned').all()
    if not unassigned_devices:
        return redirect(url_for('dashboard'))
    print(type(unassigned_devices))
    if unassigned_devices != []:
        cus = []
        for device in unassigned_devices:
            users = device.customer_id
            customer = Customer.query.get(users)
            cus.append(customer)
    else:
        return redirect(url_for('dashboard'))

    user = User.query.all()
    return render_template('device_assign.html',  unassigned_devices = unassigned_devices, available_users = user, customer = cus)

# @app.route('/delivery_ready')
# def delivery_ready():
#     # Query devices with delivery pending status
#     delivery_devices = Device.query.filter_by(assign_status='Delivery Pending').all()
#     if delivery_devices == [] :
#         return redirect(url_for('dashboard'))
#     device_service_info = []
#     print(delivery_devices)
#     for device in delivery_devices:
#         s_id = device.id
#         print("service id is: ",s_id)
#         service_id = SparePart.query.filter_by(service_id = s_id).all()
#         print("query result",service_id)
#         device_service_info.append(service_id)
#         # for service in device_service_info:
#         #     print("level 2",service.service_id)
#
#     # return render_template('delivery_ready.html', devices_with_service_info=devices_service_info)
#
#     return render_template('delivery_ready.html', delivery_devices=delivery_devices, device_service_info=service_id)


@app.route('/delivery_ready')
@login_required
def delivery_ready():
    if current_user.user_level == 'admin':
        delivery_devices = Device.query.filter_by(assign_status='Delivery Pending').all()
        if not delivery_devices:
            return redirect(url_for('dashboard'))

        device_service_info = {}
        for device in delivery_devices:
            s_id = device.service_id
            # Query spare parts for each device
            service_parts = SparePart.query.filter_by(service_id=s_id).all()
            device_service_info[s_id] = service_parts

        return render_template('delivery_ready.html', delivery_devices=delivery_devices,
                           device_service_info=device_service_info)
    return redirect(url_for('dashboard'))



@app.route('/assigning_devices', methods=['POST'])
@login_required
def assigning_devices():

    if request.method == 'POST':
        device_id = request.form['device_id']
        user_id = request.form['user_id']


        # Retrieve the device from the database
        device = Device.query.get(device_id)
        if device:
            # Update the assigned_to column with the selected user_id
            device.assigned_to = user_id
            device.assign_status = "Assigned"
            db.session.commit()
            flash('Device assigned successfully!', 'success')
        else:
            flash('Device not found!', 'error')

    return redirect(url_for('assigned_devices'))


@app.route('/service/<int:device_id>')
def service(device_id):
    # Logic to fetch device details and spare parts for the given device_id
    device = Device.query.get_or_404(device_id)
    print(device)
    dev_id = device_id
    user_is = Device.assigned_to
    print(device_id)
    print("check this",user_is)
    spare_parts = Service.query.filter_by(device_id=device_id).all()
    return render_template('service.html', device=device,dev_id=dev_id, spare_parts=spare_parts, user_is = user_is)
@app.route('/assigned_devices')
@login_required
def assigned_devices():
    # Fetch assigned devices from the database (you need to implement this logic)
    #todo Assigned --> capital and small cases based key value error recovery needed

    if current_user.user_level != 'admin':
        assigned_devices = Device.query.filter_by(assigned_to=current_user.id).all()
    if current_user.user_level == 'admin':
        assigned_devices = Device.query.filter_by(assign_status='Assigned').all()
    if not assigned_devices:
        return redirect(url_for('dashboard'))
    return render_template('assigned_devices.html', assigned_devices=assigned_devices)



@app.route('/finish_service', methods=['POST'])
@login_required
def finish_service():
    if request.method == 'POST':
        device_id = request.form['device_id']
        print("device_id is:",device_id)
        user_id = request.form['user_id']
        print("user is:", device_id)
        # Retrieve the device from the database
        device = Device.query.get(device_id)
        if device:
            # Update the assigned_to column with the selected user_id
            device.assigned_to = user_id
            device.assign_status = "Delivery Pending"
            db.session.commit()
            flash('Device assigned successfully!', 'success')
        else:
            flash('Device not found!', 'error')

    return redirect(url_for('device_assign'))


@app.route('/close_device', methods=['POST'])
@login_required
def close_device():
    if current_user.user_level == 'admin':
        print("stated close waiting")
        if request.method == 'POST':
            device_id = request.form['device_id']
            print("device_id is:",device_id)
            bill_value = request.form['bill_value']
            print("user is:", device_id)
            # Retrieve the device from the database
            device = Device.query.get(device_id)
            if device:
                # Update the assigned_to column with the selected user_id
                device.bill_value = bill_value
                device.assign_status = "Closed"
                device.device_status = "Ready"
                db.session.commit()
                flash('Device State Updated successfully!', 'success')
            else:
                flash('Device not found!', 'error')

        return redirect(url_for('dashboard'))
    return redirect(url_for('dashboard'))



@app.route('/closed_devices')
@login_required
def closed_devices():

    if current_user.user_level !='staff':
        # Query devices with 'Closed' status
        closed_devices = Device.query.filter_by(assign_status='Closed').all()

        # Fetch customer details for each closed device
        device_customer_info = {}
        for device in closed_devices:
            customer = Customer.query.get(device.customer_id)
            device_customer_info[device.id] = customer

        return render_template('closed_devices.html', closed_devices=closed_devices,
                               device_customer_info=device_customer_info)
    return redirect(url_for('dashboard'))

#todo using one field for both delivery update and expected delivery date need to change
# @app.route('/close_device_all', methods=['POST'])
# def close_device_all():
#     device_id = request.form.get('device_id')
#     bill_status = request.form.get('bill_status')
#     amount_received = request.form.get('amount_received')
#     delivery_status = request.form.get('delivery_status')
#     if delivery_status == 'true':
#         delivery_status = 'Delivered'
#     else:
#         delivery_status = 'Undelivered'
#     print("this is",delivery_status)
#     # Check if amount received is null and delivery status is unticked
#     if not amount_received and not delivery_status:
#         return jsonify({'error': 'Amount received is required and delivery status must be checked'}), 400
#
#     # Assuming you have a Device model with appropriate fields
#     device = Device.query.get(device_id)
#     if not device:
#         return jsonify({'error': 'Device not found'}), 404
#
#     # Update the device status and bill status
#     device.bill_status = bill_status
#     print(bill_status)
#     device.amount_received = amount_received
#     device.device_status = delivery_status
#     device.assign_status = delivery_status
#     # Update the expected delivery date to today's date if delivery status is checked
#     if delivery_status:
#         device.expected_delivery_date = datetime.now().date()
#
#     # Save changes to the database
#     db.session.commit()
#
#     return jsonify({'message': 'Device closed successfully'}), 200

@app.route('/close_device_all', methods=['POST'])
@login_required
def close_device_all():
    device_id = request.form.get('device_id')
    bill_status = request.form.get('bill_status')
    amount_received = request.form.get('amount_received')
    delivery_status = request.form.get('delivery_status')

    if delivery_status == 'true':
        delivery_status = 'Delivered'
    else:
        delivery_status = 'Undelivered'

    # Check if amount received is null and delivery status is unticked
    if not amount_received and delivery_status != 'Delivered':
        return jsonify({'error': 'Amount received is required and delivery status must be checked'}), 400

    # Assuming you have a Device model with appropriate fields
    device = Device.query.get(device_id)
    if not device:
        return jsonify({'error': 'Device not found'}), 404

    # Update the device status and bill status
    device.bill_status = bill_status
    device.amount_received = amount_received
    device.device_status = delivery_status
    device.assign_status = delivery_status
    # Update the expected delivery date to today's date if delivery status is checked
    if delivery_status == 'Delivered':
        device.expected_delivery_date = datetime.now().date()

    # Save changes to the database
    db.session.commit()

    return jsonify({'message': 'Device closed successfully'}), 200


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables if they don't exist (optional)
        app.run(host='0.0.0.0',debug=True)  # Run the development server
