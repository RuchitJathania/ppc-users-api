import subprocess
import sys

COMPOSE_FILE = "compose.test.yaml"

up_command = [
    "docker", "compose",
    "-f", COMPOSE_FILE,
    "up",
    "--build",
    "--force-recreate",
    "--abort-on-container-exit",
    "--exit-code-from", "tests",
]

down_command = [
    "docker", "compose",
    "-f", COMPOSE_FILE,
    "down",
    "-v",
]

try:
    result = subprocess.run(up_command, check=False)
    exit_code = result.returncode

except KeyboardInterrupt:
    exit_code = 130

finally:
    subprocess.run(down_command, check=False)

sys.exit(exit_code)
