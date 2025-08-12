# pip install Flask Flask-WTF

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory, flash
import json
import os
from werkzeug.utils import secure_filename
from flask_wtf import CSRFProtect
import re
import secrets

app = Flask(__name__)

app.secret_key = secrets.token_urlsafe(32)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max upload size
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.jpeg', '.png', '.gif', '.ico']

csrf = CSRFProtect(app)

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'content.json')
UPLOAD_FOLDER = os.path.join('static', 'img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper to load/save content

def load_content():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_content(data):
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in app.config['UPLOAD_EXTENSIONS']

def is_valid_email(email):
    return re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email)

def is_valid_price(price):
    return re.match(r'^\$?\d+(\.\d{2})?$', price)


print(load_content())
@app.route('/')
def index():
    content = load_content()
    return render_template('index.html', content=content)

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))
    content = load_content()
    return render_template('admin.html', content=content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            return render_template('login.html', error='Username and password required')
        if len(password) < 4:
            return render_template('login.html', error='Password must be at least 4 characters')
        if username == 'admin' and password == 'password':
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))











@app.route('/api/update', methods=['POST'])
def api_update():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json

    hero = data.get('hero', {})
    if not hero.get('title') or not hero.get('subtitle') or not hero.get('button_text'):
        return jsonify({'error': 'All hero section fields are required.'}), 400

    about = data.get('about', {})
    if not about.get('who') or not about.get('why'):
        return jsonify({'error': 'About section is required.'}), 400

    menu = data.get('menu', [])
    for drink in menu:
        if not drink.get('name') or not drink.get('description') or not drink.get('price'):
            return jsonify({'error': 'All menu fields are required.'}), 400
        if not is_valid_price(drink['price'].replace('$','')):
            return jsonify({'error': f"Invalid price for {drink['name']}"}), 400

    team = data.get('team', [])
    for member in team:
        if not member.get('name') or not member.get('bio'):
            return jsonify({'error': 'All team fields are required.'}), 400

    contact = data.get('contact', {})
    if not contact.get('address') or not contact.get('email') or not contact.get('phone'):
        return jsonify({'error': 'All contact fields are required.'}), 400
    if not is_valid_email(contact['email']):
        return jsonify({'error': 'Invalid email address.'}), 400

    if contact.get('map_lat') and contact.get('map_lng'):
        try:
            contact['map_lat'] = float(contact['map_lat'])
            contact['map_lng'] = float(contact['map_lng'])
        except Exception:
            return jsonify({'error': 'Invalid latitude or longitude.'}), 400

    google_maps_api_key = contact.get('google_maps_api_key', '')

    if 'google_maps_api_key' in contact:
        del contact['google_maps_api_key']

    footer = data.get('footer', {})
    if not footer.get('address') or not footer.get('city') or not footer.get('phone') or not footer.get('email'):
        return jsonify({'error': 'All footer fields are required.'}), 400
    if not is_valid_email(footer['email']):
        return jsonify({'error': 'Invalid footer email address.'}), 400

    content = load_content()
    content['hero'] = hero
    content['about'] = about
    content['menu'] = menu
    content['team'] = team
    content['contact'] = contact
    content['footer'] = footer
    if google_maps_api_key is not None:
        content['contact']['google_maps_api_key'] = google_maps_api_key
    save_content(content)
    return jsonify({'success': True})

@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return jsonify({'success': True, 'filename': filename})







@app.route('/api/upload_hero', methods=['POST'])
def upload_hero():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    if 'hero' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['hero']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    filename = 'hero_' + secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    content = load_content()
    content['hero']['image'] = filename
    save_content(content)
    return jsonify({'success': True, 'filename': filename})












@app.route('/api/delete_image', methods=['POST'])
def delete_image():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': 'Invalid filename'}), 400

    secured_filename = secure_filename(filename)
    if secured_filename != filename:
        return jsonify({'error': 'Invalid filename'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    upload_folder_abs = os.path.abspath(app.config['UPLOAD_FOLDER'])
    filepath_abs = os.path.abspath(filepath)
    
    if not filepath_abs.startswith(upload_folder_abs):
        return jsonify({'error': 'File not found or forbidden path'}), 400

    if os.path.exists(filepath_abs):
        os.remove(filepath_abs)
        
        content = load_content()
        if filename == content.get('logo'):
            content['logo'] = 'logo.png'
            save_content(content)
        elif filename == content.get('favicon'):
            content['favicon'] = 'favicon.ico'
            save_content(content)
        elif filename == content.get('hero', {}).get('image'):
            content['hero']['image'] = 'hero.jpg'
            save_content(content)
            
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/upload_logo', methods=['POST'])
def upload_logo():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    if 'logo' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['logo']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    filename = 'logo_' + secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    content = load_content()
    content['logo'] = filename
    save_content(content)
    return jsonify({'success': True, 'filename': filename})

@app.route('/api/upload_favicon', methods=['POST'])
def upload_favicon():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    if 'favicon' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['favicon']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    filename = 'favicon_' + secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    content = load_content()
    content['favicon'] = filename
    save_content(content)
    return jsonify({'success': True, 'filename': filename})

@app.route('/contact', methods=['POST'])
def contact_submit():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    message = request.form.get('message', '').strip()
    if not name or not email or not message:
        flash('All fields are required.', 'danger')
        return redirect(url_for('index') + '#contact')
    if not is_valid_email(email):
        flash('Invalid email address.', 'danger')
        return redirect(url_for('index') + '#contact')
    if len(message) < 10:
        flash('Message must be at least 10 characters.', 'danger')
        return redirect(url_for('index') + '#contact')
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('index') + '#contact')

if __name__ == '__main__':
    app.run(debug=True)
