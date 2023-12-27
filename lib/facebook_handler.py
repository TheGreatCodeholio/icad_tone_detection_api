from datetime import datetime
import logging

import requests

module_logger = logging.getLogger('icad_tone_detection.facebook')


class FacebookAPI:
    def __init__(self, facebook_config):
        """
            Initializes the FacebookAPI class with the necessary tokens and IDs.

            :param dict facebook_config: A dictionary containing the necessary Facebook credentials.
        """
        self.page_id = facebook_config.get("page_id")
        self.group_id = facebook_config.get("group_id")
        self.page_access_token = facebook_config.get("page_token")
        self.group_access_token = facebook_config.get("group_token")

        self.reel_publisher = FacebookReelPublisher(self.page_id, self.page_access_token) if self.page_id and self.page_access_token else None

        self.base_url_page = f"https://graph.facebook.com/v18.0/{self.page_id}" if self.page_id else None
        self.base_url_group = f"https://graph.facebook.com/v18.0/{self.group_id}" if self.group_id else None

    def _make_request(self, method, url, payload):
        try:
            response = requests.request(method, url, data=payload)
            response.raise_for_status()
            return {'success': True, 'message': 'Success', 'result': response.json()}
        except requests.RequestException as e:
            logging.error(f"Error in {method} request: {e}")
            return {'success': False, 'message': str(e), 'result': None}

    def post_to_page(self, message):
        if not self.page_id or not self.page_access_token:
            return {'success': False, 'message': "Facebook Page ID or access token not set", 'result': None}

        url = f"{self.base_url_page}/feed"
        payload = {"message": message, "access_token": self.page_access_token}
        return self._make_request("POST", url, payload)

    def comment_on_page_post(self, post_id, message):
        if not self.page_id or not self.page_access_token:
            return {'success': False, 'message': "Facebook Page ID or access token not set", 'result': None}

        url = f"https://graph.facebook.com/v18.0/{post_id}/comments"
        payload = {"message": message, "access_token": self.page_access_token}
        return self._make_request("POST", url, payload)

    def post_to_group(self, message):
        if not self.group_id or not self.group_access_token:
            return {'success': False, 'message': "Facebook Group ID or access token not set", 'result': None}

        url = f"{self.base_url_group}/feed"
        payload = {"message": message, "access_token": self.group_access_token}
        return self._make_request("POST", url, payload)

    def comment_on_group_post(self, post_id, message):
        if not self.group_id or not self.group_access_token:
            return {'success': False, 'message': "Facebook Group ID or access token not set", 'result': None}

        url = f"https://graph.facebook.com/v18.0/{post_id}/comments"
        payload = {"message": message, "access_token": self.group_access_token}
        return self._make_request("POST", url, payload)

    def initialize_reel_upload(self):
        if not self.reel_publisher:
            return {'success': False, 'message': "Reel publisher not initialized", 'result': None}
        return self.reel_publisher.initialize_upload_session()

    def upload_reel_video(self, video_id, file_path):
        if not self.reel_publisher:
            return {'success': False, 'message': "Reel publisher not initialized", 'result': None}
        return self.reel_publisher.upload_video(video_id, file_path)

    def publish_reel(self, video_id, description=""):
        if not self.reel_publisher:
            return {'success': False, 'message': "Reel publisher not initialized", 'result': None}
        return self.reel_publisher.publish_reel(video_id, description)

    def get_published_reels(self):
        if not self.reel_publisher:
            return {'success': False, 'message': "Reel publisher not initialized", 'result': None}
        return self.reel_publisher.get_reels_list()

    def post_message(self, message, comment=""):
        results = {}

        if self.page_id:
            logging.info("Posting to Facebook Page")
            page_response = self.post_to_page(message)
            results['page_post'] = page_response
            if page_response['success'] and comment:
                logging.info("Posting comment to Facebook Page")
                page_post_id = page_response['result']['id']
                results['page_comment'] = self.comment_on_page_post(page_post_id, comment)

        if self.group_id:
            logging.info("Posting to Facebook Group")
            group_response = self.post_to_group(message)
            results['group_post'] = group_response
            if group_response['success'] and comment:
                logging.info("Posting comment to Facebook Group")
                group_post_id = group_response['result']['id']
                results['group_comment'] = self.comment_on_group_post(group_post_id, comment)

        return results


class FacebookReelPublisher:
    def __init__(self, page_id, access_token):
        self.page_id = page_id
        self.access_token = access_token
        self.graph_base_url = "https://graph.facebook.com/v18.0"
        self.upload_base_url = "https://rupload.facebook.com"

    def _make_request(self, method, url, **kwargs):
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return {'success': True, 'message': 'Success', 'result': response.json()}
        except requests.RequestException as e:
            return {'success': False, 'message': str(e), 'result': None}

    def initialize_upload_session(self):
        url = f"{self.graph_base_url}/{self.page_id}/video_reels"
        payload = {
            "upload_phase": "start",
            "access_token": self.access_token
        }
        return self._make_request("POST", url, json=payload)

    def upload_video(self, video_id, file_path):
        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            return {'success': False, 'message': f"File error: {e}", 'result': None}

        headers = {
            "Authorization": f"OAuth {self.access_token}",
            "offset": "0",
            "file_size": str(file_size)
        }
        with open(file_path, 'rb') as f:
            return self._make_request("POST", f"{self.upload_base_url}/video-upload/v18.0/{video_id}", headers=headers,
                                      data=f)

    def publish_reel(self, video_id, description=""):
        url = f"{self.graph_base_url}/{self.page_id}/video_reels"
        payload = {
            "access_token": self.access_token,
            "video_id": video_id,
            "upload_phase": "finish",
            "video_state": "PUBLISHED",
            "description": description
        }
        return self._make_request("POST", url, params=payload)

    def get_reels_list(self):
        url = f"{self.graph_base_url}/{self.page_id}/video_reels"
        params = {"access_token": self.access_token}
        return self._make_request("GET", url, params=params)


def generate_facebook_message(config_data, detection_data, test=True):
    post_body = config_data["facebook_settings"].get("post_body",
                                                     "{timestamp} Departments:\n{detector_list}")

    # Preprocess timestamp
    timestamp = datetime.fromtimestamp(detection_data.get("timestamp", 0))
    hr_timestamp = timestamp.strftime("%H:%M %b %d %Y")

    detector_list = "\n".join([
        f'{x["detector_name"]} {x["detector_config"]["station_number"] if x["detector_config"].get("station_number", 0) != 0 else ""}'
        for x in detection_data["matches"]])

    if test:
        post_body = f"TEST TEST TEST TEST TEST\n\n{post_body}"

    # Create a mapping
    mapping = {
        "detector_list": detector_list,
        "timestamp": hr_timestamp,
        "transcript": detection_data["transcript"] if detection_data.get("transcript") else "",
        "mp3_url": detection_data["mp3_url"] if detection_data.get("mp3_url") else "",
        "stream_url": config_data["stream_settings"]["stream_url"] if config_data["stream_settings"].get(
            "stream_url") else ""
    }

    post_body = post_body.format_map(mapping)
    return post_body


def generate_facebook_comment(config_data, detection_data):
    comment_body = config_data["facebook_settings"].get("comment_body", "{transcript}{stream_url}")

    if comment_body == "":
        return comment_body

    timestamp = datetime.fromtimestamp(detection_data.get("timestamp", 0))
    hr_timestamp = timestamp.strftime("%H:%M %b %d %Y")

    detector_list = "\n".join([
        f'{x["detector_name"]} {x["detector_config"]["station_number"] if x["detector_config"].get("station_number", 0) != 0 else ""}'
        for x in detection_data["matches"]])

    # Create a mapping
    mapping = {
        "detector_list": detector_list,
        "timestamp": hr_timestamp,
        "transcript": detection_data["transcript"] if detection_data.get("transcript") else "",
        "mp3_url": detection_data["mp3_url"] if detection_data.get("mp3_url") else "",
        "stream_url": config_data["stream_settings"]["stream_url"] if config_data["stream_settings"].get(
            "stream_url") else ""
    }

    comment_body = comment_body.format_map(mapping)
    return comment_body
