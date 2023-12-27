import logging
import smtplib
import ssl
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

module_logger = logging.getLogger('icad_tone_detection.email')


class EmailSender:
    """EmailSender is a class responsible for sending emails with given configurations.

        Attributes:
            sender_email (str): Sender's email address.
            sender_name (str): Sender's name.
            smtp_username (str): Username for the SMTP server.
            smtp_password (str): Password for the SMTP server.
            smtp_hostname (str): Hostname of the SMTP server.
            smtp_port (int): Port number of the SMTP server.
            smtp_security (str): Security protocol for the SMTP server, either SSL or TLS.
        """

    def __init__(self, config_data):
        """Initializes the EmailSender with configuration data.

                Args:
                    config_data (dict): A dictionary containing configuration data.
        """
        # Validate the config data before initializing attributes
        self.validate_config_data(config_data)

        self.sender_email = config_data["email_settings"]["email_address_from"]
        self.sender_name = config_data["email_settings"]["email_text_from"]
        self.smtp_username = config_data["email_settings"]["smtp_username"]
        self.smtp_password = config_data["email_settings"]["smtp_password"]
        self.smtp_hostname = config_data["email_settings"]["smtp_hostname"]
        self.smtp_port = config_data["email_settings"]["smtp_port"]
        self.smtp_security = config_data["email_settings"]["smtp_security"]

    def send_alert_email(self, to, subject, body_html):
        """Sends an alert email with the given parameters.

                Args:
                    to (list): A list of recipient email addresses.
                    subject (str): The subject of the email.
                    body_html (str): The HTML body of the email.

                Returns:
                    None
        """
        module_logger.info("Sending Alert Email")

        # Validate the recipient list
        if not isinstance(to, list) or not to:
            module_logger.error("Invalid recipient list")
            return

        # Create a multipart message object
        message = MIMEMultipart()
        message['From'] = formataddr(
            (str(Header(self.sender_name, 'utf-8')),
             self.sender_email))

        # Determine whether to use 'To' or 'Bcc' field for the recipient addresses based on list size
        if len(to) == 1:
            message['To'] = to[0]
        else:
            message['Bcc'] = ", ".join(to)

        # Set the subject of the email
        message['Subject'] = subject

        # Attach the HTML message body
        html_part = MIMEText(body_html, 'html')
        message.attach(html_part)

        try:
            # Connect to the SMTP server and send the email based on the chosen security protocol
            if self.smtp_security.upper() == "SSL":
                with smtplib.SMTP_SSL(self.smtp_hostname, self.smtp_port,
                                      context=ssl.create_default_context()) as smtp_server:
                    smtp_server.login(self.smtp_username, self.smtp_password)
                    smtp_server.send_message(message)
                    module_logger.info("Email sent successfully using SSL")

            elif self.smtp_security.upper() == "TLS":
                with smtplib.SMTP(self.smtp_hostname, self.smtp_port) as smtp_server:
                    smtp_server.ehlo()
                    smtp_server.starttls()
                    smtp_server.login(self.smtp_username, self.smtp_password)
                    smtp_server.send_message(message)
                    module_logger.info("Email sent successfully using TLS")

            else:
                module_logger.error(f'Unsupported security protocol: {self.smtp_security}')

        except smtplib.SMTPException as e:
            # Log SMTP-specific errors
            module_logger.error(f"SMTP error occurred: {e}")

        except Exception as e:
            # Log any other unexpected errors
            module_logger.error(f"An error occurred: {e}")

    def validate_config_data(self, config_data):
        """Validates the configuration data.

        Args:
            config_data (dict): A dictionary containing configuration data.

        Raises:
            ValueError: If any of the necessary configuration data is missing.
        """
        required_keys = [
            "email_address_from",
            "email_text_from",
            "smtp_username",
            "smtp_password",
            "smtp_hostname",
            "smtp_port",
            "smtp_security"
        ]

        # Check that "email_settings" key exists
        if "email_settings" not in config_data:
            raise ValueError("Missing 'email_settings' in config data")

        email_settings = config_data["email_settings"]

        # Check that all required keys exist
        for key in required_keys:
            if key not in email_settings:
                raise ValueError(f"Missing '{key}' in email settings")

        # Additional validation for smtp_port (should be an integer)
        if not isinstance(email_settings["smtp_port"], int):
            raise ValueError("'smtp_port' should be an integer")

        # Additional validation for smtp_security (should be either "SSL" or "TLS")
        if email_settings["smtp_security"].upper() not in ["SSL", "TLS"]:
            raise ValueError("'smtp_security' should be either 'SSL' or 'TLS'")


def generate_alert_email(config_data, detection_data, test=True, detector_data=None, triggered_detectors=None):
    """
    Generates the subject and body of an alert email by replacing placeholders with actual data.

    :param config_data: Dictionary containing configuration data
    :param detection_data: Dictionary containing data about the detection
    :param detector_data: Dictionary containing a single detectors alert data (optional)
    :param triggered_detectors: List containing all detectors that triggered for this alert (optional)
    :return: Tuple containing the subject and body of the email
    """



    try:
        if detector_data is None and triggered_detectors is None:
            module_logger.error(
                "Failed to generate alert email: Neither detector_data nor triggered_detectors was provided.")
            return False, False

        if triggered_detectors is not None:
            # Case: Grouped alert for many detectors
            email_subject_template = config_data["email_settings"].get("grouped_email_subject", "Dispatch Alert")
            email_body_template = config_data["email_settings"].get("grouped_email_body",
                                                                    "{detector_list} Alert at {timestamp}")
            detector_list = ", ".join([f'{x["detector_name"]} {x["detector_config"]["station_number"] if x["detector_config"].get("station_number", 0) != 0 else ""}' for x in triggered_detectors])
            detector_name = "Multiple Detectors"  # Default value for grouped detectors

            stream_url = config_data["stream_settings"].get("stream_url") if config_data["stream_settings"].get("stream_url") else "https://openmhz.com/"


        else:
            # Case: Single alert for one detector
            email_subject_template = detector_data["detector_config"].get("alert_email_subject") or config_data[
                "email_settings"].get("alert_email_subject", "Dispatch Alert - {detector_name}")
            email_body_template = detector_data["detector_config"].get("alert_email_body") or config_data[
                "email_settings"].get("alert_email_body",
                                      "{detector_name} Alert at {timestamp}")
            detector_name = detector_data.get("detector_name", "Example Detector")
            detector_list = None
            stream_url = detector_data.get("stream_url") or config_data["stream_settings"].get("stream_url") if config_data["stream_settings"].get("stream_url") else "https://openmhz.com/"

        # Convert UNIX timestamp to human-readable format
        timestamp = datetime.fromtimestamp(detection_data.get("timestamp", 0))  # added default value to avoid None
        hr_timestamp = timestamp.strftime("%H:%M:%S %b %d %Y")

        if test:
            email_body_template = f"<font color=\"red\"><b>TEST TEST TEST TEST</b></font><br><br>{email_body_template}"

        # Create a mapping dictionary to replace placeholders in the subject and body templates
        mapping = {
            "detector_name": detector_name,
            "detector_list": detector_list,
            "timestamp": hr_timestamp,
            "transcript": detection_data["transcript"] if detection_data.get("transcript") else "Empty Transcript",
            "mp3_url": detection_data["mp3_url"] if detection_data.get("mp3_url") else "https://openmhz.com/",
            "stream_url": stream_url
        }

        # Format the email subject and body using the mapping
        email_subject = email_subject_template.format_map(mapping)
        email_body = email_body_template.format_map(mapping)

        return email_subject, email_body

    except Exception as e:
        module_logger.exception("Failed to generate alert email")
        return False, False
