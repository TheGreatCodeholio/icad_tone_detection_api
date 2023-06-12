import json
import logging
import time
from datetime import datetime

module_logger = logging.getLogger('tr_tone_detection.tone_detection')


class ToneDetection:
    """Matches tones that were extracted to a set detector"""

    def __init__(self, config_data, detector_data, detector_list):
        self.config_data = config_data
        self.detector_data = detector_data
        self.detector_list = detector_list

    def detect_quick_call(self, extracted_quick_call, audio_segment, audio_path):
        match_list = [(tone[1][0], tone[1][1]) for tone in extracted_quick_call]

        for detector in self.detector_data:
            detector_config = self.detector_data[detector]
            excluded_id_list = [t[2] for t in self.detector_list]
            if detector_config["detector_id"] in excluded_id_list:
                continue
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
                    self.detector_list.append(
                        (time.time(), detector_config["ignore_time"], detector_config["detector_id"]))
                    # handle the match here
                    detection_json = {"detector": detector, "detected_tones": [tone[0], tone[1]], "detector_tones": [detector_config["a_tone"], detector_config["b_tone"]], "tolerance": detector_config["tone_tolerance"],
                                      "ts": time.time(),
                                      "time": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}
                    file_name = f'{detector}_{round(time.time(), 2)}'
                    audio_segment.export(f'{audio_path}/{file_name}.mp3', format='mp3')
                    with open(f'{audio_path}/{file_name}.json', 'w+') as outjs:
                        outjs.write(json.dumps(detection_json, indent=4))
                    outjs.close()

        return self.detector_list
