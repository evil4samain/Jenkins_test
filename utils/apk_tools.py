import os
import subprocess
import json
import logging

logger = logging.getLogger(__name__)
GPKEEP_PATH = "/opt/app_security_score/gpkeep"
APKEEP_PATH = "/opt/app_security_score/apkeep"

def remove_existing_apk(package: str, download_dir: str):
    apk_file = os.path.join(download_dir, f"{package}.apk")
    if os.path.isfile(apk_file):
        try:
            os.remove(apk_file)
            logger.info(f"Removed old APK: {apk_file}")
        except Exception as e:
            logger.error(f"Failed to remove {apk_file}: {e}")
            raise

def run_gkeep(package: str, email: str, token: str, device: str) -> dict:
    if not os.path.isfile(GPKEEP_PATH):
        msg = f"gpkeep binary not found at {GPKEEP_PATH}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    cmd = [GPKEEP_PATH, f"--package={package}", f"--email={email}", \
           f"--aas-token={token}", f"--device={device}"]
    logger.info(f"Invoking gpkeep: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    out, err = result.stdout.strip(), result.stderr.strip()

    if result.returncode != 0:
        logger.error(f"gpkeep failed (exit {result.returncode}). stdout: '{out}', stderr: '{err}'")
        raise RuntimeError(f"gpkeep error: {err or out}")
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from gpkeep: {e}. Output: '{out}'")
        raise ValueError(f"Could not parse gpkeep output: {e}")

    logger.info(f"gpkeep succeeded for {package}: version {data.get('version')} updated {data.get('last_updated_on')}")
    return data


def download_apk(package: str, email: str, token: str, download_dir: str):
    if not os.path.isfile(APKEEP_PATH):
        msg = f"apkeep binary not found at {APKEEP_PATH}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    cmd = [APKEEP_PATH, "-a", package, "-d", "google-play",
           "-e", email, "-t", token, download_dir]
    logger.info(f"Invoking apkeep: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    out, err = result.stdout.strip(), result.stderr.strip()
    if result.returncode != 0:
        logger.error(f"apkeep failed (exit {result.returncode}). stdout: '{out}', stderr: '{err}'")
        raise RuntimeError(f"apkeep error: {err or out}")
    logger.info(f"APK downloaded for {package} into {download_dir}")