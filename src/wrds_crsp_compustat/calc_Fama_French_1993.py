"""
This code replicates the Fama-French 1993 factors.
Note that this code uses the CRSP SIZ format. See
`pull_CRSP_Compustat.py` for more information.

For more information about the methodology behind
the construction of these factors, including a series
of helpful videos published by WRDS, see here:

https://wrds-www.wharton.upenn.edu/pages/wrds-research/applications/risk-factors-and-industry-benchmarks/fama-french-factors/#smb-1970-1979

Code to calculate the Fama-French 1993 factors
from: https://www.fredasongdrechsler.com/data-crunching/fama-french
Citation: Drechsler, Qingyi (Freda) S., 2023, Python Programs for Empirical
Finance, https://www.fredasongdrechsler.com

This file was lightly modified from the original by Tobias Rodriguez
del Pozo for use in the course "Full Stack Quantitative Finance" by
Jeremy Bejarano.

"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
print(sys.path)
import datetime

import numpy as np
import pandas as pd
import pull_CRSP_Compustat
from matplotlib import pyplot as plt
from pandas.tseries.offsets import MonthEnd, YearEnd
from scipy import stats

from settings import config

DATA_DIR = config("DATA_DIR")
OUTPUT_DIR = config("OUTPUT_DIR")


def calc_book_equity_and_years_in_compustat(comp):
    """Calculate book equity and number of years in Compustat.

    Use pull_CRSP_Compustat.description_crsp for help
    """
    ##
    ## Create a new column 'ps' for preferred stock value in 'comp'.

    # First check if 'pstkrv' (Preferred Stock - Redemption Value) is null.
    # If 'pstkrv' is null, use 'pstkl' (Preferred Stock - Liquidating Value) instead.
    comp["ps"] = np.where(comp["pstkrv"].isnull(), comp["pstkl"], comp["pstkrv"])

    # Update the 'ps' column. If 'ps' is still null after the previous operation
    # (meaning both 'pstkrv' and 'pstkl' were null), try to use
    # 'pstk' (Preferred/Preference Stock (Capital) - Total) as the preferred
    # stock value. This step ensures that any available preferred stock value is used.
    comp["ps"] = np.where(comp["ps"].isnull(), comp["pstk"], comp["ps"])

    # Another update to the 'ps' column. If 'ps' is still null
    # set the preferred stock value to 0.
    comp["ps"] = np.where(comp["ps"].isnull(), 0, comp["ps"])

    # Replace null values in the 'txditc' column (Deferred Taxes and Investment Tax Credit)
    # with 0.
    comp["txditc"] = comp["txditc"].fillna(0)

    ##
    ## Calculate book equity ('be')
    # Book equity is calculated as the sum of 'seq' (Stockholders' Equity - Parent)
    # and 'txditc' (Deferred Taxes and Investment Tax Credit),
    # minus 'ps' (the calculated preferred stock value from previous steps).
    # This formula reflects the accounting equation where book equity is essentially
    # the net worth of the company from a bookkeeping perspective, adjusted for
    # preferred stock and tax considerations.
    comp["be"] = comp["seq"] + comp["txditc"] - comp["ps"]

    # Update the 'be' (book equity) column to ensure that only positive values
    # are retained. If 'be' is less than or equal to 0, it is replaced with NaN
    comp["be"] = np.where(comp["be"] > 0, comp["be"], np.nan)

    # number of years in Compustat
    comp = comp.sort_values(by=["gvkey", "datadate"])
    comp["count"] = comp.groupby(["gvkey"]).cumcount()

    comp = comp[["gvkey", "datadate", "year", "be", "count"]]

    return comp


def subset_CRSP_to_common_stock_and_exchanges(crsp):
    """Subset to common stock universe and
    stocks traded on NYSE, AMEX and NASDAQ.

    NOTE:
        With the new CIZ format, it is not necessary to apply delisting
        returns, as they are already applied.
    """
    # In the old SIZ format, this would condition on shrcd = 10 or 11

    ## Select common stock universe
    ##
    # sharetype=='NS': Filters for securities where the 'Share Type' is
    # "Not specified". This is confusing. See here:
    # https://wrds-www.wharton.upenn.edu/pages/support/manuals-and-overviews/crsp/stocks-and-indices/crsp-stock-and-indexes-version-2/crsp-ciz-faq/#replicating-common-tasks

    # securitytype=='EQTY': Selects only securities classified as 'EQTY'

    # securitysubtype=='COM': Narrows down to securities with a 'Security Subtype'
    # of 'COM', suggesting these are common stocks.

    # usincflg=='Y': Includes only securities issued by companies incorporated in
    # the U.S., as indicated by the 'U.S. Incorporation Flag'.

    # issuertype.isin(['ACOR', 'CORP']): Further filters securities to those issued
    # by entities classified as either 'ACOR' (Asset-Backed Corporate)
    # or 'CORP' (Corporate), based on the 'Issuer Type' classification.

    crsp = crsp.loc[
        (crsp.sharetype == "NS")
        & (crsp.securitytype == "EQTY")
        & (crsp.securitysubtype == "COM")
        & (crsp.usincflg == "Y")
        & (crsp.issuertype.isin(["ACOR", "CORP"]))
    ]

    ## Select stocks traded on NYSE, AMEX and NASDAQ
    ##
    ## Again, see https://wrds-www.wharton.upenn.edu/pages/support/manuals-and-overviews/crsp/stocks-and-indices/crsp-stock-and-indexes-version-2/crsp-ciz-faq/#replicating-common-tasks
    # Also, filters securities with a "Regular Way" trading status and active trading status
    crsp = crsp.loc[
        (crsp.primaryexch.isin(["N", "A", "Q"]))
        & (crsp.conditionaltype == "RW")
        & (crsp.tradingstatusflg == "A")
    ]

    return crsp


def calculate_market_equity(crsp):
    """
    Calculate market equity for each firm in the CRSP dataset.

    There were cases when the same firm (permco) had two or more securities
    (permno) on the same date. For the purpose of ME for the firm, we
    aggregated all ME for a given permco, date. This aggregated ME was assigned
    to the CRSP permno that has the largest ME. We remove all other permnos
    except the one with the largest ME.

    """
    ########### YOUR CODE BELOW ############

    df = crsp.copy()
    ## Calculate Market Equity for each permno. Call the column "permno_me"
    df["permno_me"] = df["mthprc"] * df["shrout"]
    df = df.drop(["mthprc", "shrout"], axis=1)
    df = df.sort_values(by=["jdate", "permco", "permno_me"])

    ### Aggregate Market Cap ###
    # sum of me across different permno belonging to same permco a given jdate
    # Call the column "me" (market equity)
    permco_me = df.groupby(["jdate", "permco"])["permno_me"].sum().reset_index()
    permco_me = permco_me.rename(columns={"permno_me": "me"})

    ## Find the permno with the largest permno-level market cap
    # largest mktcap within a permco/jdate
    permno_max_me = df.groupby(["jdate", "permco"])["permno_me"].max().reset_index()
    # inner join by jdate/maxme to find the permno with the largest market cap
    df = pd.merge(df, permno_max_me, how="inner", on=["jdate", "permco", "permno_me"])

    # inner join with to get "me" (permco-level market equity) into the data
    df = pd.merge(df, permco_me, how="inner", on=["jdate", "permco"])

    # drop the permno_me column. We'll only use the "me" column in the future
    df = df.drop(["permno_me"], axis=1)

    # sort by permno and jdate and also drop duplicates
    df = df.sort_values(by=["permno", "jdate"]).drop_duplicates()

    return df


def use_dec_market_equity(crsp2):
    """
    Finally, ME at June and December
    were flagged since (1) December ME will be used to create Book-to-Market
    ratio (BEME) and (2) June ME has to be positive in order to be part of
    the portfolio.'

    """
    # keep December market cap
    crsp2["year"] = crsp2["jdate"].dt.year
    crsp2["month"] = crsp2["jdate"].dt.month
    decme = crsp2[crsp2["month"] == 12]
    decme = decme[["permno", "mthcaldt", "jdate", "me", "year"]].rename(
        columns={"me": "dec_me"}
    )

    ### July to June dates
    crsp2["ffdate"] = crsp2["jdate"] + MonthEnd(-6)
    crsp2["ffyear"] = crsp2["ffdate"].dt.year
    crsp2["ffmonth"] = crsp2["ffdate"].dt.month
    crsp2["1+retx"] = 1 + crsp2["mthretx"]
    crsp2 = crsp2.sort_values(by=["permno", "mthcaldt"])

    # cumret by stock
    crsp2["cumretx"] = crsp2.groupby(["permno", "ffyear"])["1+retx"].cumprod()

    # lag cumret
    crsp2["L_cumretx"] = crsp2.groupby(["permno"])["cumretx"].shift(1)

    # lag market cap
    crsp2["L_me"] = crsp2.groupby(["permno"])["me"].shift(1)

    # if first permno then use me/(1+retx) to replace the missing value
    crsp2["count"] = crsp2.groupby(["permno"]).cumcount()
    crsp2["L_me"] = np.where(
        crsp2["count"] == 0, crsp2["me"] / crsp2["1+retx"], crsp2["L_me"]
    )

    # baseline me
    mebase = crsp2[crsp2["ffmonth"] == 1][["permno", "ffyear", "L_me"]].rename(
        columns={"L_me": "mebase"}
    )

    # merge result back together
    crsp3 = pd.merge(crsp2, mebase, how="left", on=["permno", "ffyear"])
    crsp3["wt"] = np.where(
        crsp3["ffmonth"] == 1, crsp3["L_me"], crsp3["mebase"] * crsp3["L_cumretx"]
    )

    decme["year"] = decme["year"] + 1
    decme = decme[["permno", "year", "dec_me"]]

    # Info as of June
    crsp3_jun = crsp3[crsp3["month"] == 6]

    crsp_jun = pd.merge(crsp3_jun, decme, how="inner", on=["permno", "year"])
    crsp_jun = crsp_jun[
        [
            "permno",
            "mthcaldt",
            "jdate",
            "sharetype",
            "securitytype",
            "securitysubtype",
            "usincflg",
            "issuertype",
            "primaryexch",
            "conditionaltype",
            "tradingstatusflg",
            "mthret",
            "me",
            "wt",
            "cumretx",
            "mebase",
            "L_me",
            "dec_me",
        ]
    ]
    crsp_jun = crsp_jun.sort_values(by=["permno", "jdate"]).drop_duplicates()
    return crsp3, crsp_jun


def size_bucket(row):
    """Assign stock to portfolio by size"""
    if row["me"] == np.nan:
        value = ""
    elif row["me"] <= row["sizemedn"]:
        value = "S"
    else:
        value = "B"
    return value


def book_to_market_bucket(row):
    """Assign stock to portfolio by book-to-market ratio"""
    if 0 <= row["beme"] <= row["bm30"]:
        value = "L"
    elif row["beme"] <= row["bm70"]:
        value = "ME"
    elif row["beme"] > row["bm70"]:
        value = "H"
    else:
        value = ""
    return value


def merge_CRSP_and_Compustat(crsp_jun, comp, ccm):
    """
    Merge CRSP and Compustat data to compute the book-to-market ratio (beme).

    This function merges Compustat fundamentals with the CRSP June data using
    the CRSP-Compustat linking table (ccm). It first cleans the linking table by
    setting missing linkenddt values to today's date, then merges on the company
    identifier (gvkey). The function computes the end-of-year and portfolio
    formation date (jdate) by offsetting the Compustat data date, and restricts
    the links to those where the formation date falls between the link start
    (linkdt) and end (linkenddt) dates. Finally, it merges the restricted
    linking data with the CRSP June dataset on permno and jdate, and calculates
    the book-to-market ratio (beme) as the scaled book equity divided by
    December market equity.

    **Parameters**
        - **crsp_jun** (:class:`pandas.DataFrame`): CRSP data for June, must
          include a "dec_me" column representing the December market equity.
        - **comp** (:class:`pandas.DataFrame`): Compustat fundamentals data with
          columns for "gvkey", "datadate", "be" (book equity), and "count"
          (number of years in Compustat).
        - **ccm** (:class:`pandas.DataFrame`): CRSP-Compustat linking table
          containing "gvkey", "permno", "linkdt", and "linkenddt" used to match
          records across datasets.

    **Returns**
        - **ccm_jun** (:class:`pandas.DataFrame`): A merged DataFrame that
          includes the common identifiers and dates along with a computed column
          "beme" defined as:

          .. math::

              beme = 1000 * be / dec_me
    """
    # if linkenddt is missing then set to today date
    ccm["linkenddt"] = ccm["linkenddt"].fillna(pd.to_datetime("today"))

    ccm1 = pd.merge(
        comp[["gvkey", "datadate", "be", "count"]], ccm, how="left", on=["gvkey"]
    )
    ccm1["yearend"] = ccm1["datadate"] + YearEnd(0)
    ccm1["jdate"] = ccm1["yearend"] + MonthEnd(6)
    # set link date bounds
    ccm2 = ccm1[
        (ccm1["jdate"] >= ccm1["linkdt"]) & (ccm1["jdate"] <= ccm1["linkenddt"])
    ]
    ccm2 = ccm2[["gvkey", "permno", "datadate", "yearend", "jdate", "be", "count"]]

    # link comp and crsp
    ccm_jun = pd.merge(crsp_jun, ccm2, how="inner", on=["permno", "jdate"])
    ccm_jun["beme"] = ccm_jun["be"] * 1000 / ccm_jun["dec_me"]
    return ccm_jun


def assign_size_and_bm_portfolios(ccm_jun, crsp3):
    # select NYSE stocks for bucket breakdown
    # legacy data format: exchcd = 1 and positive beme and positive me and shrcd
    # in (10,11) and at least 2 years in compustat
    # new CIZ format: primaryexch == 'N', positive beme, positive me, at least
    # 2 years in compustat
    # shrcd in 10 and 11 is already handled in the code earlier

    nyse = ccm_jun[
        (ccm_jun["primaryexch"] == "N")
        & (ccm_jun["beme"] > 0)
        & (ccm_jun["me"] > 0)
        & (ccm_jun["count"] >= 1)
    ]

    # size breakdown
    nyse_sz = (
        nyse.groupby(["jdate"])["me"]
        .median()
        .to_frame()
        .reset_index()
        .rename(columns={"me": "sizemedn"})
    )

    # beme breakdown
    nyse_bm = (
        nyse.groupby(["jdate"])["beme"].describe(percentiles=[0.3, 0.7]).reset_index()
    )
    nyse_bm = nyse_bm[["jdate", "30%", "70%"]].rename(
        columns={"30%": "bm30", "70%": "bm70"}
    )

    nyse_breaks = pd.merge(nyse_sz, nyse_bm, how="inner", on=["jdate"])

    # join back size and beme breakdown
    ccm1_jun = pd.merge(ccm_jun, nyse_breaks, how="left", on=["jdate"])

    # assign size portfolio
    ccm1_jun["szport"] = np.where(
        (ccm1_jun["beme"] > 0) & (ccm1_jun["me"] > 0) & (ccm1_jun["count"] >= 1),
        ccm1_jun.apply(size_bucket, axis=1),
        "",
    )

    # assign book-to-market portfolio
    ccm1_jun["bmport"] = np.where(
        (ccm1_jun["beme"] > 0) & (ccm1_jun["me"] > 0) & (ccm1_jun["count"] >= 1),
        ccm1_jun.apply(book_to_market_bucket, axis=1),
        "",
    )

    # create positivebmeme and nonmissport variable
    ccm1_jun["posbm"] = np.where(
        (ccm1_jun["beme"] > 0) & (ccm1_jun["me"] > 0) & (ccm1_jun["count"] >= 1), 1, 0
    )
    ccm1_jun["nonmissport"] = np.where((ccm1_jun["bmport"] != ""), 1, 0)

    # store portfolio assignment as of June

    june = ccm1_jun[
        ["permno", "mthcaldt", "jdate", "bmport", "szport", "posbm", "nonmissport"]
    ].copy()
    june["ffyear"] = june["jdate"].dt.year

    # merge back with monthly records
    crsp3 = crsp3[
        [
            "mthcaldt",
            "permno",
            "sharetype",
            "securitytype",
            "securitysubtype",
            "usincflg",
            "issuertype",
            "primaryexch",
            "conditionaltype",
            "tradingstatusflg",
            "mthret",
            "me",
            "wt",
            "cumretx",
            "ffyear",
            "jdate",
        ]
    ]
    ccm3 = pd.merge(
        crsp3,
        june[["permno", "ffyear", "szport", "bmport", "posbm", "nonmissport"]],
        how="left",
        on=["permno", "ffyear"],
    )

    # keeping only records that meet the criteria
    ccm4 = ccm3[(ccm3["wt"] > 0) & (ccm3["posbm"] == 1) & (ccm3["nonmissport"] == 1)]
    return ccm4


def wavg(group, avg_name, weight_name):
    """function to calculate value weighted return"""
    d = group[avg_name]
    w = group[weight_name]
    try:
        return (d * w).sum() / w.sum()
    except ZeroDivisionError:
        return np.nan


def create_fama_french_portfolios(data_dir=DATA_DIR):
    """Create value-weighted Fama-French portfolios
    and provide count of firms in each portfolio.
    """
    ## Load Data
    comp = pull_CRSP_Compustat.load_compustat(data_dir=data_dir)
    crsp = pull_CRSP_Compustat.load_CRSP_stock_ciz(data_dir=data_dir)
    ccm = pull_CRSP_Compustat.load_CRSP_Comp_Link_Table(data_dir=data_dir)

    ## Prep Data
    # Prep CRSP and Compustat data according to the Fama-French 1993
    # methodology described in the document linked in the
    # module's docstring (at the top of this file).
    comp = calc_book_equity_and_years_in_compustat(comp)
    crsp = subset_CRSP_to_common_stock_and_exchanges(crsp)
    # crsp['mthret']=crsp['mthret'].fillna(0)
    # crsp['mthretx']=crsp['mthretx'].fillna(0)
    crsp2 = calculate_market_equity(crsp)
    crsp3, crsp_jun = use_dec_market_equity(crsp2)
    ccm_jun = merge_CRSP_and_Compustat(crsp_jun, comp, ccm)

    ## Form Fama French Factors
    ccm4 = assign_size_and_bm_portfolios(ccm_jun, crsp3)

    # value-weigthed return
    vwret = (
        ccm4.groupby(["jdate", "szport", "bmport"])
        .apply(wavg, "mthret", "wt")
        .to_frame()
        .reset_index()
        .rename(columns={0: "vwret"})
    )
    vwret["sbport"] = vwret["szport"] + vwret["bmport"]

    # firm count
    vwret_n = (
        ccm4.groupby(["jdate", "szport", "bmport"])["mthret"]
        .count()
        .reset_index()
        .rename(columns={"mthret": "n_firms"})
    )
    vwret_n["sbport"] = vwret_n["szport"] + vwret_n["bmport"]

    return vwret, vwret_n


def create_factors_from_portfolios(vwret, vwret_n):
    """
    Create Fama-French factors (SMB and HML) from portfolio-level value-weighted returns and firm counts.

    The function pivots the input DataFrames so that rows represent formation dates and columns
    represent the six portfolios formed by intersecting size (big, small) and book-to-market (high,
    medium, low) splits, with portfolio identifiers as follows:

      - BH: Big, High BM
      - BME: Big, Medium BM
      - BL: Big, Low BM
      - SH: Small, High BM
      - SME: Small, Medium BM
      - SL: Small, Low BM

    **Factor Construction:**

    - **HML (High Minus Low):**
      - First, compute the average returns for the high BM portfolios (H) as
        ``(BH + SH) / 2``
      - Next, compute the average returns for the low BM portfolios (L) as
        ``(BL + SL) / 2``
      - Then, HML is given by ``H - L``.

    - **SMB (Small Minus Big):**
      - Compute the average return for big stocks (B) as
        ``(BL + BME + BH) / 3``
      - Compute the average return for small stocks (S) as
        ``(SL + SME + SH) / 3``
      - Then, SMB is ``S - B``.

    The function renames the date column (`jdate`) to `date` and returns only the columns
    necessary for the factor outputs. Firms counts are similarly aggregated for diagnostic purposes,
    with total counts provided in the `TOTAL` column.

    **Parameters**
    -----------
    vwret : pandas.DataFrame
        A DataFrame containing monthly value-weighted returns including:
          - `jdate`: the portfolio formation date,
          - `sbport`: portfolio identifier (BH, BME, BL, SH, SME, or SL),
          - `vwret`: the portfolio return.

    vwret_n : pandas.DataFrame
        A DataFrame with corresponding firm counts for each portfolio with similar structure.

    **Returns**
    -----------
    ff_factors : pandas.DataFrame
        A DataFrame with columns:
          - `date` : the formation date (renamed from jdate),
          - `SMB`  : the Small Minus Big factor,
          - `HML`  : the High Minus Low factor.

    ff_nfirms : pandas.DataFrame
        A DataFrame with firm counts for the portfolios, including:
          - `date`, `SMB`, `HML`, and `TOTAL` (the overall firm count).

    **Reference**
    -----------
    Fama, E.F. & French, K.R. (1993), "Common Risk Factors in the Returns on Stocks and Bonds."
    """
    # tranpose
    ff_factors = vwret.pivot(
        index="jdate", columns="sbport", values="vwret"
    ).reset_index()
    ff_nfirms = vwret_n.pivot(
        index="jdate", columns="sbport", values="n_firms"
    ).reset_index()

    # create SMB and HML factors
    ff_factors["H"] = (ff_factors["BH"] + ff_factors["SH"]) / 2
    ff_factors["L"] = (ff_factors["BL"] + ff_factors["SL"]) / 2
    ff_factors["HML"] = ff_factors["H"] - ff_factors["L"]

    ff_factors["B"] = (ff_factors["BL"] + ff_factors["BME"] + ff_factors["BH"]) / 3
    ff_factors["S"] = (ff_factors["SL"] + ff_factors["SME"] + ff_factors["SH"]) / 3
    ff_factors["SMB"] = ff_factors["S"] - ff_factors["B"]
    ff_factors = ff_factors.rename(columns={"jdate": "date"})
    ff_factors = ff_factors[["date", "SMB", "HML"]]

    # n firm count
    ff_nfirms["H"] = ff_nfirms["SH"] + ff_nfirms["BH"]
    ff_nfirms["L"] = ff_nfirms["SL"] + ff_nfirms["BL"]
    ff_nfirms["HML"] = ff_nfirms["H"] + ff_nfirms["L"]

    ff_nfirms["B"] = ff_nfirms["BL"] + ff_nfirms["BME"] + ff_nfirms["BH"]
    ff_nfirms["S"] = ff_nfirms["SL"] + ff_nfirms["SME"] + ff_nfirms["SH"]
    ff_nfirms["SMB"] = ff_nfirms["B"] + ff_nfirms["S"]
    ff_nfirms["TOTAL"] = ff_nfirms["SMB"]
    ff_nfirms = ff_nfirms.rename(columns={"jdate": "date"})
    ff_nfirms = ff_nfirms[["date", "SMB", "HML", "TOTAL"]]

    return ff_factors, ff_nfirms


def create_Fama_French_factors(data_dir=DATA_DIR):
    vwret, vwret_n = create_fama_french_portfolios(data_dir=data_dir)
    ff_factors, ff_nfirms = create_factors_from_portfolios(vwret, vwret_n)
    return vwret, vwret_n, ff_factors, ff_nfirms


def compare_with_actual_ff_factors(ff_factors, data_dir=DATA_DIR):
    ######################################################
    # Compare With FF provided by Ken French Data Library
    ######################################################
    actual_ff = pull_CRSP_Compustat.load_Fama_French_factors(data_dir=DATA_DIR)
    actual_ff = actual_ff[["date", "smb", "hml"]]

    ff_compare = pd.merge(
        actual_ff, ff_factors[["date", "SMB", "HML"]], how="inner", on="date"
    )

    ff_compare = ff_compare.rename(
        columns={
            "smb": "smb_actual",
            "hml": "hml_actual",
            "SMB": "smb_manual",
            "HML": "hml_manual",
        }
    )

    ff_compare_post_1970 = ff_compare[ff_compare["date"] >= "01/01/1970"]

    ff_compare.set_index("date", inplace=True)
    ff_compare_post_1970.set_index("date", inplace=True)

    return ff_compare, ff_compare_post_1970


def _demo():
    vwret, vwret_n, ff_factors, ff_nfirms = create_Fama_French_factors(
        data_dir=DATA_DIR
    )
    ff_compare, ff_compare_post_1970 = compare_with_actual_ff_factors(
        ff_factors, data_dir=DATA_DIR
    )

    print(
        stats.pearsonr(
            ff_compare_post_1970["smb_actual"], ff_compare_post_1970["smb_manual"]
        )
    )
    print(
        stats.pearsonr(
            ff_compare_post_1970["hml_actual"], ff_compare_post_1970["hml_manual"]
        )
    )

    ff_compare.tail(2)


if __name__ == "__main__":
    vwret, vwret_n, ff_factors, ff_nfirms = create_Fama_French_factors(
        data_dir=DATA_DIR
    )
    vwret.to_parquet(DATA_DIR / "FF_1993_vwret.parquet")
    vwret_n.to_parquet(DATA_DIR / "FF_1993_vwret_n.parquet")
    ff_factors.to_parquet(DATA_DIR / "FF_1993_factors.parquet")
    ff_nfirms.to_parquet(DATA_DIR / "FF_1993_nfirms.parquet")

    ff_compare, ff_compare_post_1970 = compare_with_actual_ff_factors(
        ff_factors, data_dir=DATA_DIR
    )

    ## Plot Comparison
    plt.figure(figsize=(16, 12))
    plt.suptitle("Manually Created Factors vs Ken French Data Library", fontsize=20)

    ax1 = plt.subplot(211)
    ax1.set_title("SMB", fontsize=15)
    ax1.set_xlim([datetime.datetime(1961, 1, 1), datetime.datetime(2022, 6, 30)])
    ax1.plot(ff_compare["smb_actual"], "r--", ff_compare["smb_manual"], "b-")
    ax1.legend(("smb_actual", "smb_manual"), loc="upper right", shadow=True)

    ax2 = plt.subplot(212)
    ax2.set_title("HML", fontsize=15)
    ax2.plot(ff_compare["hml_actual"], "r--", ff_compare["hml_manual"], "b-")
    ax2.set_xlim([datetime.datetime(1961, 1, 1), datetime.datetime(2022, 6, 30)])
    ax2.legend(("hml_actual", "hml_manual"), loc="upper right", shadow=True)

    plt.subplots_adjust(top=0.92, hspace=0.2)

    plt.savefig(OUTPUT_DIR / "FF_1993_Comparison.png")
