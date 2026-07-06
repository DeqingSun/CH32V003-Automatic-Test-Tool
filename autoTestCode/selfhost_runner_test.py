# Mimic the GitHub self-hosted runner environment:
# python3 selfhost_runner_test.py sampleArtifacts/examples
# python3 selfhost_runner_test.py sampleArtifacts/examples/blink

import os
import sys
import time
import subprocess

from lib.ch32v003_test_target import Ch32V003_test_target

AUTO_TEST_CODE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEST_SCRIPT_DIR = os.path.join(AUTO_TEST_CODE_DIR, "testScripts")

if len(sys.argv) < 2:
    print("Usage: python3 selfhost_runner_test.py <path to compiled firmwares> [path to test scripts]")
    sys.exit(1)

firmware_path = os.path.abspath(sys.argv[1])
test_script_directory = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TEST_SCRIPT_DIR

print("Firmware path: " + firmware_path)
print("Test script path: " + test_script_directory)

if not os.path.isdir(firmware_path):
    print(f"Firmware path not found: {firmware_path}")
    sys.exit(1)

if not os.path.isdir(test_script_directory):
    print(f"Test script directory not found: {test_script_directory}")
    sys.exit(1)

compiled_firmwares = []
for root, dirs, files in os.walk(firmware_path):
    for file in files:
        if file.endswith(".bin"):
            compiled_firmwares.append(os.path.join(root, file))

if len(compiled_firmwares) == 0:
    print("No compiled firmwares found.")
    sys.exit(1)

compiled_firmwares.sort()

target = Ch32V003_test_target()
if not target.initialize():
    print("Test target initialization failed")
    sys.exit(1)

success_count = 0
failure_count = 0
skipped_count = 0
MAX_TEST_ATTEMPTS = 3
TEST_RETRY_DELAY_S = 0.5


def run_test_script(test_script_path):
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = AUTO_TEST_CODE_DIR
    return subprocess.run(
        [sys.executable, test_script_path],
        cwd=AUTO_TEST_CODE_DIR,
        env=test_env,
        capture_output=True,
        text=True,
    )


for firmware in compiled_firmwares:
    sketch_name = os.path.splitext(os.path.basename(firmware))[0]
    test_script_path = os.path.join(test_script_directory, sketch_name + ".py")
    if not os.path.isfile(test_script_path):
        # print(f"Test script not found at {test_script_path} for {sketch_name}, skipping")
        skipped_count += 1
        continue

    print(f"Now testing {sketch_name}")
    start_time = time.monotonic()

    if not target.flashFirmware(firmware):
        print(f"Firmware flashing failed for {sketch_name}")
        sys.exit(1)

    print(f"Flash of {sketch_name} completed after {time.monotonic() - start_time:.2f} seconds")

    test_passed = False
    for attempt in range(1, MAX_TEST_ATTEMPTS + 1):
        if (attempt > 1):
            print(f"Retrying {sketch_name} (attempt {attempt}/{MAX_TEST_ATTEMPTS})")
            time.sleep(TEST_RETRY_DELAY_S)

        test_process = run_test_script(test_script_path)
        if (test_process.stdout):
            print(test_process.stdout, end="")
        if (test_process.stderr):
            print(test_process.stderr, end="", file=sys.stderr)

        if (test_process.returncode == 0):
            test_passed = True
            break

        if (attempt < MAX_TEST_ATTEMPTS):
            print(f"Test {sketch_name} failed on attempt {attempt}, retrying...")

    if (test_passed):
        print(f"Test of {sketch_name} completed after {time.monotonic() - start_time:.2f} seconds")
        success_count += 1
    else:
        print(f"Error testing {sketch_name} after {MAX_TEST_ATTEMPTS} attempts")
        failure_count += 1

print(f"Test completed. Success: {success_count}, Failure: {failure_count}, Skipped: {skipped_count}")
if failure_count > 0:
    sys.exit(1)
