import bs4 as bs
import pandas as pd
import numpy as np
import re, urllib.request, requests

pd.set_option('display.max_columns', None)

start_yr = 2008
end_yr = 2018

## create year range df
years = []
for y in range(0,(end_yr - start_yr+1)):
    years.append(str(start_yr+y))
    
years = pd.DataFrame(years)
years.columns = ['YEAR']


## ASSESSMENT DATA
## city has been using same assessment roll throughout period
## https://www.wkbw.com/news/local-news/sticker-shock-with-new-buffalo-property-assessments
asmt = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/2017-2018_Assessment_Roll.csv', dtype=object)
asmt = asmt[['PRINT KEY','PROPERTY CLASS','TOTAL VALUE','NEIGHBORHOOD']].drop_duplicates()
asmt.rename(columns={'PRINT KEY':'SBL','PROPERTY CLASS':'PROP_TYPE','TOTAL VALUE':'ASMT','NEIGHBORHOOD':'NBHD'},inplace=True)

## only want the 200s (residentials) and 400s (commercials)
## https://www.tax.ny.gov/research/property/assess/manuals/prclas.htm
asmt = asmt.loc[asmt['PROP_TYPE'].astype(str).str[0].isin(['2','4'])]



## PERMITS DATA
pmts = pd.read_csv('/home/dan/Python/QueenCityCounts/bldg_up/data/Permits 2019-2007.csv',  dtype=object)
pmts = pmts[['PERMIT NUMBER','ISSUED','SBL']].drop_duplicates()
pmts['YEAR'] = pmts['ISSUED'].apply(lambda x: x.split('/')[-1])

## Permits lists long sbl, Assessment uses short sbl.  Get the two to agree.
## https://www.preservationready.org/Main/SBLNumber
def long_sbl_to_short(long_sbl):
    short_sbl = str(long_sbl)[0:3].strip('0') + '.' + str(long_sbl)[3:5].strip('0') + '-' + str(long_sbl)[5:10].strip('0') + '-' + str(long_sbl)[10:13].strip('0')  + '.' + str(long_sbl)[13:16].strip('0') + '/' + str(long_sbl)[16:].strip('0')
    if short_sbl[-1] == '/' and short_sbl[-2] != '.':
        short_sbl = short_sbl[:-1]
    elif short_sbl[-2:] == './':
        short_sbl = short_sbl[:-2]
    if short_sbl == 'nan.--' or short_sbl == '.--':
        short_sbl = 'missing'
    return short_sbl

pmts['SBL'] = pmts['SBL'].apply(long_sbl_to_short)

## count how many permits were ever filed at each sbl
pmts = pd.pivot_table(pmts, index=['YEAR','SBL'],values=['PERMIT NUMBER'],aggfunc='count')
pmts.reset_index(inplace=True)
pmts.rename(columns={'PERMIT NUMBER':'PERMIT_COUNT'},inplace=True)


## CONSTRUCT MAIN DF

## repeat entire asmt df for ever year in the time range
years = years.assign(key=1)
asmt = asmt.assign(key=1)
df = asmt.merge(years, on='key',how='inner').drop(columns=['key'])
df = df.sort_values(['YEAR','SBL'], ascending=True).reset_index(drop=True)

## if property has any permits recorded in pmts df, bring that in to main df
df = pd.merge(df, pmts[['PERMIT_COUNT', 'YEAR','SBL']], how = 'left', left_on = ['YEAR','SBL'], right_on = ['YEAR','SBL'])

## SALES HISTORY

## get long sbl from the short sbl
## https://www.preservationready.org/Main/SBLNumber
def short_sbl_to_long(short_sbl):
    long_sbl = re.split('[.|/|-]',short_sbl)
    try:
        SECTION = long_sbl[0].zfill(3)
    except:
        SECTION = '000'
    try:
        SUBSECTION = long_sbl[1].zfill(2)
    except:
        SUBSECTION = '00'
    try:
        BLOCK = long_sbl[2].zfill(5)
    except:
        BLOCK = '00000' 
    try:
        LOT = long_sbl[3].zfill(3)
    except:
        LOT = '000'
    try:
        SUBLOT = long_sbl[4].strip()
    except:
        SUBLOT = '000'
    try:
        SUFFIX = long_sbl[5].strip()
    except:
        SUFFIX = ''
    long_sbl = (SECTION + SUBSECTION + BLOCK + LOT + SUBLOT).replace(' ','').ljust(16, '0')
    long_sbl = long_sbl + SUFFIX
    return long_sbl

lkup = pd.DataFrame()
lkup['SHORT_SBL'] = df['SBL'].drop_duplicates()
lkup['LONG_SBL'] = lkup['SHORT_SBL'].apply(short_sbl_to_long)
lkup['TARGET_URL'] = 'https://buffalo.oarsystem.com/assessment/r1parc.asp?swis=140200&sbl=' + lkup['LONG_SBL']

def parcelid_lookup(url):
    if requests.get(url).status_code == 200:
        raw = urllib.request.urlopen(url).read().decode("utf8")
        start = raw.find('parcelid=')
        end = raw.find('\'',start)
        parcelid = str(raw[start+9:end])
        return parcelid
    else:
        return 'error'

###OBS####
lkup = lkup[:3]
###OBS####

lkup['PARCEL_ID'] = lkup['TARGET_URL'].apply(parcelid_lookup)

## CREATE SALES DF
parcels = pd.DataFrame()
parcels = lkup[lkup['PARCEL_ID']!='error'].drop(columns=['TARGET_URL']).drop_duplicates()
parcels['TARGET_URL'] = 'https://buffalo.oarsystem.com/assessment/sales.asp?swis=140200&parcelid=' + parcels['PARCEL_ID']

def get_sales_records(target_url):
    try:
        source = urllib.request.urlopen(target_url)
        soup = bs.BeautifulSoup(source, 'lxml')

        raw = []
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            raw.append(tds)
        
        records = []
        if "No Sales History" in str(raw[-1]):
            records.append(['na']*len(raw[1]))
        else:
            for row in range(2, int(len(raw))):
                data = [i.getText() for i in raw[row]]
                records.append(data)

        df = pd.DataFrame.from_records(records)
        df.columns = [i.getText().replace(' ','_') for i in raw[1]]
    except:
        pass
    return df

sales = pd.DataFrame()
for row in range(0,len(parcels)):
	target_url = parcels.loc[row,'TARGET_URL']
	data = get_sales_records(target_url)
	data['SHORT_SBL'] = parcels.loc[row,'SHORT_SBL']
	sales = sales.append(data)
