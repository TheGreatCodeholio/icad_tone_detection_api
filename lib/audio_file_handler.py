import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from typing import List
from uuid import uuid4
import traceback

module_logger = logging.getLogger('icad_tone_detection.audio_file_handler')


def get_unique_file_path(temp_dir_path, suffix):
    """Generates a unique file path within the specified directory with the given suffix."""
    return f"{temp_dir_path}/{uuid4()}{suffix}"


def group_tones_by_time(tone_data: List[dict], time_gap: float) -> List[List[dict]]:
    """
    This function takes a list of tone data dictionaries and groups them based on a specified time gap.
    If the difference in the 'occurred' time between two consecutive tones is less than or equal to the
    specified time gap, they are considered to be part of the same group. The function returns a list of
    such groups.

    Args:
        tone_data (List[dict]): A list containing dictionaries where each dictionary holds data for a single tone.
                                Each dictionary should have an 'occurred' key holding the time at which the tone occured.
        time_gap (float): A float specifying the maximum time gap between two consecutive tones to consider
                          them as part of the same group.

    Returns:
        List[List[dict]]: A list of tone groups where each group is a list of tone data dictionaries that
                          occurred within the specified time gap of each other.
    """

    # Initializing an empty list to hold the grouped tones
    grouped_tones = []

    # Initializing the first group with the first tone data dictionary
    current_group = [tone_data[0]]

    # Iterating through the tone data starting from the second item
    for i in range(1, len(tone_data)):
        # Checking if the time gap between the current and previous tone is less than or equal to the specified time gap
        if tone_data[i]['occured'] - tone_data[i - 1]['occured'] <= time_gap:
            # If the condition is met, add the current tone data to the current group
            current_group.append(tone_data[i])
        else:
            # If the time gap is larger, add the current group to the list of grouped tones and start a new group with the current tone data
            grouped_tones.append(current_group)
            current_group = [tone_data[i]]

    # Adding the last group to the list of grouped tones if it is not empty
    if current_group:
        grouped_tones.append(current_group)

    # Returning the list of grouped tones
    return grouped_tones


def extract_tone_times(detection_data, time_gap, post_cut_duration, pre_cut_duration):
    """
        This function extracts intervals and tone IDs from the provided tone data and call data based on specified
        parameters such as time gap, post cut duration, and pre cut duration.

        Args:
            detection_data (dict): The dictionary containing the tones and their respective data including occurred times.
            time_gap (float): The time gap parameter used to group tones together.
            post_cut_duration (float): The duration after which to cut the post tone period.
            pre_cut_duration (float): The duration before which to cut the pre tone period.

        Returns:
            list, list: Returns two lists - one with the intervals (start time and end time) and another with the respective
                        tone IDs present in those intervals.
    """

    # Sorting the tone data based on the 'occured' key in each tone data dictionary
    tone_data_sorted = sorted(detection_data["quick_call"], key=lambda x: x['occured'])

    # Grouping the sorted tones by time using the specified time gap
    tone_groups = group_tones_by_time(tone_data_sorted, time_gap)

    # Initializing empty lists to hold the intervals and tone IDs for each interval
    intervals = []
    tone_ids_for_intervals = []

    # Handling the case where there is only a single group of tones
    if len(tone_groups) == 1:
        # Calculating the duration of the single group
        single_group_duration = (tone_groups[0][-1]['occured'] + post_cut_duration) - tone_groups[0][0]['occured']

        # Adjusting the start time based on the call data's call length and the single group's duration
        if abs(single_group_duration - detection_data["call_length"]) < 4.5:
            start_time = 0
        else:
            start_time = max(tone['occured'] for tone in tone_groups[0]) + post_cut_duration

        # Setting up the interval and extracting the tone IDs for the single group case
        end_time = None
        interval_tone_ids = [tone['tone_id'] for tone in tone_groups[0]]
        intervals.append((start_time, end_time))
        tone_ids_for_intervals.append(interval_tone_ids)
    else:
        # Handling the case where there are multiple groups of tones
        for i in range(0, len(tone_groups) - 1, 2):
            # Setting the start time and extracting tone IDs for the current group
            start_time = max(tone['occured'] for tone in tone_groups[i]) + post_cut_duration
            interval_tone_ids = [tone['tone_id'] for tone in tone_groups[i]]

            # Trying to set the end time and extract tone IDs for the next group (if exists)
            try:
                end_time = min(tone['occured'] for tone in tone_groups[i + 1]) - pre_cut_duration
                interval_tone_ids.extend([tone['tone_id'] for tone in tone_groups[i + 1]])
            except IndexError:
                end_time = None

            # Adding the created interval and tone IDs to their respective lists
            intervals.append((start_time, end_time))
            tone_ids_for_intervals.append(interval_tone_ids)

    # Returning the lists of intervals and tone IDs for intervals
    return intervals, tone_ids_for_intervals


def extract_audio_segment(input_file: str, start_time: float, end_time: float, output_file: str) -> bool:
    """
    Extracts a specific segment of an audio from the input file, using the given start and end times,
    and then saves that segment to a specified output file. This function utilizes the ffmpeg command-line
    tool to perform the extraction.

    Args:
        input_file (str): The path to the input audio file from which to extract the segment.
        start_time (float): The start time (in seconds) of the segment to extract.
        end_time (float): The end time (in seconds) of the segment to extract. If None, extracts till the end of the file.
        output_file (str): The path to save the output audio file.

    Returns:
        bool: True if the segment was successfully extracted and saved, otherwise False.
    """

    try:
        # Initializing the command list with "ffmpeg" and the "-ss" option to specify the start time
        command = [
            "ffmpeg",
            "-ss", str(start_time)
        ]

        # If an end time is provided, extending the command list with the "-to" option and the end time
        if end_time is not None:
            command.extend(["-to", str(end_time)])

        # Extending the command list with the input file, the "-y" option to overwrite output files, and the output file
        command.extend([
            "-i", input_file,
            "-y",
            output_file
        ])

        # Running the command using subprocess and checking the return code to determine if the command was successful
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        # Logging an error message if a CalledProcessError occurs (indicating the command failed)
        module_logger.error(f"An error occurred while extracting audio segment: {e}")
        return False
    except Exception as e:
        # Logging an error message if any other type of exception occurs
        module_logger.error(f"An unexpected error occurred: {e}")
        return False


def normalize_audio(input_file: str, output_file: str):
    """
    Analyzes and normalizes the audio level of the input file and writes the normalized audio to the output file.

    This function uses ffmpeg to first analyze the loudness of the input audio file and then normalize the audio
    based on the calculated parameters to meet the specified loudness standards.

    Args:
        input_file (str): The path to the input audio file which needs to be normalized.
        output_file (str): The path to save the normalized output audio file.

    Returns:
        bool: True if the audio was successfully normalized and saved, otherwise False.
    """

    try:
        # Construct the command for analyzing the loudness of the audio using ffmpeg
        analyze_command = [
            "ffmpeg",
            "-i", input_file,
            "-af", "loudnorm=print_format=json",
            "-f", "null",
            "-"
        ]

        # Run the analyze command and extract loudnorm parameters from the output
        result = subprocess.run(analyze_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stderr_output = result.stderr.decode('utf-8')
        lines = stderr_output.split('\n')

        # Find the start and end index of the JSON formatted loudnorm parameters in the command output
        json_start_index = next(i for i, line in enumerate(lines) if line.strip().startswith('{'))
        json_end_index = next(i for i, line in enumerate(lines) if line.strip().endswith('}'))

        # Extract and parse the loudnorm parameters JSON string
        json_str = '\n'.join(lines[json_start_index:json_end_index + 1])
        loudnorm_params = json.loads(json_str)

    except Exception as e:
        module_logger.error(f"An unexpected anyalize normalize error occurred: {e}")
        traceback.print_exc()
        return False

    try:
        # Construct the command for normalizing the audio using ffmpeg and the extracted loudnorm parameters
        normalize_command = [
            "ffmpeg",
            "-i", input_file,
            "-af",
            f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={loudnorm_params['input_i']}:measured_LRA={loudnorm_params['input_lra']}:measured_TP={loudnorm_params['input_tp']}:measured_thresh={loudnorm_params['input_thresh']}:offset={loudnorm_params['target_offset']}",
            "-y",
            output_file
        ]

        # Run the normalize command to create the normalized audio file
        subprocess.run(normalize_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return True
    except subprocess.CalledProcessError as e:
        traceback.print_exc()
        module_logger.error(f"An error occurred while normalizing audio: {e}")
        return False
    except Exception as e:
        module_logger.error(f"An unexpected normalize error occurred: {e}")
        traceback.print_exc()
        return False


def apply_filters(input_file: str, output_file: str, filters: str) -> bool:
    """
    Applies the specified FFmpeg filters to the audio in the input file and saves the processed audio to the output file.

    This function uses the ffmpeg command-line tool to apply the given audio filters to the input file. The processed audio
    is then saved to the output file. This can be used to adjust various audio properties such as volume, equalization, etc.

    Args:
        input_file (str): The path to the input audio file that needs to be processed.
        output_file (str): The path where the processed audio file will be saved.
        filters (str): The ffmpeg filter chain to apply to the audio.

    Returns:
        bool: True if the audio was successfully processed and saved, otherwise False.
    """
    try:
        # Construct the command for applying filters using ffmpeg
        command = [
            "ffmpeg",
            "-i", input_file,
            "-af", filters,
            "-y",
            output_file
        ]

        # Execute the command to apply the filters and save the processed audio
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        # Handle the specific exception raised for errors during the subprocess call
        module_logger.error(f"An error occurred while applying filters: {e}")
        return False
    except Exception as e:
        # Catch any other exceptions and log the error
        traceback.print_exc()
        module_logger.error(f"An unexpected ffmpeg filter error occurred: {e}")
        return False


def calculate_cut_length(call_length, interval):
    if interval[0] is None and interval[1] is None:
        return call_length  # No cutting, return the original length.
    elif interval[0] is None:
        return round(interval[1], 2)  # Cut only from the end return end cut time
    elif interval[1] is None:
        return round(call_length - interval[0], 2)  # Cut only from the beginning.
    else:
        return round(interval[1] - interval[0], 2)  # Cut both from the beginning and end.


def process_detection_audio(config_data, detection_data):
    """
        Processes the detected audio segments based on the configurations and data provided.

        This function processes detected audio segments by applying various operations such as
        trimming, applying filters, and normalization based on the configurations provided in
        `config_data`. It uses information from `detection_data` and `call_data` to identify the
        segments and process them accordingly.

        Args:
            config_data: Configuration data with details about how to process the audio.
            detection_data: Data containing details about the detected audio segments.
            call_data: Additional data related to the call.

        Returns:
            list: A list of dictionaries containing the final processed data.
            In case of an error, it returns an empty list.
        """

    try:
        input_audio_path = Path(detection_data["local_audio_path"])

        # Retrieve audio processing configurations
        post_cut_time = config_data["audio_processing"].get("trim_post_cut", 5.5)
        pre_cut_time = config_data["audio_processing"].get("trim_pre_cut", 2.2)
        time_gap = config_data["audio_processing"].get("trim_group_tone_gap", 6.5)

        # Determine intervals and tone IDs for trimming based on configuration
        input_base_dir = input_audio_path.parent
        if config_data["audio_processing"]["trim_tones"] == 1:
            intervals, tone_ids_for_intervals = extract_tone_times(detection_data, time_gap, post_cut_time,
                                                                   pre_cut_time)
        else:
            intervals = [(0, None)]
            tone_ids_for_intervals = [tone["tone_id"] for tone in detection_data["quick_call"]]

        matches_dict = detection_data['matches']

        final_data = []

        for interval, tone_ids in zip(intervals, tone_ids_for_intervals):

            detection_json = {
                "quick_call": [item for item in detection_data["quick_call"] if item['tone_id'] in tone_ids],
                "hi_low": detection_data["hi_low"],
                "long": detection_data["long"],
                "dtmf": detection_data["dtmf"],
                "timestamp": detection_data["timestamp"] + (interval[0] - post_cut_time) if interval[
                                                                                                0] >= post_cut_time else
                detection_data["timestamp"],
                "timestamp_string": datetime.fromtimestamp(
                    detection_data["timestamp"] + (interval[0] - post_cut_time) if interval[0] >= post_cut_time else
                    detection_data["timestamp"]).strftime("%m/%d/%Y, %H:%M:%S"),
                'call_length': calculate_cut_length(detection_data["call_length"], interval),
                'talkgroup_decimal': detection_data.get('talkgroup_decimal', 0),
                'talkgroup_alpha_tag': detection_data.get('talkgroup_alpha_tag'),
                'talkgroup_name': detection_data.get('talkgroup_name'),
                'talkgroup_service_type': detection_data.get('talkgroup_service_type'),
                'talkgroup_group': detection_data.get('talkgroup_group')
            }
            new_match_data = {}
            for match in matches_dict:
                key = (match["detector_name"], match["tones_matched"])
                if key not in new_match_data:
                    new_match_data[key] = match
                    if "tone_id" in match:
                        new_match_data[key]["tone_ids"] = [match.pop("tone_id")]

                else:
                    if "tone_id" in match:
                        new_match_data[key]["tone_ids"].append(match["tone_id"])  # add the new tone_id to the list

            detection_json["matches"] = list(new_match_data.values())

            departments_in_segment = detection_json["matches"][0]
            if departments_in_segment:
                department_name = departments_in_segment["detector_name"].lower()
                department_name = re.sub(r'[^\w\s]', '', department_name).replace(' ', '_')
                timestamp = datetime.fromtimestamp(detection_json["timestamp"]).strftime("%Y%m%d_%H%M%S")
                output_file_name = f'{department_name}_{timestamp}.mp3'
            else:
                continue

            with TemporaryDirectory() as temp_dir:
                output_file_path = f'{input_base_dir}/{output_file_name}'
                temp_dir_path = temp_dir

                tmpfile_path = get_unique_file_path(temp_dir_path, "_segment.mp3")
                extract_audio_segment(detection_data["local_audio_path"], interval[0], interval[1], tmpfile_path)

                last_processed_file = tmpfile_path

                if config_data["audio_processing"]["ffmpeg_filter"] != "":
                    output_file = get_unique_file_path(temp_dir_path, "_filtered.mp3")
                    apply_filters(last_processed_file, output_file, config_data["audio_processing"]["ffmpeg_filter"])
                    last_processed_file = output_file

                if config_data["audio_processing"]["normalize"]:
                    segment_normalized_file = get_unique_file_path(temp_dir_path, "_segment_normalized.mp3")
                    normalize_audio(last_processed_file, segment_normalized_file)
                    last_processed_file = segment_normalized_file

                copyfile(last_processed_file, output_file_path)

            detection_json["local_audio_path"] = output_file_path

            final_data.append(detection_json)

        return final_data
    except Exception as e:
        traceback.print_exc()
        module_logger.error(f"An error occurred in process_detection_audio: {e}")
        return []
