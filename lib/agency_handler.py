import json
import logging

from lib.quickcall_handler import add_quickcall_detector

module_logger = logging.getLogger("icad_tone_detection.agency_handler")


def get_agency_emails(db, agency_id):
    if not agency_id:
        return {"success": False, "message": "agency_id required", "result": []}

    query = f"SELECT * from agency_emails WHERE agency_id = %s"
    params = (agency_id,)
    result = db.execute_query(query, params)
    email_list = []
    if result["success"] and result["result"]:
        for res in result:
            email_list.append(res.get("email_address"))

    return {"success": False if not result.get("success") else True,
            "message": "Unknown Error" if not result.get("messsage") else result.get("message"), "result": email_list}


def get_agencies(db, system_ids=None, agency_id=None):
    # Base query
    query = """
        SELECT ag.*, qd.*, GROUP_CONCAT(ae.email_address SEPARATOR ',') as agency_emails
        FROM `agencies` ag
        LEFT JOIN icad.qc_detectors qd ON ag.agency_id = qd.agency_id
        LEFT JOIN icad.agency_emails ae ON ag.agency_id = ae.agency_id
        """

    # Conditions and parameters list
    conditions = []
    params = []

    # Check if system_ids are provided and append the condition and parameter
    if system_ids:
        # Prepare a string with placeholders for system_ids (e.g., %s, %s, ...)
        placeholders = ', '.join(['%s'] * len(system_ids))
        conditions.append(f"ag.system_id IN ({placeholders})")
        params.extend(system_ids)

    # Check if agency_id is provided and append the condition and parameter
    if agency_id is not None:
        conditions.append("ag.agency_id = %s")
        params.append(agency_id)

    # If there are conditions, append them to the query
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Add GROUP BY to ensure emails are aggregated per agency
    query += " GROUP BY ag.agency_id, qd.detector_id"

    # Convert params to a tuple
    params = tuple(params)

    # Execute the query with the parameters
    result = db.execute_query(query, params)

    # Process the result to convert agency_emails from string to list
    processed_result = []
    for row in result["result"]:
        # Convert the 'agency_emails' field from a comma-separated string to a list
        row_dict = dict(row)  # Assuming row is a dict-like object
        if row_dict['agency_emails']:
            row_dict['agency_emails'] = row_dict['agency_emails'].split(',')
        else:
            row_dict['agency_emails'] = []
        processed_result.append(row_dict)

    result["result"] = processed_result

    return result


def check_agency(db, system_id, agency_code):
    query = f"SELECT DISTINCT COUNT(agency_id) as total FROM agencies WHERE system_id = %s and agency_code = %s"
    params = (system_id, agency_code)
    check_result = db.execute_query(query, params)

    module_logger.warning(check_result)

    if check_result.get("result", [{}])[0].get("total", 0) >= 1:
        return True
    else:
        return False


def add_agency(db, agency_data):
    module_logger.warning(agency_data)
    if not agency_data:
        module_logger.warning(f"Agency Data Empty")
        return {"success": False, "message": "Agency Data Empty", "result": []}
    if not agency_data.get('system_id'):
        return {"success": False, "message": "No System ID Given.", "result": []}

    if check_agency(db, agency_data.get('system_id'), agency_data.get('agency_code')):
        return {"success": False, "message": "Agency with that agency code already exists.", "result": []}

    query = f"INSERT INTO `agencies` (system_id, agency_code, agency_name, mqtt_topic, mqtt_start_alert_message, mqtt_end_alert_message, mqtt_message_interval, pushover_group_token, pushover_app_token, pushover_subject, pushover_body, pushover_sound, webhook_url, webhook_headers, enable_facebook_post, enable_telegram_post) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    params = (
        agency_data.get("system_id"), agency_data.get("agency_code") or None, agency_data.get("agency_name") or None,
        agency_data.get("mqtt_topic") or None, agency_data.get("mqtt_start_alert_message") or None,
        agency_data.get("mqtt_end_alert_message") or None, agency_data.get("mqtt_message_interval") or 5.0,
        agency_data.get("pushover_group_token") or None, agency_data.get("pushover_app_token") or None,
        agency_data.get("pushover_subject") or None, agency_data.get("pushover_body") or None,
        agency_data.get("pushover_sound") or None, agency_data.get("webhook_url") or None,
        agency_data.get("webhook_headers") or json.dumps("{}"), agency_data.get("enable_facebook_post") or 0,
        agency_data.get("enable_telegram_post") or 0)
    result = db.execute_commit(query, params, return_row=True)
    return result


def update_agency_settings(db, agency_data):
    if not agency_data:
        module_logger.warning(f"Agency Data Empty")
        return {"success": False, "message": "No Agency Data.", "result": []}

    if not agency_data.get('system_id'):
        return {"success": False, "message": "No System ID Given.", "result": []}

    if not check_agency(db, agency_data.get('system_id'), agency_data.get('agency_code')):
        return {"success": False, "message": "Agency doesn't exist.", "result": []}

    query = f"UPDATE agencies SET agency_code = %s"


def delete_agency(db, system_id, agency_code):
    if not system_id:
        return {"success": False, "message": "No system ID given.", "result": []}
    if not agency_code:
        return {"success": False, "message": "No agency code given.", "result": []}

    if not check_agency(db, system_id, agency_code):
        return {"success": False, "message": "Agency Doesn't Exist", "result": []}

    query = f"DELETE FROM agencies WHERE system_id = %s AND agency_code = %s"
    params = (system_id, agency_code)
    result = db.execute_commit(query, params)
    return result


def import_agencies_from_detectors(db, agency_data, system_id):
    for agency in agency_data:
        agency_name = agency
        agency = agency_data[agency]

        mapped_agency_data = {
            "system_id": system_id,
            "agency_code": agency.get("station_number"),
            "agency_name": agency_name,
            "mqtt_topic": agency.get("mqtt_topic"),
            "mqtt_start_alert_message": agency.get("mqtt_start_message"),
            "mqtt_end_alert_message": agency.get("mqtt_stop_message"),
            "mqtt_message_interval ": agency.get("mqtt_message_interval"),
            "pushover_group_token": agency.get("pushover_group_token"),
            "pushover_app_token": agency.get("pushover_app_token"),
            "pushover_subject": agency.get("pushover_subject"),
            "pushover_body": agency.get("pushover_body"),
            "pushover_sound": agency.get("pushover_sound"),
            "webhook_url": agency.get("webhook_url") or None,
            "webhook_headers": agency.get("webhook_headers") or {},
            "enable_facebook_post": agency.get("post_to_facebook"),
            "enable_telegram_post": agency.get("post_to_telegram")
        }

        agency_result = add_agency(db, mapped_agency_data)
        if not agency_result["success"] or not agency_result["result"]:
            module_logger.error("Error Adding Agency.")
            return False

        qc_detector_data = {"a_tone": agency.get("a_tone"),
                            "b_tone": agency.get("b_tone"), "tone_tolerance": agency.get("tone_tolerance"),
                            "ignore_time": agency.get("ignore_time")}

        qc_result = add_quickcall_detector(db, agency_result.get("result"), qc_detector_data)
        if not qc_result["success"] or not qc_result["result"]:
            module_logger.error("Error Adding Agency QC Detector")
            return False

    return True
