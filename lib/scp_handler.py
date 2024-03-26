import logging
import os
import time

from paramiko import SSHClient, AutoAddPolicy, RSAKey, SSHException
from paramiko.sftp import SFTPError
import traceback

module_logger = logging.getLogger('icad_tone_detection.scp_upload')


class SCPStorage:
    def __init__(self, config_data):
        scp_config = config_data['scp']
        self.host = scp_config['host']
        self.port = scp_config['port']
        self.username = scp_config['user']
        self.password = scp_config['password']
        self.private_key_path = scp_config['private_key_path']
        self.base_url = scp_config['base_url']
        self.remote_path = config_data['remote_path']

    def upload_file(self, audio_file, audio_file_name, max_attempts=3):
        """Uploads a file to the SCP storage.

        :param max_attempts: Maximum times we will try file upload if there is an SCP exception
        :param audio_file: File-like object to upload.
        :param audio_file_name: The name of the file to save as on the server.
        :return: Dictionary containing the file URL or False if upload fails.
        """
        attempt = 0
        while attempt < max_attempts:
            try:
                full_remote_path = os.path.join(self.remote_path, audio_file_name)
                ssh_client, sftp = self._create_sftp_session()

                try:
                    sftp.stat(self.remote_path)
                except FileNotFoundError:
                    return {"success": False, "message": f'Remote Path {self.remote_path} doesn\'t exist', "result": None}

                if hasattr(audio_file, 'read'):
                    audio_file.seek(0)

                # Use putfo for file-like objects
                sftp.putfo(audio_file, full_remote_path)
                sftp.close()
                ssh_client.close()

                file_url = f"{self.base_url}/{audio_file_name}"

                return {"success": True, "message": "SCP Upload Success", "result": file_url}
            except SFTPError as error:
                traceback.print_exc()
                module_logger.warning(f'Attempt {attempt + 1} failed during uploading a file: {error}')
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(5)
            except Exception as error:
                traceback.print_exc()
                return {"success": False, "message": f'Error occurred during uploading a file: {error}', "result": None}

        return {"success": False, "message": f'All {max_attempts} attempts failed.', "result": None}

    def _create_sftp_session(self):
        """Creates an SFTP session.

        :return: A tuple of SSH client and SFTP session.
        :raises: FileNotFoundError if private key file doesn't exist.
                  SSHException for other SSH connection errors.
        """
        ssh_client = SSHClient()
        ssh_client.load_system_host_keys()

        # Automatically add host key
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())

        try:
            # Use the private key for authentication instead of a password
            private_key = RSAKey.from_private_key_file(self.private_key_path)
            ssh_client.connect(self.host, port=self.port, username=self.username, pkey=private_key,
                               look_for_keys=False, allow_agent=False)
        except FileNotFoundError as e:
            module_logger.error(f'Private key file not found: {e}')
            raise FileNotFoundError(f'Private key file not found: {e}')
        except SSHException as e:
            module_logger.error(f'SSH connection error: {e}')
            raise SSHException(f'SSH connection error: {e}')

        sftp = ssh_client.open_sftp()
        return ssh_client, sftp