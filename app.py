from flask import Flask, render_template, request, redirect, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from pytz import timezone
from flask import session
from flask import request, render_template, redirect, url_for, flash
import psycopg2
import json
import pygame
import glob
from gtts import gTTS
from sqlalchemy import cast, Date
import tempfile
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

load_dotenv()

USERS_FILE = 'users.json'

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "fallback-secret-key")

scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)
db = SQLAlchemy(app)

class FoodClaim(db.Model):
    __tablename__ = 'food_claim'
    id = db.Column(db.Integer, primary_key=True)
    ref_id = db.Column(db.String(50), db.ForeignKey('employees.ref_id', ondelete="CASCADE"), nullable=False)
    claim_date = db.Column(db.DateTime, nullable=False)


class Employee(db.Model):
    __tablename__ = 'employees'
    ref_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_archived = db.Column(db.Boolean, default=False)
    archived_date = db.Column(db.DateTime)

    # Relationship to FoodClaim
    claims = db.relationship(
        'FoodClaim',
        backref='employee',
        cascade="all, delete-orphan"
    )


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    target_employee = db.Column(db.String(100))
    details = db.Column(db.JSON)  # Store additional data as JSON
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Add this field
    
    def __repr__(self):
        return f'<ActivityLog {self.user_id} - {self.action}>'

@app.template_filter("indo_day_date")
def indo_day_date(value):
    indonesian_days = {
        'Monday': 'Senin',
        'Tuesday': 'Selasa',
        'Wednesday': 'Rabu',
        'Thursday': 'Kamis',
        'Friday': 'Jumat',
        'Saturday': 'Sabtu',
        'Sunday': 'Minggu'
    }

    indonesian_months = {
        1: 'Januari',
        2: 'Februari',
        3: 'Maret',
        4: 'April',
        5: 'Mei',
        6: 'Juni',
        7: 'Juli',
        8: 'Agustus',
        9: 'September',
        10: 'Oktober',
        11: 'November',
        12: 'Desember'
    }

    day_name = indonesian_days.get(value.strftime('%A'), value.strftime('%A'))
    day = value.day  # This should be an integer like 11
    month = indonesian_months[value.month]
    year = value.year

    return f"{day_name}, {day} {month} {year}"

def generate_custom_sound(text, filename):
    """Generate a custom TTS sound file for the alert"""
    try:
        tts = gTTS(text=text, lang='id')
        filepath = os.path.join('static', 'sounds', filename)
        tts.save(filepath)
        return filepath
    except Exception as e:
        print(f"Error generating TTS: {e}")
        return url_for('static', filename='sounds/sudah_diambil.mp3')

def generate_custom_sound(text, filename):
    """Generate a custom TTS sound file for the alert"""
    try:
        # Create sounds directory if it doesn't exist
        os.makedirs(os.path.join('static', 'sounds', 'custom'), exist_ok=True)
        
        tts = gTTS(text=text, lang='id')
        filepath = os.path.join('static', 'sounds', 'custom', filename)
        tts.save(filepath)
        return url_for('static', filename=f'sounds/custom/{filename}')
    except Exception as e:
        print(f"Error generating TTS: {e}")
        # Return default sounds based on context
        if "selamat" in text.lower():
            return url_for('static', filename='sounds/sukses_ambil.mp3')
        else:
            return url_for('static', filename='sounds/sudah_diambil.mp3')

@app.route('/', methods=['GET', 'POST'])
def index():
    play_sound = None  # default
    already_claimed_user = None  # Initialize variable
    success_user = None  # Initialize variable for successful claim

    if request.method == 'POST':
        ref_id = request.form['ref_id']
        jakarta = timezone('Asia/Jakarta')
        now = datetime.now(jakarta)
        today = now.date()

        # Hari dalam bahasa Indonesia
        indonesian_days = {
            'Monday': 'Senin',
            'Tuesday': 'Selasa',
            'Wednesday': 'Rabu',
            'Thursday': 'Kamis',
            'Friday': 'Jumat',
            'Saturday': 'Sabtu',
            'Sunday': 'Minggu'
        }
        day_eng = now.strftime('%A')
        day = indonesian_days.get(day_eng, day_eng)

        # ✅ Check employee
        employee = Employee.query.filter_by(ref_id=ref_id).first()
        if not employee:
            flash("Ref ID tidak terdaftar. Silakan hubungi HRD.", "danger")
            return render_template('index.html', play_sound=url_for('static', filename='sounds/hubungi_hrd.mp3'))

        # ✅ Check claim
        existing_claim = FoodClaim.query.filter(
            FoodClaim.ref_id == ref_id,
            db.func.date(FoodClaim.claim_date) == today
        ).first()

        if existing_claim:
            flash(f'Kamu sudah ambil makanan hari ini!', 'danger')
            # Generate custom sound with the user's name
            sound_text = f"Hey {employee.name}, kamu sudah mengambil makanan hari ini!"
            sound_filename = f"already_claimed_{employee.ref_id}.mp3"
            play_sound = generate_custom_sound(sound_text, sound_filename)
            already_claimed_user = employee.name  # Set the user name for display
        else:
            new_claim = FoodClaim(ref_id=ref_id, claim_date=now)
            db.session.add(new_claim)
            db.session.commit()
            flash(f'Makanan hari {day} diambil pada {now.strftime("%d %B %Y pukul %H:%M")}', 'success')
            # Generate custom success sound with the user's name
            sound_text = f"{employee.name}, selamat menikmati makanan hari {day} sudah diambil."
            sound_filename = f"success_claim_{employee.ref_id}.mp3"
            play_sound = generate_custom_sound(sound_text, sound_filename)
            success_user = employee.name  # Set the user name for display

        return render_template('index.html', play_sound=play_sound, 
                              already_claimed_user=already_claimed_user,
                              success_user=success_user)

    return render_template('index.html', play_sound=None, 
                          already_claimed_user=None, success_user=None)

@app.route('/admin')
def admin():
    jakarta = timezone('Asia/Jakarta')

    # Get all claims
    claims = db.session.query(FoodClaim).join(Employee).order_by(FoodClaim.claim_date.asc()).all()

    # Extract unique dates (store as datetime, not date)
    unique_dates = sorted(
        set([c.claim_date.astimezone(jakarta).replace(hour=0, minute=0, second=0, microsecond=0) for c in claims])
    )

    # Stats
    now = datetime.now(jakarta)
    today = now.date()
    start_of_week = today - timedelta(days=today.weekday())

    today_claims = FoodClaim.query.filter(
        db.func.date(FoodClaim.claim_date) == today
    ).count()

    week_claims = FoodClaim.query.filter(
        db.func.date(FoodClaim.claim_date) >= start_of_week
    ).count()

    return render_template(
        'admin.html',
        claims=claims,
        today_claims=today_claims,
        week_claims=week_claims,
        unique_dates=unique_dates  # now contains datetime objects
    )

@app.template_filter('format_indonesian_datetime')
def format_indonesian_datetime(value):
    if isinstance(value, datetime):
        dt = value
    else:
        # Combine with midnight time if it's just a date
        dt = datetime.combine(value, time.min)

    jakarta = timezone('Asia/Jakarta')
    localized = dt.astimezone(jakarta)

    indonesian_days = {
        'Monday': 'Senin',
        'Tuesday': 'Selasa',
        'Wednesday': 'Rabu',
        'Thursday': 'Kamis',
        'Friday': 'Jumat',
        'Saturday': 'Sabtu',
        'Sunday': 'Minggu'
    }

    indonesian_months = {
        'January': 'Januari',
        'February': 'Februari',
        'March': 'Maret',
        'April': 'April',
        'May': 'Mei',
        'June': 'Juni',
        'July': 'Juli',
        'August': 'Agustus',
        'September': 'September',
        'October': 'Oktober',
        'November': 'November',
        'December': 'Desember'
    }

    day = indonesian_days[localized.strftime('%A')]
    month = indonesian_months[localized.strftime('%B')]
    return f"{day}, {localized.strftime('%d')} {month} {localized.strftime('%Y')} pukul {localized.strftime('%H:%M')}"

@app.route("/employee_list/register", methods=["POST"])
def register_employee():
    ref_id = request.form["ref_id"]
    name = request.form["name"]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT * FROM employees WHERE ref_id = %s", (ref_id,))
        if cur.fetchone():
            flash("Karyawan sudah pernah didaftarkan", "warning")
        else:
            cur.execute("INSERT INTO employees (ref_id, name) VALUES (%s, %s)", (ref_id, name))
            conn.commit()
            flash("Karyawan berhasil didaftarkan!", "success")

              # Log the activity - ADD THIS
            log_activity(
                user_id=session.get('user_id', 'unknown'),  # or session.get('user_id', 'unknown')
                action="add_employee",
                target_employee=ref_id,
                details={"name": name}
            )
    except Exception as e:
        flash(f"Error occurred: {str(e)}", "danger")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('employee_list'))

@app.route('/employee-list')
def employee_list():
    # Get all non-archived employees sorted by name
    employees = Employee.query.filter_by(is_archived=False).order_by(Employee.ref_id.desc()).all()
    return render_template('employee_list.html', employees=employees)


# Update employee
@app.route("/employees/<string:ref_id>/update", methods=["POST"])
def update_employee_route(ref_id):
    try:
        data = request.get_json()
        new_ref_id = data.get("ref_id")
        name = data.get("name")

        # Find the employee by the old ref_id
        employee = Employee.query.get(ref_id)
        if not employee:
            return jsonify({"error": "Employee not found"}), 404

        # Save old name BEFORE updating
        old_name = employee.name

        # Log the activity with old and new names
        log_activity(
            user_id=session.get('user_id', 'unknown'),
            action="edit_employee",
            target_employee=ref_id,
            details={
                "old_ref_id": ref_id,
                "new_ref_id": new_ref_id,
                "old_name": old_name,  # 👈 Store old name
                "new_name": name       # 👈 Store new name
            }
        )
        
        # Update the employee
        employee.ref_id = new_ref_id
        employee.name = name
        
        db.session.commit()

        return jsonify({"message": "Employee updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print("Error updating employee:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/admin/archive')
def employee_archive():
    # Fetch archived employees from database
    archived_employees = Employee.query.filter_by(is_archived=True).order_by(Employee.archived_date.desc()).all()

    # Convert archived_date to Jakarta time for each employee
    jakarta = timezone('Asia/Jakarta')
    for emp in archived_employees:
        if emp.archived_date:
            emp.archived_date_jakarta = emp.archived_date.astimezone(jakarta)

    return render_template('archive.html', employees=archived_employees)

@app.route('/employees/<ref_id>/delete', methods=['POST'])
def delete_employee(ref_id):
    try:
        employee = Employee.query.filter_by(ref_id=ref_id).first()
        if employee:
            # Instead of deleting, mark as archived
            employee.is_archived = True
            employee.archived_date = datetime.utcnow()
            db.session.commit()
            
            # Log the deletion/archiving activity
            log_activity(session.get('user_id', 'unknown'), 'archive_employee', ref_id, 
                        details={'name': employee.name})
            
            return jsonify({'success': True, 'message': 'Employee archived successfully'})
        else:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    


# Add a route to restore archived employees
@app.route('/employees/<ref_id>/restore', methods=['POST'])
def restore_employee(ref_id):
    try:
        employee = Employee.query.filter_by(ref_id=ref_id).first()
        if employee:
            employee.is_archived = False
            employee.archived_date = None
            db.session.commit()
            
            # Log the restoration activity
            log_activity(session.get('user_id', 'unknown'), 'restore_employee', ref_id, 
                        details={'name': employee.name})
            
            return jsonify({'success': True, 'message': 'Employee restored successfully'})
        else:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Create a simple log function
def log_activity(user_id, action, target_employee, details=None):
    """Log user activities"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'action': action,
        'target_employee': target_employee,
        'details': details or {}
    }
    
    # Write to a log file (you could also use a database)
    with open('activity_log.jsonl', 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')
    
    # Also print to console for debugging
    print(f"ACTIVITY: {user_id} {action} {target_employee}")


@app.route('/activity-logs')
def get_activity_logs():
    try:
        logs = []
        # Read last 50 log entries
        if os.path.exists('activity_log.jsonl'):
            with open('activity_log.jsonl', 'r') as log_file:
                lines = log_file.readlines()
                # Get last 50 lines (or all if less than 50)
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                for line in recent_lines:
                    log_data = json.loads(line.strip())
                    
                    # Create a formatted message for display but keep original data
                    formatted_message = format_log_message(log_data)
                    log_data['formatted_message'] = formatted_message
                    
                    logs.append(log_data)
        
        # Reverse to show newest first
        logs.reverse()
        return jsonify(logs)
    except Exception as e:
        print(f"Error reading logs: {e}")
        return jsonify([])

# Add this route for permanent deletion
@app.route('/employees/<ref_id>/permanent-delete', methods=['POST'])
def permanent_delete_employee(ref_id):
    try:
        employee = Employee.query.filter_by(ref_id=ref_id).first()
        if employee:
            # Log the permanent deletion activity BEFORE deleting
            log_activity(
                user_id=session.get('user_id', 'unknown'),
                action="permanent_delete_employee",
                target_employee=ref_id,
                details={'name': employee.name}
            )
            
            # Permanently delete the employee
            db.session.delete(employee)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Employee permanently deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Update the format_log_message function to handle the new action
def format_log_message(log_data):
    """Format log data into a human-readable message"""
    try:
        timestamp = datetime.fromisoformat(log_data['timestamp'])
        formatted_time = timestamp.strftime('%d %B %Y %H:%M')
        username = log_data.get('user_id', 'unknown')
        
        if log_data['action'] == 'add_employee':
            return f"{formatted_time} - {username} menambahkan karyawan baru: {log_data['details']['name']} ({log_data['target_employee']})"
        elif log_data['action'] == 'edit_employee':
            return f"{formatted_time} - {username} mengedit karyawan {log_data['details']['old_ref_id']} → menjadi {log_data['details']['new_name']} ({log_data['details']['new_ref_id']})"
        elif log_data['action'] == 'delete_employee':
            return f"{formatted_time} - {username} menghapus karyawan: {log_data['target_employee']}"
        elif log_data['action'] == 'import_employees':
            details = log_data.get('details', {})
            added = details.get('added', 0)
            duplicates = details.get('duplicates', 0)
            return f"{formatted_time} - {username} mengimpor data karyawan: {added} ditambahkan, {duplicates} duplikat"
        elif log_data['action'] == 'archive_employee':
            return f"{formatted_time} - {username} mengarsipkan karyawan: {log_data['details']['name']} ({log_data['target_employee']})"
        elif log_data['action'] == 'restore_employee':
            return f"{formatted_time} - {username} memulihkan karyawan: {log_data['details']['name']} ({log_data['target_employee']})"
        elif log_data['action'] == 'permanent_delete_employee':  # Add this case
            return f"{formatted_time} - {username} menghapus permanen karyawan: {log_data['details']['name']} ({log_data['target_employee']})"
        else:
            return f"{formatted_time} - {username} {log_data['action']} {log_data['target_employee']}"
    except Exception as e:
        print(f"Error formatting log message: {e}")
        return f"Log entry - {log_data}"
    
# In your login route or authentication middleware
@app.before_request
def set_user():
    # Check if user is authenticated and set username in session
    if 'username' not in session:
        # Your authentication logic here
        # For example, if using basic auth:
        auth = request.authorization
        if auth and auth.username in USERS and USERS[auth.username] == auth.password:
            session['username'] = auth.username

@app.route('/employees/<ref_id>/food-history')
def get_food_history(ref_id):
    try:
        # Query the food_claim table for this employee's claims
        history = db.session.query(FoodClaim) \
            .filter_by(ref_id=ref_id) \
            .order_by(FoodClaim.claim_date.desc()) \
            .all()
        
        history_data = []
        for claim in history:
            history_data.append({
                'timestamp': claim.claim_date.isoformat(),
                'meal_type': 'Makanan'  # Default value since your table doesn't have meal_type
            })
        
        return jsonify(history_data)
    except Exception as e:
        print(f"Error fetching food history: {e}")
        return jsonify([])  # Return empty array on error

# Update your log_activity calls to use the username from session
def some_function_that_logs():
    log_activity(
        user_id=session.get('username', 'unknown'),
        action="some_action",
        target_employee="some_employee",
        details={"some": "detail"}
    )


@app.route('/recent-claims')
def recent_claims():
    jakarta = timezone('Asia/Jakarta')
    now = datetime.now(jakarta).date()

    # Get the 10 latest claims for today
    claims = (
        db.session.query(FoodClaim, Employee)
        .join(Employee)
        .filter(db.func.date(FoodClaim.claim_date) == now)
        .order_by(FoodClaim.claim_date.desc())
        .limit(10)
        .all()
    )

    # Indonesian day and month names
    indonesian_days = {
        'Monday': 'Senin',
        'Tuesday': 'Selasa',
        'Wednesday': 'Rabu',
        'Thursday': 'Kamis',
        'Friday': 'Jumat',
        'Saturday': 'Sabtu',
        'Sunday': 'Minggu'
    }
    
    indonesian_months = {
        'January': 'Januari',
        'February': 'Februari',
        'March': 'Maret',
        'April': 'April',
        'May': 'Mei',
        'June': 'Juni',
        'July': 'Juli',
        'August': 'Agustus',
        'September': 'September',
        'October': 'Oktober',
        'November': 'November',
        'December': 'Desember'
    }

    claims_data = []
    for claim in claims:
        # Convert to Jakarta timezone (GMT+7)
        claim_date = claim.FoodClaim.claim_date
        
        # If date is naive (no timezone), assume it's UTC and convert to Jakarta
        if claim_date.tzinfo is None:
            utc_time = timezone('UTC').localize(claim_date)
            jakarta_time = utc_time.astimezone(jakarta)
        else:
            jakarta_time = claim_date.astimezone(jakarta)
        
        # Format the date in Indonesian
        english_day = jakarta_time.strftime("%A")
        english_month = jakarta_time.strftime("%B")
        
        indonesian_day = indonesian_days.get(english_day, english_day)
        indonesian_month = indonesian_months.get(english_month, english_month)
        
        formatted_date = f"{indonesian_day}, {jakarta_time.day} {indonesian_month} {jakarta_time.year}"
        formatted_time = jakarta_time.strftime("%H:%M")
        
        claims_data.append({
            "id": claim.FoodClaim.id,
            "name": claim.Employee.name,
            "date": formatted_date,
            "time": formatted_time
        })

    return jsonify(claims_data)

@app.template_filter('format_jakarta_date')
def format_jakarta_date(value):
    jakarta = timezone('Asia/Jakarta')
    return value.astimezone(jakarta).strftime('%d-%m-%Y')

@app.template_filter('format_jakarta_time')
def format_jakarta_time(value):
    jakarta = timezone('Asia/Jakarta')
    return value.astimezone(jakarta).strftime('%H:%M')

def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

@app.route('/register')
def register_page():
    """Render the registration page"""
    return render_template('register.html')

@app.route('/register-admin', methods=['POST'])
def register_admin():
    """Register a new admin"""
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate inputs
    if not username or not password:
        flash('Username dan password harus diisi', 'error')
        return redirect(url_for('register_page'))
    
    if password != confirm_password:
        flash('Password dan konfirmasi password tidak cocok', 'error')
        return redirect(url_for('register_page'))
    
    if len(password) < 8:
        flash('Password harus minimal 8 karakter', 'error')
        return redirect(url_for('register_page'))
    
    # Load existing users
    users = load_users()
    
    # Check if username already exists
    if username in users:
        flash('Username sudah digunakan', 'error')
        return redirect(url_for('register_page'))
    
    # Add new user
    users[username] = password
    
    # Save users
    save_users(users)
    
    flash('Admin berhasil didaftarkan!', 'success')
    return redirect(url_for('register_page'))

# Update your login function to use the JSON file
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Load users from JSON file
    users = load_users()
        
    if username in users and users[username] == password:
        session['user_id'] = username
        return jsonify({"message": "Login successful"}), 200
        
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/employees/import', methods=['POST'])
def import_employees():
    if 'excel_file' not in request.files:
        return jsonify({'success': False, 'message': 'Tidak ada file yang diunggah'})
    
    file = request.files['excel_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Tidak ada file yang dipilih'})
    
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({'success': False, 'message': 'Format file tidak didukung'})
    
    try:
        # Read the Excel file
        df = pd.read_excel(file)
        
        # Check required columns
        if len(df.columns) < 2:
            return jsonify({'success': False, 'message': 'Format file tidak valid'})
        
        added = 0
        duplicates = 0
        errors = []
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Skip header row if it contains text instead of data
                if index == 0 and (isinstance(row[0], str) and ('ref' in row[0].lower() or 'nama' in row[0].lower())):
                    continue
                
                ref_id = str(row[0]).strip()
                name = str(row[1]).strip()
                
                # Validate data
                if not ref_id or not name:
                    errors.append(f"Baris {index+1}: Data tidak lengkap")
                    continue
                
                # Check if employee already exists
                if Employee.query.filter_by(ref_id=ref_id).first():
                    duplicates += 1
                    continue
                
                # Add new employee
                new_employee = Employee(ref_id=ref_id, name=name)
                db.session.add(new_employee)
                added += 1
                
            except Exception as e:
                errors.append(f"Baris {index+1}: {str(e)}")
        
        # Commit changes to database
        db.session.commit()
        
        # Log the import activity
        log_import_activity_after_commit(added, duplicates)
        
        return jsonify({
            'success': True,
            'added': added,
            'duplicates': duplicates,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error processing file: {str(e)}'})

# Helper function to log import activity
def log_import_activity_after_commit(added, duplicates):
    """Log import activity after successful commit"""
    try:
        # Get current user ID from session
        user_id = session.get('user_id', 'unknown')
        
        # Create a new activity log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': 'import_employees',
            'target_employee': 'Multiple Employees',
            'details': {
                'added': added,
                'duplicates': duplicates
            }
        }
        
        # Write to log file
        with open('activity_log.jsonl', 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')
            
        print(f"Logged import activity: {added} added, {duplicates} duplicates")
    except Exception as e:
        print(f"Error logging import activity: {e}")

# Add this route for logging import activity
@app.route('/log-import-activity', methods=['POST'])
def log_import_activity():
    try:
        data = request.get_json()
        added = data.get('added', 0)
        duplicates = data.get('duplicates', 0)
        
        # Get current user ID from session
        user_id = session.get('user_id', 'unknown')
        
        # Create a new activity log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': 'import_employees',
            'target_employee': 'Multiple Employees',
            'details': {
                'added': added,
                'duplicates': duplicates
            }
        }
        
        # Write to log file
        with open('activity_log.jsonl', 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')
        
        return jsonify({'success': True, 'message': 'Import activity logged'})
        
    except Exception as e:
        print(f"Error logging import activity: {e}")
        return jsonify({'success': False, 'message': str(e)})
    
def cleanup_old_sounds(days=7):
    try:
        custom_sounds_dir = os.path.join('static', 'sounds', 'custom')
        
        os.makedirs(custom_sounds_dir, exist_ok=True)
        
        now = datetime.now()
        
        sound_files = glob.glob(os.path.join(custom_sounds_dir, '*.mp3'))
        
        deleted_count = 0
        for file_path in sound_files:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if (now - file_mtime) > timedelta(days=days):
                os.remove(file_path)
                deleted_count += 1
                print(f"Deleted old sound file: {os.path.basename(file_path)}")
        
        print(f"Cleanup completed: {deleted_count} files deleted")
        return deleted_count
        
    except Exception as e:
        print(f"Error during sound file cleanup: {e}")
        return 0

@scheduler.scheduled_job(IntervalTrigger(days=1))
def scheduled_cleanup():
    print("Running scheduled sound file cleanup...")
    cleanup_old_sounds(7)
    

if __name__ == '__main__':
    # Create sounds directory if it doesn't exist
    os.makedirs(os.path.join('static', 'sounds'), exist_ok=True)
    app.run(host='0.0.0.0', port=5003, debug=True)