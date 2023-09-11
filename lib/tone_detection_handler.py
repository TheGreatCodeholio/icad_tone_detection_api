import logging
import threading
import time

from lib.detection_action_handler import process_alert_actions

module_logger = logging.getLogger('tr_tone_detection.tone_detection')


class ToneDetection:
    """Matches tones that were extracted to a set detector"""

    def __init__(self, config_data, detector_data, detector_list, call_data):
        self.config_data = config_data
        self.detector_data = detector_data
        self.detector_list = detector_list
        self.call_data = call_data

    def detect_quick_call(self, extracted_quick_call, audio_segment):
        matches_found = []
        match_list = [(tone["exact"][0], tone["exact"][1]) for tone in extracted_quick_call]
        triggered_detectors = []

        for detector in self.detector_data:
            detector_config = self.detector_data[detector]
            excluded_id_list = [t["detector_id"] for t in self.detector_list]
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
                    match_data = {"department": detector, "tones_matched": f'{tone[0]}, {tone[1]}',
                                  "tones_config": f'{detector_config["a_tone"]}, {detector_config["b_tone"]}',
                                  "already_matched": True if detector_config[
                                                                 "detector_id"] in excluded_id_list else False,
                                  "detector_list": self.detector_list}

                    for existing_match_data in matches_found:
                        if existing_match_data["department"] == match_data["department"]:
                            break
                    else:
                        matches_found.append(match_data)

                    if detector_config["detector_id"] in excluded_id_list:
                        continue
                    else:
                        excluded_id_list.append(detector_config["detector_id"])

                    self.detector_list.append(
                        {"last_detected": time.time(), "ignore_seconds": detector_config["ignore_time"],
                         "detector_id": detector_config["detector_id"]})

                    detector_config["detector_name"] = detector

                    if detector_config not in triggered_detectors:
                        triggered_detectors.append(detector_config)

        if len(triggered_detectors) >= 1:
            threading.Thread(target=process_alert_actions, args=(
                self.config_data, triggered_detectors, self.call_data, audio_segment)).start()
        else:
            module_logger.warning("No matches found in detectors.")
        module_logger.debug(f'Current detector List: {self.detector_list}')
        return self.detector_list, matches_found
