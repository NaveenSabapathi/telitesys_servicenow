# 🧾Computers/Hardware Service Management System (TELITE Billing App)

A full-featured **Flask-based service management and CRM application** for managing customer devices, service tracking, billing, and team assignments — built for computer service centers.

---

## 🚀 Overview

This web app helps service centers manage devices from intake to delivery — tracking customers, technicians, spare parts, billing, and service progress.  
It includes secure authentication, role-based access, a visual dashboard, and CRM lead integration.

---

## 🏗️ Features

### 🔐 Authentication
- Secure login/logout with **Flask-Login**
- CSRF-protected forms via **Flask-WTF**
- Role-based registration (Admin, Manager, Staff)

### 🧰 Service Management
- Add new devices with customer linkage (auto-fetch by WhatsApp number)
- Track device intake, repair, and delivery stages
- Assign devices to service personnel
- Add spare parts dynamically to service tickets
- Close and print service bills

### 💸 Billing & Delivery
- Generate delivery challans / bills (`print_bill.html`)
- Mark devices as “Delivery Pending”, “Closed”, or “Delivered”
- Update bill value, amount received, and delivery status

### 🕒 Overdue Tracking
- Automatically list devices past expected delivery date
- Admin can reassign overdue devices and set new deadlines

### 📊 Dashboard Insights
- Visual dashboard cards for:
  - Assigned / Unassigned devices
  - Pending deliveries
  - Closed device history
  - Bill processed today
  - CRM leads and new lead creation

### 📞 CRM Integration
- Integrated blueprint (`/crm`) for managing sales/lead tracking (extensible)

---

## ⚙️ Tech Stack

| Component | Technology |
|------------|-------------|
| **Backend** | Flask 3.1, Flask-SQLAlchemy |
| **Frontend** | Bootstrap 4/5, Jinja2 |
| **Database** | PostgreSQL (recommended) |
| **Authentication** | Flask-Login |
| **Migrations** | Flask-Migrate / Alembic |
| **Environment** | python-dotenv |
| **PDF/Printing** | HTML-to-print view |

---

## 🧩 Project Structure

```
📦 Flask TELITE Billing
│
├── app.py                  # Main Flask app (production-ready)
├── app_cusdata.py          # Alternate app version
├── manage.py               # CLI entry point for Flask commands
├── config.py               # Configuration (loads .env)
├── models.py               # Database models (User, Device, Customer, etc.)
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
│
├── templates/              # Jinja2 Templates
│   ├── base.html
│   ├── dashboard.html
│   ├── add_device.html
│   ├── device_assign.html
│   ├── delivery_ready.html
│   ├── closed_devices.html
│   ├── service.html
│   ├── device_overlap.html
│   ├── login.html
│   ├── register.html
│   ├── print_bill.html
│   └── ...
│
└── static/
    ├── css/
    ├── js/
    ├── uploads/
    └── images/logo.png
```

---

## 🧠 Database Models

### **User**
| Field | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `username` | String | Unique username |
| `password_hash` | String | Securely stored password |
| `phone_number` | String | Unique user phone number |
| `user_level` | String | admin / manager / staff |

### **Customer**
| Field | Type |
|--------|------|
| `id`, `name`, `location`, `whatsapp_number`, `device_count`, `bill_value` |

### **Device**
Tracks all service items and states.

| Field | Type | Description |
|--------|------|-------------|
| `device_name`, `model`, `serial_number`, `issue_description` | String |
| `device_status` | String | Service state |
| `assign_status` | String | Assigned / Unassigned / Closed / Delivered |
| `expected_delivery_date`, `expected_budget` | DateTime, Float |
| `bill_value`, `bill_status` | Float, String |
| `customer_id`, `assigned_to`, `added_by` | Foreign Keys |

### **Service / SparePart**
- `Service` → linked to each device
- `SparePart` → linked to a service (name, cost)

---

## 🔑 Environment Configuration (`.env`)

```bash
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
SQLALCHEMY_DATABASE_URI=postgresql://postgres:password@localhost/breeze
```

---

## 🛠️ Setup Instructions

### 1️⃣ Install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2️⃣ Set up PostgreSQL
```sql
CREATE DATABASE breeze;
CREATE USER breeze_user WITH PASSWORD 'securepassword';
GRANT ALL PRIVILEGES ON DATABASE breeze TO breeze_user;
```

Update `.env`:
```
SQLALCHEMY_DATABASE_URI=postgresql://breeze_user:securepassword@localhost/breeze
```

### 3️⃣ Initialize Database
```bash
flask db init
flask db migrate
flask db upgrade
```

### 4️⃣ Run the App
```bash
python manage.py run
```
Or directly:
```bash
flask run
```

Access on:  
👉 `http://127.0.0.1:5000`

---

## 🔒 Security Notes
- All POST routes are CSRF-protected.
- Passwords hashed using **Werkzeug security**.
- Session cookies secured (`HttpOnly`, `SameSite`, `Secure`).
- Validate uploaded image extensions & size for production.

---

## 🧾 Key Routes Summary

| Route | Method | Description |
|--------|---------|-------------|
| `/login` | GET/POST | Login page |
| `/register` | GET/POST | Register (admin-controlled) |
| `/dashboard` | GET | Dashboard overview |
| `/add_device` | GET/POST | Add customer & device |
| `/device_assign` | GET | Assign devices |
| `/service/<id>` | GET | Manage spare parts |
| `/delivery_ready` | GET | List ready devices |
| `/close_device` | POST | Mark device closed |
| `/print_bill/<id>` | GET | Printable delivery challan |
| `/closed_devices` | GET | Devices marked closed |
| `/device_time_overlap` | GET | Overdue device list |
| `/logout` | GET | Logout |

---

## 💡 Deployment Guide (Production)

### Using Gunicorn + Nginx
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Configure Nginx reverse proxy:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        include proxy_params;
    }
}
```

Enable HTTPS with **Certbot**:
```bash
sudo certbot --nginx -d your-domain.com
```

---

## 🧾 Print Bill Example
Auto-printable HTML:
```
Customer: John Doe
Device: HP Laptop
Issue: No Power On
Bill: ₹2500
Amount Received: ₹2000
Balance: ₹500
```

---

## 👨‍💻 Contributors
**Developed by:** Naveen L S  
**Organization:** Breeze Computers  

---

## 📜 License
This project is licensed under the **MIT License** — free to modify and distribute with attribution.

---

## ✅ Future Enhancements
- ✅ WhatsApp Notification Integration (Twilio / Meta API)
- ✅ PDF Export for Bills
- ⏳ CRM Lead Conversion tracking
- ⏳ Staff Performance reports
- ⏳ Cloud-based backups (AWS S3 or GDrive)

---

> _“Simplifying service workflows with smart automation.”_
