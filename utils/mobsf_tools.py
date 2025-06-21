import subprocess
import json
import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)
# MobSF API endpoints and auth
UPLOAD_URL = "http://192.168.30.6:803/api/v1/upload/"
SCAN_URL = "http://192.168.30.6:803/api/v1/scan/"
SCORECARD_URL = "http://192.168.30.6:803/api/v1/scorecard/"
REPORT_URL = "http://192.168.30.6:803/api/v1/report_json/"
API_KEY = "0a1b7a64f24a3faac9424af7cc3eabb354b56990dc5a124ad4596e55c3ae5ce8"
TIMEOUT = (10, 300)
POLL_INTERVAL = 5
MAX_POLL_ATTEMPTS = 40
SCORECARD_POLL_INTERVAL = 10
MAX_SCORECARD_POLL_ATTEMPTS = 10
RETRY_COUNT = 3

headers = {"X-Mobsf-Api-Key": API_KEY}


def upload_to_mobsf(apk_path: str) -> Optional[str]:
    """
    Uploads an APK file to MobSF using curl to avoid chunking issues.
    """
    for attempt in range(1, RETRY_COUNT + 1):
        logger.info(f"[Upload Attempt {attempt}] {apk_path}")
        cmd = [
            "curl", "-s",
            "-F", f"file=@{apk_path}",
            "-H", f"X-Mobsf-Api-Key: {API_KEY}",
            "-H", "Expect:",
            UPLOAD_URL
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"MobSF upload failed (attempt {attempt}): {result.stderr}")
        else:
            try:
                data = json.loads(result.stdout)
                apk_hash = data.get('hash')
                if apk_hash:
                    return apk_hash
                logger.error(f"No hash in upload response: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error during upload (attempt {attempt}): {e}")
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"Failed to upload {apk_path} after {RETRY_COUNT} attempts")


def initiate_scan(apk_hash: str) -> None:
    payload = {'hash': apk_hash}
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        logger.info(f"[Scan Attempt {attempt}] hash={apk_hash}")
        resp = requests.post(SCAN_URL, headers=headers, data=payload, timeout=TIMEOUT)
        if resp.ok:
            data = resp.json()
            if data.get('error') == '500':
                time.sleep(POLL_INTERVAL)
                continue
            return
        else:
            logger.error(f"Scan initiation failed: {resp.status_code} {resp.text}")
            time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"Failed to initiate scan after {MAX_POLL_ATTEMPTS} attempts")


def fetch_security_score(apk_hash: str) -> int:
    payload = {'hash': apk_hash}
    # Try scorecard endpoint
    for attempt in range(1, MAX_SCORECARD_POLL_ATTEMPTS + 1):
        logger.info(f"[Scorecard Attempt {attempt}] hash={apk_hash}")
        resp = requests.post(SCORECARD_URL, headers=headers, data=payload, timeout=TIMEOUT)
        if resp.status_code == 404:
            break
        if resp.ok:
            data = resp.json()
            if data.get('error') == '500':
                time.sleep(SCORECARD_POLL_INTERVAL)
                continue
            score = data.get('security_score')
            if score is not None:
                return score
        time.sleep(SCORECARD_POLL_INTERVAL)
    # Fallback to report JSON
    for attempt in range(1, RETRY_COUNT + 1):
        logger.info(f"[Report JSON Attempt {attempt}] hash={apk_hash}")
        resp = requests.post(REPORT_URL, headers=headers, data=payload, timeout=TIMEOUT)
        if resp.ok:
            data = resp.json()
            score = data.get('severity_score') or data.get('security_score')
            if score is not None:
                return int(score)
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"Failed to fetch security score for {apk_hash}")


def scan_apk(apk_path: str) -> int:
    apk_hash = upload_to_mobsf(apk_path)
    initiate_scan(apk_hash)
    return fetch_security_score(apk_hash)