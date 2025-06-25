
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from models_old import User, db, Device
from functools import partial

app = Flask(__name__)

# Replace with a strong secret key for production
app.config['SECRET_KEY'] = 'your_strong_secret_key'

# Adjust database URI as needed. Consider using an environment variable.
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users1.db'  # Or other database connection details
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:12345@localhost/breezedb'

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

device_data = {
        'Available service devices': 5,
        'Device Ready': 2,
        'Under warranty': 4,
        'Device return': 0,
        'Device unassigned': 1,
    }
@app.route('/dashboard')
@login_required
def dashboard():
     # Make sure this is a dictionary
    print(device_data.items())
    print(type(device_data))
    safe_sum = partial(sum, device_data.values())
    return render_template('dashboard.html',list_data = device_data, safe_sum=safe_sum)

@app.route('/add_device.html', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'POST':
        # Extract form data
        device_type = request.form['device_type']
        device_name = request.form['device_name']
        model = request.form['model']
        serial_number = request.form['serial_number']
        issue_description = request.form['issue_description']
        device_status = request.form['device_status']
        remark = request.form['remark']
        # added_by = request.form['user']

        # Generate unique service ID (you can use a library like UUID or generate it manually)
        # For simplicity, let's assume it's sequential for now
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
            added_by=current_user.id
        )
        db.session.add(new_device)
        db.session.commit()

        flash('Device added successfully!', 'success')
        return redirect(url_for('dashboard'))

    # If the request method is GET, render the add_device template
    return render_template('add_device.html')
@app.route('/section/<section_name>')
def section(section_name):
    # Placeholder logic for the section endpoint
    return f"This is the section page for {section_name}"

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables if they don't exist (optional)
        app.run(debug=True)  # Run the development server
