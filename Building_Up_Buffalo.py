import pandas as pd


## ASSESSMENT DATA

## city has been using same assessment roll throughout period
## https://www.wkbw.com/news/local-news/sticker-shock-with-new-buffalo-property-assessments
asmt = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/2017-2018_Assessment_Roll.csv', dtype=object)
asmt = asmt[['PRINT KEY','PROPERTY CLASS','ADDRESS','TOTAL VALUE','NEIGHBORHOOD','ZIP CODE (5-DIGIT)']]

## only want the 200s, 400s, and 500s
## https://www.tax.ny.gov/research/property/assess/manuals/prclas.htm
asmt = asmt.loc[asmt['PROPERTY CLASS'].astype(str).str[0].isin(['2','4','5'])]



## SALES DATA
## read in and clean
sales = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/property_sales_(2000-01-01--2019-10-15).csv', dtype=object)

sales["prop_type"] = sales["prop_type"].str.split(" -", expand = True)
sales = sales.loc[sales['prop_type'].astype(str).isin(['Residential','Commercial','Recreation and Entertainment'])]

sales['assessment'] = sales.assessment.apply(lambda x: x.strip('$').replace(',',''))
sales['sale_price'] = sales.sale_price.apply(lambda x: x.strip('$').replace(',',''))

sales['yr_sold'] = sales.sale_date.apply(lambda x: x.split('/')[-1])

## pull in neighborhood from asmt, on sbl
sales = pd.merge(sales, asmt[['PRINT KEY','NEIGHBORHOOD']], how='left', left_on='sbl_short', right_on = 'PRINT KEY')
sales = sales.drop(columns='PRINT KEY')

## find assessment vs sale_price differential
sales['price_diff'] = sales['sale_price'].astype(float) - sales['assessment'].astype(float)
