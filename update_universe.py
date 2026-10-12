
import io
import logging
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "universe.csv"

NSE_CSV_URL = (
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    response = requests.get(
        NSE_CSV_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
            ),
            "Accept": "text/csv,*/*",
            "Referer": "https://www.nseindia.com/",
        },
        timeout=30,
    )
    response.raise_for_status()

    df = pd.read_csv(io.BytesIO(response.content))
    df.columns = [str(c).strip() for c in df.columns]

    required = {"Symbol", "Company Name"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"Unexpected NSE CSV columns: {list(df.columns)}"
        )

    df["Symbol"] = df["Symbol"].astype(str).str.strip()
    df["Company Name"] = df["Company Name"].astype(str).str.strip()

    # Keep equity series when the source provides a Series column.
    if "Series" in df.columns:
        df = df[df["Series"].astype(str).str.strip().eq("EQ")]

    df = df[
        df["Symbol"].ne("")
        & df["Company Name"].ne("")
        & df["Symbol"].ne("nan")
    ].copy()

    universe = pd.DataFrame({
        "symbol": df["Symbol"] + ".NS",
        "name": df["Company Name"],
    })

    universe = (
        universe.drop_duplicates(subset="symbol")
        .sort_values("symbol")
        .reset_index(drop=True)
    )

    # Guard against replacing the universe with an incomplete download.
    if len(universe) < 450:
        raise ValueError(
            f"Only {len(universe)} constituents received; "
            "refusing to overwrite universe.csv."
        )

    universe.to_csv(OUTPUT, index=False, encoding="utf-8")
    logging.info("Updated %s with %d constituents.", OUTPUT, len(universe))


if __name__ == "__main__":
    main()
