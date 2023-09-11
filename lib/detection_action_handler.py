import logging
from threading import Thread
import traceback

from lib.email_handler import generate_alert_email, EmailSender
from lib.file_save_handler import get_storage
from lib.pushover_handler import send_push
from lib.transcription_handler import get_transcription

module_logger = logging.getLogger('tr_tone_detection.action_handler')

threads = []


def process_alert_actions(config_data, triggered_detectors, call_data, audio_segment):
    module_logger.info("Processing Tone Detection Alerts")

    module_logger.info("Uploading Audio to Remote Server")
    try:

        # Get the appropriate storage class based on the storage_type.
        storage = get_storage(config_data["file_storage"]["storage_type"], config_data["file_storage"])

        remote_file_name = triggered_detectors[0]["detector_name"].replace(" ", "_").lower() + f'{round(float(call_data["start_time"]), -1)}.mp3'

        # Call the upload_file method to upload the audio file.
        response = storage.upload_file(call_data["local_audio_path"], config_data["file_storage"]["remote_path"], remote_file_name)

        if response:
            module_logger.info("Audio uploaded successfully.")
            call_data["mp3_url"] = response["file_path"]
        else:
            module_logger.error("Failed to upload audio.")
            return
    except Exception as e:
        traceback.print_exc()
        module_logger.error(f"Error during audio upload: {e}")
        return

    if config_data["transcription_settings"]["transcribe_alert"] == 1:
        module_logger.info("Transcribing Audio")
        try:

            response = get_transcription(config_data, audio_segment)
            if response is None:
                module_logger.error("An error occurred and no response was returned.")
                call_data["transcript"] = ""
            else:
                # Process the response here
                call_data["transcript"] = response["transcription"]
        except Exception as e:
            module_logger.error(f"An error occurred while getting Transcript: {e}")
            call_data["transcript"] = ""
    else:
        module_logger.debug("Transcription Disabled")

    # Send Alert Emails
    if config_data["email_settings"]["send_alert_email"] == 1:
        for detector in triggered_detectors:
            if len(detector["alert_emails"]) >= 1:
                try:
                    module_logger.debug("Starting Alert Email Sending")

                    email_subject, email_body = generate_alert_email(config_data, detector, call_data)

                    for em in detector["alert_emails"]:
                        em = [em]
                        EmailSender(config_data).send_alert_email(em, email_subject, email_body)

                except Exception as e:
                    module_logger.critical(f"Alert Email Sending Failure: {repr(e)}")

    else:
        module_logger.debug("Alert Email Sending Disabled")

    if config_data["pushover_settings"]["enabled"] == 1:
        module_logger.debug("Starting Pushover Notifications")

        for detector in triggered_detectors:
            Thread(target=send_push, args=(config_data, detector, call_data)).start()

    else:
        module_logger.debug("Pushover Notifications Disabled")

    # if config_data["twitter_settings"]["enabled"] == 1:
    #     module_logger.debug("Starting Twitter Post")
    #
    #     for detector in triggered_detectors:
    #         Thread(target=send_push, args=(config_data, detector, call_data)).start()
    #
    # else:
    #     module_logger.debug("Pushover Notifications Disabled")

    module_logger.info("Notifications <<Completed>> Successfully!")


