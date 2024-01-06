import os.path
from datetime import datetime
import logging

import requests

from lib.audio_file_handler import convert_mp3_opus

module_logger = logging.getLogger('icad_tone_detection.telegram')


class TelegramAPI:
    BASE_URL = 'https://api.telegram.org/bot'

    def __init__(self, telegram_config):
        self.bot_token = telegram_config.get("telegram_bot_token")
        self.channel = telegram_config.get("telegram_channel_id")
        if not self.bot_token or not self.channel:
            raise ValueError("Bot token and channel ID must be provided")

    def _send_request(self, method, payload, files=None):
        url = f'{self.BASE_URL}{self.bot_token}/{method}'
        try:
            resp = requests.post(url, data=payload, files=files)
            resp.raise_for_status()
            logging.info("Successfully posted to telegram")
            return True
        except requests.exceptions.HTTPError as err:
            logging.error(f"Telegram Post Failed: {err.response.status_code} {err.response.text}")
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return False

    def post_text(self, message, chat_id=None):
        if not message:
            logging.error("Message content is empty.")
            return False
        payload = {
            'chat_id': chat_id or self.channel,
            'text': message,
            'parse_mode': 'HTML'
        }
        return self._send_request('sendMessage', payload)

    def post_audio(self, detection_data, test_mode=True):
        audio_path = detection_data.get("local_audio_path", None)
        if not os.path.exists(audio_path):
            logging.error(f"Audio file does not exist: {audio_path}")
            return False

        opus_file = self._convert_to_opus(audio_path)
        if not opus_file:
            logging.error("Could not post audio to Telegram: no OGG file converted.")
            return False

        try:
            test_text = f'TEST TEST TEST TEST TEST'
            timestamp = datetime.fromtimestamp(detection_data.get("timestamp", 0))
            hr_timestamp = timestamp.strftime("%H:%M %b %d %Y")
            if test_mode:
                hr_timestamp = f"{test_text}\n{hr_timestamp}"

            transcript = detection_data.get("transcript", "")
            agencies = "\n".join([f'{x["detector_name"]} {x["detector_config"]["station_number"] if x["detector_config"].get("station_number", 0) != 0 else ""}' for x in detection_data["matches"]])

            with open(opus_file, 'rb') as audio_file:
                payload = {
                    'chat_id': self.channel,
                    "caption": f'{hr_timestamp}\n{agencies}\n{transcript}\niCAD Dispatch'
                }
                files = {'voice': audio_file}
                result = self._send_request('sendAudio', payload, files)
        except IOError as e:
            logging.error(f"Failed to open or read the audio file: {e}")
            return False
        finally:
            if os.path.exists(opus_file):
                os.remove(opus_file)

        return result

    def _convert_to_opus(self, mp3_path):
        try:
            opus_result = convert_mp3_opus(mp3_path)
            if opus_result:
                return opus_result
            else:
                logging.error("Conversion to OPUS failed.")
                return None
        except Exception as e:
            logging.error(f"Error during conversion: {e}")
            return None