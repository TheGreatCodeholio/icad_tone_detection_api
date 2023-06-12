import io
import logging

import numpy as np
from scipy.signal import stft

module_logger = logging.getLogger('tr_tone_detection.tone_extraction')

class ToneExtraction:
    """Extracts tones from an audio file."""
    def __init__(self, config_data, audio_segment):
        self.qcii = [288.5, 296.5, 304.7, 313.8, 321.7, 330.5, 339.6, 349.0, 358.6, 368.5, 378.6, 389.0, 399.8, 410.8,
                     422.1, 433.7, 445.7, 457.9, 470.5, 483.5, 496.8, 510.5, 524.6, 539.0, 553.9, 569.1, 584.8, 600.9,
                     617.4, 634.5, 651.9, 669.9, 688.3, 707.3, 726.8, 746.8, 767.4, 788.5, 810.2, 832.5, 855.5, 879.0,
                     903.2, 928.1, 953.7, 979.9, 989.0, 1006.9, 1034.7, 1063.2, 1092.4, 1122.5, 1153.4, 1185.2, 1217.8,
                     1251.4, 1285.8, 1321.2, 1357.6, 1395.0, 1433.4, 1472.9, 1513.5, 1555.2, 1598.0, 1642.0, 1687.2,
                     1733.7, 1781.5, 1830.5, 1881.0, 1930.2, 1981.1, 2043.8, 2094.5, 2155.6, 2212.2, 2271.7, 2334.6,
                     2401.0, 2468.2, 2573.2]
        self.dtmf = {(697, 1209): "1", (697, 1336): "2", (697, 1477): "3", (770, 1209): "4", (770, 1336): "5",
                     (770, 1477): "6",
                     (852, 1209): "7", (852, 1336): "8", (852, 1477): "9", (941, 1209): "*", (941, 1336): "0",
                     (941, 1477): "#",
                     (697, 1633): "A", (770, 1633): "B", (852, 1633): "C", (941, 1633): "D"}
        self.audio_segment = audio_segment
        self.config_data = config_data

    def load_audio(self, audio_segment):
        audio = audio_segment
        audio = audio.set_channels(1)  # Ensure the audio is mono
        audio = audio.set_frame_rate(22050)  # Set the frame rate to 22050 Hz
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        samples /= np.iinfo(audio.sample_width * 8 - 1).max
        return samples, audio.frame_rate, audio.duration_seconds

    def find_long_tones(self, matches, final_list):
        long_matches = []
        excluded_frequencies = []
        if not matches:
            return long_matches
        last_set = matches[0]
        for tt in final_list:
            if tt["actual"][0] not in excluded_frequencies:
                excluded_frequencies.append(tt["actual"][0])
            if tt["actual"][1] not in excluded_frequencies:
                excluded_frequencies.append(tt["actual"][1])

        for x in matches:
            if len(x[1]) >= 8:
                match_found = False
                if 12 >= len(last_set) >= 8 and len(x[1]) >= 20:
                    last_set = x[1]
                elif len(x[1]) >= 15:
                    if x[1][0] == 0 or x[1][0] == 0.0:
                        continue
                    if x[1][0] in excluded_frequencies:
                        continue

                    if x[1][0] > 250:
                        tone_data = {"actual": x[1][0], "occurred": round(x[0], 2)}
                        long_matches.append(tone_data)

        return long_matches

    def find_hi_low_matches(self, lst):
        detected = True
        final_results = []
        result = []
        if not lst:
            return
        current_time = lst[0][0]
        current_group = [(lst[0][0], lst[0][1])]
        for i in range(1, len(lst)):
            if lst[i][0] - current_time <= 0.35:
                current_group.append((lst[i][0], lst[i][1]))
                current_time = lst[i][0]
            else:
                result.append(current_group)
                current_time = lst[i][0]
                current_group = [(lst[i][0], lst[i][1])]
        result.append(current_group)

        tuples_to_check = []
        for pd in result:
            if len(pd) >= 6:
                tuples_to_check.append(pd)

        for ct in tuples_to_check:
            for i in range(0, len(ct) - 2):
                if ct[i][1][0] != ct[i + 2][1][0]:
                    detected = False

            if detected:
                # first = ct[0][1][0]
                # second = ct[1][1][0]
                tone_data = {"actual": [ct[0][1][0], ct[1][1][0]], "occurred": round(ct[0][0], 2)}
                final_results.append(tone_data)

        return final_results

    def closest_match(self, target):
        self.qcii.sort()
        closest = self.qcii[0]
        smallest_difference = abs(target - closest)
        for number in self.qcii:
            difference = abs(target - number)
            if difference < smallest_difference:
                closest = number
                smallest_difference = difference
        return closest

    def normalize_qc2_matches(self, matches, threshold_percent):
        qc2_matches = []
        last_set = None
        for x in matches:
            if last_set is None:
                last_set = x
            else:
                if len(x[1]) >= 8:
                    match_found = False
                    for q in self.qcii:
                        if abs(x[1][0] - q) <= q * (threshold_percent / 100):
                            match_found = True
                            break
                    if match_found:
                        # check for long set
                        if len(last_set[1]) <= 12 and len(x[1]) >= 28:
                            a_tone_exact = self.closest_match(last_set[1][0])
                            b_tone_exact = self.closest_match(x[1][0])
                            a_tone_actual = last_set[1][0]
                            b_tone_actual = x[1][0]
                            tone_data = {"exact": [a_tone_exact, b_tone_exact], "actual": [a_tone_actual, b_tone_actual], "occured": round(last_set[0], 2)}
                            # exact = [a_tone_exact, b_tone_exact]
                            # actual = [a_tone_actual, b_tone_actual]
                            # start_time = last_set[0]
                            qc2_matches.append(tone_data)
                            last_set = x
                        else:
                            # set as last set and check next time for matching tone.
                            last_set = x
                    else:
                        continue

        return qc2_matches

    def match_frequencies(self, frequencies, file_duration, threshold_percent):
        # Round frequencies to 2 decimal places
        frequencies = [round(f, 1) for f in frequencies]

        # Initialize variables
        matching_frequencies = []
        current_match = [frequencies[0]]
        start_time = 0

        # Iterate over frequencies, checking for matches
        for i in range(1, len(frequencies)):

            # Calculate the threshold for the current frequency
            threshold = frequencies[i - 1] * threshold_percent / 100

            # Check if frequency is within the threshold of the previous frequency
            if abs(frequencies[i] - frequencies[i - 1]) <= threshold:
                # If it is, add it to the current match
                current_match.append(frequencies[i])

            # If frequency is not within the threshold of the previous frequency, start a new match
            else:
                # If the match has been going on for the desired duration, add it to the list of matches
                if len(current_match) >= 2:
                    matching_frequencies.append((start_time, current_match))
                current_match = [frequencies[i]]
                start_time = i * file_duration / len(frequencies)

        return matching_frequencies

    def amplitude_to_db(self, amplitude, ref):
        return 20 * np.log10(np.maximum(amplitude, 1e-20) / ref)

    def detect_tones(self, audio_data, rate, time_resolution_ms=100):
        window = 'hann'
        n_fft = 2048

        # Calculate hop_length based on the desired time resolution
        hop_length = rate * time_resolution_ms // 1000

        f, t, Zxx = stft(audio_data, rate, window=window, nperseg=n_fft, noverlap=n_fft - hop_length)
        amplitude = np.abs(Zxx)
        amplitude_db = self.amplitude_to_db(amplitude, np.max(amplitude))

        detected_frequencies = f[np.argmax(amplitude_db, axis=0)]

        return detected_frequencies

    def detect_key_presses(self, data, fps, duration, precision=0.04, freq_error=20):

        step = int(len(data) // (duration // precision))

        key_presses = []
        for i in range(0, len(data) - step, step):
            signal = data[i:i + step]

            frequencies = np.fft.fftfreq(signal.size, d=1 / fps)
            amplitudes = np.fft.fft(signal)

            # Low frequency
            i_min = np.where(frequencies > 0)[0][0]
            i_max = np.where(frequencies > 1050)[0][0]

            freq = frequencies[i_min:i_max]
            amp = abs(amplitudes.real[i_min:i_max])

            lf = freq[np.where(amp == max(amp))[0][0]]

            delta = freq_error
            best = 0

            for f in [697, 770, 852, 941]:
                if abs(lf - f) < delta:
                    delta = abs(lf - f)
                    best = f

            lf = best

            # High frequency
            i_min = np.where(frequencies > 1100)[0][0]
            i_max = np.where(frequencies > 2000)[0][0]

            freq = frequencies[i_min:i_max]
            amp = abs(amplitudes.real[i_min:i_max])

            hf = freq[np.where(amp == max(amp))[0][0]]

            delta = freq_error
            best = 0

            for f in [1209, 1336, 1477, 1633]:
                if abs(hf - f) < delta:
                    delta = abs(hf - f)
                    best = f

            hf = best

            t = int(i // step * precision)
            current_time = i * 1000 / fps

            if lf != 0 and hf != 0:
                current_key = self.dtmf[(lf, hf)]
                current_press = {"key": current_key, "time": t, "ms_time": current_time}
                key_presses.append(current_press)

        return key_presses

    def get_positive_key_presses(self, key_presses, threshold=250, min_presses=4):
        positive_key_presses = []
        current_group = []

        for press in key_presses:
            if not current_group or (press['key'] == current_group[-1]['key'] and press['ms_time'] - current_group[0][
                'ms_time'] <= threshold):
                current_group.append(press)
            else:
                if len(current_group) >= min_presses:
                    tone_data = {"key": current_group[0]['key'], "occurred": round(current_group[0]['ms_time'] / 1000, 2)}
                    positive_key_presses.append(tone_data)
                current_group = [press]

        if current_group and len(current_group) >= min_presses:
            tone_data = {"key": current_group[0]['key'], "occurred": round(current_group[0]['ms_time'] / 1000, 2)}
            positive_key_presses.append(tone_data)

        return positive_key_presses

    def main(self):
        audio_data, rate, file_duration = self.load_audio(self.audio_segment)
        averaged_frequencies = self.detect_tones(audio_data, rate)

        # Convert the averaged frequencies NumPy array to a list
        averaged_frequencies_list = averaged_frequencies.tolist()

        # You can print or process the averaged frequencies further as needed
        matched_frequencies = self.match_frequencies(averaged_frequencies_list, file_duration,
                                                     self.config_data["tone_extraction"]["threshold_percent"])

        if self.config_data["tone_extraction"]["quick_call"]["enabled"]:
            # Find Quick Call Matches. Frequency must be +- 2% of actual QC2 Tones. Tries to match what it heard to actual QCII frequencies within +-2%
            quick_call = self.normalize_qc2_matches(matched_frequencies, 2)
        else:
            # required empty list for Long Tone
            quick_call = []

        if self.config_data["tone_extraction"]["long_tone"]["enabled"]:
            # Find Lone Tone Matches. If QCII enabled check Detected QCII tones to make sure match isn't part of the QCII tone set. Tone must last for 1.2 seconds minimum.
            long_tones = self.find_long_tones(matched_frequencies, quick_call)
        else:
            long_tones = []

        if self.config_data["tone_extraction"]["hi-low_tone"]["enabled"]:
            # Find any Alternating Hi-Low Tone patterns as short as 200ms each. Must occur 3 times alternating matched frequencies.
            hi_low_tones = self.find_hi_low_matches(matched_frequencies)
        else:
            hi_low_tones = []


        # Find DTMF Key Presses must detect a key press for 250ms minimum and last for 1000ms. Considers 1000ms length one key press.
        if self.config_data["tone_extraction"]["dtmf"]["enabled"]:
            key_presses = self.detect_key_presses(audio_data, rate, file_duration)
            dtmf_tones = self.get_positive_key_presses(key_presses)
        else:
            dtmf_tones = []

        return quick_call, hi_low_tones, long_tones, dtmf_tones
