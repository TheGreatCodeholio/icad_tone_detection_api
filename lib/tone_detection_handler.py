import logging
import threading
import time

import redis

from lib.audio_file_handler import process_detection_audio
from lib.detection_action_handler import process_alert_actions

module_logger = logging.getLogger('icad_tone_detection.tone_detection')


def add_active_detections_cache(rd, list_name, dict_data):
    """
    Add a dictionary to a Redis list.

    Args:
        rd (RedisCache): An instance of the RedisCache class.
        list_name (str): The name of the Redis list.
        dict_data (dict): The dictionary to add to the list.

    Returns:
        bool: True if successful, False otherwise.
    """

    try:
        rd.client.rpush(list_name, dict_data)
        return True
    except redis.RedisError as error:
        module_logger.error(f"Error adding dict to list {list_name}: {error}")
        return False


def delete_active_detections_cache(rd, list_name):
    """
    Clear a Redis list.

    Args:
        rd (RedisCache): An instance of the RedisCache class.
        list_name (str): The name of the Redis list to clear.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        rd.delete(list_name)
        return True
    except redis.RedisError as error:
        module_logger.error(f"Error clearing list {list_name}: {error}")
        return False


def get_active_detections_cache(rd, list_name):
    """
    Get all dictionaries from a Redis list.

    Args:
        rd (RedisCache): An instance of the RedisCache class.
        list_name (str): The name of the Redis list.

    Returns:
        list: A list of dictionaries, or an empty list if an error occurs.
    """
    try:
        result = rd.lrange(list_name, 0, -1)
        if result['success']:
            return result.get("result", [])
        else:
            return []
    except redis.RedisError as error:
        module_logger.error(f"Error retrieving list {list_name}: {error}")
        return []


class ToneDetection:
    """Matches tones that were extracted to a set detector"""

    def __init__(self, config_data, detector_data, detection_data):
        self.config_data = config_data
        self.detector_data = detector_data
        self.detection_data = detection_data

    def detect_quick_call(self, rd):
        qc_detector_list = []

        matches_found = []
        matches_ignored = []
        tone_mode = self.config_data["tone_extraction"]["quick_call"].get("tone_mode", "actual")
        if tone_mode != "exact" and tone_mode != "actual":
            tone_mode = "actual"

        match_list = [(tone[tone_mode][0], tone[tone_mode][1], tone["tone_id"]) for tone in
                      self.detection_data["quick_call"]]

        if not match_list:
            return self.detection_data

        for detector in self.detector_data:
            qc_detector_list = get_active_detections_cache(rd, "icad_current_detectors")
            detector_config = self.detector_data[detector]
            excluded_id_list = [t["detector_id"] for t in qc_detector_list]
            tolerance_a = detector_config["tone_tolerance"] / 100.0 * detector_config["a_tone"]
            tolerance_b = detector_config["tone_tolerance"] / 100.0 * detector_config["b_tone"]
            detector_ranges = [
                (detector_config["a_tone"] - tolerance_a, detector_config["a_tone"] + tolerance_a),
                (detector_config["b_tone"] - tolerance_b, detector_config["b_tone"] + tolerance_b)
            ]
            for tone in match_list:
                match_a = detector_ranges[0][0] <= tone[0] <= detector_ranges[0][1]
                match_b = detector_ranges[1][0] <= tone[1] <= detector_ranges[1][1]
                if match_a and match_b:
                    module_logger.info(f"Match found for {detector}")
                    match_data = {"tone_id": tone[2], "detector_name": detector,
                                  "tones_matched": f'{tone[0]}, {tone[1]}',
                                  "detector_config": detector_config,
                                  "ignored": True if detector_config[
                                                         "detector_id"] in excluded_id_list else False}

                    if not detector_config["detector_id"] in excluded_id_list:
                        matches_found.append(match_data)
                        active_dict = {"last_detected": time.time(), "ignore_seconds": detector_config["ignore_time"],
                                       "detector_id": detector_config["detector_id"]}

                        rd.rpush("icad_current_detectors", active_dict)
                    else:
                        matches_ignored.append(match_data)
                        module_logger.warning(f"Ignoring {detector}")

        self.detection_data["matches"] = matches_found
        self.detection_data["ignored_matches"] = matches_ignored

        if len(matches_found) >= 1:
            detection_data_processed = process_detection_audio(self.config_data, self.detection_data)
            self.detection_data = detection_data_processed

            for dd in self.detection_data:
                module_logger.info(f"Starting Detection Action Thread for {dd}")
                # threading.Thread(target=process_alert_actions, args=(
                #     self.config_data, dd)).start()
        else:
            module_logger.warning(f"No matches for {match_list} found in detectors.")
        module_logger.warning(f"Active Detector List: {qc_detector_list}")
        return self.detection_data
