import json
import logging

from lib.email_handler import EmailSender, generate_finder_email, generate_system_alert_email
from lib.helpers import is_fernet_token, decrypt_password
from lib.scp_handler import SCPStorage
from lib.webhook_handler import WebHook

module_logger = logging.getLogger('icad_tone_detection.action_handler')

threads = []


def process_finder_action_scp(config_data, audio_file, audio_filename, call_data):
    try:
        if call_data.get("audio_url") is None and config_data.get("finder_mode", {}).get("scp", {}).get("enabled",
                                                                                                        0) == 1:
            scp = SCPStorage(config_data.get("finder_mode", {}))

            scp_result = scp.upload_file(audio_file, audio_filename)
            if not scp_result.get("success"):
                module_logger.error(f"Failed to upload audio via SCP. {scp_result.get('message')}")
                return scp_result
            else:
                module_logger.info(scp_result.get("message"))
                return scp_result
        else:
            enable_text = ""
            upload_text = ""
            if config_data.get("finder_mode", {}).get("scp", {}).get("enabled", 0) != 1:
                enable_text = "SCP not enabled"
            if call_data.get("audio_url") is not None:
                upload_text = "Audio File Already has URL Skipping Upload."
            module_logger.warning(f"{enable_text} {upload_text}")
            return {"success": True, "message": f"{enable_text} {upload_text}"}

    except Exception as e:
        module_logger.error(f"SCP Exception Occurred: {e}")
        return {"success": False, "message": f"SCP Exception Occurred: {e}"}


def process_finder_action_email(config_data, call_data):
    try:
        # Process Finder Alert Emails
        if config_data.get("finder_mode", {}).get("email", {}).get("alert_email_enabled", 0) == 1:
            # Send Emails for Tone Finder
            email = EmailSender(config_data.get("finder_mode", {}).get("email"))
            subject, body = generate_finder_email(call_data)

            recipients = config_data.get("finder_mode", {}).get("email", {}).get("alert_email_recipients", [])

            if len(recipients) < 1:
                module_logger.warning("Finder Mode Email List Empty")
                return {"success": True, "message": "Finder Mode Email List Empty"}
            else:
                email_result = email.send_alert_email(recipients, subject, body)
                if not email_result.get("success"):
                    module_logger.error(f"Finder Alert Email Failed: {email_result.get('message')}")
                else:
                    module_logger.info(f'Finder Email Alert: {email_result.get("message")}')

                return email_result
        else:
            module_logger.warning("Finder Alert Email Disabled.")
            return {"success": True, "message": "Finder Alert Email Disabled."}

    except Exception as e:
        module_logger.error(f"Email Exception Occurred: {e}")
        return {"success": False, "message": f"Email Exception Occurred: {e}"}


def process_finder_action_webhook(config_data, call_data):
    try:
        # Process Finder Alert Webhooks
        if config_data.get("finder_mode", {}).get("webhook", {}).get("enabled", 0) == 1:
            wh = WebHook(config_data.get("finder_mode", {}).get("webhook", {}))
            webhook_result = wh.post_to_webhook_finder(call_data)
            if not webhook_result.get("success"):
                module_logger.error(f"Tone Finder - {webhook_result.get('message')}")
            else:
                module_logger.info(f"Tone Finder - {webhook_result.get('message')}")
            return webhook_result
        else:
            module_logger.warning("Finder Alert Webhook Disabled.")
            return {"success": True, "message": "Finder Alert Webhook Disabled."}

    except Exception as e:
        module_logger.error(f"Webhook Exception Occurred: {e}")
        return {"success": False, "message": f"Webhook Exception Occurred: {e}"}


def process_finder_action_database(db, config_data, detection_mode, call_data):
    query = f"INSERT INTO finder_matches (two_tone, long_tone, hi_low_tone, system_short_name, talkgroup_id, talkgroup_alpha_tag, audio_path, find_timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    params = (json.dumps(call_data.get("tones", {}).get("two_tone", [])),
              json.dumps(call_data.get("tones", {}).get("long_tone", [])),
              json.dumps(call_data.get("tones", {}).get("hi_low_tone", [])), call_data.get("short_name", None),
              call_data.get("talkgroup", None), call_data.get("talkgroup_tag"), call_data.get("audio_url", None),
              call_data.get("start_time", None))
    insert_result = db.execute_commit(query, params)
    # query = "SELECT * FROM finder_matches WHERE system_short_name = %s"
    # params = (call_data.get('short_name'),)
    # finder_results = db.execute_query(query, params)
    # if not finder_results.get("success"):
    #     return {"success": False, "message": f"Unable to Get Finder Results: {finder_results.get('message')}"}
    #
    # finder_results = json.loads(finder_results.get("result", []))
    # detected_tones = call_data.get("tones", {})
    # module_logger.warning(finder_results)
    # module_logger.warning(detected_tones)
    return insert_result


def process_system_alert_scp(config_data, system_data, audio_file, audio_filename, call_data):
    try:
        if call_data.get("audio_url") is None and system_data.get("scp_enabled", 0) == 1:

            scp_password = system_data.get("scp_password") or None

            if scp_password is not None:
                if is_fernet_token(scp_password, config_data):
                    scp_password = decrypt_password(scp_password, config_data)

            scp_config = {"scp": {
                "host": system_data.get("scp_host"),
                "port": system_data.get("scp_port"),
                "user": system_data.get("scp_username"),
                "password": scp_password,
                "private_key_path": system_data.get("scp_private_key"),
                "base_url": system_data.get("web_url_path"),
                "remote_path": system_data.get("scp_remote_folder")
            }}

            scp = SCPStorage(scp_config)

            scp_result = scp.upload_file(audio_file, audio_filename)
            if not scp_result.get("success"):
                module_logger.error("Failed to upload audio.")
            else:
                module_logger.info(scp_result.get("message"))
                call_data["audio_url"] = scp_result.get("result")
        else:
            enable_text = ""
            upload_text = ""
            if system_data.get("scp_enabled", 0) != 1:
                enable_text = "SCP not enabled"
            if call_data.get("audio_url") is not None:
                upload_text = "Audio File Already has URL Skipping Upload."
            module_logger.warning(f"{enable_text} {upload_text}")
            return {"success": True, "message": f"{enable_text} {upload_text}"}

    except Exception as e:
        module_logger.error(f"SCP Exception Occurred: {e}")
        return {"success": False, "message": f"SCP Exception Occurred: {e}"}


def process_system_alert_email(config_data, system_data, detection_matches, call_data):
    try:
        if system_data.get("email_enabled", 0) == 1:

            smtp_password = system_data.get("smtp_password") or None

            if smtp_password is not None:
                if is_fernet_token(smtp_password, config_data):
                    smtp_password = decrypt_password(smtp_password, config_data)

            email_config = {
                "email": {
                    "host": system_data.get("smtp_hostname"),
                    "port": system_data.get("smtp_port"),
                    "user": system_data.get("smtp_username"),
                    "password": smtp_password,
                    "email_address_from": system_data.get("email_address_from"),
                    "email_text_from": system_data.get("email_text_from"),
                }
            }

            email = EmailSender(email_config)
            subject, body = generate_system_alert_email(system_data, detection_matches, call_data)

            recipients = system_data.get("system_alert_emails")

            if len(recipients) < 1:
                module_logger.warning("System Alert Email List Empty")
                return {"success": True, "message": "System Alert Email List Empty"}
            else:

                recipient_list = [element.strip() for element in recipients.split(",")]

                email_result = email.send_alert_email(recipient_list, subject, body)
                if not email_result.get("success"):
                    module_logger.error(f"System Alert Email Failed: {email_result.get('message')}")
                else:
                    module_logger.info(f'System Alert Email: {email_result.get("message")}')

                return email_result
        else:
            module_logger.warning("System Alert Email Disabled.")
            return {"success": True, "message": "System Alert Email Disabled."}

    except Exception as e:
        module_logger.error(f"System Alert Email Exception Occurred: {e}")
        return {"success": False, "message": f"System Alert Email Exception Occurred: {e}"}

def process_system_alert_transcript(config_data, system_data, call_data):
