import json
import os

default_config = {
    "general": {
        "detection_mode": 3,
        "test_mode": True,
        "base_url": "http://localhost",
        "cookie_domain": "localhost",
        "cookie_secure": False,
        "cookie_name": "icad_tone_detect",
        "cookie_path": "/"
    },
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
    "upload_processing": {
        "check_for_split": 0,
        "maximum_split_length": 30,
        "maximum_split_interval": 45,
        "minimum_audio_length": 4.5
    },
    "audio_processing": {
        "trim_tones": 0,
        "trim_post_cut": 5.5,
        "trim_pre_cut": 2.0,
        "trim_group_tone_gap": 6.5,
        "normalize": 0,
        "ffmpeg_filter": ""
    },
    "transcription_settings": {
        "transcribe_alert": 0,
        "transcribe_detection": 0,
        "transcription_url": "https://example.com/transcribe"
    },
    "email_settings": {
        "enabled": 0,
        "smtp_hostname": "mail.example.com",
        "smtp_port": 587,
        "smtp_username": "dispatch@example.com",
        "smtp_password": "CE3########QM",
        "smtp_security": "TLS",
        "email_address_from": "dispatch@example.com",
        "email_text_from": "iCAD Example County",
        "alert_email_subject": "Dispatch Alert - {detector_name}",
        "alert_email_body": "{detector_name} Alert at {timestamp}<br><br>{transcript}<br><br><a href=\"{mp3_url}\">Click for Dispatch Audio</a><br><br><a href=\"{stream_url}\">Click Audio Stream</a>",
        "grouped_alert_emails": [],
        "grouped_email_subject": "Dispatch Alert",
        "grouped_email_body": "{detector_list} Alert at {timestamp}<br><br>{transcript}<br><br><a href=\"{mp3_url}\">Click for Dispatch Audio</a><br><br><a href=\"{stream_url}\">Click Audio Stream</a>"
    },
    "pushover_settings": {
        "enabled": 0,
        "all_detector_group": 0,
        "all_detector_group_token": "g23#####################ns7",
        "all_detector_app_token": "aen#######################vuru",
        "pushover_body": "<font color=\"red\"><b>{detector_name}</b></font><br><br><a href=\"{mp3_url}\">Click for Dispatch Audio</a><br><br><a href=\"{stream_url}\">Click Audio Stream</a>",
        "pushover_subject": "Alert!",
        "pushover_sound": "pushover"
    },
    "facebook_settings": {
        "enabled": 0,
        "page_id": 12345678910,
        "page_token": "EA###########ZDZD",
        "group_id": 12345678910,
        "group_token": "EAAW##########g54ZD",
        "post_comment": 1,
        "post_body": "{timestamp} Departments:\n{detector_list}\n\nDispatch Audio:\n{mp3_url}",
        "comment_body": "{transcript}{stream_url}"
    },
    "telegram_settings": {
        "enabled": 0,
        "telegram_bot_token": "57######:AA############ac",
        "telegram_channel_id": 00000000000
    },
    "stream_settings": {
        "stream_url": ""
    },
    "remote_storage_settings": {
        "enabled": 0,
        "storage_type": "scp",
        "remote_path": "/var/www/example.com/detection_audio",
        "google_cloud": {
            "project_id": "some-projectname-444521",
            "bucket_name": "bucket-name",
            "credentials_path": "etc/google_cloud.json"
        },
        "aws_s3": {
            "access_key_id": "AK###########B",
            "secret_access_key": "l###################8",
            "bucket_name": "bucket-name",
            "region": "us-east-1"
        },
        "scp": {
            "host": "upload.example.com",
            "port": 22,
            "user": "sshuser",
            "password": "",
            "audio_url_path": "https://example.com/detection_audio",
            "remote_path": "/var/www/example.com/detection_audio",
            "keep_audio_days": 0,
            "private_key": "/home/sshuser/.ssh/id_rsa"
        }
    },
    "sqlite": {
        "enabled": 1,
        "database_path": "tr_tone_detect.db"
    }
}

default_detectors = {
    "Example Department": {
        "detector_id": 1,
        "station_number": 0,
        "a_tone": 726.8,
        "b_tone": 1122.5,
        "c_tone": 0,
        "d_tone": 0,
        "tone_tolerance": 2,
        "ignore_time": 300.0,
        "alert_emails": ["user@example.com"],
        "alert_email_subject": "",
        "alert_email_body": "",
        "mqtt_topic": "detect/Example Department",
        "mqtt_start_message": "ON",
        "mqtt_stop_message": "OFF",
        "mqtt_message_interval": 5.0,
        "pushover_group_token": "g9##########w2",
        "pushover_app_token": "arkj########6i",
        "pushover_subject": "",
        "pushover_body": "",
        "pushover_sound": "",
        "stream_url": "",
        "post_to_facebook": 0,
        "post_to_telegram": 0
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
