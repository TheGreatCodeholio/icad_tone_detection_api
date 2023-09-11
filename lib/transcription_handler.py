import io
import logging

import requests

module_logger = logging.getLogger('tr_tone_detection.transcription_handler')


def get_transcription(config_data, audio_segment):
    try:
        file_data = io.BytesIO()
        audio_segment.export(file_data, format='mp3')
        file_data.seek(0)  # go back to the start of the file stream

        files = {'file': ('audio.mp3', file_data, 'audio/mpeg')}
        response = requests.post(config_data["transcription_settings"]["transcription_url"], files=files)

        response.raise_for_status()  # raise an HTTPError if the HTTP request returned an unsuccessful status code

    except requests.exceptions.HTTPError as errh:
        print(f"An HTTP error occurred: {errh}")
        response = False
    except requests.exceptions.ConnectionError as errc:
        print(f"A connection error occurred: {errc}")
        response = False
    except requests.exceptions.Timeout as errt:
        print(f"A timeout error occurred: {errt}")
        response = False
    except requests.exceptions.RequestException as err:
        print(f"An unexpected error occurred: {err}")
        response = False

    if response:
        return response.json()
    else:
        return None
