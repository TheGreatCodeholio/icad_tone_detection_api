import logging
import os
import time
from contextlib import contextmanager
from urllib.parse import urljoin
from google.cloud import storage
import boto3
from paramiko import SSHClient, AutoAddPolicy, RSAKey, SSHException
from paramiko.sftp import SFTPError
import traceback

module_logger = logging.getLogger('icad_tone_detection.remote_storage')


def get_storage(storage_type, config_data):
    if storage_type == 'google_cloud':
        return GoogleCloudStorage(config_data)
    elif storage_type == 'aws_s3':
        return AWSS3Storage(config_data)
    elif storage_type == 'scp':
        return SCPStorage(config_data)
    else:
        raise ValueError(f"Invalid storage type: {storage_type}")


class GoogleCloudStorage:
    def __init__(self, config_data):
        google_cloud_config = config_data['google_cloud']

        self.storage_client = storage.Client.from_service_account_json(
            google_cloud_config['credentials_path'], project=google_cloud_config['project_id'])
        self.bucket_name = google_cloud_config['bucket_name']
        self.bucket = self.storage_client.get_bucket(self.bucket_name)

    def upload_file(self, local_audio_path, remote_path, remote_file_name, make_public=True):
        if self.bucket:
            # Full path for file in GCS, composed of remote_folder and remote_file_name
            full_remote_path = os.path.join(remote_path, remote_file_name)

            # Open the file in binary mode
            with open(local_audio_path, 'rb') as audio_file:
                # Upload the file
                blob = self.bucket.blob(full_remote_path)
                blob.upload_from_file(audio_file)

            if make_public:
                blob.make_public()

            public_url = blob.public_url if make_public else None
            return {"file_path": public_url}

    def download_file(self, remote_path, local_path):
        if self.bucket:
            blob = self.bucket.blob(remote_path)
            blob.download_to_filename(local_path)

    def delete_file(self, remote_path):
        if self.bucket:
            blob = self.bucket.blob(remote_path)
            blob.delete()

    def list_files(self, prefix=None):
        if self.bucket:
            blobs = self.storage_client.list_blobs(self.bucket_name, prefix=prefix)
            return [blob.name for blob in blobs]


class AWSS3Storage:
    def __init__(self, config_data):
        aws_s3_config = config_data['aws_s3']

        self.s3 = boto3.resource(
            's3',
            aws_access_key_id=aws_s3_config['access_key_id'],
            aws_secret_access_key=aws_s3_config['secret_access_key']
        )
        self.bucket_name = aws_s3_config['bucket_name']
        self.bucket = self.s3.Bucket(self.bucket_name)

    def upload_file(self, local_audio_path, remote_path, remote_file_name, make_public=True):
        if self.bucket:

            full_remote_path = os.path.join(remote_path, remote_file_name)

            # Open the file in binary mode
            with open(local_audio_path, 'rb') as audio_file:
                # Upload the file
                obj = self.bucket.put_object(Key=full_remote_path, Body=audio_file.read())

            if make_public:
                obj.Acl().put(ACL='public-read')

            public_url = f"https://{self.bucket_name}.s3.amazonaws.com/{full_remote_path}" if make_public else None

            return {"file_path": public_url}

    def download_file(self, remote_path, local_path):
        if self.bucket:
            self.bucket.download_file(remote_path, local_path)

    def delete_file(self, remote_path):
        if self.bucket:
            self.s3.Object(self.bucket_name, remote_path).delete()

    def list_files(self, prefix=None):
        if self.bucket:
            return [obj.key for obj in self.bucket.objects.filter(Prefix=prefix)]


class SCPStorage:
    def __init__(self, config_data):
        self.scp_config = config_data.get('scp', {})
        self.host = self.scp_config.get("host")
        self.port = self.scp_config.get("port", 22)
        self.username = self.scp_config.get("user", "")
        self.password = self.scp_config.get("password", "")
        self.private_key_path = self.scp_config.get('private_key_path', "")

    def upload_file(self, local_audio_path, remote_path, remote_file_name, make_public=True):
        """Uploads a file to the SCP storage.

        :param local_audio_path: The local path to the audio file to upload.
        :param remote_path: The remote directory to upload the file to.
        :param remote_file_name: The name of the remote file.
        :param make_public: Flag indicating whether to make the file public (default is True).
        :return: Dictionary containing the file URL or False if upload fails.
        """
        try:
            full_remote_path = os.path.join(remote_path, remote_file_name)
            ssh_client, sftp = self._create_sftp_session()

            if not os.path.exists(local_audio_path):
                raise FileNotFoundError(f'Local File {local_audio_path} doesn\'t exist')

            with self._create_sftp_session() as (ssh_client, sftp):
                try:
                    sftp.stat(remote_path)
                except FileNotFoundError:
                    raise FileNotFoundError(f'Remote Path {remote_path} doesn\'t exist')

                sftp.put(local_audio_path, full_remote_path)
                sftp.close()
                ssh_client.close()

            file_url = urljoin(self.scp_config["audio_url_path"], remote_file_name)

            if self.scp_config["keep_audio_days"] > 0:
                self.clean_remote_files()

            return {"file_path": file_url}
        except SFTPError as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during uploading a file: {error}')
            return False
        except Exception as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during uploading a file: {error}')
            return False

    def download_file(self, remote_path, local_path):
        """Downloads a file from the SCP storage.

        :param remote_path: The remote file path to download from.
        :param local_path: The local path to download the file to.
        :return: Dictionary containing the local file path or False if download fails.
        """
        try:
            with self._create_sftp_session() as (ssh_client, sftp):
                sftp.get(remote_path, local_path)
                sftp.close()
                ssh_client.close()

            file_name = os.path.basename(remote_path)
            return {"file_path": os.path.join(local_path, file_name)}
        except SFTPError as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during downloading a file: {error}')
            return False
        except Exception as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during downloading a file: {error}')
            return False

    def delete_file(self, remote_path):
        """Deletes a file from the SCP storage.

        :param remote_path: The remote file path to delete.
        :return: True if deletion succeeds, False otherwise.
        """
        try:
            with self._create_sftp_session() as (ssh_client, sftp):
                sftp.remove(remote_path)
                sftp.close()
                ssh_client.close()

            return True
        except SFTPError as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during deleting a file: {error}')
            return False
        except Exception as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during deleting a file: {error}')
            return False

    def list_files(self, remote_path):
        """Lists files in a directory on the SCP storage.

        :param remote_path: The remote directory path to list files from.
        :return: List of files in the directory or None if the directory is empty, False if an error occurs.
        """
        try:
            with self._create_sftp_session() as (ssh_client, sftp):
                files = sftp.listdir(remote_path)
                sftp.close()
                ssh_client.close()

            if not files:
                return None

            return files
        except SFTPError as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during listing files: {error}')
            return False
        except Exception as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during listing files: {error}')
            return False

    def clean_remote_files(self):
        """Cleans remote files older than the specified number of days from SCP storage."""
        try:
            with self._create_sftp_session() as (ssh_client, sftp):

                command = fr"find {self.scp_config['remote_path']}* -mtime +{self.scp_config['keep_audio_days']} -exec rm {{}} \;"
                stdin, stdout, stderr = ssh_client.exec_command(command)
                for line in stdout:
                    module_logger.debug(str(line))
                module_logger.debug("Cleaned Remote Files")
                ssh_client.close()
        except SSHException as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during cleaning remote files: {error}')
        except Exception as error:
            traceback.print_exc()
            module_logger.critical(f'Error occurred during cleaning remote files: {error}')

    @contextmanager
    def _create_sftp_session(self, timeout=15):
        """Creates and manages an SFTP session using context management."""
        ssh_client = SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        sftp = None

        try:
            ssh_connect_kwargs = {
                "username": self.username,
                "port": self.port,
                "look_for_keys": False,
                "allow_agent": False,
                "timeout": timeout
            }

            if self.private_key_path and os.path.exists(self.private_key_path):
                try:
                    private_key = RSAKey.from_private_key_file(self.private_key_path)
                    ssh_connect_kwargs["pkey"] = private_key
                except SSHException as e:
                    module_logger.error(f"Failed to load private key: {e}")
                    if self.password:
                        ssh_connect_kwargs["password"] = self.password

            elif self.password:
                ssh_connect_kwargs["password"] = self.password
            else:
                raise ValueError("No valid authentication method provided.")

            start_ssh_time = time.time()
            ssh_client.connect(self.host, **ssh_connect_kwargs)
            ssh_connect_duration = time.time() - start_ssh_time
            module_logger.debug(f"SSH connection to {self.host} established in {ssh_connect_duration:.2f} seconds.")

            sftp = ssh_client.open_sftp()
            yield ssh_client, sftp

        except SSHException as e:
            module_logger.error(f'SSH connection error: {e}')
            raise
        finally:
            if sftp:
                sftp.close()
                module_logger.debug("SFTP session closed.")
            ssh_client.close()
            module_logger.debug("SSH connection closed.")
