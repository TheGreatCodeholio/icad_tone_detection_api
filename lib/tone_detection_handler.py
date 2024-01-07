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
        match_list = [(tone["exact"][0], tone["exact"][1], tone["tone_id"]) for tone in
                      self.detection_data["quick_call"]]
        excluded_id_list = [t["detector_id"] for t in self.qc_detector_list]

        for detector in self.detector_data:
            detector_config = self.detector_data[detector]
            tolerance_a = detector_config["tone_tolerance"] / 100.0 * detector_config.get("a_tone", 0)
            tolerance_b = detector_config["tone_tolerance"] / 100.0 * detector_config.get("b_tone", 0)
            tolerance_c = detector_config["tone_tolerance"] / 100.0 * detector_config.get("c_tone", 0)
            tolerance_d = detector_config["tone_tolerance"] / 100.0 * detector_config.get("d_tone", 0)
            detector_ranges = [
                (detector_config["a_tone"] - tolerance_a, detector_config["a_tone"] + tolerance_a),
                (detector_config["b_tone"] - tolerance_b, detector_config["b_tone"] + tolerance_b),
                (detector_config.get("c_tone", 0) - tolerance_c, detector_config.get("c_tone", 0) + tolerance_c),
                (detector_config.get("d_tone", 0) - tolerance_d, detector_config.get("d_tone", 0) + tolerance_d)
            ]

            for i, tone in enumerate(match_list):
                match_a = detector_ranges[0][0] <= tone[0] <= detector_ranges[0][1]
                match_b = detector_ranges[1][0] <= tone[1] <= detector_ranges[1][1]
                if match_a and match_b:
                    valid_match = True
                    tones_matched = [tone[0], tone[1]]
                    tone_id = f"{tone[2]}"

                    if detector_config.get("c_tone", 0) > 0 and detector_config.get("d_tone", 0) > 0:
                        if i + 1 < len(match_list):
                            next_tone = match_list[i + 1]
                            match_c = detector_ranges[2][0] <= next_tone[0] <= detector_ranges[2][1]
                            match_d = detector_ranges[3][0] <= next_tone[1] <= detector_ranges[3][1]
                            if match_c and match_d:
                                # If C and D tones also match, include them in the tones_matched
                                tones_matched.append(next_tone[0])
                                tones_matched.append(next_tone[1])
                                tone_id += f', {next_tone[2]}'
                            else:
                                # If C and D tones don't match, this isn't a valid match
                                valid_match = False
                        else:
                            valid_match = False

                    if valid_match:
                        module_logger.info(f"Match found for {detector}")

                        match_data = {"tone_id": tone_id, "detector_name": detector,
                                      "tones_matched": tones_matched,
                                      "detector_config": detector_config
                                      }

                        if detector_config["detector_id"] in excluded_id_list:
                            continue
                        else:
                            matches_found.append(match_data)
                            excluded_id_list.append(detector_config["detector_id"])

                            self.qc_detector_list.append({"last_detected": time.time(),
                                                          "ignore_seconds": detector_config["ignore_time"],
                                                          "detector_id": detector_config["detector_id"]})

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
