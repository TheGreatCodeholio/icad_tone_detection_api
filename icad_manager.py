import argparse
import os
import re
import secrets
import string
import subprocess
from urllib.parse import urlparse


def is_valid_url(url):
    # Regular expression to validate the URL
    regex = re.compile(
        r'^(https?://)'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ipv4
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return re.match(regex, url) is not None


def generate_password(length=16):
    # Define the characters to use, excluding problematic ones
    safe_chars = string.ascii_letters + string.digits + ''.join(
        c for c in string.punctuation if c not in {'"', "'", "\\", "`"})

    # Use secrets.SystemRandom for cryptographic strength
    secure_random = secrets.SystemRandom()
    return ''.join(secure_random.choice(safe_chars) for i in range(length))


def generate_secure_token(length=64):
    return secrets.token_hex(length)


def generate_env_file(working_path, url):
    parsed_url = urlparse(url)
    domain = parsed_url.hostname

    # Special handling for localhost and IP addresses
    if domain == 'localhost' or re.match(r'^\d{1,3}(\.\d{1,3}){3}$', domain):
        cookie_secure = 'False'  # Disable secure cookies for localhost/IP
    else:
        cookie_secure = 'True'

    env_content = f"""# Redis Configuration
REDIS_PASSWORD={generate_password()}

# MySQL Configuration
MYSQL_ROOT_PASSWORD='{generate_password()}'
MYSQL_USER=icad
MYSQL_HOST=mysql
MYSQL_PASSWORD='{generate_password()}'
MYSQL_DATABASE=icad
MYSQL_PORT=3306

# RabbitMQ Configuration
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=icad
RABBITMQ_PASS='{generate_password()}'

# Flask Log Level
LOG_LEVEL=DEBUG
WORKING_PATH={working_path}

# Flask Secret Key
SECRET_KEY='{os.urandom(24).hex()}'

#Flask Cookie Configuration
BASE_URL={url}
COOKIE_DOMAIN={domain}
COOKIE_SECURE={cookie_secure}
COOKIE_NAME=icad_tone_detect
COOKIE_PATH=/

#Google Recaptcha Configuration
GOOGLE_RECAPTCHA_ENABLED=False
GOOGLE_RECAPTCHA_SECRET_KEY=
GOOGLE_RECAPTCHA_SITE_KEY=

#SMTP Configuration
SMTP_HOST=
SMTP_PORT=
SMTP_USERNAME=
SMTP_PASSWORD=
EMAIL_SENDER=
EMAIL_SENDER_NAME=
"""
    env_file_path = os.path.join(working_path, '.env')
    with open(env_file_path, 'w') as file:
        file.write(env_content)

    # Set file permissions to chmod 600
    os.chmod(env_file_path, 0o600)
    print(f"Generated .env file in {working_path} with random passwords and set permissions to 600.")


def run_docker_compose():
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    print("Docker Compose has started the services.")


def update_services():
    subprocess.run(["docker-compose", "pull"], check=True)
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    print("Services have been updated.")


def reset_services(working_path, url):
    # Stop and remove all containers, networks, and volumes associated with the project
    subprocess.run(["docker-compose", "down", "-v"], check=True)
    print("Stopped and removed all project containers, networks, and volumes.")

    # Remove .env file if it exists
    env_file_path = os.path.join(working_path, '.env')
    if os.path.exists(env_file_path):
        os.remove(env_file_path)
        print(f"Removed Environment Variables from {env_file_path}: .env")

    generate_env_file(working_path, url)
    subprocess.run(["docker-compose", "pull"], check=True)
    run_docker_compose()
    print("Services have been reset and started with new configurations.")


def main():
    parser = argparse.ArgumentParser(description='Manage iCAD Docker services.')
    parser.add_argument('-a', '--action', choices=['init', 'update', 'reset'], help='Action to perform')
    parser.add_argument('-u', '--url', type=str, help='Base URL')

    working_path = os.getcwd()

    args = parser.parse_args()

    if working_path is None or args.url is None:
        print("Missing required arguments. Must provide --id and --url.")
        return

    if args.action == 'init':
        generate_env_file(working_path, args.url)
        run_docker_compose()
    elif args.action == 'update':
        update_services()
    elif args.action == 'reset':
        reset_services(working_path, args.url)
    else:
        print("No valid action specified. Use --action with 'init', 'update', or 'reset'.")


if __name__ == "__main__":
    main()
