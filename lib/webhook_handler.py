import logging
import time

import requests

module_logger = logging.getLogger("icad_tone_detection.webhooks")


class WebHook:
    def __init__(self, webhook_config):
        self.url = webhook_config.get("webhook_url") or None
        self.headers = webhook_config.get("webhook_headers", {})

    def post_to_webhook_finder(self, call_data, max_retries=3, retry_delay=5):
        tone_data = call_data.get("tones", [])

        webhook_json = {
            "timestamp": call_data.get("start_time"),
            "agencies": None,
            "tones": tone_data,
            "transcript": call_data.get("transcript") or None,
            "audio_url": call_data.get("audio_url") or None,
            "is_test": call_data.get("")
        }

        retry_attempts = 0
        if self.url:
            while retry_attempts < max_retries:
                try:
                    r = requests.post(self.url, headers=self.headers if len(self.headers) > 0 else None, json=webhook_json)
                    if r.status_code == 200:
                        return {"success": True, "message": f"Webhook posted to {self.url} successfully"}
                    else:
                        module_logger.warning(
                            f"Webhook attempt {retry_attempts + 1} failed with status code {r.status_code} {r.text}. Retrying...")
                except requests.exceptions.RequestException as e:
                    return {"success": False,
                            "message": f"An Error occured while posting webhook posted to {self.url}."}

                if retry_attempts < max_retries - 1:
                    time.sleep(retry_delay)
                retry_attempts += 1

            return {"success": False, "message": f"Max retries exhausted while posting webhook to {self.url}."}

        else:
            return {"success": False, "message": f"Webhook enabled, but no URL given."}
