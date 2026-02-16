import os
import subprocess
import uuid
import yaml
import bcrypt
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

config = load_config()

UPLOAD_FOLDER = config['update']['upload_directory']
ALLOWED_EXTENSIONS = set(ext.strip() for ext in config['update']['supported_extensions'].split(','))
UPDATE_COMMAND = config['update']['update_command']
REBOOT_COMMAND = config['update']['reboot_command']
LOGIN_REQUIRED = config['security']['login_required']
USERNAME = config['security']['username']
PASSWORD_HASH = config['security']['password_hash'].encode('utf-8')
SERVER_PORT = config['server']['port']
SERVER_HOST = config['server']['host']

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
    if LOGIN_REQUIRED and not session.get('authenticated'):
        return render_template('index.html', login_required=True, supported_extensions=config['update']['supported_extensions'])
    return render_template('index.html', login_required=False, supported_extensions=config['update']['supported_extensions'])

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    if username == USERNAME and bcrypt.checkpw(password.encode('utf-8'), PASSWORD_HASH):
        session['authenticated'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    authenticated = not LOGIN_REQUIRED or session.get('authenticated', False)
    return jsonify({'authenticated': authenticated})

@app.route('/api/upload', methods=['POST'])
@login_required
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
    
    return jsonify({'success': True, 'filepath': filepath, 'filename': filename})

@app.route('/api/update', methods=['POST'])
@login_required
def run_update():
    data = request.get_json()
    filepath = data.get('filepath')
    
    if not filepath or not os.path.exists(filepath):
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
def reboot():
    try:
        subprocess.Popen(REBOOT_COMMAND, shell=True)
        return jsonify({'success': True, 'message': 'Reboot initiated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)
