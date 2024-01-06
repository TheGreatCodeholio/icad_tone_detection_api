import logging
import subprocess

module_logger = logging.getLogger("icad_tone_detection.shell_handler")


def run_command(command, timeout=None, env=None):
    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env) as proc:
            while True:
                output = proc.stdout.readline()
                if output == '' and proc.poll() is not None:
                    break
                if output:
                    print(output, end='')

            # Print any errors
            errors = proc.stderr.readlines()
            for error in errors:
                print(error.strip())

            if proc.returncode != 0:
                print(f"Command '{' '.join(command)}' exited with error code {proc.returncode}")
                return False  # Return False on non-zero return code

            return True  # Return True on success

    except subprocess.TimeoutExpired:
        print(f"Command '{' '.join(command)}' timed out after {timeout} seconds.")
        return False
    except Exception as e:
        print(f"An error occurred while running '{' '.join(command)}': {str(e)}")
        return False
