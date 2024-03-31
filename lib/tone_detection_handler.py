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
    detection_matches = []
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
            scp_result = process_system_alert_scp(config_data, system_data, audio_file, audio_filename, call_data)
            if not scp_result.get("success"):
                result["success"] = False
                error_messages.append(scp_result.get("message"))

            email_result = process_system_alert_email(config_data, system_data, detection_matches, call_data)
            if not email_result.get("success"):
                result["success"] = False
                error_messages.append(email_result.get("message"))

    if len(error_messages) > 0:
        result["message"] = "Processed Detection with errors." + "; ".join(error_messages)

    if len(detection_matches) > 0:
        for match in detection_matches:
            del match["agency_config"]

    return {"success": result["success"], "message": result["message"], "matches": detection_matches}


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


def get_tolerance(agency, tone_key):
    """Calculate the tolerance for a tone."""
    return agency.get("tone_tolerance", 2) / 100.0 * agency.get(tone_key)


def is_within_range(tone, tone_range):
    """Check if the tone is within the given range."""
    return tone_range[0] <= tone <= tone_range[1]


def detect_quick_call(rd, agency_data, call_data):
    matches_found = []
    matches_ignored = []

    # Simplify the extraction of match_list
    match_list = [(tone['detected'][0], tone['detected'][1], tone["tone_id"])
                  for tone in call_data.get("tones", {}).get("two_tone", [])]

    # Get the list of excluded agency ids once for this agency
    qc_detector_list = get_active_detections_cache(rd, f"icad_current_detectors:{call_data.get('short_name')}")
    excluded_id_list = [t["agency_id"] for t in qc_detector_list]

    for agency in agency_data:
        a_tone, b_tone = agency.get("a_tone"), agency.get("b_tone")
        # Skip the agency if either a_tone or b_tone is missing
        if not a_tone or not b_tone:
            continue

        tolerance_a, tolerance_b = get_tolerance(agency, "a_tone"), get_tolerance(agency, "b_tone")
        detector_ranges = [(a_tone - tolerance_a, a_tone + tolerance_a), (b_tone - tolerance_b, b_tone + tolerance_b)]

        for tone in match_list:
            match_a, match_b = is_within_range(tone[0], detector_ranges[0]), is_within_range(tone[1],
                                                                                             detector_ranges[1])

            if match_a and match_b:
                is_ignored = agency.get("agency_id") in excluded_id_list
                match_data = {
                    "tone_id": tone[2],
                    "agency_name": agency.get('agency_name'),
                    "tones_matched": f'{tone[0]}, {tone[1]}',
                    "agency_config": agency,
                    "ignored": is_ignored
                }

                if not is_ignored:
                    matches_found.append(match_data)
                    excluded_id_list.append(agency.get("agency_id"))
                    active_dict = {
                        "last_detected": time.time(),
                        "ignore_seconds": agency.get("ignore_time", 300),
                        "agency_id": agency.get("agency_id")
                    }
                    rd.rpush(f"icad_current_detectors:{call_data.get('short_name')}", active_dict)
                    module_logger.info(f"Match found for {agency.get('agency_name')}")
                else:
                    matches_ignored.append(match_data)
                    module_logger.warning(f"Ignoring {agency.get('agency_name')}")

    return matches_found, matches_ignored
