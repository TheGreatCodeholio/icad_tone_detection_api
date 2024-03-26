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
        """

    def __init__(self, config_data):
        """Initializes the EmailSender with configuration data.

                Args:
                    config_data (dict): A dictionary containing configuration data.
        """

        self.sender_email = config_data["email"]["email_address_from"]
        self.sender_name = config_data["email"]["email_text_from"]
        self.smtp_username = config_data["email"]["user"]
        self.smtp_password = config_data["email"]["password"]
        self.smtp_hostname = config_data["email"]["host"]
        self.smtp_port = config_data["email"]["port"]

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
            error_message = "Invalid recipient list"
            return {"success": False, "message": error_message}

        # Create a multipart message object
        message = MIMEMultipart()
        message['From'] = formataddr(
            (str(Header(self.sender_name, 'utf-8')),
             self.sender_email))

        # Extract the domain from the sender's email address
        sender_domain = self.sender_email.split('@')[1]

        # Determine whether to use 'To' or 'Bcc' field for the recipient addresses based on list size
        if len(to) == 1:
            message['To'] = to[0]
        else:
            message['To'] = f'Undisclosed Recipients <noreply@{sender_domain}>'
            message['Bcc'] = ", ".join(to)

        # Set the subject of the email
        message['Subject'] = subject

        # Attach the HTML message body
        html_part = MIMEText(body_html, 'html')
        message.attach(html_part)

        try:
            # Connect to the SMTP server and send the email based on the chosen security protocol deciphered from
            # port number
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_hostname, self.smtp_port,
                                      context=ssl.create_default_context()) as smtp_server:
                    smtp_server.login(self.smtp_username, self.smtp_password)
                    smtp_server.send_message(message)
                    return {"success": True, "message": "Email sent successfully using SSL"}

            elif self.smtp_port == 587:
                with smtplib.SMTP(self.smtp_hostname, self.smtp_port) as smtp_server:
                    smtp_server.ehlo()
                    smtp_server.starttls()
                    smtp_server.login(self.smtp_username, self.smtp_password)
                    smtp_server.send_message(message)
                    return {"success": True, "message": "Email sent successfully using TLS"}

            else:
                error_message = f'Unsupported security protocol: {self.smtp_port}'
                return {"success": False, "message": error_message}

        except smtplib.SMTPAuthenticationError as e:
            error_message = f"SMTP authentication occurred: {e}"
            return {"success": False, "message": error_message}

        except smtplib.SMTPException as e:
            error_message = f"SMTP error occurred: {e}"
            return {"success": False, "message": error_message}

        except Exception as e:
            error_message = f"An error occurred: {e}"
            return {"success": False, "message": error_message}


def generate_finder_email(call_data):
    # Get the current time in the container's timezone
    current_time = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

    tone_data = call_data.get('tones')
    subject = "iCAD Tone Finder Alert"
    email_body = f"Below is the summary of the tones detected:\n\nTimestamp: {current_time}\n\n"

    # Process hi_low_tone
    if tone_data.get('hi_low_tone'):
        email_body += "**Hi-Low Tones:**\n"
        for idx, tone in enumerate(tone_data['hi_low_tone'], 1):
            email_body += f"{idx}. Detected Tones: {', '.join(map(str, tone['detected']))}\n"
            email_body += f"   - Start Time: {tone['start']} seconds\n"
            email_body += f"   - End Time: {tone['end']} seconds\n\n"
    else:
        email_body += "**Hi-Low Tones:**\n- No detections were found.\n\n"

    # Process long_tone
    if tone_data.get('long_tone'):
        email_body += "**Long Tones:**\n"
        for idx, tone in enumerate(tone_data['long_tone'], 1):
            email_body += f"{idx}. Detected Tones: {', '.join(map(str, tone['detected']))}\n"
            email_body += f"   - Start Time: {tone['start']} seconds\n"
            email_body += f"   - End Time: {tone['end']} seconds\n\n"
    else:
        email_body += "**Long Tones:**\n- No detections were found.\n\n"

    # Process two_tone
    if tone_data.get('two_tone'):
        email_body += "**Two-Tone Detections:**\n"
        for idx, tone in enumerate(tone_data['two_tone'], 1):
            email_body += f"{idx}. Tone ID: {tone['tone_id']}\n"
            email_body += f"   - Detected Tones: {', '.join(map(str, tone['detected']))}\n"
            email_body += f"   - Start Time: {tone['start']} seconds\n"
            email_body += f"   - End Time: {tone['end']} seconds\n\n"
    else:
        email_body += "**Two-Tone Detections:**\n- No detections were found.\n\n"

    return subject, email_body


def generate_system_alert_email(system_data, match_list, call_data, test=True):
    """
    Generates the subject and body of an alert email by replacing placeholders with actual data.

    :param system_data: Dictionary containing data about the detection
    :param match_list: List containing all detectors that triggered for this alert (optional)
    :param call_data: The call data uploaded from Trunk Recorder
    :param test: Test mode (optional, defaults to True)
    :return: Tuple containing the subject and body of the email
    """

    # Get the current time in the container's timezone
    current_time = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

    subject = system_data.get('email_alert_subject', "Dispatch Alert")
    email_body = system_data.get('email_alert_body', '{detector_list} Alert at {timestamp}<br><br>{transcript}<br><br><a href="{audio_url}">Click for Dispatch Audio</a><br><br><a href="{stream_url}">Click Audio Stream</a>')

    try:

        agency_list = ", ".join(match.get("agency_name") for match in match_list if match.get("agency_name") is not None)

        if test:
            email_body = f"<font color=\"red\"><b>TEST TEST TEST TEST</b></font><br><br>{email_body}<br><br>"

        # Create a mapping dictionary to replace placeholders in the subject and body templates
        mapping = {
            "agency_list": agency_list,
            "timestamp": current_time,
            "transcript": call_data.get("transcript", "Empty Transcript"),
            "audio_url": call_data.get("audio_url", ""),
            "stream_url": call_data.get("stream_url", "")
        }

        # Format the email subject and body using the mapping
        email_subject = subject.format_map(mapping)
        email_body = email_body.format_map(mapping)

        return email_subject, email_body

    except Exception as e:
        module_logger.exception(f"Failed to generate system alert email: {e}")
        return None, None
