import logging
import smtplib
import ssl
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

module_logger = logging.getLogger('tr_tone_detection.email')


class EmailSender:
    def __init__(self, config_data):
        self.sender_email = config_data["email_settings"]["email_address_from"]
        self.sender_name = config_data["email_settings"]["email_text_from"]
        self.smtp_username = config_data["email_settings"]["smtp_username"]
        self.smtp_password = config_data["email_settings"]["smtp_password"]
        self.smtp_hostname = config_data["email_settings"]["smtp_hostname"]
        self.smtp_port = config_data["email_settings"]["smtp_port"]
        self.smtp_security = config_data["email_settings"]["smtp_security"]

    def send_alert_email(self, to, subject, body_html):
        module_logger.info("Sending Alert Email")
        # Create a multipart message object
        message = MIMEMultipart()
        message['From'] = formataddr(
            (str(Header(self.sender_name, 'utf-8')),
             self.sender_email))
        message['To'] = to
        message['Subject'] = subject

        # Attach the HTML message
        html_part = MIMEText(body_html, 'html')
        message.attach(html_part)

        # Connect to the SMTP server.
        if self.smtp_security.upper() == "SSL":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_hostname, self.smtp_port, context=context) as smtp_server:
                smtp_server.login(self.smtp_username, self.smtp_password)
                # Send the email
                smtp_server.send_message(message)
        elif self.smtp_security.upper() == "TLS":
            with smtplib.SMTP(self.smtp_hostname, self.smtp_port) as smtp_server:
                smtp_server.ehlo()
                smtp_server.starttls()
                smtp_server.login(self.smtp_username, self.smtp_password)
                # Send the email
                smtp_server.send_message(message)
        else:
            module_logger.error(f'Unsupported security protocol: {self.smtp_security}')


def generate_alert_email(config_data, detector_data, call_data):
    if detector_data["alert_email_subject"] == "":
        email_subject = config_data["email_settings"]["alert_email_subject"]
    else:
        email_subject = detector_data["alert_email_subject"]

    if detector_data["alert_email_body"] == "":
        email_body = config_data["email_settings"]["alert_email_body"]
    else:
        email_body = detector_data["alert_email_body"]

    # Preprocess timestamp
    timestamp = datetime.fromtimestamp(call_data.get("start_time"))
    hr_timestamp = timestamp.strftime("%H:%M:%S %b %d %Y")

    # Create a mapping
    mapping = {
        "detector_name": detector_data.get("detector_name"),
        "timestamp": hr_timestamp,
        "transcript": call_data.get("transcript"),
        "mp3_url": call_data.get("mp3_url")
    }

    # Use the mapping to format the strings
    email_subject = email_subject.format_map(mapping)
    email_body = email_body.format_map(mapping)

    return email_subject, email_body
