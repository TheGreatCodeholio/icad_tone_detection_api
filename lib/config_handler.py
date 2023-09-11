import json
import os

default_config = {
    "detection_mode": 2,
    "tone_extraction": {
        "threshold_percent": 2,
        "dtmf": {
            "enabled": 1
        },
        "quick_call": {
            "enabled": 1
        },
        "long_tone": {
            "enabled": 1
        },
        "hi-low_tone": {
            "enabled": 1
        }
    },
    "transcription_settings": {
        "transcribe_alert": 0,
        "transcribe_detection": 0,
        "transcription_url": "http://localhost/transcribe"
    },
    "email_settings": {
        "send_detection_email": 0,
        "send_alert_email": 0,
        "send_as_single_email": 0,
        "smtp_hostname": "mail.example.com",
        "smtp_port": 587,
        "smtp_username": "dispatch@example.com",
        "smtp_password": "CE3QsT2biDfruQM",
        "smtp_security": "TLS",
        "email_address_from": "dispatch@example.com",
        "email_text_from": "iCAD Example County",
        "alert_email_subject": "Dispatch Alert - {detector_name}",
        "alert_email_body": "{detector_name} Alert at {timestamp}<br><br> {mp3_url} <br><br>{transcript}"
    },
    "pushover_settings": {
        "enabled": 0,
        "all_detector_group": 0,
        "all_detector_group_token": "secretgrouptokengoeshere",
        "all_detector_app_token": "secretapptokengoeshere",
        "message_html_string": "<font color=\"red\"><b>{detector_name}</b></font><br><br><a href=\"{mp3_url}\">Click for Dispatch Audio</a>",
        "subject": "Alert!",
        "sound": "pushover"
    },
    "sqlite": {
        "enabled": 1,
        "database_path": "tr_tone_detect.db"
    }
}

default_detectors = {
    "Test Department": {
        "detector_id": 0,
        "station_number": 0,
        "a_tone": 0,
        "b_tone": 0,
        "tone_tolerance": 1,
        "ignore_time": 120.0,
        "alert_emails": [],
        "alert_email_subject": "Dispatch Alert - {detector_name}",
        "alert_email_body": "{detector_name} Alert at {timestamp}<br><br>",
        "mqtt_topic": "dispatch/TestDepartment",
        "mqtt_start_message": "ON",
        "mqtt_stop_message": "OFF",
        "mqtt_message_interval": 5.0,
        "pushover_group_token": "group_token",
        "pushover_app_token": "application_token",
        "pushover_subject": "Alert!",
        "pushover_body": "<font color=\"red\"><b>{detector_name}</b></font><br><br><a href=\"{mp3_url}\">Click for Dispatch Audio</a>",
        "pushover_sound": "pager",
        "post_to_facebook": 0

    }
}


def create_main_config(root_path, config_file):
    root_path = os.path.join(root_path + "/etc")
    config_path = os.path.join(root_path, config_file)
    if not os.path.exists(root_path):
        os.makedirs(root_path)
    if not os.path.exists(config_path):
        with open(config_path, "w+") as outfile:
            outfile.write(json.dumps(default_config, indent=4))
        outfile.close()


def create_detector_config(root_path, detector_file):
    root_path = os.path.join(root_path + "/etc")
    detector_path = os.path.join(root_path, detector_file)
    if not os.path.exists(root_path):
        os.makedirs(root_path)
    if not os.path.exists(detector_path):
        with open(detector_path, "w+") as outfile:
            outfile.write(json.dumps(default_detectors, indent=4))
        outfile.close()


def save_main_config(root_path, config_file, config_data):
    root_path = os.path.join(root_path + "/etc")
    config_path = os.path.join(root_path, config_file)
    if not os.path.exists(root_path):
        os.makedirs(root_path)
    if not os.path.exists(config_path):
        with open(config_path, "w+") as outfile:
            outfile.write(json.dumps(config_data, indent=4))
        outfile.close()
