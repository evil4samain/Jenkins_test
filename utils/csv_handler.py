import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_and_prepare_csv(csv_path: str, copy_path: str) -> pd.DataFrame:
    if not os.path.isfile(csv_path):
        logger.error(f"CSV file not found at {csv_path}")
        raise FileNotFoundError(f"CSV file not found at {csv_path}")
    df = pd.read_csv(csv_path)
    # Add missing columns
    for col in ["security_score", "updated"]:
        if col not in df.columns:
            df[col] = ""
    df.to_csv(copy_path, index=False)
    logger.info(f"Copied and prepared CSV at {copy_path}")
    return df