import logging
import time

import requests

module_logger = logging.getLogger("icad_tone_detection.webhooks")


class WebHook:
    def __init__(self, webhook_config, detection_data):
        self.url = webhook_config.get("webhook_url")
        self.headers = webhook_config.get("webhook_headers")
        self.detection_data = detection_data

    def process_webhook(self, test_mode=True):
        self.post_to_webhook_global(test_mode)
        for match in self.detection_data.get("matches"):
            self.post_to_webhook_individual(match, test_mode)

    def post_to_webhook_global(self, test_mode):
        webhook_json = {
            "timestamp": self.detection_data.get("timestamp"),
            "agency": [match["detector_name"] for match in self.detection_data.get("matches")],
            "transcript": self.detection_data.get("transcript"),
            "mp3_url": self.detection_data.get("mp3_url"),
            "local_audio_file": self.detection_data.get("local_audio_path"),
            "is_test": test_mode
        }
        max_retries = 3
        attempts = 0
        delay_between_retries = 5  # seconds

        while attempts < max_retries:
            try:
                result = requests.post(self.url, headers=self.headers, json=webhook_json)
                if result.status_code == 200:
                    module_logger.info("Global webhook posted successfully.")
                    return
                else:
                    module_logger.error(
                        f"Attempt {attempts + 1} failed with status code {result.status_code} {result.text}. Retrying...")
            except requests.exceptions.RequestException as e:
                module_logger.error(f"An error occurred while sending Global Webhook: {e}")

            if attempts < max_retries - 1:
                time.sleep(delay_between_retries)  # Wait before retrying
            attempts += 1

        module_logger.error("Max retries exhausted for Global Webhook, could not send.")

    def post_to_webhook_individual(self, match_data, test_mode):
        detector_config = match_data.get("detector_config", {})
        webhook_url = detector_config.get("webhook_url_override", None)
        webhook_headers = detector_config.get("webhook_headers_override", None)

        if not webhook_url or not detector_config:
            module_logger.warning(f'Skipping Webhook for {match_data.get("detector_name")}: No Agency Webhook URL.')
            return

        webhook_json = {
            "timestamp": self.detection_data.get("timestamp"),
            "agency": match_data.get("detector_name"),
            "transcript": self.detection_data.get("transcript"),
            "mp3_url": self.detection_data.get("mp3_url"),
            "local_audio_file": self.detection_data.get("local_audio_path"),
            "is_test": test_mode
        }

        max_retries = 3
        attempts = 0
        delay_between_retries = 5  # seconds

        while attempts < max_retries:
            try:
                result = requests.post(webhook_url, headers=webhook_headers, json=webhook_json)
                if result.status_code == 200:
                    module_logger.info(f"Agency {match_data.get('detector_name')} webhook posted successfully.")
                else:
                    module_logger.error(
                        f"Attempt {attempts + 1} failed with status code {result.status_code} {result.text}. Retrying...")
            except requests.exceptions.RequestException as e:
                module_logger.error(
                    f"An error occurred while sending Agency {match_data.get('detector_name')} Webhook: {e}")

            if attempts < max_retries - 1:
                time.sleep(delay_between_retries)  # Wait before retrying
            attempts += 1

        module_logger.error(
            f"Max retries exhausted for Agency {match_data.get('detector_name')} Webhook, could not send.")
