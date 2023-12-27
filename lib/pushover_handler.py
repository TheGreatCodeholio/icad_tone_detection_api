from datetime import datetime

import requests
from requests.exceptions import RequestException
import logging
import traceback

module_logger = logging.getLogger('icad_tone_detection.pushover')


class PushoverSender:
    """PushoverSender is a class responsible for sending push notifications with given configurations.

    Attributes:
        config_data (dict): A dictionary containing configuration data.
        detector_data (dict): A dictionary containing detector data.
    """

    def __init__(self, config_data, detector_data):
        """Initializes the PushoverSender with configuration and detector data.

        Args:
            config_data (dict): A dictionary containing configuration data.
            detector_data (dict): A dictionary containing detector data.

        Raises:
            ValueError: If config_data or detector_data are not dictionaries or are missing expected keys.
        """
        if not isinstance(config_data, dict):
            raise ValueError("config_data should be a dictionary")

        if not isinstance(detector_data, dict):
            raise ValueError("detector_data should be a dictionary")

        expected_config_keys = ["pushover_settings", "stream_settings"]
        for key in expected_config_keys:
            if key not in config_data:
                raise ValueError(f"config_data is missing expected key: {key}")

        expected_detector_keys = ["detector_config", "detector_name"]
        for key in expected_detector_keys:
            if key not in detector_data:
                raise ValueError(f"detector_data is missing expected key: {key}")

        self.config_data = config_data
        self.detector_data = detector_data

    def send_push(self, detection_data, test=True):
        """Sends a push notification with the given parameters.

        Args:
            detection_data (dict): A dictionary containing call data.
            test (bool): A bool to signify if test mode enabled

        Returns:
            None
        """


        try:
            title = self.detector_data["detector_config"].get("pushover_subject") or self.config_data[
                "pushover_settings"].get("pushover_subject", "Alert!")
            sound = self.detector_data["detector_config"].get("pushover_sound") or self.config_data[
                "pushover_settings"].get("pushover_sound", "pushover")
            body = self.detector_data["detector_config"].get("pushover_body") or self.config_data[
                "pushover_settings"].get("pushover_body",
                                         "<font color=\"red\"><b>{detector_name}</b></font>")

            if test:
                body = f"<font color=\"red\"><b>TEST TEST TEST TEST</b></font><br><br>{body}"


            # Preprocess timestamp
            timestamp = datetime.fromtimestamp(detection_data.get("timestamp", 0))
            hr_timestamp = timestamp.strftime("%H:%M:%S %b %d %Y")

            detector_name = self.detector_data.get("detector_name", "Unknown Detector")

            # Create a mapping
            mapping = {
                "detector_name": detector_name,
                "timestamp": hr_timestamp,
                "transcript": detection_data["transcript"] if detection_data.get("transcript") else "",
                "mp3_url": detection_data["mp3_url"] if detection_data.get("mp3_url") else "",
                "stream_url": self.detector_data.get("stream_url") or self.config_data["stream_settings"].get("stream_url") if self.config_data["stream_settings"].get("stream_url") else ""
            }

            # Use the mapping to format the strings
            title = title.format_map(mapping)
            body = body.format_map(mapping)

            # Internal method to send request
            def send_request(token, user, group_name):
                try:
                    response = requests.post(
                        "https://api.pushover.net/1/messages.json",
                        data={
                            "token": token,
                            "user": user,
                            "html": 1,
                            "message": body,
                            "title": title,
                            "sound": sound
                        },
                        timeout=10
                    )
                    if response.status_code == 200:
                        module_logger.debug(f"Pushover Successful: Group {group_name}")
                    else:
                        module_logger.error(f"Pushover Unsuccessful: Group {group_name} {response.text}")
                except RequestException as e:
                    module_logger.error(f"Pushover Request Error for Group {group_name}: {e}")
                except Exception as e:
                    module_logger.error(f"Unexpected Pushover Request Error for Group {group_name}: {e}")

            self._process_push_notifications(send_request)

        except Exception as e:
            module_logger.error(f"Pushover Send Failure:\n {repr(e)}")
            traceback.print_exc()

    def _process_push_notifications(self, send_request):
        """Processes push notifications by sending requests to different groups based on configuration data.

        Args:
            send_request (function): The function to send the push notification request.

        Returns:
            None
        """
        all_detector_app_token = self.config_data["pushover_settings"].get("all_detector_app_token", "")
        all_detector_group_token = self.config_data["pushover_settings"].get("all_detector_group_token", "")

        if all_detector_app_token != "" and all_detector_group_token != "":
            module_logger.debug("Sending Pushover All Detectors Group")
            send_request(all_detector_app_token, all_detector_group_token, "All")
        else:
            module_logger.debug("Pushover All Detector Group Disabled")

        app_token = self.detector_data["detector_config"].get("pushover_app_token")
        group_token = self.detector_data["detector_config"].get("pushover_group_token")

        if app_token and group_token:
            module_logger.debug("Sending Pushover Detector Group")
            send_request(app_token, group_token, self.detector_data.get("detector_name", "Unknown Detector"))
        else:
            module_logger.error("Missing Pushover APP or Group Token")
