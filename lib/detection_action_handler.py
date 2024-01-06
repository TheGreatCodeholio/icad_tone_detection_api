import logging
import os
from threading import Thread
import traceback

from lib.email_handler import generate_alert_email, EmailSender
from lib.facebook_handler import generate_facebook_message, generate_facebook_comment, FacebookAPI
from lib.remote_storage_handler import get_storage
from lib.pushover_handler import PushoverSender
from lib.telegram_handler import TelegramAPI
from lib.transcribe_handler import get_transcription

module_logger = logging.getLogger('icad_tone_detection.action_handler')

threads = []


def process_alert_actions(config_data, detection_data):
    module_logger.info("Processing Tone Detection Alerts")

    triggered_detectors = detection_data["matches"]


    # upload to remote storage
    if config_data["remote_storage_settings"].get("enabled", 0) == 1:
        module_logger.info("Uploading Audio to Remote Server")

        try:
            storage = get_storage(config_data["remote_storage_settings"]["storage_type"], config_data["remote_storage_settings"])

            remote_file_name = os.path.basename(detection_data['local_audio_path'])

            # Call the upload_file method to upload the audio file.
            response = storage.upload_file(detection_data['local_audio_path'], config_data["remote_storage_settings"]["remote_path"],
                                           remote_file_name)

            if response:
                module_logger.info("Audio uploaded successfully.")
                detection_data["mp3_url"] = response["file_path"]
            else:
                module_logger.error("Failed to upload audio.")
                return

        except Exception as e:
            traceback.print_exc()
            module_logger.error(f"Error during audio upload: {e}")
            return
    else:
        detection_data["mp3_url"] = ""

    if config_data["transcribe_settings"].get("transcribe_detection", 0) == 1:
        module_logger.info("Transcribing Audio")
        try:
            trans_result = get_transcription(config_data, detection_data['local_audio_path'])
            if not trans_result:
                detection_data["transcript"] = ""
            else:
                detection_data["transcript"] = trans_result
        except Exception as e:
            module_logger.error(f"An error occurred while getting Transcript: {e}")
            detection_data["transcript"] = ""
    else:
        module_logger.debug("Transcribe Detection Disabled")

    # Send Alert Emails
    if config_data["email_settings"].get("enabled", 0) == 1:
        module_logger.info("Sending Grouped Alert Emails.")
        if len(config_data["email_settings"].get("grouped_alert_emails", [])) >= 1:

            email_subject, email_body = generate_alert_email(config_data, detection_data, triggered_detectors=triggered_detectors)

            em_list = []
            for em in config_data["email_settings"]["grouped_alert_emails"]:
                em_list.append(em)
            EmailSender(config_data).send_alert_email(em_list, email_subject, email_body)

        for detector in triggered_detectors:
            if len(detector["detector_config"].get("alert_emails", [])) >= 1:
                try:

                    email_subject, email_body = generate_alert_email(config_data, detection_data, detector_data=detector)

                    em_list = []
                    for em in detector["detector_config"]["alert_emails"]:
                        em_list.append(em)
                    EmailSender(config_data).send_alert_email(em_list, email_subject, email_body)

                except Exception as e:
                    module_logger.critical(f"Alert Email Sending Failure: {repr(e)}")

    else:
        module_logger.debug("Alert Email Sending Disabled")

    if config_data["pushover_settings"].get("enabled", 0) == 1:
        module_logger.debug("Starting Pushover Notifications")

        for detector in triggered_detectors:
            try:
                # Creating an instance of PushoverSender
                pushover_sender = PushoverSender(config_data, detector)

                # Starting a new thread to send the push notification
                Thread(target=pushover_sender.send_push, args=(detection_data,)).start()
            except ValueError as e:
                # Handling potential initialization errors (like validation failures)
                module_logger.error(f"Error initializing Pushover: {e}")

    else:
        module_logger.debug("Pushover Notifications Disabled")

    if config_data["facebook_settings"]["enabled"] == 1:
        module_logger.debug("Starting Facebook Post")

        try:
            if all(match["detector_config"]["post_to_facebook"] == 0 for match in detection_data["matches"]):
                module_logger.debug("Skipping Facebook post as all matches have 'post_to_facebook' set to 0")
            else:
                post_body = generate_facebook_message(config_data, detection_data, config_data.get("test_mode", True))
                if config_data["facebook_settings"].get("post_comment", 0) == 1:
                    comment_body = generate_facebook_comment(config_data, detection_data)
                else:
                    comment_body = ""

                FacebookAPI(config_data["facebook_settings"]).post_message(post_body, comment_body)
        except Exception as e:
            traceback.print_exc()
            module_logger.error(e)

    if config_data["telegram_settings"]["enabled"] == 1:
        module_logger.debug("Starting Telegram Post")

        try:
            TelegramAPI(config_data["telegram_settings"]).post_audio(detection_data, config_data.get("test_mode"))
        except Exception as e:
            traceback.print_exc()
            module_logger.error(e)

    else:
        module_logger.debug("Telegram Posts Disabled")

    # if config_data["twitter_settings"]["enabled"] == 1:
    #     module_logger.debug("Starting Twitter Post")
    #
    #     for detector in triggered_detectors:
    #         Thread(target=send_push, args=(config_data, detector, call_data)).start()
    #
    # else:
    #     module_logger.debug("Pushover Notifications Disabled")

    module_logger.info("Notifications <<Completed>> Successfully!")
