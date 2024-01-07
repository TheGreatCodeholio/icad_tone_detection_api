import csv
import logging
import os.path
import re

import requests

module_logger = logging.getLogger('icad_tone_detection.transcription_handler')


def get_transcription(config_data, mp3_path):
    """
        This function takes configuration data and a path to an MP3 file as inputs. It then tries to send a POST request to
        the transcription service specified in the configuration data to get the transcription of the audio file. If any
        kind of exception occurs (like HTTPError, ConnectionError, Timeout, RequestException, or FileNotFoundError),
        it logs the error message and returns None.

        Args:
        config_data (dict): The configuration data containing the details of the transcription service, among other settings.
        mp3_path (str): The file path of the MP3 file to be transcribed.

        Returns:
        dict or None: If the request is successful, it returns the JSON response from the transcription service as a dictionary.
                      If any exception occurs or the response is unsuccessful, it returns None.
    """

    try:
        with open(mp3_path, 'rb') as audio_file:
            files = {'file': audio_file}
            response = requests.post(config_data["transcribe_settings"]["transcribe_url"], files=files)

        if response:
            transcribe_result = response.json()
            if response.status_code == 200:
                transcript = do_transcribe_replacements(config_data["transcribe_settings"], transcribe_result.get("transcription"))
                return transcript
            else:
                module_logger.error(
                    f'Error Transcribing Audio: {transcribe_result.get("message", "Unknown Exception")}')
                return False


        else:
            module_logger.error('No response from server')
            return False

    except requests.exceptions.HTTPError as errh:
        module_logger.error(f"An HTTP error occurred: {errh}")
    except requests.exceptions.ConnectionError as errc:
        module_logger.error(f"A connection error occurred: {errc}")
    except requests.exceptions.Timeout as errt:
        module_logger.error(f"A timeout error occurred: {errt}")
    except requests.exceptions.RequestException as err:
        module_logger.error(f"An unexpected error occurred: {err}")
    except FileNotFoundError as err:
        module_logger.error(f"File Not Found: {mp3_path}")


def do_transcribe_replacements(transcribe_config, transcript):
    replacement_file_path = transcribe_config.get("replacements_file")
    if not os.path.exists(replacement_file_path):
        return transcript

    with open(replacement_file_path, "r") as rf:
        csv_reader = csv.DictReader(rf)
        replace_data = [row for row in csv_reader]

    def replace_func(match):
        word = match.group(0)
        for replacement in replace_data:
            if word.lower() == replacement.get("Word").lower():
                return replacement.get("Replacement")
        return word  # return the original word if not found

    # Create a combined regex pattern from all words to be replaced
    pattern = '|'.join(re.escape(replacement.get("Word")) for replacement in replace_data)
    # Use re.IGNORECASE to perform case-insensitive matching
    transcript = re.sub(pattern, replace_func, transcript, flags=re.IGNORECASE)

    return transcript




