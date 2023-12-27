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


# def group_tones_by_time(tone_data: List[dict], time_gap: float) -> List[List[dict]]:
#     """
#     This function takes a list of tone data dictionaries and groups them based on a specified time gap.
#     If the difference in the 'occurred' time between two consecutive tones is less than or equal to the
#     specified time gap, they are considered to be part of the same group. The function returns a list of
#     such groups.
#
#     Args:
#         tone_data (List[dict]): A list containing dictionaries where each dictionary holds data for a single tone.
#                                 Each dictionary should have an 'occurred' key holding the time at which the tone occured.
#         time_gap (float): A float specifying the maximum time gap between two consecutive tones to consider
#                           them as part of the same group.
#
#     Returns:
#         List[List[dict]]: A list of tone groups where each group is a list of tone data dictionaries that
#                           occurred within the specified time gap of each other.
#     """
#
#     def are_similar_tones(tone1, tone2):
#         # Function to check if two tones are similar within a 1% threshold
#         return all(abs(t1 - t2) / t2 <= 0.01 for t1, t2 in zip(tone1, tone2))
#
#     def have_similar_tones(group1, group2):
#         # Function to check if more than 50% of tones are similar between two groups
#         similar_count = sum(
#             any(are_similar_tones(tone1['actual'], tone2['actual']) for tone2 in group2) for tone1 in group1)
#         return similar_count >= max(len(group1), len(group2)) * 0.5
#
#     # Initializing an empty list to hold the grouped tones
#     grouped_tones = []
#
#     # Initializing the first group with the first tone data dictionary
#     current_group = [tone_data[0]]
#
#     # Iterating through the tone data starting from the second item
#     for i in range(1, len(tone_data)):
#         # Checking if the time gap between the current and previous tone is less than or equal to the specified time gap
#         if tone_data[i]['occured'] - tone_data[i - 1]['occured'] <= time_gap:
#             # If the condition is met, add the current tone data to the current group
#             current_group.append(tone_data[i])
#         else:
#             # If the time gap is larger, add the current group to the list of grouped tones and start a new group with the current tone data
#             grouped_tones.append(current_group)
#             current_group = [tone_data[i]]
#
#     # Adding the last group to the list of grouped tones if it is not empty
#     if current_group:
#         grouped_tones.append(current_group)
#
#         # Now we will merge groups that have more than 50% similar tones
#         merged_groups = []
#         i = 0
#         while i < len(grouped_tones):
#             if i < len(grouped_tones) - 1 and have_similar_tones(grouped_tones[i], grouped_tones[i + 1]):
#                 grouped_tones[i].extend(grouped_tones[i + 1])
#                 i += 2
#             else:
#                 merged_groups.append(grouped_tones[i])
#                 i += 1
#
#         return merged_groups

def group_tones_by_time(tone_data_sorted, time_gap):
    """
    This function groups tones that are closer to each other in time based on a specified time gap.

    Args:
        tone_data_sorted (list of dicts): A list containing dictionaries that represent individual tones.
                                          Each dictionary contains details about a single tone,
                                          including its 'occurred' time.
                                          The list is sorted in ascending order based on the 'occurred' time.
        time_gap (float): A float representing the maximum time gap between two tones to consider
                          them as belonging to the same group.

    Process:
        - Initializes the first tone as the starting point of the first group.
        - Iterates through the sorted tone data starting from the second tone.
        - If the time gap between the current tone and the last tone in the current group is less than the
          specified time gap, it adds the current tone to the current group.
        - If the time gap is equal to or greater than the specified time gap, it considers the current tone
          as the start of a new group, adds the current group to the list of tone groups, and starts a new group
          with the current tone.
        - After iterating through all tones, if the current group contains any tones, it adds it to the list
          of tone groups.

    Returns:
        list of lists: A list where each element is a list of tones representing a group.
                       Each tone in a group is closer in time to each other than the specified time gap.
    """
    tone_groups = []
    current_group = [tone_data_sorted[0]]

    for i in range(1, len(tone_data_sorted)):
        if tone_data_sorted[i]['occured'] - current_group[-1]['occured'] < time_gap:
            current_group.append(tone_data_sorted[i])
        else:
            tone_groups.append(current_group)
            current_group = [tone_data_sorted[i]]

    if current_group:
        tone_groups.append(current_group)

    return tone_groups


def extract_tone_times(detection_data, time_gap, post_cut_duration, pre_cut_duration):
    """
        Extracts intervals and tone IDs from the tone data and groups them based on the specified time gap, post-cut,
        and pre-cut durations. The function iterates through the groups, creating intervals using the occurred times
        in the current and next groups (if exists). If there isn't a next group, it ends the interval at the end
        of the file. It also ensures that the end time of an interval is always greater than the start time.

        Args:
            detection_data (dict): A dictionary containing details of the tones including their occurred times.
            time_gap (float): The time gap parameter used to group tones together.
            post_cut_duration (float): The duration after which to set the cutting start time post tone period.
            pre_cut_duration (float): The duration before which to set the cutting end time pre tone period.

        Returns:
            tuple: Two lists, one containing tuples with start and end times of each interval,
                   and another containing lists of tone IDs present in those intervals.
    """

    # Sorting the tone data based on the 'occured' key in each tone data dictionary
    tone_data_sorted = sorted(detection_data["quick_call"], key=lambda x: x['occured'])


    # Grouping the sorted tones by time using the specified time gap
    tone_groups = group_tones_by_time(tone_data_sorted, time_gap)

    module_logger.warning(tone_groups)

    # Initializing empty lists to hold the intervals and tone IDs for each interval
    intervals = []
    tone_ids_for_intervals = []

    # Check if the list is not empty
    if tone_groups:
        i = 0
        while i < len(tone_groups):
            # Setting the start time and extracting tone IDs for the current group
            start_time = max(tone['occured'] for tone in tone_groups[i]) + post_cut_duration
            interval_tone_ids = [tone['tone_id'] for tone in tone_groups[i]]

            # Setting the end time to None as a default value (will be used in case this is the last group or a single group)
            end_time = None

            # If there is a next group, set the end time based on the earliest tone in the next group
            if i + 1 < len(tone_groups):
                end_time = min(tone['occured'] for tone in tone_groups[i + 1]) - pre_cut_duration
                interval_tone_ids.extend([tone['tone_id'] for tone in tone_groups[i + 1]])

                # Ensure that end_time is greater than start_time
                if end_time <= start_time:
                    end_time = start_time + 0.1  # Adjust end time to be slightly greater than start time

                i += 2  # Move to the group after the next group
            else:
                i += 1  # Move to the next group (which does not exist, effectively ending the loop)

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
        # Getting the stderr output and decoding it to a string
        error_message = e.stderr.decode('utf-8') if e.stderr else "No stderr output available"
        # Logging an error message if a CalledProcessError occurs (indicating the command failed)
        module_logger.error(f"An error occurred while extracting audio segment: {e}\n\n{error_message}")
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
        time_gap = config_data["audio_processing"].get("trim_group_tone_gap", 7.5)

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

        # If we have more than 4 intervals something isn't correct.
        if len(intervals) > 4:
            # Set intervals to one interval grabbing the inital audio before tones start. without precut time
            intervals = [(0, detection_data["quick_call"][0]["occured"])]
            # keep the first set of tone_ids so we have a detector name
            tone_ids_for_intervals = tone_ids_for_intervals[:1]

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
