#testing this
#again testing
#testing trufflehog
import os
import sys
import logging
from datetime import datetime
from config.logging_config import configure_logging
from utils.csv_handler import load_and_prepare_csv
from utils.apk_tools import run_gkeep, download_apk, remove_existing_apk
from utils.mobsf_tools import scan_apk


def main():
    configure_logging()
    logger = logging.getLogger(__name__)

    root = os.path.dirname(os.path.abspath(__file__))
    csv_src = os.path.join(root, "app.csv")
    csv_copy = os.path.join(root, "app_copy.csv")
    download_dir = os.path.join(root, "Downloaded_apk")

    try:
        df = load_and_prepare_csv(csv_src, csv_copy)
    except FileNotFoundError:
        print("CSV not found")
        sys.exit(1)

    os.makedirs(download_dir, exist_ok=True)

    email = "subselatestwale@gmail.com"
    token = "aas_et/AKppINZVNAp2aaChsOBqGgjRbTrhbDE9yrEOWM7LafGe-bd7m_qQRtY1zkaPNRZzhEvmpnrOLPm4oFvYHkstRy161GDtNYtNBYwNkUA9sOUqszg5aS5vhXpDTZImWhFpbwvm0HMd6v5mVV2RbI-9e_enY06RJiqOrkpXijHsZSfG64sKxheQX8hQgsmQarfVdpQ2zXI-Zl_f-NM0Xs4Jq4U"
    device = "px_7a"

    for idx, row in df.iterrows():
        pkg = row["package_name"]
        curr_ver = row.get("version", "")
        try:
            info = run_gkeep(pkg, email, token, device)
        except Exception as e:
            print(f"Error during gpkeep for {pkg}: {e}")
            continue

        new_ver = info.get("version", "")
        last_upd = info.get("last_updated_on", "")

        if curr_ver and new_ver != curr_ver:
            try:
                remove_existing_apk(pkg, download_dir)
            except Exception as e:
                print(f"Failed to delete old APK for {pkg}: {e}")
                continue

        if not curr_ver or new_ver != curr_ver:
            df.at[idx, "version"] = new_ver
            df.at[idx, "date"] = last_upd
            df.to_csv(csv_copy, index=False)
            try:
                download_apk(pkg, email, token, download_dir)
            except Exception as e:
                print(f"APK download failed for {pkg}: {e}")
                continue
            apk_path = os.path.join(download_dir, f"{pkg}.apk")
            try:
                score = scan_apk(apk_path)
            except Exception as e:
                print(f"MobSF scan failed for {pkg}.apk: {e}")
                continue
            df.at[idx, "security_score"] = score
            df.at[idx, "updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df.to_csv(csv_copy, index=False)
        else:
            print(f"{pkg} version is same")

    print("Processing complete")

if __name__ == "__main__":
    main()
