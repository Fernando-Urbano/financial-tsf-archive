"""
This module contains functions to load the zero coupon yield curve from the Federal Reserve.
It saves the pulled raw data to a parquet file for future use.
Functions to load the raw/clean data from the parquet file are also provided for future use.

"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from io import BytesIO

import pandas as pd
import requests

from settings import config

DATA_DIR = config("DATA_DIR")


def pull_fed_yield_curve():
    """
    Download the latest yield curve from the Federal Reserve

    This is the published data using Gurkaynak, Sack, and Wright (2007) model
    """

    url = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
    response = requests.get(url)
    pdf_stream = BytesIO(response.content)
    df = pd.read_csv(pdf_stream, skiprows=9, index_col=0, parse_dates=True)
    cols = ["SVENY" + str(i).zfill(2) for i in range(1, 31)]
    return df[cols]


def load_fed_yield_curve(data_dir=DATA_DIR):
    path = data_dir / "fed_yield_curve.parquet"
    _df = pd.read_parquet(path)
    return _df


if __name__ == "__main__":
    df = pull_fed_yield_curve()
    data_dir = DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "fed_yield_curve.parquet"
    df.to_parquet(path)
