import io
import json
import os
import threading
import time
from os.path import splitext

from pydub import AudioSegment

from lib.logging_handler import CustomLogger
from flask import Flask, request, session, redirect, url_for, render_template, flash, jsonify

from lib.tone_detection_handler import ToneDetection
from lib.tone_extraction_handler import ToneExtraction

log_level = 1

app_name = "tr_tone_detection"
config_data = {}
detector_data = {}
detector_list = []
root_path = os.getcwd()
config_file = 'etc/config.json'
detector_file = 'etc/detectors.json'
log_path = os.path.join(root_path, 'log')
log_file_name = f"{app_name}.log"
config_path = os.path.join(root_path, config_file)
detector_path = os.path.join(root_path, detector_file)

if not os.path.exists(log_path):
    os.makedirs(log_path)


def load_configuration():
    global config_data
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        f.close()

    except FileNotFoundError:
        logger.error(f'Configuration file {config_file} not found.')
        return {'success': False,
                'alert': {'type': 'danger', 'message': f'Configuration file {config_file} not found.'}}
    except json.JSONDecodeError:
        logger.error(f'Configuration file {config_file} is not in valid JSON format.')
        return {'success': False, 'alert': {'type': 'danger',
                                            'message': f'Configuration file {config_file} is not in valid JSON format.'}}
    else:
        logger.info(f'Successfully loaded configuration from {config_file}')
        return {'success': True,
                'alert': {'type': 'danger', 'message': f'Successfully loaded configuration from {config_file}'},
                'config_data': config_data}


def load_detectors():
    global detector_data

    try:
        with open(detector_path, 'r') as f:
            detector_data = json.load(f)
        f.close()

    except FileNotFoundError:
        logger.error(f'Detector configuration file {detector_file} not found.')
        return {'success': False,
                'alert': {'type': 'danger', 'message': f'Detector configuration file {detector_file} not found.'}}
    except json.JSONDecodeError:
        logger.error(f'Detector configuration file {detector_file} is not in valid JSON format.')
        return {'success': False, 'alert': {'type': 'danger',
                                            'message': f'Detector configuration file {detector_file} is not in valid JSON format.'}}
    else:
        logger.info(f'Successfully loaded detector configuration from {detector_file}')
        return {'success': True,
                'alert': {'type': 'danger',
                          'message': f'Successfully loaded detector configuration from {detector_file}'},
                'detector_data': detector_data}


logger = CustomLogger(log_level, f'{app_name}', os.path.abspath(os.path.join(log_path, log_file_name))).logger
config_loaded = load_configuration()
detector_loaded = load_detectors()

if not config_loaded.get("success", False):
    exit(1)

if not detector_loaded.get("success", False):
    exit(1)

app = Flask(__name__)

try:
    with open('etc/secret_key.txt', 'rb') as f:
        app.config['SECRET_KEY'] = f.read()
except FileNotFoundError:
    secret_key = os.urandom(24)
    with open('etc/secret_key.txt', 'wb') as f:
        f.write(secret_key)
    app.config['SECRET_KEY'] = secret_key

# tell Flask to serve static files from the "static" directory
app.static_folder = 'static'


# Loop to run that clears old detections.
def clear_old_items():
    global detector_list
    while True:
        time.sleep(1)  # wait for 60 seconds
        current_time = time.time()
        detector_list = [(timestamp, timeout, id) for timestamp, timeout, id in detector_list if
                         current_time - timestamp <= int(timeout)]
        print(detector_list)



@app.route('/', methods=['GET'])
def index():
    return render_template("index.html", config_data=config_data)


@app.route('/tone_detect', methods=['POST'])
def tone_upload():
    global detector_list
    if request.method == "POST":
        start = time.time()
        file = request.files.get('file')
        if not file:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        allowed_extensions = ['.mp3', '.wav', '.m4a']
        ext = splitext(file.filename)[1]
        if ext not in allowed_extensions:
            return jsonify({"status": "error", "message": "File must be an MP3, WAV or M4A"}), 400

        file_data = file.read()

        audio = AudioSegment.from_file(io.BytesIO(file_data))

        try:
            extracted_quick_call, hi_low_tones, long_tones, dtmf_tones = ToneExtraction(config_data, audio).main()
        except Exception as e:
            return jsonify({"status": "error", "message": f"Exception while extracting tones. {e}"}), 500

        # Check Detectors for matches in quick_call tones.
        qc_result = ToneDetection(config_data, detector_data, detector_list).detect_quick_call(extracted_quick_call)
        detector_list = qc_result

        return jsonify(detector_list), 200
    else:
        return 200


@app.route('/save_config', methods=['POST'])
def save_config():
    global config_data
    try:
        form_data = request.form
        print(form_data)
        new_value = form_data.get('test')
        config_data['general']['test'] = int(new_value)
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)

        reload_config = load_configuration()
        if reload_config:
            reload_config['alert']['message'] = f'Successfully updated test variable to {new_value}'

        response = reload_config

    except KeyError:
        flash('Missing required form field.', 'error')
        response = {'success': False, 'alert': {'type': 'danger', 'message': 'Missing required form field.'}}
    except (ValueError, TypeError):
        flash('Invalid form field value.', 'error')
        response = {'success': False, 'alert': {'type': 'danger', 'message': 'Invalid form field value.'}}
    except Exception as e:
        flash(f'An unexpected error occurred: {e}', 'error')
        response = {'success': False, 'alert': {'type': 'danger', 'message': f'An unexpected error occurred: {e}'}}
    return jsonify(response)


threading.Thread(target=clear_old_items, daemon=True).start()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
