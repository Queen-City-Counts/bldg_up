import pandas as pd


## ASSESSMENT DATA

## City has been using same assessment roll throughout period
## https://www.wkbw.com/news/local-news/sticker-shock-with-new-buffalo-property-assessments
asmt = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/2017-2018_Assessment_Roll.csv', dtype=object)
asmt = asmt[['PRINT KEY','PROPERTY CLASS','ADDRESS','TOTAL VALUE','NEIGHBORHOOD','ZIP CODE (5-DIGIT)']]

## I only want the 200s, 400s, and 500s
## https://www.tax.ny.gov/research/property/assess/manuals/prclas.htm
asmt = asmt.loc[asmt['PROPERTY CLASS'].astype(str).str[0].isin(['2','4','5'])]



## SALES DATA

sales = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/property_sales_(2000-01-01--2019-10-15).csv', dtype=object)
sales["prop_type"] = sales["prop_type"].str.split(" -", expand = True)
sales = sales.loc[sales['prop_type'].astype(str).isin(['Residential','Commercial','Recreation and Entertainment'])]

## Pull in neighborhood from asmt, on sbl
## TODO: check this join is working, and that the results make sense...write out first 1000 rows to csv and manually inspect
df = pd.merge(sales, asmt[['PRINT KEY','NEIGHBORHOOD']], how='left', left_on='sbl_short', right_on = 'PRINT KEY')
