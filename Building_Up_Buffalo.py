import pandas as pd
import numpy as np

start_yr = 2008
end_yr = 2018

## create year df
year = list()
for y in range(0,(end_yr - start_yr+1)):
    year.append(str(start_yr+y))
    
year = pd.DataFrame(year)
year.columns = ['YEAR']

## ASSESSMENT DATA
## city has been using same assessment roll throughout period
## https://www.wkbw.com/news/local-news/sticker-shock-with-new-buffalo-property-assessments
asmt = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/2017-2018_Assessment_Roll.csv', dtype=object)
asmt = asmt[['PRINT KEY','PROPERTY CLASS','TOTAL VALUE','NEIGHBORHOOD']].drop_duplicates()

## only want the 200s (residentials) and 400s (commercials)
## https://www.tax.ny.gov/research/property/assess/manuals/prclas.htm
asmt = asmt.loc[asmt['PROPERTY CLASS'].astype(str).str[0].isin(['2','4'])]
asmt.rename(columns={'PRINT KEY':'SBL','PROPERTY CLASS':'PROP_TYPE','TOTAL VALUE':'ASMT','NEIGHBORHOOD':'NBHD'},inplace=True)

## SALES DATA
## read in and clean
sales = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/property_sales_(2000-01-01--2019-10-15).csv', dtype=object)

sales['assessment'] = sales.assessment.apply(lambda x: x.strip('$').replace(',',''))
sales['sale_price'] = sales.sale_price.apply(lambda x: x.strip('$').replace(',',''))

sales['sale_yr'] = sales.sale_date.apply(lambda x: x.split('/')[-1])

## PERMITS DATA
pmts = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/Permits 2019-2007.csv',  dtype=object)
pmts = pmts[['PERMIT NUMBER','ISSUED','SBL']].drop_duplicates()
pmts['YEAR'] = pmts.ISSUED.apply(lambda x: x.split('/')[-1])

## create short sbl
## https://www.preservationready.org/Main/SBLNumber
pmts['SBL_SHORT'] = pmts.SBL.apply(lambda x: str(x)[0:3].strip('0') + '.' + str(x)[3:5].strip('0') + '-' + str(x)[5:10].strip('0') + '-' + str(x)[10:13].strip('0')  + '.' + str(x)[13:16].strip('0') + '-' + str(x)[16:].strip('0'))

## CONSTRUCT MAIN DF
## repeat entire asmt df, for each year in the time range
year = year.assign(key=1)
asmt = asmt.assign(key=1)
df = asmt.merge(year, on='key',how='inner').drop('key',axis=1)
df = df.sort_values('YEAR', ascending=True).reset_index(drop=True)

## if property has a sale recorded in sales df, bring that in
df = pd.merge(df, sales[['sale_price','sale_yr','sbl_short']], how = 'left', left_on = ['YEAR','SBL'], right_on = ['sale_yr','sbl_short'])
df = df.astype({'ASMT': float, 'sale_price': float})

