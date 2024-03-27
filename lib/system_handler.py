import json
import logging
import traceback
import uuid

from lib.helpers import encrypt_password, is_fernet_token, decrypt_password

module_logger = logging.getLogger("icad_tone_detection.system_handler")


def get_systems(db, system_id=None, system_short_name=None):
    # Base query without GROUP_CONCAT for emails
    base_query = """
SELECT 
    rs.system_id,
    rs.system_short_name,
    rs.system_name,
    rs.system_county,
    rs.system_state,
    rs.system_fips,
    rs.system_api_key,
    ses.email_enabled,
    ses.smtp_hostname,
    ses.smtp_port,
    ses.smtp_username,
    ses.smtp_password,
    ses.smtp_security,
    ses.email_address_from,
    ses.email_text_from,
    ses.email_alert_subject,
    ses.email_alert_body,
    sps.pushover_enabled,
    sps.pushover_all_group_token,
    sps.pushover_all_app_token,
    sps.pushover_body,
    sps.pushover_subject,
    sps.pushover_sound,
    sfs.facebook_enabled,
    sfs.facebook_page_id,
    sfs.facebook_page_token,
    sfs.facebook_group_id,
    sfs.facebook_group_token,
    sfs.facebook_comment_enabled,
    sfs.facebook_post_body,
    sfs.facebook_comment_body,
    sts.telegram_enabled,
    sts.telegram_bot_token,
    sts.telegram_channel_id,
    sss.stream_url,
    sws.webhook_enabled,
    sws.webhook_url,
    sws.webhook_headers,
    s.scp_enabled,
    s.scp_host,
    s.scp_port,
    s.scp_username,
    s.scp_password,
    s.scp_remote_folder,
    s.web_url_path,
    s.scp_archive_days,
    s.scp_private_key,
    sms.mqtt_enabled,
    sms.mqtt_hostname,
    sms.mqtt_port,
    sms.mqtt_username,
    sms.mqtt_password
FROM radio_systems rs
LEFT JOIN system_email_settings ses ON rs.system_id = ses.system_id
LEFT JOIN system_pushover_settings sps ON rs.system_id = sps.system_id
LEFT JOIN system_facebook_settings sfs ON rs.system_id = sfs.system_id
LEFT JOIN system_telegram_settings sts ON rs.system_id = sts.system_id
LEFT JOIN system_stream_settings sss ON rs.system_id = sss.system_id
LEFT JOIN system_webhook_settings sws ON rs.system_id = sws.system_id
LEFT JOIN system_mqtt_settings sms on rs.system_id = sms.system_id
LEFT JOIN system_scp_settings s ON rs.system_id = s.system_id
"""

    # Building the WHERE clause based on provided arguments
    where_clauses = []
    parameters = []
    if system_id:
        where_clauses.append("rs.system_id = %s")
        parameters.append(system_id)
    if system_short_name:
        where_clauses.append("rs.system_short_name = %s")
        parameters.append(system_short_name)

    if where_clauses:
        where_clause = "WHERE " + " AND ".join(where_clauses)
        final_query = f"{base_query} {where_clause}"
    else:
        final_query = base_query

    systems_result = db.execute_query(final_query, tuple(parameters) if parameters else None)
    if not systems_result.get("success"):
        module_logger.error("Systems Result Empty")

    # For each system, fetch its alert emails and concatenate them into a comma-separated string
    email_query = """
SELECT GROUP_CONCAT(email SEPARATOR ', ') AS alert_emails
FROM system_alert_emails
WHERE system_id = %s
"""

    for system in systems_result['result']:
        email_result = db.execute_query(email_query, (system['system_id'],), fetch_mode="one")
        if not email_result.get("success"):
            module_logger.warning("Email Result Empty")
        # Add the concatenated emails to the system's dictionary
        system['system_alert_emails'] = email_result['result']['alert_emails'] if email_result['result'] else ''
        system['webhook_headers'] = json.loads(system.get("webhook_headers", {}) or {})

    return systems_result


def check_for_system(db, system_name=None, system_id=None):
    if not system_id:
        query = f"SELECT * FROM radio_systems WHERE system_name = %s"
        params = (system_name,)
    else:
        query = f"SELECT * FROM radio_systems WHERE system_id = %s"
        params = (system_id,)

    result = db.execute_query(query, params, fetch_mode='one')
    return result.get("result", {})


def add_system(db, system_data):
    if not system_data:
        module_logger.warning(f"System Data Empty")
        return {"success": False, "message": "System Data Empty", "result": []}

    # Check if the system already exists
    result = check_for_system(db, system_name=system_data.get('system_name'))
    if result:
        module_logger.warning(f"System already exists: {result}")
        return {"success": False, "message": f"System already exists: {result}", "result": []}

    # Generate a unique API key for the new system
    api_key = str(uuid.uuid4())
    query = "INSERT INTO `radio_systems` (system_short_name, system_name, system_county, system_state, system_fips, system_api_key) VALUES (%s, %s, %s, %s, %s, %s)"
    params = (
        system_data.get('system_short_name') or None, system_data.get('system_name') or None, system_data.get("system_county") or None, system_data.get("system_state") or None,
        system_data.get("system_fips") or None, api_key
    )

    # Execute the query to insert the new system
    result = db.execute_commit(query, params, return_row=True)

    if result['success'] and result['result']:
        system_id = result['result']  # Assuming this returns the new system's ID
        module_logger.info(f"New system added with ID: {system_id}")

        # Insert default settings for the new system
        insert_default_system_settings(db, system_id)
        module_logger.info("Default settings inserted for the new system.")
        result['message'] = f"New system added with ID: {system_id}"
    else:
        result['success'] = False
        system_id = None
        result['message'] = "Failed to add new system."
        module_logger.error("Failed to add new system.")

    return {"success": result['success'], "message": result.get("message"), "result": system_id}


def update_system(db, system_data, config_data):
    if not system_data:
        module_logger.warning(f"System Data Empty")
        return {"success": False, "message": "System Data Empty", "result": []}

    result = check_for_system(db, system_id=system_data.get('system_id'))
    module_logger.warning(result)

    query = f"UPDATE `radio_systems` SET system_short_name = %s, system_name = %s, system_county = %s, system_state = %s, system_fips = %s, system_api_key = %s WHERE system_id = %s"
    params = (
        system_data.get('system_short_name') or None, system_data.get('system_name') or None, system_data.get("system_county") or None,
        system_data.get("system_state") or None,
        system_data.get("system_fips") or None, system_data.get('api_key') or None, system_data.get('system_id'))
    result = db.execute_commit(query, params)
    return result


def update_system_settings(db, system_data, config_data):
    if not system_data:
        module_logger.warning(f"System Data Empty")
        return {"success": False, "message": "System Data Empty", "result": []}
    try:

        result = check_for_system(db, system_id=system_data.get('system_id'))
        module_logger.warning(result)

        query = f"UPDATE `radio_systems` SET system_short_name = %s, system_name = %s, system_county = %s, system_state = %s, system_fips = %s, system_api_key = %s WHERE system_id = %s"
        params = (
            system_data.get('system_short_name') or None, system_data.get('system_name') or None, system_data.get("system_county") or None,
            system_data.get("system_state") or None,
            system_data.get("system_fips") or None, system_data.get('system_api_key') or None,
            system_data.get('system_id'))
        db.execute_commit(query, params)

        smtp_password = system_data.get("smtp_password") or None

        if smtp_password is not None:
            if not is_fernet_token(smtp_password, config_data):
                smtp_password = encrypt_password(smtp_password, config_data)

        # Insert updated email settings
        db.execute_commit(
            "UPDATE system_email_settings SET email_enabled = %s, smtp_hostname = %s, smtp_port = %s, smtp_username = %s, "
            "smtp_password = %s, smtp_security = %s, email_address_from = %s, email_text_from = %s, "
            "email_alert_subject = %s, email_alert_body = %s WHERE system_id = %s",
            (
                system_data.get("email_enabled") or 0, system_data.get("smtp_hostname") or None,
                system_data.get("smtp_port") or None, system_data.get("smtp_username") or None,
                smtp_password, system_data.get("smtp_security") or 2,
                system_data.get("email_address_from") or "dispatch@example.com",
                system_data.get("email_text_from") or "iCAD Dispatch",
                system_data.get("email_alert_subject") or "Dispatch Alert",
                system_data.get("email_alert_body") or
                "{agency_list} Alert at {timestamp}<br><br>{transcript}<br><br><a href=\"{audio_url}\">Click for Dispatch Audio</a><br><br><a href=\"{stream_url}\">Click Audio Stream</a>",
                system_data.get("system_id"))
        )

        update_system_alert_emails(db, system_data.get("system_id"), system_data.get("system_alert_emails"))

        mqtt_password = system_data.get("mqtt_password") or None

        if mqtt_password is not None:
            if not is_fernet_token(mqtt_password, config_data):
                mqtt_password = encrypt_password(mqtt_password, config_data)

        # Update MQTT settings
        db.execute_commit(
            "UPDATE system_mqtt_settings SET mqtt_enabled = %s, mqtt_hostname = %s, mqtt_port = %s, mqtt_username = %s, mqtt_password = %s WHERE system_id = %s",
            (system_data.get("mqtt_enabled") or 0, system_data.get("mqtt_hostname") or None,
             system_data.get("mqtt_port") or 1883, system_data.get("mqtt_username") or None,
             mqtt_password, system_data.get("system_id")
             )
        )

        # Update Pushover settings
        db.execute_commit(
            "UPDATE system_pushover_settings SET pushover_enabled = %s, pushover_all_group_token = %s, pushover_all_app_token = %s, pushover_body = %s, pushover_subject = %s, pushover_sound = %s WHERE system_id = %s",
            (system_data.get("pushover_enabled", 0), system_data.get("pushover_all_group_token") or None,
             system_data.get("pushover_all_app_token") or None,
             system_data.get("pushover_body") or
             "<font color=\"red\"><b>{agency_name}</b></font><br><br><a href=\"{audio_url}\">Click for Dispatch Audio</a><br><br><a href=\"{stream_url}\">Click Audio Stream</a>",
             system_data.get("pushover_subject") or "Dispatch Alert", system_data.get("pushover_sound") or "pushover",
             system_data.get("system_id")
             )
        )

        # Update facebook settings
        db.execute_commit(
            "UPDATE system_facebook_settings SET facebook_enabled = %s, facebook_page_id = %s, facebook_page_token = %s, "
            "facebook_group_id = %s, facebook_group_token = %s, facebook_comment_enabled = %s, facebook_post_body = %s, "
            "facebook_comment_body = %s  WHERE system_id = %s",
            (system_data.get("facebook_enabled") or 0, system_data.get("facebook_page_id") or None,
             system_data.get("facebook_page_token") or None, system_data.get("facebook_group_id") or None,
             system_data.get("facebook_group_token") or None, system_data.get("facebook_comment_enabled") or 0,
             system_data.get(
                 "facebook_post_body") or "{timestamp} Departments:\n{agency_list}\n\nDispatch Audio:\n{audio_url}",
             system_data.get("facebook_comment_body") or "{transcript}{stream_url}",
             system_data.get("system_id"))
            )

        # Update telegram settings
        db.execute_commit(
            "UPDATE system_telegram_settings SET telegram_enabled = %s, telegram_bot_token = %s, telegram_channel_id = %s WHERE system_id = %s",
            (system_data.get("telegram_enabled") or 0, system_data.get("telegram_bot_token") or None,
             system_data.get("telegram_channel_id") or None, system_data.get("system_id"))
        )

        # Update webhook settings
        db.execute_commit(
            "UPDATE system_webhook_settings SET webhook_enabled = %s, webhook_url = %s, webhook_headers = %s WHERE system_id = %s",
            (system_data.get("webhook_enabled") or 0, system_data.get("webhook_url") or None,
             json.dumps(system_data.get("webhook_headers", {})), system_data.get("system_id"))
        )

        # Update stream settings
        db.execute_commit(
            "UPDATE system_stream_settings SET stream_url = %s WHERE system_id = %s",
            (system_data.get("stream_url") or None, system_data.get("system_id"))
        )

        scp_password = system_data.get("scp_password") or None

        if scp_password is not None:
            if not is_fernet_token(scp_password, config_data):
                scp_password = encrypt_password(scp_password, config_data)

        # Update system scp settings
        db.execute_commit(
            "UPDATE system_scp_settings SET scp_enabled = %s, scp_host = %s, scp_port = %s, scp_username = %s, "
            "scp_password = %s, scp_remote_folder = %s, web_url_path = %s, scp_archive_days = %s, "
            "scp_private_key = %s WHERE system_id = %s",
            (system_data.get("scp_enabled") or 0, system_data.get("scp_host") or None, system_data.get("scp_port") or None,
             system_data.get("scp_username") or None, scp_password, system_data.get("scp_remote_folder") or None,
             system_data.get("web_url_path") or None, system_data.get("scp_archive_days") or 0,
             system_data.get("scp_private_key") or None, system_data.get("system_id"))
        )
        module_logger.info(f"Settings updated successfully for system_id: {system_data.get('system_id')}")

        return {'success': True,
                'message': f"Settings updated successfully for system_id: {system_data.get('system_id')}"}

    except Exception as e:
        traceback.print_exc()
        module_logger.error(
            f"Failed to update settings for system_id: {system_data.get('system_id')}. Error: {e}")
        return {'success': False,
                'message': f"Failed to update settings for system_id: {system_data.get('system_id')}. Error: {e}"}


def update_system_alert_emails(db, system_id, email_string):
    # Convert the comma-separated string into a set of emails
    if email_string:
        new_emails = {email.strip() for email in email_string.split(',') if email.strip()}
    else:
        return True

    # Fetch the current emails from the database
    current_emails = set()
    get_result = db.execute_query("SELECT email FROM system_alert_emails WHERE system_id = %s", (system_id,))
    if get_result.get("success") and get_result.get("result"):
        for email_data in get_result.get("result"):
            current_emails.add(email_data.get("email"))

    # Determine emails to add and remove
    emails_to_add = new_emails - current_emails
    emails_to_remove = current_emails - new_emails

    # Add new emails
    for email in emails_to_add:
        db.execute_commit("INSERT INTO system_alert_emails (system_id, email) VALUES (%s, %s)", (system_id, email))

    # Remove old emails
    for email in emails_to_remove:
        db.execute_commit("DELETE FROM system_alert_emails WHERE system_id = %s AND email = %s", (system_id, email))


def insert_default_system_settings(db, system_id):
    try:
        # Insert default email settings
        db.execute_commit(
            "INSERT INTO system_email_settings (system_id, email_alert_body) VALUES (%s, %s)",
            (system_id,
             "{agency_list} Alert at {timestamp}<br><br>{transcript}<br><br><a href=\"{audio_url}\">Click for Dispatch Audio</a><br><br><a href=\"{stream_url}\">Click Audio Stream</a>")
        )

        # Insert default MQTT settings
        db.execute_commit(
            "INSERT INTO system_mqtt_settings (system_id) VALUES (%s)",
            (system_id,)
        )

        # Insert default pushover settings
        db.execute_commit(
            "INSERT INTO system_pushover_settings (system_id, pushover_body) VALUES (%s, %s)",
            (system_id,
             "<font color=\"red\"><b>{agency_name}</b></font><br><br><a href=\"{audio_url}\">Click for Dispatch Audio</a><br><br><a href=\"{stream_url}\">Click Audio Stream</a>")
        )

        # Insert default facebook settings
        db.execute_commit(
            "INSERT INTO system_facebook_settings (system_id, facebook_post_body, facebook_comment_body) VALUES (%s, %s, %s)",
            (system_id, "{timestamp} Departments:\n{agency_list}\n\nDispatch Audio:\n{audio_url}",
             "{transcript}{stream_url}")
        )

        # Insert default telegram settings
        db.execute_commit(
            "INSERT INTO system_telegram_settings (system_id) VALUES (%s)",
            (system_id,)
        )

        # Insert default webhook settings
        db.execute_commit(
            "INSERT INTO system_webhook_settings (system_id, webhook_headers) VALUES (%s, %s)",
            (system_id, json.dumps({}))
        )

        # Insert default stream settings
        db.execute_commit(
            "INSERT INTO system_stream_settings (system_id) VALUES (%s)",
            (system_id,)
        )

        # Insert default remote storage settings (general)
        db.execute_commit(
            "INSERT INTO system_scp_settings (system_id) VALUES (%s)",
            (system_id,))

        module_logger.info(f"Default settings inserted successfully for system_id: {system_id}")
    except Exception as e:
        module_logger.error(f"Failed to insert default settings for system_id: {system_id}. Error: {e}")
        # Handle error or rollback as necessary


def delete_radio_system(db, system_id):
    if not system_id:
        module_logger.warning(f"System ID Empty")
        return {"success": False, "message": "System ID Empty", "result": []}

    check_result = check_for_system(db, system_id=system_id)
    module_logger.debug(check_result)

    query = f"DELETE FROM radio_systems WHERE system_id = %s"
    params = (int(system_id),)
    result = db.execute_commit(query, params)
    return result
