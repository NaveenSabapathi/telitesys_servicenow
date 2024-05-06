from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from models import User, db, Device, Customer
from functools import partial
from flask_migrate import Migrate
from flask import jsonify
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# Replace with a strong secret key for production
app.config['SECRET_KEY'] = 'your_strong_secret_key'

# Adjust database URI as needed. Consider using an environment variable.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Or other database connection details

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
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User(username=username)
        user.set_password(password)  # Use set_password from User model
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():

    assigned_devices_count = Device.query.filter_by(device_status='Assigned').count()
    available_devices = Device.query.filter_by(device_status='Assigned').all()
    unassigned_devices_count = Device.query.filter_by(device_status='Unassigned').count()

    # Matplotlib bar chart
    plt.figure(figsize=(8, 6))
    plt.bar(['Assigned Devices'], [assigned_devices_count], color='skyblue')
    plt.xlabel('Device Status')
    plt.ylabel('Count')
    plt.title('Assigned Devices Count')
    plt.grid(True)

    # Convert the plot to HTML format
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plot_data = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return render_template('dashboard.html', assigned_devices_count=assigned_devices_count,unassigned_devices_count=unassigned_devices_count, available_devices=available_devices, plot_data=plot_data)


    # return render_template('dashboard.html', list_data=device_data, safe_sum=safe_sum)

@app.route('/section/<section_name>')
def section(section_name):
    # Your logic for the section endpoint
    return render_template('dashboard.html')
    pass

@app.route('/search_customer/<whatsapp_number>', methods=['GET'])
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
            added_by=current_user.id  # Assuming you're tracking the user who added the device
        )
        db.session.add(new_device)
        db.session.commit()

        flash('Device added successfully!', 'success')
        return redirect(url_for('dashboard'))

    # If the request method is GET, render the add_device template
    return render_template('add_device.html')

# Section route (similar to login and dashboard routes)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables if they don't exist (optional)
        app.run(debug=True)  # Run the development server
