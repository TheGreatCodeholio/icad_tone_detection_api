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

    return {"success": False if not result.get("success") else True, "message": "Unknown Error" if not result.get("messsage") else result.get("message"), "result": email_list}


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


def add_agency(db, agency_data):
    if not agency_data:
        module_logger.warning(f"Agency Data Empty")
        return
    query = f"INSERT INTO `agencies` (system_id, agency_code, agency_name, alert_email_subject, alert_email_body, mqtt_topic, mqtt_start_alert_message, mqtt_end_alert_message, mqtt_message_interval, pushover_group_token, pushover_app_token, pushover_subject_override, pushover_body_override, pushover_sound_override, agency_stream_url, enable_facebook_post) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    params = (agency_data.get("system_id"), agency_data.get("agency_code", None), agency_data.get("agency_name", None),
              agency_data.get("alert_email_subject", None), agency_data.get("alert_email_body", None),
              agency_data.get("mqtt_topic", None), agency_data.get("mqtt_start_alert_message", None),
              agency_data.get("mqtt_end_alert_message", None), agency_data.get("mqtt_message_interval", 5.0),
              agency_data.get("pushover_group_token", None), agency_data.get("pushover_app_token", None),
              agency_data.get("pushover_subject_override", None), agency_data.get("pushover_body_override", None),
              agency_data.get("pushover_sound_override", None), agency_data.get("agency_stream_url", None),
              agency_data.get("enable_facebook_post", 0))
    result = db.execute_commit(query, params, return_row=True)
    return result


def import_agencies_from_detectors(db, agency_data, system_id):
    for agency in agency_data:
        agency_name = agency
        agency = agency_data[agency]

        mapped_agency_data = {
            "system_id": system_id,
            "agency_code": agency.get("station_number"),
            "agency_name": agency_name,
            "alert_email_subject": agency.get("alert_email_subject"),
            "alert_email_body": agency.get("alert_email_body"),
            "mqtt_topic": agency.get("mqtt_topic"),
            "mqtt_start_alert_message": agency.get("mqtt_start_message"),
            "mqtt_end_alert_message": agency.get("mqtt_stop_message"),
            "mqtt_message_interval ": agency.get("mqtt_message_interval"),
            "pushover_group_token": agency.get("pushover_group_token"),
            "pushover_app_token": agency.get("pushover_app_token"),
            "pushover_subject_override": agency.get("pushover_subject"),
            "pushover_body_override": agency.get("pushover_body"),
            "pushover_sound_override ": agency.get("pushover_sound"),
            "agency_stream_url ": agency.get("stream_url"),
            "enable_facebook_post ": agency.get("post_to_facebook")
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
