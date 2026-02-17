import os
import subprocess
import uuid
import yaml
import bcrypt
import hmac
import time
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = uuid.uuid4().hex
    return session['csrf_token']

def csrf_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('csrf_token')
        request_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        if not token or not hmac.compare_digest(token, request_token or ''):
            return jsonify({'error': 'CSRF token missing or invalid'}), 403
        return f(*args, **kwargs)
    return decorated_function

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {config_path}")
        exit(1)
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse config file: {e}")
        exit(1)

def get_config_value(config, *keys, required=True):
    """Safely get a nested config value with helpful error messages."""
    current = config
    path = []
    for key in keys:
        path.append(key)
        if not isinstance(current, dict) or key not in current:
            if required:
                print(f"ERROR: Missing required config key: {'.'.join(path)}")
                print(f"  Expected path: {' -> '.join(str(k) for k in keys)}")
                print(f"  Please add this key to your config.yaml file.")
                exit(1)
            return None
        current = current[key]
    return current

config = load_config()

UPLOAD_FOLDER = get_config_value(config, 'update', 'upload_directory')
ALLOWED_EXTENSIONS = set(ext.strip() for ext in get_config_value(config, 'update', 'supported_extensions').split(','))
UPDATE_COMMAND = get_config_value(config, 'update', 'update_command')
REBOOT_COMMAND = get_config_value(config, 'update', 'reboot_command')
LOGIN_REQUIRED = get_config_value(config, 'security', 'login_required')
USERNAME = get_config_value(config, 'security', 'username')
PASSWORD_HASH = get_config_value(config, 'security', 'password_hash').encode('utf-8')
SERVER_PORT = get_config_value(config, 'server', 'port')
SERVER_HOST = get_config_value(config, 'server', 'host')
MAX_LOGIN_ATTEMPTS = get_config_value(config, 'security', 'max_login_attempts', required=False) or 3
LOGIN_TIMEOUT = get_config_value(config, 'security', 'login_timeout', required=False) or 60

failed_login_attempts = {}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not LOGIN_REQUIRED or session.get('authenticated'):
            return f(*args, **kwargs)
        return jsonify({'error': 'Authentication required'}), 401
    return decorated_function

def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = '.' + filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    csrf_token = get_csrf_token()
    if LOGIN_REQUIRED and not session.get('authenticated'):
        return render_template('index.html', login_required=True, supported_extensions=get_config_value(config, 'update', 'supported_extensions'), csrf_token=csrf_token)
    return render_template('index.html', login_required=False, supported_extensions=get_config_value(config, 'update', 'supported_extensions'), csrf_token=csrf_token)

@app.route('/api/login', methods=['POST'])
@csrf_required
def login():
    client_ip = request.remote_addr

    if client_ip in failed_login_attempts:
        attempts_data = failed_login_attempts[client_ip]
        if attempts_data['count'] >= MAX_LOGIN_ATTEMPTS:
            elapsed = time.time() - attempts_data['timestamp']
            if elapsed < LOGIN_TIMEOUT:
                remaining = int(LOGIN_TIMEOUT - elapsed)
                return jsonify({'error': f'Too many failed attempts. Try again in {remaining} seconds.'}), 429
            else:
                del failed_login_attempts[client_ip]

    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    if username == USERNAME and bcrypt.checkpw(password.encode('utf-8'), PASSWORD_HASH):
        if client_ip in failed_login_attempts:
            del failed_login_attempts[client_ip]
        session['authenticated'] = True
        return jsonify({'success': True})

    if client_ip not in failed_login_attempts:
        failed_login_attempts[client_ip] = {'count': 0, 'timestamp': time.time()}
    failed_login_attempts[client_ip]['count'] += 1
    failed_login_attempts[client_ip]['timestamp'] = time.time()

    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
@csrf_required
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    authenticated = not LOGIN_REQUIRED or session.get('authenticated', False)
    return jsonify({'authenticated': authenticated})

@app.route('/api/upload', methods=['POST'])
@login_required
@csrf_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file extension. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(filepath)
    
    return jsonify({'success': True, 'filename': unique_filename})

@app.route('/api/update', methods=['POST'])
@login_required
@csrf_required
def run_update():
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 400

    try:
        command = UPDATE_COMMAND.format(filepath=filepath)
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Update completed successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Update command failed',
                'error': result.stderr or result.stdout
            })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Update command timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reboot', methods=['POST'])
@login_required
@csrf_required
def reboot():
    try:
        subprocess.Popen(REBOOT_COMMAND, shell=True)
        return jsonify({'success': True, 'message': 'Reboot initiated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)
