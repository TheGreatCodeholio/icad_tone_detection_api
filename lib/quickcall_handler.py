import logging

module_logger = logging.getLogger("icad_tone_detection.quickcall_handler")


def add_quickcall_detector(db, agency_id, detector_data):
    if not agency_id or not detector_data:
        module_logger.warning(f"Agency ID or Detector Data Empty")
        return
    query = f"INSERT INTO `qc_detectors` (agency_id, a_tone, b_tone, tone_tolerance, ignore_time) VALUES (%s, %s, %s, %s, %s)"
    params = (agency_id, detector_data.get("a_tone", 0.0), detector_data.get("b_tone", 0.0),
              detector_data.get("tone_tolerance", 2), detector_data.get("ignore_time", 180))
    result = db.execute_commit(query, params, return_row=True)
    return result


def get_quickcall_detector(db, detector_id=None):
    if not detector_id:
        query = f"SELECT qcd.*, ag.* FROM `qc_detectors` qcd LEFT JOIN icad.agencies ag on qcd.agency_id = ag.agency_id WHERE 1"
        params = None
    else:
        query = f"SELECT qcd.*, ag.* FROM `qc_detectors` qcd LEFT JOIN icad.agencies ag on qcd.agency_id = ag.agency_id WHERE qcd.detector_id = %s"
        params = (detector_id,)
    result = db.execute_query(query, params)
    return result
