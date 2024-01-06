import logging
import subprocess

module_logger = logging.getLogger("icad_tone_detection.shell_handler")


def run_command(command, timeout=None, env=None):
    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env) as proc:
            try:
                # Wait for the command to complete
                stdout, stderr = proc.communicate(timeout=timeout)

                # Log the output
                for line in stdout.splitlines():
                    module_logger.info(line.strip())

                # Log any errors
                for line in stderr.splitlines():
                    module_logger.error(line.strip())

            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                module_logger.error(f"Command '{' '.join(command)}' timed out after {timeout} seconds.")
                return False

            # Check the return code and log if there was an error
            if proc.returncode != 0:
                module_logger.warning(f"Command '{' '.join(command)}' exited with error code {proc.returncode}")
                return False  # Return False on non-zero return code

            return True  # Return True on success

    except Exception as e:
        module_logger.error(f"An error occurred while running '{' '.join(command)}': {str(e)}")
        return False
