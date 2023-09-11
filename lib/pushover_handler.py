from datetime import datetime

import requests
import logging
import traceback

module_logger = logging.getLogger('tr_tone_detection.pushover')


def send_push(config_data, detector_data, call_data):
    try:

        if detector_data["pushover_subject"] != "":
            title = detector_data["pushover_subject"]
        else:
            title = config_data["pushover_settings"]["subject"]

        if detector_data["pushover_sound"] != "":
            sound = detector_data["pushover_sound"]
        else:
            sound = config_data["pushover_settings"]["sound"]

        if detector_data["pushover_body"] != "":
            body = detector_data["pushover_body"]
        else:
            body = config_data["pushover_settings"]["message_html_string"]

        # Preprocess timestamp
        timestamp = datetime.fromtimestamp(float(call_data.get("start_time", 0)))
        hr_timestamp = timestamp.strftime("%H:%M:%S %b %d %Y")

        detector_name = detector_data.get("detector_name")

        # Create a mapping
        mapping = {
            "detector_name": detector_name,
            "timestamp": hr_timestamp,
            "mp3_url": call_data.get("mp3_url"),
            "transcript": call_data.get("transcript")
        }

        # Use the mapping to format the strings
        title = title.format_map(mapping)
        body = body.format_map(mapping)

        if config_data["pushover_settings"]["all_detector_group"] == 1:
            module_logger.debug("Sending Pushover All Detectors Group")
            if config_data["pushover_settings"]["all_detector_app_token"] and config_data["pushover_settings"]["all_detector_group_token"]:

                r = requests.post("https://api.pushover.net/1/messages.json", data={
                    "token": config_data["pushover_settings"]["all_detector_app_token"],
                    "user": config_data["pushover_settings"]["all_detector_group_token"],
                    "html": 1,
                    "message": body,
                    "title": title,
                    "sound": sound
                })
                if r.status_code == 200:
                    module_logger.debug("Pushover Successful: Group All")
                else:
                    module_logger.critical(f"Pushover Unsuccessful: Group All {r.text}")

            else:
                module_logger.critical("Missing Pushover APP or Group Token for All group")
        else:
            module_logger.debug("Pushover all detector group disabled.")

        if "pushover_app_token" in detector_data and "pushover_group_token" in detector_data:
            if detector_data["pushover_app_token"] and detector_data["pushover_group_token"]:
                module_logger.debug("Sending Pushover Detector Group")
                r = requests.post("https://api.pushover.net/1/messages.json", data={
                    "token": detector_data["pushover_app_token"],
                    "user": detector_data["pushover_group_token"],
                    "html": 1,
                    "message": body,
                    "title": title,
                    "sound": sound
                })
                if r.status_code == 200:
                    module_logger.debug(f"Pushover Successful: Group {detector_name}")
                else:
                    module_logger.critical(f"Pushover Unsuccessful: Group {detector_name} {r.text}")
            else:
                module_logger.critical("Missing Pushover APP or Group Token")
        else:
            module_logger.critical("Missing Pushover APP or Group Token")

    except Exception as e:
        module_logger.critical(f"Pushover Send Failure:\n {repr(e)}")
        traceback.print_exc()