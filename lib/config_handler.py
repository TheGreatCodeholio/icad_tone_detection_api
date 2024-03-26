import json
import logging
import os
import time
import traceback
from cryptography.fernet import Fernet

from lib.agency_handler import get_agencies
from lib.system_handler import get_systems

module_logger = logging.getLogger('icad_tone_detection.config')

default_config = {
    "log_level": 1,
    "general": {
        "detection_mode": 1,
        "test_mode": True,
        "base_url": "http://localhost",
        "cookie_domain": "localhost",
        "cookie_secure": False,
        "cookie_name": "icad_tone_detect",
        "cookie_path": "/"
    },
    "audio_upload": {
        "allowed_mimetypes": ["audio/x-wav", "audio/x-m4a", "audio/mpeg"],
        "max_audio_length": 300,
        "max_file_size": 3
    },
    "tone_extraction": {
        "threshold_percent": 2
    },
    "finder_mode": {
        "email": {
            "enabled": 0,
            "host": "",
            "port": 587,
            "user": "",
            "password": "",
            "email_address_from": "",
            "email_text_from": "",
            "alert_email_recipients": []
        },
        "scp": {
            "enabled": 0,
            "host": "",
            "port": 22,
            "user": "",
            "password": "",
            "private_key_path": "",
            "base_url": "",
            "remote_path": ""
        },
        "webhook": {
            "enabled": 0,
            "webhook_url": "http://localhost",
            "webhook_headers": {}
        }
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
        "webhook_url": "",
        "webhook_headers": "",
        "post_to_facebook": 0,
        "post_to_telegram": 0
    }
}


def get_max_content_length(config_data, default_size_mb=3):
    try:
        # Attempt to retrieve and convert the max file size to an integer
        max_file_size = int(config_data.get("audio_upload", {}).get("max_file_size", default_size_mb))
    except (ValueError, TypeError) as e:
        # Log the error and exit if the value is not an integer or not convertible to one
        module_logger.error(f'Max File Size Must be an Integer: {e}')
        time.sleep(5)
        exit(1)
    else:
        # Return the size in bytes
        return max_file_size * 1024 * 1024


def deep_update(source, overrides):
    for key, value in overrides.items():
        if isinstance(value, dict):
            # Get the existing nested dictionary or create a new one
            node = source.setdefault(key, {})
            deep_update(node, value)
        else:
            source[key] = value


def generate_default_config(config_type):
    try:
        if config_type == "config":
            global default_config
            default_data = default_config.copy()
            default_data["general"]["base_url"] = os.getenv('BASE_URL', "http://localhost")
            default_data["general"]["cookie_domain"] = os.getenv('COOKIE_DOMAIN', "localhost")
            default_data["general"]["cookie_secure"] = bool(os.getenv('COOKIE_SECURE', False))
            default_data["general"]["cookie_name"] = os.getenv('COOKIE_NAME', "icad_tone_detect")
            default_data["general"]["cookie_path"] = os.getenv('COOKIE_PATH', "/")
            default_data['mysql'] = {}
            default_data["mysql"]["host"] = os.getenv('MYSQL_HOST', "mysql")
            default_data["mysql"]["port"] = int(os.getenv('MYSQL_PORT', 3306))
            default_data["mysql"]["user"] = os.getenv('MYSQL_USER', "icad")
            default_data["mysql"]["password"] = os.getenv('MYSQL_PASSWORD', "")
            default_data["mysql"]["database"] = os.getenv('MYSQL_DATABASE', "icad")
            default_data["redis"] = {}
            default_data["redis"]["host"] = os.getenv('REDIS_HOST', "redis")
            default_data["redis"]["port"] = int(os.getenv('REDIS_PORT', 6379))
            default_data["redis"]["password"] = os.getenv('REDIS_PASSWORD', "")
            default_data["rabbitmq"] = {}
            default_data["rabbitmq"]["host"] = os.getenv('RABBITMQ_HOST', "rabbitmq")
            default_data["rabbitmq"]["port"] = int(os.getenv('RABBITMQ_PORT', 5672))
            default_data["rabbitmq"]["user"] = os.getenv('RABBITMQ_USER', "icad")
            default_data["rabbitmq"]["password"] = os.getenv('RABBITMQ_PASSWORD', "")

        elif config_type == "detectors":
            global default_detectors
            default_data = default_detectors.copy()
        else:
            module_logger.error(f'Invalid config type {config_type}')
            return None

        return default_data

    except Exception as e:
        traceback.print_exc()
        module_logger.error(f'Error generating default configuration for {config_type}: {e}')
        return None


def generate_key_and_save_to_file(key_path):
    """
    Generates a new Fernet key and saves it to a file.
    """
    key = Fernet.generate_key()
    with open(key_path, 'wb') as key_file:
        key_file.write(key)
    module_logger.info(f"Encryption Key generated and saved to {key_path}")


def load_key_from_file(key_path):
    """
    Loads the Fernet key from a file or generates a new one if the file doesn't exist.
    """
    try:
        with open(key_path, 'rb') as key_file:
            key = key_file.read()
    except FileNotFoundError:
        module_logger.info(f"Encryption Key file {key_path} not found. Generating a new one.")
        generate_key_and_save_to_file(key_path)
        with open(key_path, 'rb') as key_file:
            key = key_file.read()
    return key


def load_config_file(file_path, config_type):
    """
    Loads the configuration file and encryption key.
    """
    key_path = file_path.replace("config.json", "secret.key")

    # Load or generate the encryption key
    encryption_key = load_key_from_file(key_path)

    # Attempt to load the configuration file
    try:
        with open(file_path, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        module_logger.warning(f'Configuration file {file_path} not found. Creating default.')
        config_data = generate_default_config(config_type)  # Assuming this function is defined elsewhere
        if config_data:
            save_config_file(file_path, config_data)  # Assuming this function is defined elsewhere
    except json.JSONDecodeError:
        module_logger.error(f'Configuration file {file_path} is not in valid JSON format.')
        return None
    except Exception as e:
        module_logger.error(f'Unexpected Exception Loading file {file_path} - {e}')
        return None

    # Add the encryption key to the configuration data
    if not config_data:
        config_data = {}
    config_data["fernet_key"] = encryption_key

    return config_data


def save_config_file(file_path, default_data):
    """Creates a configuration file with default data if it doesn't exist."""
    try:
        with open(file_path, "w") as outfile:
            outfile.write(json.dumps(default_data, indent=4))
        return True
    except Exception as e:
        module_logger.error(f'Unexpected Exception Saving file {file_path} - {e}')
        return None


def load_systems_agencies_detectors(db, system_id=None):
    systems_config = {}
    systems_result = get_systems(db, system_id)
    if systems_result.get("success") and systems_result.get("result"):
        for system in systems_result.get("result"):
            agency_result = get_agencies(db, [system.get("system_id")])
            if not agency_result.get("success") or not agency_result.get("result"):
                agency_result = {"result": []}
            systems_config[system.get("system_id")] = system
            systems_config["agencies"] = agency_result.get("result", [])

    return systems_config
