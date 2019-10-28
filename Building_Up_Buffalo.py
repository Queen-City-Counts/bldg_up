import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)

start_yr = 2008
end_yr = 2018
trim = .025

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

sales['assessment'] = sales['assessment'].apply(lambda x: x.strip('$').replace(',',''))
sales['SALE_PRICE'] = sales['sale_price'].apply(lambda x: x.strip('$').replace(',',''))

sales['sale_yr'] = sales['sale_date'].apply(lambda x: x.split('/')[-1])

## PERMITS DATA
pmts = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/Permits 2019-2007.csv',  dtype=object)
pmts = pmts[['PERMIT NUMBER','ISSUED','SBL']].drop_duplicates()
pmts['YEAR'] = pmts['ISSUED'].apply(lambda x: x.split('/')[-1])

def format_sbl(sbl_long):
    sbl = str(sbl_long)[0:3].strip('0') + '.' + str(sbl_long)[3:5].strip('0') + '-' + str(sbl_long)[5:10].strip('0') + '-' + str(sbl_long)[10:13].strip('0')  + '.' + str(sbl_long)[13:16].strip('0') + '/' + str(sbl_long)[16:].strip('0')
    if sbl[-1] == '/' and sbl[-2] != '.':
        sbl = sbl[:-1]
    elif sbl[-2:] == './':
        sbl = sbl[:-2]
    if sbl == 'nan.--' or sbl == '.--':
        sbl = 'missing'
    return sbl

pmts['SBL'] = pmts['SBL'].apply(format_sbl)

pmts = pd.pivot_table(pmts, index=['YEAR','SBL'],values=['PERMIT NUMBER'],aggfunc='count')
pmts.reset_index(inplace=True)
pmts.rename(columns={'PERMIT NUMBER':'PERMITS'},inplace=True)

## CONSTRUCT MAIN DF
## repeat entire asmt df, for each year in the time range
year = year.assign(key=1)
asmt = asmt.assign(key=1)
df = asmt.merge(year, on='key',how='inner').drop('key',axis=1)
df = df.sort_values('YEAR', ascending=True).reset_index(drop=True)

## if property has a sale recorded in sales df, bring that into main df
df = pd.merge(df, sales[['SALE_PRICE','sale_yr','sbl_short']], how = 'left', left_on = ['YEAR','SBL'], right_on = ['sale_yr','sbl_short'])

## if property has any permits recorded in pmts df, bring that in to main df
df = pd.merge(df, pmts[['PERMITS', 'YEAR','SBL']], how = 'left', left_on = ['YEAR','SBL'], right_on = ['YEAR','SBL'])

## polish up the df
df = df[['SBL','YEAR','PROP_TYPE','ASMT','SALE_PRICE','NBHD','PERMITS']]
df = df.astype({'ASMT': float, 'SALE_PRICE': float, 'PERMITS': float})
df['PRICE_DIFF'] = (df['SALE_PRICE'] - df['ASMT'])/df['ASMT']

## outliers per year (by hard threshold)
olrs = pd.pivot_table(df, index=['YEAR'],values=['SALE_PRICE'],aggfunc='count')
olrs.reset_index(inplace=True)
olrs.rename(columns={'SALE_PRICE':'SALES'},inplace=True)
olrs['CUTOFF'] = olrs['SALES'].apply(lambda x: int(x*trim))

min_max = []
for row in range(0, len(olrs)):
    year = olrs.loc[row,'YEAR']
    trim = olrs.loc[row,'CUTOFF']
    mx = df[df['YEAR'] == year]['PRICE_DIFF'].nlargest(trim).iloc[-1]
    mn = df[df['YEAR'] == year]['PRICE_DIFF'].nsmallest(trim).iloc[0]
    min_max.append([year,mn,mx])

min_max  = pd.DataFrame(min_max)
min_max.columns=['YEAR','MIN','MAX']

## outliers per year (by std dev)
olrs_std = pd.pivot_table(df, index=['YEAR'],values=['PRICE_DIFF'],aggfunc=('std','mean'))
olrs_std.reset_index(inplace=True)
olrs_std.columns = olrs_std.columns.droplevel(0)
olrs_std['LOW'] = olrs_std['mean']-(2*olrs_std['std'])
olrs_std['HI'] = olrs_std['mean']+(2*olrs_std['std'])
