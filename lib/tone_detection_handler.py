import logging
import threading
import time

import redis

from lib.agency_handler import get_agencies
from lib.audio_file_handler import process_detection_audio
from lib.detection_action_handler import process_finder_action_scp, \
    process_finder_action_email, process_finder_action_webhook, process_finder_action_database, \
    process_system_alert_scp, process_system_alert_email
from lib.helpers import save_posted_files
from lib.system_handler import get_systems

module_logger = logging.getLogger('icad_tone_detection.tone_detection')


def process_tone_detection(db, rd, config_data, audio_file, audio_filename, json_filename, call_data):
    error_messages = []
    detection_mode = config_data.get("general", {}).get('detection_mode', 0)
    result = {"success": True, "message": "Processed Detections"}
    if detection_mode in [1, 3]:
        save_result = save_posted_files(audio_file, audio_filename, json_filename, call_data)
        if not save_result.get("success"):
            result["success"] = False
            error_messages.append(save_result.get("message"))

        mysql_result = process_finder_action_database(db, config_data, detection_mode, call_data)
        if not mysql_result.get("success"):
            result["success"] = False
            error_messages.append(mysql_result.get("message"))

        scp_result = process_finder_action_scp(config_data, audio_file, audio_filename, call_data)
        if not scp_result.get("success"):
            result["success"] = False
            error_messages.append(scp_result.get("message"))

        email_result = process_finder_action_email(config_data, call_data)
        if not email_result.get("success"):
            result["success"] = False
            error_messages.append(email_result.get("message"))

        webhook_result = process_finder_action_webhook(config_data, call_data)
        if not webhook_result.get("success"):
            result["success"] = False
            error_messages.append(webhook_result.get("message"))

    if detection_mode in [2, 3]:
        match_result = get_agency_matches(db, rd, call_data)
        if not match_result.get("success"):
            result["success"] = False
            error_messages.append(match_result.get("message"))

        system_data = match_result.get("system_data")
        agency_data = match_result.get("agency_data")
        detection_matches = match_result.get("result")

        if len(detection_matches) > 0:
            scp_result = process_system_alert_scp(system_data, audio_file, audio_filename, call_data)
            if not scp_result.get("success"):
                result["success"] = False
                error_messages.append(scp_result.get("message"))

            email_result = process_system_alert_email(system_data, detection_matches, call_data)
            if not email_result.get("success"):
                result["success"] = False
                error_messages.append(email_result.get("message"))

    if len(error_messages) > 0:
        result["message"] = "Processed Detection with errors." + "; ".join(error_messages)

    return {"success": result["success"], "message": result["message"]}


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


def get_agency_matches(db, rd, call_data):
    system_data = get_systems(db, system_short_name=call_data.get('short_name'))
    if not system_data.get("success", False) or len(system_data.get("result", [])) < 1:
        module_logger.error(f"Error retrieving: System Data {system_data}")
        return {"success": False,
                "message": f"Unable to retrieve system data for {call_data.get('short_name')}", "result": []}

    system_data = system_data.get("result")[0]

    agency_data = get_agencies(db, system_ids=[system_data.get("system_id")])
    if not agency_data.get("success", False) or len(agency_data.get("result", [])) < 1:
        return {"success": False,
                "message": f"Unable to retrieve agency data for {call_data.get('short_name')}", "result": []}

    matches_found, matches_ignored = detect_quick_call(rd, agency_data.get('result'), call_data)

    return {"success": True,
            "message": f"Got agency data for {call_data.get('short_name')}", "system_data": system_data,
            "agency_data": agency_data, "result": matches_found}


def detect_quick_call(rd, agency_data, call_data):
    matches_found = []
    matches_ignored = []

    match_list = [(tone['detected'][0], tone['detected'][1], tone["tone_id"]) for tone in
                  call_data.get("tones", {}).get("two_tone", [])]

    for agency in agency_data:
        if agency.get("a_tone", None) is None:
            continue
        if agency.get("b_tone", None) is None:
            continue

        qc_detector_list = get_active_detections_cache(rd,
                                                       f"icad_current_detectors:{call_data.get('short_name')}")

        module_logger.debug("qc_detector_list: {}".format(qc_detector_list))
        excluded_id_list = [t["agency_id"] for t in qc_detector_list]
        tolerance_a = agency.get("tone_tolerance", 2) / 100.0 * agency.get("a_tone")
        tolerance_b = agency.get("tone_tolerance", 2) / 100.0 * agency.get("b_tone")
        detector_ranges = [
            (agency.get("a_tone") - tolerance_a, agency.get("a_tone") + tolerance_a),
            (agency.get("b_tone") - tolerance_b, agency.get("b_tone") + tolerance_b)
        ]
        for tone in match_list:
            match_a = detector_ranges[0][0] <= tone[0] <= detector_ranges[0][1]
            match_b = detector_ranges[1][0] <= tone[1] <= detector_ranges[1][1]
            if match_a and match_b:
                module_logger.info(f"Match found for {agency.get('agency_name')}")
                match_data = {"tone_id": tone[2], "agency_name": agency.get('agency_name'),
                              "tones_matched": f'{tone[0]}, {tone[1]}',
                              "agency_config": agency,
                              "ignored": True if agency.get("agency_id") in excluded_id_list else False}

                if not agency.get("agency_id") in excluded_id_list:
                    matches_found.append(match_data)
                    active_dict = {"last_detected": time.time(), "ignore_seconds": agency.get("ignore_time", 300),
                                   "agency_id": agency.get("agency_id")}

                    rd.rpush(f"icad_current_detectors:{call_data.get('short_name')}", active_dict)
                else:
                    matches_ignored.append(match_data)
                    module_logger.warning(f"Ignoring {agency.get('agency_name')}")

    return matches_found, matches_ignored


class ToneDetection:
    """Matches tones that were extracted to a set detector"""

    def __init__(self, config_data, call_data):
        self.config_data = config_data
        self.call_data = call_data

    def get_agency_matches(self, db, rd):
        system_data = get_systems(db, system_short_name=self.call_data.get('short_name'))
        if not system_data.get("success", False) or len(system_data.get("result", [])) < 1:
            return {"success": False,
                    "message": f"Unable to retrieve system data for {self.call_data.get('short_name')}", "result": []}

        system_data = system_data.get("result")[0]

        agency_data = get_agencies(db, system_ids=[system_data.get("system_id")])
        if not agency_data.get("success", False) or len(agency_data.get("result", [])) < 1:
            return {"success": False,
                    "message": f"Unable to retrieve agency data for {self.call_data.get('short_name')}", "result": []}

    def detect_quick_call(self, rd):
        qc_detector_list = get_active_detections_cache(rd, "icad_current_detectors")
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
