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

        if self.page_id:
            self.base_url_page = f"https://graph.facebook.com/v18.0/{self.page_id}"

        if self.group_id:
            self.base_url_group = f"https://graph.facebook.com/v18.0/{self.group_id}"

    def post_to_page(self, message):
        """
        Posts a message to the Facebook page.

        :param str message: The message to be posted on the Facebook page.
        :return: Response JSON or False in case of an error.
        """
        if not self.page_id or not self.page_access_token:
            module_logger.error("Facebook Page ID or access token not set")
            return False

        url = f"{self.base_url_page}/feed"
        payload = {
            "message": message,
            "access_token": self.page_access_token
        }
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            return response.json()
        else:
            module_logger.error(f"Error Posting to Facebook Page: {response.text}")
            return False

    def comment_on_page_post(self, post_id, message):
        """
        Comments on a specific post on the Facebook page.

        :param str post_id: The ID of the post to comment on.
        :param str message: The message to be posted as a comment.
        :return: Response JSON or False in case of an error.
        """
        if not self.page_id or not self.page_access_token:
            module_logger.error("Facebook Page ID or access token not set")
            return False

        url = f"https://graph.facebook.com/v18.0/{post_id}/comments"
        payload = {
            "message": message,
            "access_token": self.page_access_token
        }
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            return response.json()
        else:
            module_logger.error(f"Error Posting Comment to Facebook Page: {response.text}")
            return False

    def post_to_group(self, message):
        """
        Posts a message to the Facebook group.

        :param str message: The message to be posted on the Facebook group.
        :return: Response JSON or False in case of an error.
        """
        if not self.group_id or not self.group_access_token:
            module_logger.error("Facebook Group ID or access token not set")
            return False

        url = f"{self.base_url_group}/feed"
        payload = {
            "message": message,
            "access_token": self.group_access_token
        }
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            return response.json()
        else:
            module_logger.error(f"Error Posting to Facebook Group: {response.text}")
            return False

    def comment_on_group_post(self, post_id, message):
        """
        Comments on a specific post on the Facebook group.

        :param str post_id: The ID of the post to comment on.
        :param str message: The message to be posted as a comment.
        :return: Response JSON or False in case of an error.
        """
        if not self.group_id or not self.group_access_token:
            module_logger.error("Facebook Group ID or access token not set")
            return False

        url = f"https://graph.facebook.com/v18.0/{post_id}/comments"
        payload = {
            "message": message,
            "access_token": self.group_access_token
        }
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            return response.json()
        else:
            module_logger.error(f"Error Posting to Facebook Group Comment: {response.text}")
            return False

    def post_message(self, message, comment=""):

        page_result = False
        group_result = False

        try:
            if self.page_id:
                module_logger.info("Posting to Facebook Page")
                page_response = self.post_to_page(message)
                if page_response and 'id' in page_response:
                    page_result = True
                    if comment != "":
                        module_logger.info("Posting to Facebook Group Page Comment")
                        page_post_id = page_response["id"]
                        comment_page_response = self.comment_on_page_post(page_post_id, comment)
                        page_result = comment_page_response
                else:
                    page_result = False

            if self.group_id:
                module_logger.info("Posting to Facebook Group")
                group_response = self.post_to_group(message)
                if group_response and 'id' in group_response:
                    group_result = True
                    if comment != "":
                        module_logger.info("Posting to Facebook Group Post Comment")
                        group_post_id = group_response["id"]
                        comment_group_response = self.comment_on_group_post(group_post_id, comment)
                        group_result = comment_group_response
                else:
                    group_result = False

        except Exception as e:
            module_logger.error(f"An error occurred while posting to Facebook: {e}")

        return page_result, group_result


def generate_facebook_message(config_data, detection_data, test=True):

    post_body = config_data["facebook_settings"].get("post_body",
                                                     "{timestamp} Departments:\n{detector_list}")

    # Preprocess timestamp
    timestamp = datetime.fromtimestamp(detection_data.get("timestamp", 0))
    hr_timestamp = timestamp.strftime("%H:%M %b %d %Y")

    detector_list = "\n".join([
        f'{x["detector_name"]} {x["detector_config"]["station_number"] if x["detector_config"].get("station_number", 0) != 0 else ""}' for x in detection_data["matches"]])

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
        "stream_url": config_data["stream_settings"]["stream_url"] if config_data["stream_settings"].get("stream_url") else ""
    }

    comment_body = comment_body.format_map(mapping)
    return comment_body
