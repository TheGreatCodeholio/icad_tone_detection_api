import configparser
import traceback
from datetime import datetime
import io
import json
import os
import threading
import time
from os.path import splitext
from functools import wraps

import redis
from pydub import AudioSegment

from lib.agency_handler import import_agencies_from_detectors, get_agencies
from lib.config_handler import load_config_file, save_config_file, load_systems_agencies_detectors
from lib.logging_handler import CustomLogger
from flask import Flask, request, session, redirect, url_for, render_template, flash, jsonify

from flask_session import Session

from lib.mysql_handler import DatabaseFactory
from lib.redis_handler import RedisCache
from lib.system_handler import get_systems, add_system, delete_radio_system, update_system_settings
from lib.tone_detection_handler import ToneDetection, get_active_detections_cache, add_active_detections_cache, \
    delete_active_detections_cache
from lib.tone_extraction_handler import ToneExtraction
from lib.user_handler import authenticate_user

app_name = "icad_tone_detection"

log_level = 2

root_path = os.getcwd()
config_file = 'config.json'
detector_file = 'detectors.json'
log_path = os.path.join(root_path, 'log')
log_file_name = f"{app_name}.log"
config_path = os.path.join(root_path, 'etc')

audio_path = os.path.join(root_path, 'audio')

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

if not os.path.exists(config_path):
    os.makedirs(config_path)

logging_instance = CustomLogger(1, f'{app_name}',
                                os.path.join(log_path, log_file_name))

try:
    config_data = load_config_file(os.path.join(config_path, config_file), "config")
    logging_instance.set_log_level(config_data["log_level"])
    logger = logging_instance.logger
    logger.info("Loaded Config File")
except Exception as e:
    traceback.print_exc()
    print(f'Error while <<loading>> configuration : {e}')
    exit(1)

if not config_data:
    logger.error('Failed to load configuration.')
    exit(1)

try:
    db_factory = DatabaseFactory(config_data)
    db = db_factory.get_database()

    logger.info("Database Initialized successfully.")
except Exception as e:
    traceback.print_exc()
    logger.error(f'Error while <<initializing>> Database : {e}')
    exit(1)

try:
    rd = RedisCache(config_data)
    logger.info("Redis Pool Connection Pool connected successfully.")
except Exception as e:
    traceback.print_exc()
    logger.error(f'Error while <<connecting>> to the <<Redis Cache:>> {e}')
    exit(1)

system_data = load_systems_agencies_detectors(db)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Session Configuration
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'session:'
app.config['SESSION_REDIS'] = redis.StrictRedis(host=config_data["redis"]["host"],
                                                password=config_data["redis"]["password"],
                                                port=config_data["redis"]["port"], db=3)

# Cookie Configuration
app.config['SESSION_COOKIE_SECURE'] = config_data["general"]["cookie_secure"]
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_DOMAIN'] = config_data["general"]["cookie_domain"]
app.config['SESSION_COOKIE_NAME'] = config_data["general"]["cookie_name"]
app.config['SESSION_COOKIE_PATH'] = config_data["general"]["cookie_path"]
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initializing the session
sess = Session()
sess.init_app(app)


# Loop to run that clears old detections.
def clear_old_items():
    while True:
        time.sleep(1)  # Sleep to prevent a tight loop that hogs the CPU

        # Fetch the current list of detections
        qc_detector_list = get_active_detections_cache(rd, "icad_current_detectors")
        current_time = time.time()
        if len(qc_detector_list) < 1:
            # logger.warning(f"Empty Detector List")
            continue  # Skip this iteration if list is empty

        updated_list = []
        for item in qc_detector_list:
            # Calculate the expiration time for each item
            expire_time = item['last_detected'] + item['ignore_seconds']
            if current_time <= expire_time:
                # If the item hasn't expired, add it to the updated list
                updated_list.append(item)

        # If the updated list is shorter, some items were removed
        if len(updated_list) < len(qc_detector_list):
            # Clear the old list
            delete_active_detections_cache(rd, "icad_current_detectors")

            # Add the updated items back, if any
            if updated_list:
                # Push all items at once to the list
                rd.lpush("icad_current_detectors", *updated_list)

                logger.warning(f"Removed {len(qc_detector_list) - len(updated_list)}")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        authenticated = session.get('authenticated')

        if not authenticated:
            logger.debug(f"Redirecting User: Current session data: {session.items()}")

            return redirect(url_for('index'))
        else:
            logger.debug(f"User Authorized: Current session data: {session.items()}")

        return f(*args, **kwargs)

    return decorated_function


@app.route('/', methods=['GET'])
def index():
    logger.debug(session)
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
    if not username or not password:
        flash('Username and Password Required', 'danger')
        return redirect(url_for('index'))

    auth_result = authenticate_user(db, username, password)
    flash(auth_result["message"], 'success' if auth_result["success"] else 'danger')
    return redirect(url_for('admin') if auth_result["success"] else url_for('index'))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route("/api/get_systems")
def api_get_systems():
    system_id = request.args.get('system_id', None)
    with_agencies = request.args.get('with_agencies', False)

    # Fetch system data once
    system_data_result = get_systems(db, system_id)

    # If agencies are requested, enhance the system data with agency information
    if with_agencies and system_data_result["result"]:
        # Prepare a list of system IDs to fetch their agencies in one go (if applicable)
        system_ids = [system.get("system_id") for system in system_data_result["result"]]

        # Fetch all agencies for the systems in one go (modify this function to accept multiple system_ids)
        all_agencies = get_agencies(db, system_ids)

        # Map agencies back to their respective systems
        for system in system_data_result["result"]:
            # Filter agencies for this specific system
            system["agencies"] = [agency for agency in all_agencies["result"] if
                                  agency["system_id"] == system["system_id"]]

    return jsonify(system_data_result)


@app.route("/api/get_agency")
def api_get_agencies():
    system_id = request.args.get('system_id', None)
    agency_id = request.args.get('agency_id', None)

    system_data_result = get_agencies(db, system_id, agency_id)

    return jsonify(system_data_result)


@app.route('/tone_detect', methods=['POST'])
def tone_upload():
    tones_with_data = []
    logger.info("Got New HTTP request.")

    if request.method != "POST":
        return jsonify({"status": "error", "message": "Invalid request method"}), 400

    call_data_post = request.form.to_dict()

    if not call_data_post:
        return jsonify({"status": "error", "message": "No call data"}), 400

    if config_data["general"].get("detection_mode", 0) == 0:
        return jsonify({"status": "error", "message": "Detection Disabled"}), 400

    file = request.files.get('file')
    if not file:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    allowed_extensions = ['.mp3', '.wav', '.m4a']
    ext = splitext(file.filename)[1]
    if ext not in allowed_extensions:
        return jsonify({"status": "error", "message": "File must be an MP3, WAV, or M4A"}), 400

    qc_detector_list = get_active_detections_cache(rd, "icad_current_detectors")
    logger.warning(f'Active Detector List: {qc_detector_list}')

    file_data = file.read()
    audio_segment = AudioSegment.from_file(io.BytesIO(file_data))

    try:
        quick_call, hi_low, long_tone, dtmf_tone = ToneExtraction(config_data, audio_segment).main()
        detection_data = {
            "quick_call": quick_call,
            "hi_low": hi_low,
            "long": long_tone,
            "dtmf": dtmf_tone,
            "timestamp": float(call_data_post.get("start_time")),
            "timestamp_string": datetime.fromtimestamp(float(call_data_post.get("start_time"))).strftime(
                "%m/%d/%Y, %H:%M:%S"),
            'call_length': float(call_data_post.get('call_length', 0)),
            'talkgroup_decimal': int(call_data_post.get('talkgroup', 0)),
            'talkgroup_alpha_tag': str(call_data_post.get('talkgroup_tag')),
            'talkgroup_name': str(call_data_post.get('talkgroup_description')),
            'talkgroup_service_type': str(call_data_post.get('talkgroup_group_tag')),
            'talkgroup_group': str(call_data_post.get('talkgroup_group'))
        }

    except Exception as e:
        return jsonify({"status": "error", "message": f"Exception while extracting tones. {e}"}), 500

    if quick_call:
        tones_with_data.append(f"quick_call: {quick_call}")
    if hi_low:
        tones_with_data.append(f"hi_low: {hi_low}")
    if long_tone:
        tones_with_data.append(f"long_tone: {long_tone}")
    if dtmf_tone:
        tones_with_data.append(f"dtmf_tone: {dtmf_tone}")

    if not tones_with_data:
        logger.debug(f"No tones found in audio. {quick_call} {hi_low} {long_tone} {dtmf_tone}")
    else:
        data_message = ', '.join(tones_with_data)
        logger.warning(f"Tones Detected: {data_message}")
        file_name = f'{round(detection_data["timestamp"], -1)}_detection'
        local_audio_path = os.path.join(audio_path, f"{file_name}.mp3")
        local_json_path = os.path.join(audio_path, f"{file_name}_metadata.json")
        audio_segment.export(local_audio_path, format='mp3')
        detection_data["local_audio_path"] = local_audio_path
        logger.info(f"Saving Audio and Metadata: {local_audio_path}")
        with open(local_json_path, 'w') as outjs:
            outjs.write(json.dumps(call_data_post, indent=4))

        if config_data["general"].get("detection_mode", 0) in [2, 3]:
            logger.warning("Processing Tones Through Detectors")

            logger.debug("Processing QuickCall Tones")
            processed_detection_data = ToneDetection(config_data, detector_data, detection_data).detect_quick_call(rd)
            detection_data = processed_detection_data
        if config_data["general"].get("detection_mode", 0) in [1, 3]:
            with open(local_audio_path.replace(".mp3", ".json"), 'w+') as outjs:
                outjs.write(json.dumps(detection_data, indent=4))
    qc_detector_list = get_active_detections_cache(rd, "icad_current_detectors")
    logger.warning(f"Active Detectors List: {qc_detector_list}")
    logger.info("HTTP Request Completed")
    return jsonify(detection_data), 200


@app.route('/admin/edit_systems', methods=['POST', 'GET'])
@login_required
def edit_systems():
    if request.method == "GET":
        return render_template('systems_config.html')
    elif request.method == "POST":
        pass


@app.route('/admin/save_system', methods=['POST'])
@login_required
def save_system_config():
    new_system = request.args.get("new_system", False)
    delete_system = request.args.get("delete_system", False)
    try:
        # Get Form Data
        form_data = request.form

        if delete_system:
            result = delete_radio_system(db, form_data.get("system_id"))
            response = {'success': result.get("success", False), 'message': f'Successfully Removed System' if result.get("success", False) else result.get("message")}
        elif new_system:
            add_system(db, form_data)
            response = {'success': True, 'message': f'Successfully added system.'}
        else:
            update_system_settings(db, form_data, config_data)
            response = {'success': True, 'message': f'Successfully updated system.'}

    except KeyError:
        flash('Missing required form field.', 'error')
        response = {'success': False, 'message': 'Missing required form field.'}
    except (ValueError, TypeError):
        flash('Invalid form field value.', 'error')
        response = {'success': False, 'message': 'Invalid form field value.'}
    except Exception as e:
        flash(f'An unexpected error occurred: {e}', 'error')
        response = {'success': False, 'message': f'An unexpected error occurred: {e}'}
    return jsonify(response)


@app.route('/save_main_config', methods=['POST'])
@login_required
def save_main_config():
    """
    Save Main Config

    This method is used to save the main configuration settings. It receives a POST request containing form data and
    saves the configuration data to a file on disk.

    :return: A JSON response containing the result of the operation.

    Example Usage:
        response = save_main_config()

    """
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
        reload_config = save_config_file(os.path.join(config_path, config_file), config_data)
        if not reload_config:
            logger.error('Failed to reload configuration.')
            response = {'success': False, 'alert': {'type': 'danger', 'message': 'Failed to reload configuration.'}}
            return jsonify(response)

        response = {'success': True, 'alert': {'type': 'success', 'message': 'Successfully updated configuration.'}}

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
        detector_tone_b = request.form.get("detector_tone_b", None)
        detector_tolerance = request.form.get("detector_tolerance", None)
        detector_ignore_time = request.form.get("detector_ignore_time", None)
        detector_alert_emails = request.form.get("detector_alert_emails", None)
        detector_alert_email_subject = request.form.get("alert_subject", None)
        detector_alert_email_body = request.form.get("alert_body", None)
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

            else:
                detector_data[detector_name]["a_tone"] = float(detector_tone_a)

            if detector_tone_b == 0:
                detector_data[detector_name]["b_tone"] = 0

            else:
                detector_data[detector_name]["b_tone"] = float(detector_tone_b)

            if not detector_tolerance:
                detector_data[detector_name]["tone_tolerance"] = 0.02
            else:
                detector_data[detector_name]["tone_tolerance"] = float(detector_tolerance)

            if not detector_ignore_time:
                detector_data[detector_name]["ignore_time"] = 60
            else:
                detector_data[detector_name]["ignore_time"] = float(detector_ignore_time)

            alert_emails = []
            if len(detector_alert_emails) >= 1:
                temp_post_emails = detector_alert_emails.split(", ")
                for em in temp_post_emails:
                    alert_emails.append(em)

            detector_data[detector_name]["alert_emails"] = alert_emails
            detector_data[detector_name]["alert_email_subject"] = detector_alert_email_subject
            detector_data[detector_name]["alert_email_body"] = detector_alert_email_body

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

        save_result = save_config_file(os.path.join(config_path, detector_file), detector_data)
        if not save_result:
            flash("Failed to save detector configuration.", "danger")
            return redirect(url_for("admin_detector_config"), code=302)

        flash(f"Saved Detector: {detector_name}", "success")

    elif request.form["submit"] == "detector_delete":
        detector_id = request.form["detector_id"]
        detector_name = request.form["detector_name"]
        if detector_name in detector_data:
            if detector_data[detector_name]["detector_id"] == int(detector_id):
                del detector_data[detector_name]

                save_result = save_config_file(os.path.join(config_path, detector_file), detector_data)
                if not save_result:
                    flash("Failed to save detector configuration.", "danger")
                    return redirect(url_for("admin_detector_config"), code=302)

                flash(f"Deleted Detector: {detector_name}", "success")
            else:
                flash(f"Detector: {detector_name} ID doesn't match.", "danger")
        else:
            flash(f"Detector: {detector_name} not in config.", "danger")

    return redirect(url_for("admin_detector_config"), code=302)


@app.route('/icad_import', methods=['POST'])
def import_icad_agencies():
    system_id = request.args.get("system_id")
    if not system_id:
        return jsonify({"success": False, "message": "System ID Required."}), 400

    try:
        file = request.files['cfgFile']
        if not file:
            return jsonify({"success": False, "message": "detector.json file required."}), 400

        import_content = file.read()
        import_data = json.loads(import_content)
    except Exception as e:
        return jsonify({"success": False, "message": f"Unexpected Exception: {e}"}), 400

    import_result = import_agencies_from_detectors(db, import_data, int(system_id))

    if not import_result:
        return jsonify({"success": False, "message": "Import Error"})
    else:
        return jsonify({"success": True, "message": "Import Success"})


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

        save_result = save_config_file(os.path.join(config_path, detector_file), detector_data)
        if not save_result:
            flash("Failed to save detector configuration.", "danger")
            return redirect(url_for("admin_detector_config"), code=302)

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

# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=8002, debug=False)
