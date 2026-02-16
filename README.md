# Open Device Updater

A simple web interface for updating embedded Linux devices using popular open source solutions such as RAUC, Mender, SWupdate, etc. Created with Python, Flask and Vue.js and Vuetify.

## Features

- Local-first: works without internet connection (all assets bundled)
- Optional password protection
- File extension validation
- Upload progress indicator
- Reboot confirmation

## Requirements

- Python
- Flask
- PyYAML
- Werkzeug

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml`:

| Setting | Description | Default |
|---------|-------------|---------|
| `server.port` | Web server port | 8000 |
| `server.host` | Web server bind address | 0.0.0.0 |
| `security.login_required` | Enable/disable password | true |
| `security.username` | Login username | admin |
| `security.password` | Login password | admin123 |
| `update.supported_extensions` | Allowed file extensions | .raucb,.mender,.swu |
| `update.upload_directory` | Upload directory | /tmp/updates |
| `update.update_command` | Update command (use `{filepath}`) | rauc install {filepath} |
| `update.reboot_command` | Reboot command | reboot |

## Usage

```bash
python app.py
```

Access via `http://<device-ip>:8000` from another computer on the LAN.

## Workflow

1. Open web page in browser
2. Login (if password enabled)
3. Select update file (for example .raucb)
4. Click "SELECT UPDATE FILE"
5. Click "UPLOAD & INSTALL"
7. Wait for update to complete
8. Confirm reboot when prompted

## Updating Static Assets

To upgrade Vue/Vuetify/MDI libraries:

```bash
./update_static.sh
```

Edit the script to change version numbers.
