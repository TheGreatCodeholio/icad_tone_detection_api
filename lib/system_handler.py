import logging
import uuid

module_logger = logging.getLogger("icad_tone_detection.system_handler")


def get_systems(db, system_id=None):
    if not system_id:
        query = f"SELECT * from `radio_systems` WHERE 1"
        params = None
    else:
        query = f"SELECT * from `radio_systems` WHERE system_id = %s"
        params = (system_id,)
    result = db.execute_query(query, params)
    return result


def add_system(db, system_data):
    if not system_data:
        module_logger.warning(f"System Data Empty")
        return
    api_key = str(uuid.uuid4())
    query = f"INSERT INTO `radio_systems` (system_name, system_county, system_state, system_fips, system_api_key) VALUES (%s, %s, %s, %s, %s)"
    params = (system_data.get('system_name'), system_data.get("system_county", None), system_data.get("system_state", None), system_data.get("system_fips", None), api_key)
    result = db.execute_commit(query, params)
    return result