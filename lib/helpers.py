import logging
import traceback
from datetime import datetime
import json
import os

module_logger = logging.getLogger('icad_tone_detection.helpers')


def load_json(input_data):
    """
    Loads JSON data from a file-like object or a string.

    Parameters:
    -----------
    input_data : str or file-like object
        The input containing JSON data. If input_data has a `read` method, it will be treated
        as a file-like object, and the function will attempt to read from it. If input_data is
        a string, the function will attempt to decode it as JSON directly.

    Returns:
    --------
    tuple
        A tuple where the first element is the loaded JSON data or None if an error occurs,
        and the second element is an error message or None if no error occurs.
    """
    try:
        # Check if input_data is file-like; it must have a 'read' method
        if hasattr(input_data, 'read'):
            # Assuming input_data is a file-like object with 'read' method
            data = json.loads(input_data.read())
        else:
            # Assuming input_data is a string
            data = json.loads(input_data)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON data: {e}"
    except Exception as e:
        # Catching unexpected errors
        return None, f"Error loading JSON data: {e}"


def save_posted_files(audio_file, audio_filename, json_filename, call_data):
    try:
        current_date = datetime.utcnow()
        save_folder_path = os.path.join('static', 'audio', str(current_date.year), str(current_date.month),
                                        str(current_date.day))
        os.makedirs(save_folder_path, exist_ok=True)
        with open(os.path.join(save_folder_path, audio_filename), 'wb') as af, open(
                os.path.join(save_folder_path, json_filename), 'w') as jf:
            audio_file.seek(0)
            af.write(audio_file.read())
            json.dump(call_data, jf, indent=4)
        return {"success": True, "message": f"Saved JSON and Audio File."}
    except Exception as e:
        traceback.print_exc()
        module_logger.error(f'Exception occurred while saving json and audio files: {e}')
        return {"success": False, "message": f"Unable to Save JSON and Audio File: {e}"}
