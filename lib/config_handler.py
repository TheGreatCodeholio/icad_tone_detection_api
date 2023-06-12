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
    "sqlite": {
        "enabled": 1,
        "database_path": "tr_tone_detect.db"
    }
}

default_detectors = {
    "Test Department": {
        "detector_id": 1,
        "station_number": 0,
        "a_tone": 2573.2,
        "b_tone": 1981.1,
        "tone_tolerance": 1,
        "ignore_time": 120.0,
        "pre_record_emails": [],
        "pre_record_email_subject": "Dispatch Alert - %detector_name%",
        "pre_record_email_body": "%detector_name% Alert at %timestamp%<br><br>",
        "post_record_emails": [],
        "post_record_email_subject": "Dispatch Alert - %detector_name%",
        "post_record_email_body": "%detector_name% Alert at %timestamp%<br><br>",
        "mqtt_topic": "dispatch/test_department",
        "mqtt_start_message": "ON",
        "mqtt_stop_message": "OFF",
        "mqtt_message_interval": 5.0,
        "pushover_group_token": "secrettoken",
        "pushover_app_token": "secrettoken",
        "pushover_subject": "Alert!",
        "pushover_body": "<font color=\"red\"><b>%detector_name%</b></font><br><br><a href=\"%mp3_url%\">Click for Dispatch Audio</a>",
        "pushover_sound": "pager",
        "post_to_facebook": 1
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
