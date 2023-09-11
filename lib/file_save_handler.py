import logging
import os
from urllib.parse import urljoin
from google.cloud import storage
import boto3
from paramiko import SSHClient, AutoAddPolicy, RSAKey, SSHException
from paramiko.sftp import SFTPError
import traceback

module_logger = logging.getLogger('tr_uploader.sftp')


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
        self.scp_config = config_data['scp']
        self.host = self.scp_config['host']
        self.port = self.scp_config['port']
        self.username = self.scp_config['user']
        self.password = self.scp_config['password']

    def upload_file(self, local_audio_path, remote_path, remote_file_name, make_public=True):

        # Create an SSH client
        try:
            full_remote_path = os.path.join(remote_path, remote_file_name)

            ssh_client = SSHClient()
            ssh_client.load_system_host_keys()
            self._connect_ssh_client(ssh_client)

            sftp = ssh_client.open_sftp()
            # Upload the file
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
        try:
            ssh_client = SSHClient()
            ssh_client.load_system_host_keys()
            self._connect_ssh_client(ssh_client)

            sftp = ssh_client.open_sftp()
            sftp.get(remote_path, local_path)

            sftp.close()
            ssh_client.close()
            file_name = os.path.basename(remote_path)
            return {"file_path": os.path.join(local_path, file_name)}
        except SFTPError as error:
            module_logger.critical(f'Error occurred during downloading a file: {error}')
            return False
        except Exception as error:
            module_logger.critical(f'Error occurred during downloading a file: {error}')
            return False

    def delete_file(self, remote_path):
        try:
            ssh_client = SSHClient()
            ssh_client.load_system_host_keys()
            self._connect_ssh_client(ssh_client)

            sftp = ssh_client.open_sftp()
            sftp.remove(remote_path)

            sftp.close()
            ssh_client.close()
            return True
        except SFTPError as error:
            module_logger.critical(f'Error occurred during deleting a file: {error}')
            return False
        except Exception as error:
            module_logger.critical(f'Error occurred during deleting a file: {error}')
            return False

    def list_files(self, remote_path):
        try:
            ssh_client = SSHClient()
            ssh_client.load_system_host_keys()
            self._connect_ssh_client(ssh_client)

            sftp = ssh_client.open_sftp()
            files = sftp.listdir(remote_path)

            sftp.close()
            ssh_client.close()

            if not files:
                return None

            return files
        except SFTPError as error:
            module_logger.critical(f'Error occurred during listing files: {error}')
            return False
        except Exception as error:
            module_logger.critical(f'Error occurred during listing files: {error}')
            return False

    def clean_remote_files(self):
        # Create an SSH client
        try:
            ssh_client = SSHClient()
            ssh_client.load_system_host_keys()
            self._connect_ssh_client(ssh_client)

            command = "find " + self.scp_config["remote_path"] + "* -mtime +" + str(self.scp_config["keep_audio_days"]) + " -exec rm {} \;"
            stdin, stdout, stderr = ssh_client.exec_command(command)
            for line in stdout:
                module_logger.debug(str(line))
            module_logger.debug("Cleaned Remote Files")
            ssh_client.close()
        except SSHException as error:
            module_logger.critical(f'Error occurred during cleaning remote files: {error}')
        except Exception as error:
            module_logger.critical(f'Error occurred during cleaning remote files: {error}')

    def _connect_ssh_client(self, ssh_client):
        if self.scp_config["private_key"] != "":
            private_key = RSAKey.from_private_key_file(self.scp_config["private_key"])
            ssh_client.connect(self.host, port=self.port, username=self.username, look_for_keys=False,
                               allow_agent=False, pkey=private_key)
        else:
            ssh_client.connect(self.host, port=self.port, username=self.username, password=self.password,
                               look_for_keys=False, allow_agent=False)
