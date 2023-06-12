import configparser
from datetime import datetime
import io
import json
import os
import threading
import time
from os.path import splitext
from functools import wraps
from pydub import AudioSegment
from werkzeug.security import check_password_hash

from lib.config_handler import create_main_config, create_detector_config, save_main_config
from lib.database_handler import SQLiteDatabase
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
config_file = 'config.json'
detector_file = 'detectors.json'
log_path = os.path.join(root_path, 'log')
log_file_name = f"{app_name}.log"
config_path = os.path.join(root_path + "/etc", config_file)
detector_path = os.path.join(root_path + "/etc", detector_file)
audio_path = os.path.join(root_path, "audio")

detector_template = {"detector_id": 0, "station_number": 0, "a_tone": 0, "b_tone": 0,
                     "a_tone_length": 0.6, "b_tone_length": 1,
                     "tone_tolerance": 1, "ignore_time": 60, "pre_record_emails": [],
                     "pre_record_email_subject": "", "pre_record_email_body": "",
                     "post_record_emails": [], "post_record_email_subject": "", "post_record_email_body": "",
                     "mqtt_topic": "", "mqtt_start_message": "ON",
                     "mqtt_stop_message": "OFF", "mqtt_message_interval": 5, "pushover_group_token": "",
                     "pushover_app_token": "", "pushover_subject": "", "pushover_body": "",
                     "pushover_sound": "", "post_to_facebook": 0}

if not os.path.exists(log_path):
    os.makedirs(log_path)

if not os.path.exists(audio_path):
    os.makedirs(audio_path)


def load_configuration():
    global config_data
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        f.close()

    except FileNotFoundError:
        logger.warning(f'Configuration file {config_file} not found. Creating default.')
        try:
            create_main_config(root_path, config_file)
            # Load the newly created configuration file
            load_configuration()
        except Exception as e:
            logger.error(f'Error creating default configuration file: {e}')
            return {'success': False, 'alert': {'type': 'danger',
                                                'message': f'Error creating default configuration file: {e}'}}
        logger.info(f'Successfully created and loaded configuration from {config_file}')
        return {'success': True, 'alert': {'type': 'success',
                                           'message': f'Successfully created and loaded configuration from {config_file}'}}
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
        logger.warning(f'Detector configuration file {detector_file} not found.')
        try:
            create_detector_config(root_path, detector_file)
            load_detectors()
        except Exception as e:
            logger.error(f'Error creating default detectors file: {e}')
            return {'success': False, 'alert': {'type': 'danger',
                                                'message': f'Error creating default detectors file: {e}'}}
        logger.info(f'Successfully created and loaded detectors from {detector_file}')
        return {'success': True, 'alert': {'type': 'success',
                                           'message': f'Successfully created and loaded detectors from {detector_file}'}}


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

try:
    db = SQLiteDatabase(db_path=config_data["sqlite"]["database_path"])
    logger.info("SQLite Database connected successfully.")
except Exception as e:
    logger.error(f'Error while <<connecting>> to the <<database:>> {e}')

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
        time.sleep(1)
        current_time = time.time()
        if len(detector_list) < 1:
            continue
        detector_list = [(timestamp, timeout, id) for timestamp, timeout, id in detector_list if
                         current_time - timestamp <= int(timeout)]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') is None:
            return redirect(url_for('index', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")


@app.route('/admin', methods=['GET'])
@login_required
def admin():
    return render_template("admin.html")


@app.route('/admin/global_config', methods=['GET'])
@login_required
def admin_global_config():
    return render_template("config_global.html", config_data=config_data)


@app.route('/admin/detector_config', methods=['GET'])
@login_required
def admin_detector_config():
    global detector_template

    new_detector_template = detector_template.copy()

    detector_id_all = list(range(1, 200))
    detector_id_used = []
    for det in detector_data:
        if "detector_id" in detector_data[det]:
            detector_id_used.append(detector_data[det]["detector_id"])
    for det_id in detector_id_used:
        detector_id_all.remove(det_id)
    new_detector_template["detector_id"] = detector_id_all[0]

    return render_template("config_detector.html", detector_data=detector_data, detector_template=new_detector_template)


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = db.execute_query('SELECT password FROM users WHERE username = ?', [username], fetch_mode='one')

    if user and check_password_hash(user['password'], password):
        session['logged_in'] = True
        session['user'] = username
    else:
        return 'wrong password!'
    return redirect(url_for('admin'))


@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))


@app.route('/tone_detect', methods=['POST'])
def tone_upload():
    global detector_list

    if request.method == "POST":
        if config_data["detection_mode"] == 0:
            return jsonify({"status": "error", "message": "Detection Disabled"}), 400

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
            quick_call, hi_low, long_tone, dtmf_tone = ToneExtraction(config_data, audio).main()
        except Exception as e:
            return jsonify({"status": "error", "message": f"Exception while extracting tones. {e}"}), 500

        if config_data["detection_mode"] == 1:
            qc_result = ToneDetection(config_data, detector_data, detector_list).detect_quick_call(quick_call, audio, audio_path)
            detector_list = qc_result
        elif config_data["detection_mode"] == 2:
            # check for detections
            if not (quick_call or hi_low or long_tone or dtmf_tone):
                logger.debug(f"No tones found in audio. {quick_call} {hi_low} {long_tone} {dtmf_tone}")
            else:
                logger.warning("Tones Detected")
                detection_json = {"quickcall": quick_call, "hi_low": hi_low, "long": long_tone,
                                  "dtmf": dtmf_tone, "ts": time.time(),
                                  "time": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}
                file_name = f'{round(time.time(), 2)}_detection'
                audio.export(f'{audio_path}/{file_name}.mp3', format='mp3')
                with open(f'{audio_path}/{file_name}.json', 'w+') as outjs:
                    outjs.write(json.dumps(detection_json, indent=4))
                outjs.close()

        return jsonify(detector_list), 200
    else:
        return 200


@app.route('/save_main_config', methods=['POST'])
@login_required
def save_main_config():
    global config_data

    try:
        # Get Form Data
        form_data = request.form

        # Extract individual fields from the form.
        threshold_percent = form_data.get('thresholdPercent')
        dtmf_enabled = form_data.get('dtmfEnabled')
        quick_call_enabled = form_data.get('quickCallEnabled')
        long_tone_enabled = form_data.get('longToneEnabled')
        hi_low_tone_enabled = form_data.get('hiLowToneEnabled')
        sqlite_enabled = form_data.get('sqliteEnabled')
        database_path = form_data.get('databasePath')

        # append these items in their format to config_data
        config_data['tone_extraction']['threshold_percent'] = int(threshold_percent)
        config_data['tone_extraction']['dtmf']["enabled"] = int(dtmf_enabled)
        config_data['tone_extraction']['quick_call']["enabled"] = int(quick_call_enabled)
        config_data['tone_extraction']['long_tone']["enabled"] = int(long_tone_enabled)
        config_data['tone_extraction']['hi-low_tone']["enabled"] = int(hi_low_tone_enabled)
        config_data['sqlite']['enabled'] = int(sqlite_enabled)
        config_data['sqlite']['database_path'] = str(database_path)

        # save config file to disk
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)

        # reload config, this may be redundant since we are already setting the values above ^
        reload_config = load_configuration()
        if reload_config:
            reload_config['alert']['message'] = f'Successfully updated configuration.'

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


@app.route('/save_detector_config', methods=['POST'])
@login_required
def save_detector_config():
    global detector_data
    global detector_template

    new_detector_template = detector_template.copy()

    if request.form["submit"] == "detector_save":
        detector_id = request.form.get("detector_id", None)
        detector_name = request.form.get("detector_name", None)
        detector_number = request.form.get("detector_number", None)
        detector_tone_a = request.form.get("detector_tone_a", None)
        detector_tone_a_length = request.form.get("detector_tone_a_length", None)
        detector_tone_b = request.form.get("detector_tone_b", None)
        detector_tone_b_length = request.form.get("detector_tone_b_length", None)
        detector_tolerance = request.form.get("detector_tolerance", None)
        detector_ignore_time = request.form.get("detector_ignore_time", None)
        detector_prerecord_emails = request.form.get("detector_prerecord_emails", None)
        detector_prerecord_email_subject = request.form.get("pre_record_subject", None)
        detector_prerecord_email_body = request.form.get("pre_record_body", None)
        detector_postrecord_emails = request.form.get("detector_postrecord_emails", None)
        detector_postrecord_email_subject = request.form.get("post_record_subject", None)
        detector_postrecord_email_body = request.form.get("post_record_body", None)
        detector_mqtt_topic = request.form.get("detector_mqtt_topic", None)
        detector_mqtt_start_message = request.form.get("detector_mqtt_start_message", None)
        detector_mqtt_stop_message = request.form.get("detector_mqtt_stop_message", None)
        detector_mqtt_interval_time = request.form.get("detector_mqtt_interval_time", None)
        detector_pushover_group_token = request.form.get("detector_pushover_group_token", None)
        detector_pushover_app_token = request.form.get("detector_pushover_app_token", None)
        detector_pushover_subject = request.form.get("detector_pushover_subject", None)
        detector_facebook_post = request.form.get("det_facebook_status", None)
        detector_pushover_body = request.form.get("html_message", None)
        detector_pushover_sound = request.form.get("detector_pushover_sound", None)

        if detector_id is None or detector_name is None:
            flash("All required fields not filled.", "danger")
            return redirect(url_for("admin_detector_config"), code=302)

        detector_removable = []
        for det in detector_data:
            if detector_data[det]["detector_id"] == int(detector_id):
                if det != detector_name:
                    detector_removable.append(det)
        for rem in detector_removable:
            del detector_data[rem]
        try:
            detector_data[detector_name] = new_detector_template
            detector_data[detector_name]["detector_id"] = int(detector_id)
            detector_data[detector_name]["station_number"] = int(detector_number)

            if detector_tone_a == 0:
                detector_data[detector_name]["a_tone"] = 0
                detector_data[detector_name]["a_tone_length"] = 0
            else:
                detector_data[detector_name]["a_tone"] = float(detector_tone_a)
                detector_data[detector_name]["a_tone_length"] = float(detector_tone_a_length)

            if detector_tone_b == 0:
                detector_data[detector_name]["b_tone"] = 0
                detector_data[detector_name]["b_tone_length"] = 0
            else:
                detector_data[detector_name]["b_tone"] = float(detector_tone_b)
                detector_data[detector_name]["b_tone_length"] = float(detector_tone_b_length)

            if not detector_tolerance:
                detector_data[detector_name]["tone_tolerance"] = 0.02
            else:
                detector_data[detector_name]["tone_tolerance"] = float(detector_tolerance)

            if not detector_ignore_time:
                detector_data[detector_name]["ignore_time"] = 60
            else:
                detector_data[detector_name]["ignore_time"] = float(detector_ignore_time)

            pre_record_emails = []
            if len(detector_prerecord_emails) >= 1:
                temp_pre_emails = detector_prerecord_emails.split(", ")
                for em in temp_pre_emails:
                    pre_record_emails.append(em)
            post_record_emails = []
            if len(detector_postrecord_emails) >= 1:
                temp_post_emails = detector_postrecord_emails.split(", ")
                for em in temp_post_emails:
                    post_record_emails.append(em)

            detector_data[detector_name]["pre_record_emails"] = pre_record_emails

            detector_data[detector_name]["pre_record_email_subject"] = detector_prerecord_email_subject
            detector_data[detector_name]["pre_record_email_body"] = detector_prerecord_email_body

            detector_data[detector_name]["post_record_emails"] = post_record_emails
            detector_data[detector_name]["post_record_email_subject"] = detector_postrecord_email_subject
            detector_data[detector_name]["post_record_email_body"] = detector_postrecord_email_body

            detector_data[detector_name]["mqtt_topic"] = detector_mqtt_topic
            detector_data[detector_name]["mqtt_start_message"] = detector_mqtt_start_message
            detector_data[detector_name]["mqtt_stop_message"] = detector_mqtt_stop_message
            if detector_mqtt_interval_time != "":
                detector_data[detector_name]["mqtt_message_interval"] = float(detector_mqtt_interval_time)
            else:
                detector_data[detector_name]["mqtt_message_interval"] = 0
            detector_data[detector_name]["post_to_facebook"] = int(detector_facebook_post)
            detector_data[detector_name]["pushover_group_token"] = detector_pushover_group_token
            detector_data[detector_name]["pushover_app_token"] = detector_pushover_app_token
            detector_data[detector_name]["pushover_subject"] = detector_pushover_subject
            detector_data[detector_name]["pushover_body"] = detector_pushover_body
            detector_data[detector_name]["pushover_sound"] = detector_pushover_sound

        except ValueError as e:
            flash("Value Error adjust detector configuration and try again: " + str(e), "danger")
            return redirect(url_for("admin_detector_config"), code=302)

        with open("etc/detectors.json", "w") as outfile:
            outfile.write(json.dumps(detector_data, indent=4))
        outfile.close()

        load_detectors()

        flash(f"Saved Detector: {detector_name}", "success")

    elif request.form["submit"] == "detector_delete":
        detector_id = request.form["detector_id"]
        detector_name = request.form["detector_name"]
        if detector_name in detector_data:
            if detector_data[detector_name]["detector_id"] == int(detector_id):
                del detector_data[detector_name]

                with open("etc/detectors.json", "w") as outfile:
                    outfile.write(json.dumps(detector_data, indent=4))
                outfile.close()
                load_detectors()
                flash(f"Deleted Detector: {detector_name}", "success")
            else:
                flash(f"Detector: {detector_name} ID doesn't match.", "danger")
        else:
            flash(f"Detector: {detector_name} not in config.", "danger")

    return redirect(url_for("admin_detector_config"), code=302)


@app.route('/ttd_import', methods=['POST'])
@login_required
def import_ttd():
    global detector_data
    global detector_template

    new_detector_template = detector_template.copy()

    detector_id_all = list(range(1, 200))
    detector_id_used = []
    for det in detector_data:
        if "detector_id" in detector_data[det]:
            detector_id_used.append(detector_data[det]["detector_id"])
    for det_id in detector_id_used:
        detector_id_all.remove(det_id)

    try:
        file = request.files['cfgFile']

        # Make sure a file was uploaded
        if not file:
            logger.error("No file uploaded.")
            flash("No file part in the request.", "danger")
            return redirect(url_for("admin_detector_config"), code=302)

        # Read the file data into a string
        ttd_cfg_data = file.read().decode('utf-8')

        # Use an io.StringIO object to mimic a file
        ttd_cfg_object = io.StringIO(ttd_cfg_data)

        # Create a ConfigParser object
        ttd_config = configparser.ConfigParser()
        ttd_config.read_file(ttd_cfg_object)

        # process ini -> detector.json
        count = 0
        for section in ttd_config.sections():
            try:
                if ttd_config[section]["description"] not in detector_data:
                    detector_data[ttd_config[section]["description"]] = new_detector_template.copy()
                    detector_id = detector_id_all[0]
                    detector_data[ttd_config[section]["description"]]["detector_id"] = detector_id
                    detector_id_all.remove(detector_id)
                    detector_data[ttd_config[section]["description"]]["a_tone"] = float(ttd_config[section]["atone"])
                    detector_data[ttd_config[section]["description"]]["b_tone"] = float(ttd_config[section]["btone"])
                    detector_data[ttd_config[section]["description"]]["a_tone_length"] = float(
                        ttd_config[section]["atonelength"])
                    detector_data[ttd_config[section]["description"]]["a_tone_length"] = float(
                        ttd_config[section]["btonelength"])
                    detector_data[ttd_config[section]["description"]]["tone_tolerance"] = float(
                        ttd_config[section]["tone_tolerance"]) * 100
                    count += 1
                else:
                    logger.debug(f'Skipping {ttd_config[section]["description"]} already in detectors')
            except ValueError as ve:
                logger.error(
                    f'Value error encountered while processing section {ttd_config[section]["description"]}: {ve}')
                flash(f'Error while processing ttd import {ttd_config[section]["description"]}: {ve}', "danger")
                return redirect(url_for("admin_detector_config"), code=302)

        try:
            with open("etc/detectors.json", "w") as outfile:
                outfile.write(json.dumps(detector_data, indent=4))
        except IOError:
            logger.error("IOError occurred while writing to the file.")
            flash("An error occurred while writing to the file.", "danger")
            return redirect(url_for("admin_detector_config"), code=302)

        load_detectors()
        flash(f"Imported {count} detectors from TTD", "success")
        return redirect(url_for("admin_detector_config"), code=302)

    except UnicodeDecodeError:
        # If file cannot be decoded into text
        logger.error("Uploaded file could not be decoded.")
        flash("Uploaded file could not be decoded.", "danger")
    except configparser.ParsingError:
        # If there's a problem parsing the INI file
        logger.error("Uploaded file could not be parsed.")
        flash("Uploaded file could not be parsed.", "danger")
    except Exception as e:
        # Generic catch-all for unexpected errors
        logger.error(f"Unexpected error: {e}")
        flash("An unexpected error occurred.", "danger")

    return redirect(url_for("admin_detector_config"), code=302)


threading.Thread(target=clear_old_items, daemon=True).start()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8002, debug=False)
