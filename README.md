# Financial Time-Series Forecasting Archive

This repository contains a collection of financial time-series forecasting models. It produces esting a benchmark for prac

## Create Virtual Environment

Requirements:
- Pixi: https://pixi.sh/latest/
- Conda: Perhaps move everything over to Pixi soon.
- TeX Live: https://www.tug.org/texlive/

Please start by installing Pixi. Instructions are here: https://docs.pixi.com/getting-started/installation . In short, on MacOS or Linux, you can run this:
```bash
curl -fsSL https://pixi.sh/install.sh | zsh
```
and on Windows, you can run this:
```bash
winget install prefix-dev.pixi
```

The virtual environment is created using conda. It is used to manage the dependencies of the package.

The following steps are used to create the virtual environment.

Inside your terminal, write:
```bash
conda create -n ftsf python=3.12.6
```

Activate virtual environment:
```bash
conda activate ftsf
```

Install packages:
```bash
pip install -r requirements-dev.txt
```

Install pre-commit hooks:
```bash
pre-commit install
```

Set environment variables in `.env` file. Use the `.env.example` file as a reference.

Finally, download the data using the following command:
```bash
doit
```
## Tips

For local development on forecasting scripts, you can activate a pixi environment and open a new shell with that environment activated using the following command:
```bash
pixi shell
```

# Datasets

## Datasets I've Already Included

- CRSP Returns (with and without dividends)

## Potential Datasets to Include in the Future (Notes, Work in Progress)

The paper would reference data from a few papers. The datasets would mostly be organized by the paper in which they are references.

- He, Kelly, Manela Test portfolios. You would run the time series algorithms on the test portfolios all together in a single go. Just use the test portfolios as downloaded from their website. This would just reference their paper.
	- Equity: the Fama and French (1993) **25 size and value sorted portfolios** (from Ken French’s website).
	- For **US bonds**, we include government and corporate bond portfolios in the same class. (Our choice to combine US government and corporate bonds into a single asset class is driven by our desire to estimate prices of intermediary capital risk separately for each asset class. Treating US government bonds as its own asset class is not statistically sensible due to the very high correlation in the returns on these portfolios.)
		- We use ten maturity-sorted **government bond** portfolios from CRSP’s “Fama Bond Portfolios” file with maturities in six month intervals up to five years.
		- For **corporate bonds**, we use ten portfolios sorted on yield spreads from Nozawa (2017). These portfolios are based on a comprehensive bond data set combining TRACE, the Lehman bond database, and others, starting in 1973.
	- For **sovereign bonds** we use six portfolios from Borri and Verdelhan (2012). These portfolios are based on a twoway sort on a bond’s covariance with the US equity market return and the bond’s Standard & Poor’s credit rating.
	- **Options:** For options, we use 54 portfolios of S&P 500 index options sorted on moneyness and maturity from Constantinides, Jackwerth and Savov (2013), split by contract type (27 call and 27 put portfolios), and starting in 1986. Portfolio returns are leverage-adjusted, meaning that each option portfolio is combined with the risk-free rate to achieve a targeted market beta of one.
	- For **foreign exchange**, we combine two datasets of currency portfolios to arrive at a total of 12 portfolios. First is the set of six currency portfolios sorted on the interest rate differential from Lettau et al. (2014). Second is the set of six currency portfolios sorted on momentum from Menkhoff, Sarno, Schmeling and Schrimpf (2012).
	- For **commodities**, we use returns to commodity futures from the Commodities Research Bureau. We begin from the list of 31 commodities in Table 1 of Yang (2013). For each commodity, we form an equal-weighted portfolio of all futures contracts with maturities up to four months. These 31 commodities differ in their availability, with some samples only available for a few years. To balance the benefits of a long sample and many commodities, we include in our dataset 23 commodity portfolios with at least 25 years of returns data.
	- For **CDS**, we construct 20 portfolios sorted by spreads using individual name 5-year contracts. The data are from Markit and begin in 2001. We focus on 5-year CDS for the well known reason that these are the most liquid contracts. Our definition of CDS returns follows Palhares (2013).
- Disaggregated Data from various asset classes (references)
	- Equity returns. This one wouldn't really reference Fama and French (1993), but I would let the readers know that the cleaning method is similar (very small stocks excluded, common shares, US exchanges, no ADRs, etc.) https://wrds-www.wharton.upenn.edu/pages/get-data/center-research-security-prices-crsp/annual-update/stock-version-2/
	- CRSP Daily Treasury Prices: https://wrds-www.wharton.upenn.edu/pages/get-data/center-research-security-prices-crsp/annual-update/treasuries/daily-time-series/
	- Corporate Bonds from TRACE: https://wrds-www.wharton.upenn.edu/pages/get-data/otc-corporate-bond-and-agency-debt-bond-transaction-data/
	- Options, from Constantinides, Jackwerth and Savov (2013)
	- Foreign Exchange, US to other major currencies
	- Commodity futures. list of 31 commodities in Table 1 of Yang (2013)
	- CDS returns, following Palhares (2013)
- Open Source Asset Pricing Data
	- Monthly and Daily long-short returns of 212 predictors following OPs (wide csv) (See here: https://www.openassetpricing.com/data/)
	- 209 predictive firm-level characteristics in wide format, signed so future mean returns increase in characteristics (1.6 GB zipped csv)
-  Include basis trades data from Siriwardane et al.
	- This include basis spread data from Treasury Cash-Futures basis trade, CDS-Bond Basis, Treasury Swap basis, Options Spread bases, etc
- Bank Call Report data. Include bank call report series of interest from NYU call report archive (schnabl). This will be important for publishing on OFR website
- [Industrial Production](https://www.federalreserve.gov/releases/g17/download.htm) over the period 1972-2007 obtained from the Board of Governors, and Benchmark Input-Output tables provided by the Bureau of Economic Analysis (BEA)
	- E.g., following Foerster, Andrew T., Pierre-Daniel Sarte, and Marianna Kudlyak. "Sectoral vs. Aggregate Shocks: A Structural Factor Analysis of Industrial Production, Working Paper 08-07." (2008).
- Include Compustat series (do a bank only one versus everyone else. Maybe do that with CRSP too)
- Redo FRED-MD since it's applicable here, even though it's in the other one


Other options. It's probably best to stick to those above for simplicity
- Include various test portfolios from Ken French Data Library
- Various repo series from OFR short-term funding monitor
- Include estimates of mark-to-market losses from "Monetary Tightening" paper. This will also bolster the case for publishing on OFR website
- Include CRSP panel of stock returns, cash flows (with and without buybacks)
- Include all of the signals from the Open Source Asset Pricing website
- Dividend futures, dividends, S&P 500 returns
- Average within-firm predictability
	- Match asset returns and Compustat financials within firms. That is, for a given company (e.g., via PERCMO), find the stock return, dividend payment, bond returns, associated single name CDS, options connected with that firms stocks, and various Compustat financials all associated with that company. Calculate the predictability within this firm. Then, do this for all firms. Measure the average predictability among firms.

# Interesting Packages to Use
## Darts
Darts offers a consistent fit() and predict() interface across various forecasting models (from ARIMA to deep learning models). Easy to understand, compare and switch.

https://github.com/unit8co/darts

## Prophet
Prophet is specifically designed for users with limited statistical knowledge.

https://github.com/facebook/prophet

## SKTime
SKtime provides a scikit-learn-compatible framework for time series analysis. Allows for easy model tuning, validation, and deployment.
You can also use embedded scikit-learn data transformers for feature generation.

https://github.com/sktime/sktime

https://www.sktime.net/en/stable/

## GluonTS
GluonTS is focused on probabilistic forecasting, allowing users to generate confidence intervals.

https://github.com/awslabs/gluonts

https://ts.gluon.ai/stable/


# Useful Commands

(We can delete this later. I'm putting these here as they're useful for me while I'm developing)

To run pre-commit hooks on all files:
```bash
pre-commit run --all-files
```
to format all files and fix linting errors:
```bash
ruff format . && ruff check --select I --fix . && ruff check --fix .
```