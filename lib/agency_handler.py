import json
import logging
import traceback

from lib.quickcall_handler import add_quickcall_detector

module_logger = logging.getLogger("icad_tone_detection.agency_handler")


class UpdateEmailException(Exception):
    """Exception for errors updating agency alert emails."""
    pass


class DetectorUpdateException(Exception):
    """Exception for errors updating agency detectors."""
    pass


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
        SELECT ag.*, qd.detector_id, qd.a_tone, qd.b_tone, qd.c_tone, qd.d_tone, qd.tone_tolerance, qd.ignore_time, GROUP_CONCAT(ae.email_address SEPARATOR ',') as agency_emails
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
        elif row_dict['webhook_headers']:
            row_dict['webhook_headers'] = json.loads(row_dict['webhook_headers'])
        else:
            row_dict['agency_emails'] = []
        processed_result.append(row_dict)

    result["result"] = processed_result

    return result


def check_agency(db, system_id, agency_id):
    query = f"SELECT DISTINCT COUNT(agency_id) as total FROM agencies WHERE system_id = %s and agency_id = %s"
    params = (system_id, agency_id)
    check_result = db.execute_query(query, params)

    if check_result.get("result", [{}])[0].get("total", 0) >= 1:
        return True
    else:
        return False


def check_agency_qc_detector(db, agency_id):
    query = f"SELECT COUNT(*) as total_qc_detectors from qc_detectors WHERE agency_id = %s"
    params = (agency_id,)
    check_result = db.execute_query(query, params, fetch_mode="one")
    return check_result


def add_agency(db, agency_data):
    if not agency_data:
        module_logger.warning(f"Agency Data Empty")
        return {"success": False, "message": "Agency Data Empty", "result": []}
    if not agency_data.get('system_id'):
        return {"success": False, "message": "No System ID Given.", "result": []}

    query = f"INSERT INTO `agencies` (system_id, agency_code, agency_name, mqtt_topic, mqtt_start_alert_message, mqtt_end_alert_message, mqtt_message_interval, pushover_group_token, pushover_app_token, pushover_subject, pushover_body, pushover_sound, webhook_url, webhook_headers, enable_facebook_post, enable_telegram_post) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    params = (
        agency_data.get("system_id"), agency_data.get("agency_code") or None, agency_data.get("agency_name") or None,
        agency_data.get("mqtt_topic") or None, agency_data.get("mqtt_start_alert_message") or None,
        agency_data.get("mqtt_end_alert_message") or None, agency_data.get("mqtt_message_interval") or 5.0,
        agency_data.get("pushover_group_token") or None, agency_data.get("pushover_app_token") or None,
        agency_data.get("pushover_subject") or None, agency_data.get("pushover_body") or None,
        agency_data.get("pushover_sound") or None, agency_data.get("webhook_url") or None,
        json.dumps(agency_data.get("webhook_headers")) or json.dumps({}), agency_data.get("enable_facebook_post") or 0,
        agency_data.get("enable_telegram_post") or 0)
    add_result = db.execute_commit(query, params, return_row=True)
    if not add_result.get("success"):
        return add_result

    agency_data["agency_id"] = add_result["result"]

    add_detector_result = add_agency_detectors(db, agency_data)
    if not add_detector_result.get("success"):
        return add_detector_result

    add_email_result = add_agency_alert_emails(db, agency_data.get("agency_id"), agency_data.get("alert_emails"))
    if not add_email_result.get("success"):
        return add_result

    return {"success": True, "message": f"Added Agency {agency_data.get('agency_name')}"}


def add_agency_detectors(db, agency_data):
    query = f"INSERT INTO qc_detectors (agency_id, a_tone, b_tone, c_tone, d_tone, tone_tolerance, ignore_time) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    params = (agency_data.get("agency_id"), agency_data.get("a_tone") or None, agency_data.get("b_tone") or None,
              agency_data.get("c_tone") or None, agency_data.get("d_tone") or None,
              agency_data.get("tone_tolerance", 2), agency_data.get("ignore_time", 300))
    qc_insert_result = db.execute_commit(query, params)
    return qc_insert_result


def add_agency_alert_emails(db, agency_id, email_string):
    try:
        if not email_string:
            return {"success": True, "message": "No emails to add."}

        new_emails = set(email_string.split(','))
        for email in new_emails:
            add_result = db.execute_commit("INSERT INTO agency_emails (agency_id, email_address) VALUES (%s, %s)",
                                           (agency_id, email))
            if not add_result.get("success"):
                raise UpdateEmailException(f'Error adding email {email} to agency alert email: {add_result.get("message")}')

    except UpdateEmailException as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"An unexpected error occurred adding new emails: {str(e)}"}


def update_agency_settings(db, agency_data):
    if not agency_data:
        module_logger.warning(f"Agency Data Empty")
        return {"success": False, "message": "No Agency Data.", "result": []}

    if not agency_data.get('system_id'):
        return {"success": False, "message": "No System ID Given.", "result": []}

    if not check_agency(db, agency_data.get('system_id'), agency_data.get('agency_id')):
        return {"success": False, "message": "Agency doesn't exist.", "result": []}

    query = (f"UPDATE agencies SET agency_code = %s, agency_name = %s, mqtt_topic = %s, mqtt_start_alert_message = %s, "
             f"mqtt_end_alert_message = %s, mqtt_message_interval = %s, pushover_group_token = %s, "
             f"pushover_app_token = %s, pushover_subject = %s, pushover_body = %s, pushover_sound = %s, "
             f"webhook_url = %s, webhook_headers = %s, enable_facebook_post = %s, enable_telegram_post = %s "
             f"WHERE agency_id = %s")
    params = (agency_data.get("agency_code"), agency_data.get("agency_name"), agency_data.get("mqtt_topic") or None,
              agency_data.get("mqtt_start_alert_message") or None, agency_data.get("mqtt_end_alert_message") or None,
              agency_data.get("mqtt_message_interval") or 5.0, agency_data.get("pushover_group_token") or None,
              agency_data.get("pushover_app_token") or None, agency_data.get("pushover_subject") or None,
              agency_data.get("pushover_body") or None, agency_data.get("pushover_sound") or None,
              agency_data.get("webhook_url") or None,
              json.dumps(agency_data.get("webhook_headers", {})) or json.dumps({}),
              agency_data.get("enable_facebook_post") or 0,
              agency_data.get("enable_telegram_post") or 0, agency_data.get("agency_id"))
    update_agency_result = db.execute_commit(query, params)

    if not update_agency_result.get("success"):
        return update_agency_result

    update_agency_emails = update_agency_alert_emails(db, agency_data.get("agency_id"), agency_data.get("alert_emails"))
    if not update_agency_emails:
        return update_agency_emails

    update_agency_detectors(db, agency_data)
    if not update_agency_detectors:
        return update_agency_detectors

    return {"success": True, "message": f"Updated Agency {agency_data.get('agency_name')}"}


def update_agency_detectors(db, agency_data):
    try:
        qc_result = check_agency_qc_detector(db, agency_data.get("agency_id"))
        if not qc_result.get("success"):
            raise DetectorUpdateException(f'Error checking if Agency Exists: {qc_result.get("message")}')

        if qc_result.get("success") and qc_result.get("result", {}).get("total_qc_detectors", 0) < 1:
            query = f"INSERT INTO qc_detectors (agency_id, a_tone, b_tone, c_tone, d_tone, tone_tolerance, ignore_time)VALUES (%s, %s, %s, %s, %s, %s, %s)"
            params = (
                agency_data.get("agency_id"), agency_data.get("a_tone") or None, agency_data.get("b_tone") or None,
                agency_data.get("c_tone") or None, agency_data.get("d_tone") or None,
                agency_data.get("tone_tolerance") or 2,
                agency_data.get("ignore_time") or 300)
        else:
            query = f"UPDATE qc_detectors SET a_tone = %s, b_tone =%s, c_tone =%s, d_tone = %s, tone_tolerance = %s, ignore_time = %s WHERE agency_id = %s"
            params = (
                agency_data.get("a_tone") or None, agency_data.get("b_tone") or None, agency_data.get("c_tone") or None,
                agency_data.get("d_tone") or None,
                agency_data.get("tone_tolerance") or 2, agency_data.get("ignore_time") or 300,
                agency_data.get("agency_id"))

        update_result = db.execute_commit(query, params)
        if not update_result.get("success"):
            raise DetectorUpdateException(f'Error updating Agency Settings: {update_result.get("message")}')

        return update_result

    except DetectorUpdateException as e:
        return {"success": False, "message": str(e)}

    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"An unexpected error occurred while updating detectors: {str(e)}"}


def update_agency_alert_emails(db, agency_id, email_string):
    try:
        if not email_string:
            return {"success": True, "message": "No email to update."}

        new_emails = {email.strip() for email in email_string.split(',') if email.strip()}

        # Fetch the current emails from the database
        get_result = db.execute_query("SELECT email_address FROM agency_emails WHERE agency_id = %s", (agency_id,))
        if not get_result.get("success"):
            raise UpdateEmailException(get_result.get("message"))

        current_emails = {email_data.get("email_address") for email_data in get_result.get("result")} if get_result.get(
            "result") else set()

        emails_to_add = new_emails - current_emails
        emails_to_remove = current_emails - new_emails

        for email in emails_to_add:
            add_result = db.execute_commit("INSERT INTO agency_emails (agency_id, email_address) VALUES (%s, %s)",
                                           (agency_id, email))
            if not add_result.get("success"):
                raise UpdateEmailException(add_result.get("message"))

        for email in emails_to_remove:
            remove_result = db.execute_commit("DELETE FROM agency_emails WHERE agency_id = %s AND email_address = %s",
                                              (agency_id, email))
            if not remove_result.get("success"):
                raise UpdateEmailException(remove_result.get("message"))

        return {"success": True, "message": "Emails updated successfully."}

    except UpdateEmailException as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"An unexpected error occurred updating agency alert emails: {str(e)}"}


def delete_agency(db, system_id, agency_id):
    if not system_id:
        return {"success": False, "message": "No system ID given.", "result": []}
    if not agency_id:
        return {"success": False, "message": "No agency code given.", "result": []}

    if not check_agency(db, system_id, agency_id):
        return {"success": False, "message": "Agency Doesn't Exist", "result": []}

    query = f"DELETE FROM agencies WHERE system_id = %s AND agency_code = %s"
    params = (system_id, agency_id)
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
