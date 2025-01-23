import sys
from pathlib import Path

import toml

sys.path.insert(1, "./src/")

from settings import config

BASE_DIR = Path(config("BASE_DIR"))
DATA_DIR = Path(config("DATA_DIR"))
OUTPUT_DIR = Path(config("OUTPUT_DIR"))

# Load benchmarks configuration
with open("benchmarks.toml", "r") as f:
    BENCHMARKS = toml.load(f)


def task_config():
    """Create empty directories for data and output if they don't exist"""
    file_dep = [
        "./src/settings.py",
    ]
    targets = [DATA_DIR, OUTPUT_DIR]

    return {
        "actions": [
            "ipython ./src/settings.py",
        ],
        "targets": targets,
        "file_dep": file_dep,
        "clean": [],
    }


def task_pull_data():
    """Pull selected datasets based on benchmarks.toml configuration"""
    datasets = BENCHMARKS["datasets"]

    ## Aggregate datasets
    if datasets["fed_yield_curve"]:
        yield {
            "name": "fed_yield_curve",
            "actions": ["ipython ./src/pull_fed_yield_curve.py"],
            "targets": [DATA_DIR / "fed_yield_curve.parquet"],
            "file_dep": ["./src/pull_fed_yield_curve.py"],
            "clean": [],
        }

    if datasets["ff_25_portfolios"]:
        from pull_fama_french_25_portfolios import DATA_INFO

        yield {
            "name": "ff_25_portfolios",
            "actions": ["ipython ./src/pull_fama_french_25_portfolios.py"],
            "targets": [
                DATA_DIR / "ff_25_portfolios" / info["parquet"]
                for info in DATA_INFO.values()
            ],
            "file_dep": ["./src/pull_fama_french_25_portfolios.py"],
            "clean": [],
        }

    ## Disaggregated datasets
    if datasets["crsp_returns"]:
        from pull_CRSP_stock import SUBFOLDER as subfolder

        yield {
            "name": "crsp_returns",
            "actions": ["ipython ./src/pull_CRSP_stock.py"],
            "targets": [
                DATA_DIR / subfolder / "CRSP_MSF_INDEX_INPUTS.parquet",
                DATA_DIR / subfolder / "CRSP_MSIX.parquet",
            ],
            "file_dep": ["./src/pull_CRSP_stock.py"],
            "clean": [],
        }
    if datasets["crsp_compustat"]:
        from pull_CRSP_Compustat import SUBFOLDER as subfolder

        yield {
            "name": "crsp_compustat",
            "actions": ["ipython ./src/pull_CRSP_Compustat.py"],
            "targets": [
                DATA_DIR / subfolder / "Compustat.parquet",
                DATA_DIR / subfolder / "CRSP_stock_ciz.parquet",
                DATA_DIR / subfolder / "CRSP_Comp_Link_Table.parquet",
                DATA_DIR / subfolder / "FF_FACTORS.parquet",
            ],
            "file_dep": ["./src/pull_CRSP_Compustat.py"],
            "clean": [],
        }
    # fmt: off
    if datasets["us_corp_bonds"]:
        from pull_corp_bonds_duration_matched import DATA_INFO
        from pull_corp_bonds_duration_matched import SUBFOLDER as subfolder
        yield {
            "name": "us_corp_bonds",
            "actions": ["ipython ./src/pull_corp_bonds_duration_matched.py"],
            "targets": [
                DATA_DIR / subfolder / info["parquet"]
                for info in DATA_INFO.values()
            ]
            + [
                DATA_DIR / subfolder / f"{info['parquet'].replace('.parquet', '_README.pdf')}"
                for info in DATA_INFO.values()
            ],
            "file_dep": ["./src/pull_corp_bonds_duration_matched.py"],
            "clean": [],
        }
    # fmt: on
