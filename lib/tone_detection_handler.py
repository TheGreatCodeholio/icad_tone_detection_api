import logging
import threading
import time

from lib.audio_file_handler import process_detection_audio
from lib.detection_action_handler import process_alert_actions

module_logger = logging.getLogger('icad_tone_detection.tone_detection')


class ToneDetection:
    """Matches tones that were extracted to a set detector"""

    def __init__(self, config_data, detector_data, qc_detector_list, detection_data):
        self.config_data = config_data
        self.detector_data = detector_data
        self.qc_detector_list = qc_detector_list
        self.detection_data = detection_data

    def detect_quick_call(self):
        matches_found = []
        match_list = [(tone["exact"][0], tone["exact"][1], tone["tone_id"]) for tone in self.detection_data["quick_call"]]

        for detector in self.detector_data:
            detector_config = self.detector_data[detector]
            excluded_id_list = [t["detector_id"] for t in self.qc_detector_list]
            tolerance_a = detector_config["tone_tolerance"] / 100.0 * detector_config["a_tone"]
            tolerance_b = detector_config["tone_tolerance"] / 100.0 * detector_config["b_tone"]
            detector_ranges = [
                (detector_config["a_tone"] - tolerance_a, detector_config["a_tone"] + tolerance_a),
                (detector_config["b_tone"] - tolerance_b, detector_config["b_tone"] + tolerance_b)
            ]
            for tone in match_list:
                match_a = detector_ranges[0][0] <= tone[0] <= detector_ranges[0][1]
                match_b = detector_ranges[1][0] <= tone[1] <= detector_ranges[1][1]
                if match_a and match_b:
                    module_logger.info(f"Match found for {detector}")
                    match_data = {"tone_id": tone[2], "detector_name": detector, "tones_matched": f'{tone[0]}, {tone[1]}',
                                  "detector_config": detector_config,
                                  "already_matched": True if detector_config[
                                                                 "detector_id"] in excluded_id_list else False}

                    if detector_config["detector_id"] in excluded_id_list:
                        continue
                    else:
                        matches_found.append(match_data)
                        excluded_id_list.append(detector_config["detector_id"])

                        self.qc_detector_list.append(
                            {"last_detected": time.time(), "ignore_seconds": detector_config["ignore_time"],
                             "detector_id": detector_config["detector_id"]})

                    detector_config["detector_name"] = detector

        self.detection_data["matches"] = matches_found
        self.detection_data["all_triggered_detectors"] = self.qc_detector_list

        if len(matches_found) >= 1:
            detection_data_processed = process_detection_audio(self.config_data, self.detection_data)
            self.detection_data = detection_data_processed
            for dd in self.detection_data:
                threading.Thread(target=process_alert_actions, args=(
                    self.config_data, dd)).start()
        else:
            module_logger.warning(f"No matches for {match_list} found in detectors.")

        module_logger.debug(f'Current detector List: {self.qc_detector_list}')
        return self.qc_detector_list, self.detection_data
