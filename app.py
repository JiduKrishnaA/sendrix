from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import random
import uuid
import re

def is_password_strong(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit."
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Password must contain at least one special character."
    return True, ""

def get_db():
    conn = sqlite3.connect('users.db', timeout=20)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Admin credentials — change this password!
ADMIN_PASSWORD = "sendrix_admin_2026"

# Config
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ====================== DATABASE ======================
def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY, 
                    username TEXT UNIQUE, 
                    password TEXT)''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except sqlite3.OperationalError:
        pass
    c.execute('''CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY,
                    filename TEXT,
                    uploader TEXT,
                    recipient TEXT,
                    status TEXT DEFAULT 'pending',
                    timestamp TEXT,
                    uploader_cleared INTEGER DEFAULT 0,
                    recipient_cleared INTEGER DEFAULT 0,
                    is_destruct INTEGER DEFAULT 0,
                    vault_pin TEXT DEFAULT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clipboard (
                    code TEXT PRIMARY KEY,
                    text_content TEXT,
                    uploader TEXT,
                    timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hub (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    uploader TEXT,
                    timestamp TEXT,
                    downloads INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

class User(UserMixin):
    def __init__(self, id, username, name=None):
        self.id = id
        self.username = username
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, name FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return User(user[0], user[1], user[2]) if user else None

# ====================== ROUTES ======================
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form.get('name', '').strip() or None
        
        is_strong, msg = is_password_strong(password)
        if not is_strong:
            flash(msg)
            return render_template('register.html')
            
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, name) VALUES (?, ?, ?)", (username, password, name))
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
        except:
            flash("Username already exists!")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, name FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            login_user(User(user[0], user[1], user[2]))
            return redirect(url_for('dashboard'))
        flash("Invalid credentials!")
    return render_template('login.html')

def get_dashboard_data():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM files WHERE uploader=? AND status='pending'", (current_user.username,))
    my_uploads = c.fetchall()
    c.execute("""
        SELECT * FROM files 
        WHERE recipient=? 
        AND (
            status='pending' 
            OR (status='accept' AND id = (SELECT MAX(id) FROM files WHERE recipient=?))
        )
    """, (current_user.username, current_user.username))
    received = c.fetchall()
    conn.close()
    return my_uploads, received

@app.route('/dashboard')
@login_required
def dashboard():
    my_uploads, received = get_dashboard_data()
    return render_template('dashboard.html', my_uploads=my_uploads, received=received, username=current_user.username, name=current_user.name)

@app.route('/api/dashboard')
@login_required
def api_dashboard():
    my_uploads, received = get_dashboard_data()
    return render_template('dashboard_tables.html', my_uploads=my_uploads, received=received)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        files = request.files.getlist('file')
        recipient = request.form['recipient']
        
        if not files or files[0].filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if files and files[0].filename != '':
            is_destruct = 1 if request.form.get('is_destruct') else 0
            
            if len(files) == 1:
                # Single file
                file = files[0]
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
            else:
                # Multiple files / Folder: zip them
                import zipfile
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"Package_{current_user.username}_{timestamp_str}.zip"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in files:
                        if file.filename:
                            safe_name = secure_filename(file.filename)
                            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4().hex}_{safe_name}")
                            file.save(temp_path)
                            zipf.write(temp_path, arcname=safe_name)
                            os.remove(temp_path)
            
            vault_pin = request.form.get('vault_pin', '').strip() or None
            
            conn = get_db()
            c = conn.cursor()
            c.execute("""INSERT INTO files 
                        (filename, uploader, recipient, timestamp, is_destruct, vault_pin) 
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (filename, current_user.username, recipient, datetime.now().strftime("%Y-%m-%d %H:%M"), is_destruct, vault_pin))
            conn.commit()
            conn.close()
            
            flash(f'File uploaded and sent to {recipient}')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from flask import jsonify
                return jsonify({"status": "success"})
                
            return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username != ?", (current_user.username,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('upload.html', users=users)

@app.route('/action/<int:file_id>/<action>')
@login_required
def file_action(file_id, action):
    conn = get_db()
    c = conn.cursor()
    if action in ['accept', 'reject']:
        c.execute("UPDATE files SET status=? WHERE id=?", (action, file_id))
        conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/cancel_upload/<int:file_id>')
@login_required
def cancel_upload(file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT filename, uploader, status FROM files WHERE id=?", (file_id,))
    file = c.fetchone()
    
    if file and file[1] == current_user.username and file[2] == 'pending':
        filename = file[0]
        c.execute("DELETE FROM files WHERE id=?", (file_id,))
        conn.commit()
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            
        flash("Sending cancelled successfully.")
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete_inbox/<int:file_id>')
@login_required
def delete_inbox(file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT filename, recipient, uploader_cleared FROM files WHERE id=?", (file_id,))
    file = c.fetchone()
    
    if file and file[1] == current_user.username:
        # Mark as cleared by recipient and change status so it disappears from inbox
        c.execute("UPDATE files SET recipient_cleared=1, status='cleared' WHERE id=?", (file_id,))
        conn.commit()
        
        # If uploader also cleared it, we can safely delete from disk and db
        if file[2] == 1:
            c.execute("DELETE FROM files WHERE id=?", (file_id,))
            conn.commit()
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file[0])
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                
        flash("File cleared from inbox.")
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/history')
@login_required
def history():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM files WHERE uploader=? AND status!='pending' AND uploader_cleared=0", (current_user.username,))
    my_history = c.fetchall()
    
    c.execute("""
        SELECT * FROM files 
        WHERE recipient=? 
        AND recipient_cleared=0 
        AND (
            status='reject' 
            OR (status='accept' AND id != (SELECT COALESCE(MAX(id), 0) FROM files WHERE recipient=?))
        )
    """, (current_user.username, current_user.username))
    received_history = c.fetchall()
    
    conn.close()
    return render_template('history.html', my_history=my_history, received_history=received_history, username=current_user.username)

@app.route('/clear_history')
@login_required
def clear_history():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("UPDATE files SET uploader_cleared=1 WHERE uploader=? AND status!='pending'", (current_user.username,))
    c.execute("UPDATE files SET recipient_cleared=1 WHERE recipient=? AND status!='pending'", (current_user.username,))
    
    # Delete physical files for rows that will be deleted
    c.execute("SELECT filename FROM files WHERE uploader_cleared=1 AND recipient_cleared=1")
    orphans = c.fetchall()
    for row in orphans:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
                
    c.execute("DELETE FROM files WHERE uploader_cleared=1 AND recipient_cleared=1")
    
    conn.commit()
    conn.close()
    flash("History cleared successfully!")
    return redirect(url_for('history'))

@app.route('/clipboard')
@login_required
def clipboard():
    generated_code = request.args.get('code')
    return render_template('clipboard.html', username=current_user.username, generated_code=generated_code)

@app.route('/api/clipboard/create', methods=['POST'])
@login_required
def api_clipboard_create():
    text_content = request.form.get('text_content')
    if not text_content:
        flash("Text content cannot be empty.")
        return redirect(url_for('clipboard'))
        
    conn = get_db()
    c = conn.cursor()
    
    # Cleanup clipboards older than 24 hours to prevent code exhaustion
    one_day_ago = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    c.execute("DELETE FROM clipboard WHERE timestamp < ?", (one_day_ago,))
    conn.commit()
    
    while True:
        code = str(random.randint(1000, 9999))
        c.execute("SELECT code FROM clipboard WHERE code=?", (code,))
        if not c.fetchone():
            break
            
    c.execute("INSERT INTO clipboard (code, text_content, uploader, timestamp) VALUES (?, ?, ?, ?)",
             (code, text_content, current_user.username, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    
    flash("Text shared successfully!")
    return redirect(url_for('clipboard', code=code))

@app.route('/api/clipboard/retrieve', methods=['POST'])
@login_required
def api_clipboard_retrieve():
    code = request.form.get('code')
    if not code:
        flash("Please enter a code.")
        return redirect(url_for('clipboard'))
        
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT text_content FROM clipboard WHERE code=?", (code,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return render_template('clipboard.html', username=current_user.username, retrieved_text=result[0])
    else:
        flash("Invalid code or text no longer exists.")
        return redirect(url_for('clipboard'))

@app.route('/clipboard/<code>')
def quick_retrieve(code):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT text_content FROM clipboard WHERE code=?", (code,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return render_template('quick_retrieve.html', retrieved_text=result[0])
    else:
        return "Invalid or expired QR code link."

@app.route('/download/<filename>')
@login_required
def download(filename):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, is_destruct, vault_pin, status FROM files WHERE filename=? AND recipient=? ORDER BY id DESC LIMIT 1", (filename, current_user.username))
    file_record = c.fetchone()
    
    if not file_record:
        conn.close()
        flash("File not found or access denied.")
        return redirect(url_for('dashboard'))
        
    file_id = file_record[0]
    is_destruct = file_record[1]
    vault_pin = file_record[2]
    status = file_record[3]
    
    if status != 'accept':
        conn.close()
        flash("You must accept the file before downloading.")
        return redirect(url_for('dashboard'))
        
    if vault_pin and not session.get(f'unlocked_{file_id}'):
        conn.close()
        return redirect(url_for('vault', file_id=file_id))
    
    if is_destruct == 1:
        c.execute("UPDATE files SET status='destroyed' WHERE id=?", (file_id,))
        conn.commit()
    conn.close()
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_name = request.form.get('name', '').strip() or None
        new_username = request.form.get('username', '').strip()
        new_password = request.form.get('password', '').strip()
        
        if not new_username:
            flash("Username cannot be empty.")
            return redirect(url_for('profile'))
            
        conn = get_db()
        c = conn.cursor()
        
        # Check if username is changed and if the new username already exists
        if new_username != current_user.username:
            c.execute("SELECT id FROM users WHERE username=?", (new_username,))
            if c.fetchone():
                conn.close()
                flash("Username already exists.")
                return redirect(url_for('profile'))
                
            # Perform cascading updates on username references
            old_username = current_user.username
            c.execute("UPDATE files SET uploader=? WHERE uploader=?", (new_username, old_username))
            c.execute("UPDATE files SET recipient=? WHERE recipient=?", (new_username, old_username))
            c.execute("UPDATE hub SET uploader=? WHERE uploader=?", (new_username, old_username))
            c.execute("UPDATE clipboard SET uploader=? WHERE uploader=?", (new_username, old_username))
        
        # Update user record
        if new_password:
            is_strong, msg = is_password_strong(new_password)
            if not is_strong:
                flash(msg)
                return redirect(url_for('profile'))
            c.execute("UPDATE users SET name=?, username=?, password=? WHERE id=?", (new_name, new_username, new_password, current_user.id))
        else:
            c.execute("UPDATE users SET name=?, username=? WHERE id=?", (new_name, new_username, current_user.id))
            
        conn.commit()
        conn.close()
        
        # Re-login or update the session/current_user
        current_user.name = new_name
        current_user.username = new_username
        
        flash("Profile updated successfully!")
        return redirect(url_for('dashboard'))
        
    return render_template('profile.html', username=current_user.username, name=current_user.name)

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    username = current_user.username
    user_id = current_user.id
    
    conn = get_db()
    c = conn.cursor()
    
    # 1. Fetch all physical files uploaded by this user to delete them from disk
    c.execute("SELECT filename FROM files WHERE uploader=?", (username,))
    user_files = [row[0] for row in c.fetchall()]
    
    # Also fetch files they shared in the hub
    c.execute("SELECT filename FROM hub WHERE uploader=?", (username,))
    user_hub_files = [row[0] for row in c.fetchall()]
    
    all_filenames = set(user_files + user_hub_files)
    
    # Delete from disk
    for fname in all_filenames:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
                
    # 2. Delete all records from tables
    c.execute("DELETE FROM files WHERE uploader=? OR recipient=?", (username, username))
    c.execute("DELETE FROM hub WHERE uploader=?", (username,))
    c.execute("DELETE FROM clipboard WHERE uploader=?", (username,))
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    
    conn.commit()
    conn.close()
    
    # 3. Logout the user and redirect to registration/login
    logout_user()
    flash("Your account and all associated data have been permanently deleted.")
    return redirect(url_for('register'))

# ====================== VAULT ROUTES ======================
@app.route('/vault/<int:file_id>')
@login_required
def vault(file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, filename, vault_pin FROM files WHERE id=? AND recipient=?", (file_id, current_user.username))
    file_record = c.fetchone()
    conn.close()
    
    if not file_record:
        flash("File not found or access denied.")
        return redirect(url_for('dashboard'))
    
    if not file_record[2]:
        # No PIN set — just download directly
        return redirect(url_for('download', filename=file_record[1]))
    
    return render_template('vault.html', file_id=file_id, username=current_user.username)

@app.route('/vault/<int:file_id>/unlock', methods=['POST'])
@login_required
def vault_unlock(file_id):
    entered_pin = request.form.get('pin', '').strip()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT filename, vault_pin, is_destruct FROM files WHERE id=? AND recipient=?", (file_id, current_user.username))
    file_record = c.fetchone()
    conn.close()
    
    if not file_record:
        flash("File not found or access denied.")
        return redirect(url_for('dashboard'))
    
    if file_record[1] and entered_pin == file_record[1]:
        # Correct PIN — proceed to download
        session[f'unlocked_{file_id}'] = True
        return redirect(url_for('download', filename=file_record[0]))
    else:
        flash("Incorrect PIN. Access denied.")
        return redirect(url_for('vault', file_id=file_id))

# ====================== HUB ROUTES ======================
@app.route('/hub')
@login_required
def hub():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM hub ORDER BY id DESC")
    hub_files = c.fetchall()
    conn.close()
    return render_template('hub.html', hub_files=hub_files, username=current_user.username)

@app.route('/hub/upload', methods=['POST'])
@login_required
def hub_upload():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('hub'))
    
    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        flash('No file selected')
        return redirect(url_for('hub'))
    
    if len(files) == 1:
        file = files[0]
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
    else:
        import zipfile
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"HubPackage_{current_user.username}_{timestamp_str}.zip"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                if file.filename:
                    safe_name = secure_filename(file.filename)
                    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"hub_temp_{uuid.uuid4().hex}_{safe_name}")
                    file.save(temp_path)
                    zipf.write(temp_path, arcname=safe_name)
                    os.remove(temp_path)
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO hub (filename, uploader, timestamp) VALUES (?, ?, ?)",
             (filename, current_user.username, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    flash(f'File broadcast to the Network Hub!')
    return redirect(url_for('hub'))

@app.route('/hub/download/<int:file_id>')
@login_required
def hub_download(file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT filename FROM hub WHERE id=?", (file_id,))
    result = c.fetchone()
    if result:
        c.execute("UPDATE hub SET downloads = downloads + 1 WHERE id=?", (file_id,))
        conn.commit()
    conn.close()
    if result:
        return send_from_directory(app.config['UPLOAD_FOLDER'], result[0])
    flash("File not found in hub.")
    return redirect(url_for('hub'))

@app.route('/hub/delete/<int:file_id>')
@login_required
def hub_delete(file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT filename, uploader FROM hub WHERE id=?", (file_id,))
    result = c.fetchone()
    if result and result[1] == current_user.username:
        c.execute("DELETE FROM hub WHERE id=?", (file_id,))
        conn.commit()
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], result[0])
        if os.path.exists(filepath):
            os.remove(filepath)
        flash("File removed from hub.")
    conn.close()
    return redirect(url_for('hub'))

# ====================== EASTER EGG: EMOJI ALCHEMY ======================

# Fallback combo lookup (used when GEMINI_API_KEY is not set)
EMOJI_FALLBACK = {
    # User requested combos
    ("🪵", "🔥"): ("💨", "Smoke", "Wood burns to create smoke"),
    ("🤴", "🐟"): ("🎣", "Kingfisher", "A royal fisher of the waters"),
    ("🦇", "👦"): ("🏏", "Batsman", "Bat plus boy equals cricket hero"),
    ("🦶", "⚽"): ("🏈", "Football", "Foot meets ball in sport"),
    # Nature
    ("🌊", "🔥"): ("💨", "Steam", "Water meets fire creates steam"),
    ("🌱", "💧"): ("🌿", "Plant", "Water and seed grow a plant"),
    ("🌱", "🔥"): ("🍂", "Ash", "Fire turns seedling to ash"),
    ("🌍", "💧"): ("🌊", "Ocean", "Earth covered in water"),
    ("🌍", "🔥"): ("🌋", "Volcano", "Fire within the earth"),
    ("🌍", "💨"): ("🌪️", "Tornado", "Wind across the earth"),
    ("❄️", "🔥"): ("💧", "Water", "Ice melted by fire"),
    ("❄️", "💧"): ("🧊", "Ice", "Cold water becomes ice"),
    ("☀️", "🌧️"): ("🌈", "Rainbow", "Sun after rain"),
    ("🌙", "⭐"): ("🌌", "Galaxy", "Moon and stars form a galaxy"),
    ("🌊", "🌙"): ("🌊", "Tide", "Moon controls the tides"),
    # Animals
    ("🦁", "🐯"): ("🐆", "Leopard", "Lion and tiger combine spots"),
    ("🐺", "🌙"): ("🐺", "Werewolf", "Wolf under moonlight transforms"),
    ("🐟", "🌊"): ("🐬", "Dolphin", "Fish masters the ocean"),
    ("🦅", "⭐"): ("🦸", "Hero", "Eagle eyes meet star power"),
    ("🐝", "🌸"): ("🍯", "Honey", "Bee collects pollen for honey"),
    ("🐛", "🍃"): ("🦋", "Butterfly", "Caterpillar eats leaf, transforms"),
    ("🐊", "👑"): ("🦖", "Dinosaur King", "Croc crowned as ancient ruler"),
    # Food & Drink
    ("🍎", "🔥"): ("🥧", "Apple Pie", "Baked apple becomes pie"),
    ("☕", "🥛"): ("🧋", "Latte", "Coffee meets milk"),
    ("🍋", "💧"): ("🥤", "Lemonade", "Lemon juice with water"),
    ("🌾", "💧"): ("🍺", "Beer", "Grain and water fermented"),
    ("🍇", "💧"): ("🍷", "Wine", "Grapes and water aged to wine"),
    ("🥚", "🔥"): ("🍳", "Fried Egg", "Egg on fire becomes breakfast"),
    ("🧁", "👑"): ("🎂", "Birthday Cake", "A cupcake fit for royalty"),
    # Objects & Tech
    ("⚡", "💧"): ("🔌", "Electric", "Power from water and lightning"),
    ("🔥", "💨"): ("🕯️", "Candle", "Fire and air make a candle"),
    ("📱", "💡"): ("💻", "Computer", "Phone plus ideas equal laptop"),
    ("📚", "🔥"): ("🧠", "Knowledge", "Books fuel the mind"),
    ("🔑", "🏠"): ("🏡", "Home", "Key unlocks a house into home"),
    ("⚙️", "❤️"): ("🤖", "Robot Heart", "Machine with a soul"),
    ("💎", "🔥"): ("✨", "Spark", "Diamond refracts fire to sparkle"),
    ("🎵", "❤️"): ("🎶", "Love Song", "Music from the heart"),
    # People & Magic
    ("👨", "🔬"): ("🧑‍🔬", "Scientist", "Man plus lab becomes scientist"),
    ("👸", "🐸"): ("💋", "Kiss", "Princess kisses the frog"),
    ("🧙", "📚"): ("🔮", "Oracle", "Wizard reads ancient books"),
    ("👶", "⏳"): ("🧒", "Child", "Baby grows with time"),
    ("💀", "🌹"): ("🌹", "Memento", "Death and beauty intertwine"),
    ("🧑", "🚀"): ("👨‍🚀", "Astronaut", "Human reaching for the stars"),
    # Places
    ("🏝️", "🌴"): ("🌺", "Tropical Paradise", "Island with palm trees blooms"),
    ("🏔️", "❄️"): ("🎿", "Ski Resort", "Mountain covered in snow"),
    ("🌆", "🌙"): ("🌃", "Night City", "City under the moonlight"),
    ("🏛️", "⏳"): ("🗿", "Ancient Ruins", "Old building eroded by time"),
}

def _normalize_emoji_key(e1, e2):
    """Try both orderings of a combo key."""
    return (e1, e2) if (e1, e2) in EMOJI_FALLBACK else ((e2, e1) if (e2, e1) in EMOJI_FALLBACK else None)

@app.route('/api/emoji-alchemy', methods=['POST'])
@login_required
def api_emoji_alchemy():
    from flask import jsonify
    data = request.get_json(silent=True) or {}
    emoji1 = (data.get('emoji1') or '').strip()
    emoji2 = (data.get('emoji2') or '').strip()

    if not emoji1 or not emoji2:
        return jsonify({'error': 'Two emojis required'}), 400

    # Try Gemini AI first
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = (
                f"You are an emoji alchemist. A user is combining {emoji1} and {emoji2}. "
                f"Determine a creative, fun result emoji that represents the combination. "
                f"Respond with ONLY valid JSON, no markdown, no code block, exactly: "
                f'{{\"result\": \"<single emoji>\", \"name\": \"<result name>\", \"description\": \"<one short sentence>\"}}'
            )
            resp = model.generate_content(prompt)
            import json
            text = resp.text.strip().strip('`').strip()
            if text.startswith('json'):
                text = text[4:].strip()
            result_data = json.loads(text)
            return jsonify(result_data)
        except Exception as e:
            pass  # Fall through to lookup table

    # Fallback: lookup table
    key = _normalize_emoji_key(emoji1, emoji2)
    if key:
        r, n, d = EMOJI_FALLBACK[key]
        return jsonify({'result': r, 'name': n, 'description': d})

    # Generic creative fallback based on category hints
    generic_results = [
        ("✨", "Magic Fusion", "Two emojis combine into pure magic"),
        ("🌟", "Star Combo", "A brilliant new combination!"),
        ("💥", "Explosion", "These two make quite the reaction"),
        ("🎉", "Celebration", "A surprising and joyful combination"),
        ("🔮", "Mystery", "An alchemical mystery unfolds"),
    ]
    import hashlib
    h = int(hashlib.md5((emoji1 + emoji2).encode()).hexdigest(), 16) % len(generic_results)
    r, n, d = generic_results[h]
    return jsonify({'result': r, 'name': n, 'description': d})


# ====================== ADMIN ROUTES ======================
def admin_required(f):
    """Decorator that ensures the admin is logged in via session."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Admin access required.")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def get_file_size_str(size_bytes):
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Incorrect admin password.")
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    upload_dir = app.config['UPLOAD_FOLDER']
    
    # Fetch all DB-tracked filenames and their metadata
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT filename, uploader, recipient, status FROM files")
    db_files = {row[0]: {'uploader': row[1], 'recipient': row[2], 'status': row[3]} for row in c.fetchall()}
    conn.close()
    
    db_file_count = len(db_files)
    files = []
    total_bytes = 0
    orphan_count = 0

    if os.path.exists(upload_dir):
        for fname in sorted(os.listdir(upload_dir)):
            fpath = os.path.join(upload_dir, fname)
            if os.path.isfile(fpath):
                size_bytes = os.path.getsize(fpath)
                total_bytes += size_bytes
                modified = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M")
                db_info = db_files.get(fname)
                is_orphan = db_info is None
                if is_orphan:
                    orphan_count += 1
                files.append({
                    'name': fname,
                    'size': get_file_size_str(size_bytes),
                    'modified': modified,
                    'uploader': db_info['uploader'] if db_info else None,
                    'recipient': db_info['recipient'] if db_info else None,
                    'status': db_info['status'] if db_info else None,
                    'is_orphan': is_orphan,
                })

    # Fetch all users
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, name, password FROM users")
    users = [{'id': row[0], 'username': row[1], 'name': row[2], 'password': row[3]} for row in c.fetchall()]
    conn.close()

    return render_template('admin_dashboard.html',
        files=files,
        total_files=len(files),
        total_size=get_file_size_str(total_bytes),
        orphan_count=orphan_count,
        db_file_count=db_file_count,
        users=users,
    )

@app.route('/admin/edit-user/<int:user_id>', methods=['POST'])
@admin_required
def admin_edit_user(user_id):
    new_name = request.form.get('name', '').strip() or None
    new_username = request.form.get('username', '').strip()
    new_password = request.form.get('password', '').strip()
    
    if not new_username:
        flash("Username cannot be empty.")
        return redirect(url_for('admin_dashboard'))
        
    conn = get_db()
    c = conn.cursor()
    
    # Check if username is changed and if the new username already exists for another user
    c.execute("SELECT username FROM users WHERE id=?", (user_id,))
    user_record = c.fetchone()
    if not user_record:
        conn.close()
        flash("User not found.")
        return redirect(url_for('admin_dashboard'))
        
    old_username = user_record[0]
    
    if new_username != old_username:
        c.execute("SELECT id FROM users WHERE username=? AND id!=?", (new_username, user_id))
        if c.fetchone():
            conn.close()
            flash("Username already exists.")
            return redirect(url_for('admin_dashboard'))
            
        # Perform cascading updates on username references
        c.execute("UPDATE files SET uploader=? WHERE uploader=?", (new_username, old_username))
        c.execute("UPDATE files SET recipient=? WHERE recipient=?", (new_username, old_username))
        c.execute("UPDATE hub SET uploader=? WHERE uploader=?", (new_username, old_username))
        c.execute("UPDATE clipboard SET uploader=? WHERE uploader=?", (new_username, old_username))
        
    # Validate password if changed
    if new_password:
        is_strong, msg = is_password_strong(new_password)
        if not is_strong:
            conn.close()
            flash(f"Error updating user: {msg}")
            return redirect(url_for('admin_dashboard'))
        c.execute("UPDATE users SET name=?, username=?, password=? WHERE id=?", (new_name, new_username, new_password, user_id))
    else:
        c.execute("UPDATE users SET name=?, username=? WHERE id=?", (new_name, new_username, user_id))
        
    conn.commit()
    conn.close()
    flash("User credentials updated successfully!")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        flash("User not found.")
        return redirect(url_for('admin_dashboard'))
        
    username = row[0]
    
    # Delete physical files uploaded by this user
    c.execute("SELECT filename FROM files WHERE uploader=?", (username,))
    user_files = [r[0] for r in c.fetchall()]
    c.execute("SELECT filename FROM hub WHERE uploader=?", (username,))
    user_hub_files = [r[0] for r in c.fetchall()]
    all_filenames = set(user_files + user_hub_files)
    
    for fname in all_filenames:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
                
    # Delete DB records cascadingly
    c.execute("DELETE FROM files WHERE uploader=? OR recipient=?", (username, username))
    c.execute("DELETE FROM hub WHERE uploader=?", (username,))
    c.execute("DELETE FROM clipboard WHERE uploader=?", (username,))
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    
    conn.commit()
    conn.close()
    flash(f"Permanently deleted user '{username}' and all associated files/data.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<path:filename>', methods=['POST'])
@admin_required
def admin_delete_file(filename):
    safe = secure_filename(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        os.remove(filepath)
        # Also remove the DB record if it exists
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM files WHERE filename=?", (safe,))
        c.execute("DELETE FROM hub WHERE filename=?", (safe,))
        conn.commit()
        conn.close()
        flash(f"Deleted: {safe}")
    else:
        flash(f"File not found: {safe}")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-all-orphans', methods=['POST'])
@admin_required
def admin_delete_all():
    upload_dir = app.config['UPLOAD_FOLDER']
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT filename FROM files")
    db_files = {row[0] for row in c.fetchall()}
    c.execute("SELECT filename FROM hub")
    db_files |= {row[0] for row in c.fetchall()}
    conn.close()

    deleted = 0
    if os.path.exists(upload_dir):
        for fname in os.listdir(upload_dir):
            fpath = os.path.join(upload_dir, fname)
            if os.path.isfile(fpath) and fname not in db_files:
                try:
                    os.remove(fpath)
                    deleted += 1
                except OSError:
                    pass

    flash(f"Deleted {deleted} orphaned file(s).")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-all-files', methods=['POST'])
@admin_required
def admin_delete_all_files():
    upload_dir = app.config['UPLOAD_FOLDER']
    deleted = 0

    if os.path.exists(upload_dir):
        for fname in os.listdir(upload_dir):
            fpath = os.path.join(upload_dir, fname)
            if os.path.isfile(fpath):
                try:
                    os.remove(fpath)
                    deleted += 1
                except OSError:
                    pass

    # Wipe all file and hub records from the database
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM files")
    c.execute("DELETE FROM hub")
    conn.commit()
    conn.close()

    flash(f"☢️ Purged {deleted} file(s) from uploads and cleared all database records.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/preview/<path:filename>')
@admin_required
def admin_preview_file(filename):
    """Serve the file inline (no download) for browser-renderable types."""
    from flask import send_from_directory
    safe = secure_filename(filename)
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        safe,
        as_attachment=False
    )

@app.route('/admin/preview-content/<path:filename>')
@admin_required
def admin_preview_content(filename):
    """Return raw text content for text/code files, or zip listing for zip files."""
    from flask import jsonify
    import zipfile
    safe = secure_filename(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe)

    if not os.path.isfile(filepath):
        return jsonify({'error': 'File not found'}), 404

    ext = safe.rsplit('.', 1)[-1].lower() if '.' in safe else ''

    if ext == 'zip':
        try:
            with zipfile.ZipFile(filepath, 'r') as z:
                entries = []
                for info in z.infolist():
                    entries.append({
                        'name': info.filename,
                        'size': info.file_size,
                        'compressed': info.compress_size,
                        'is_dir': info.filename.endswith('/')
                    })
            return jsonify({'type': 'zip', 'entries': entries, 'count': len(entries)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    text_exts = {
        'txt', 'md', 'csv', 'json', 'xml', 'html', 'htm',
        'js', 'css', 'py', 'sh', 'bat', 'yaml', 'yml',
        'ini', 'cfg', 'log', 'sql', 'ts', 'c', 'cpp', 'h', 'java'
    }
    if ext in text_exts:
        try:
            size = os.path.getsize(filepath)
            if size > 512 * 1024:  # cap at 512 KB to avoid huge reads
                return jsonify({'type': 'text', 'content': '[File too large to preview — over 512 KB]'})
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return jsonify({'type': 'text', 'content': content, 'ext': ext})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'type': 'unsupported'})

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash("Logged out of admin panel.")
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    # Initialize DB
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clipboard 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, text_content TEXT, uploader TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()
    
    print("Server starting... Access from other devices using your local IP")
    print("Example: http://192.168.1.XXX:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)