#!/usr/bin/python3

import re, urllib.request, requests
import pandas as pd
import datetime as dt
import bs4 as bs


## 1) READ IN STARTING DATA FILE
## the tax assessors keep a full list off all the sbl's in the city
## we'll strip just the sbl list out of their assessment roll data 
asmt_17_18 = pd.read_csv('2017-2018_Assessment_Roll.csv', dtype=object)
asmt_17_18.columns = [x.lower() for x in asmt_17_18.columns]

asmt_19_20 = pd.read_csv('2019-2020_Assessment_Roll.csv', dtype=object)
asmt_19_20 .columns = [x.lower() for x in asmt_19_20 .columns]

ttax_18_19 = pd.read_csv('True_Tax_2018-2019.csv', dtype=object)
ttax_18_19.columns = [x.lower() for x in ttax_18_19.columns]

data_files = [asmt_17_18, asmt_19_20, ttax_18_19]

sbls = pd.concat(data_files, sort=False)
sbls = sbls[['print key']].drop_duplicates()
sbls.rename(columns={'print key':'SHORT_SBL'},inplace=True)

sbls = sbls.loc[50:55,:].reset_index().drop(columns=['index'])


## 2) MAKE SOME USER DEFINED FUNCTIONS (we won't use them until later on, though)
## this one converts 'short form' sbl to 'long form' sbl
## see: https://www.preservationready.org/Main/SBLNumber
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

## knowing the 'long form' sbl, we can use this function to look up a building's
## parcel id on the Buffalo OARS site (https://buffalo.oarsystem.com/)
def get_parcel_id(url):
    if requests.get(url).status_code == 200:
        raw = urllib.request.urlopen(url).read().decode("utf8")
        start = raw.find('parcelid=')
        end = raw.find('\'',start)
        parcelid = str(raw[start+9:end])
        return parcelid
    else:
        return ''

## and knowing a building's parcel id, we can finally look up the sales history
## for that building, also on the Buffalo OARS site (https://buffalo.oarsystem.com/)
def get_sales_records(target_url):
    if requests.get(target_url).status_code == 200:
        source = urllib.request.urlopen(target_url)
        soup = bs.BeautifulSoup(source, 'lxml')

        raw = []
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            raw.append(tds)
        
        records = []
        if "No Sales History" in str(raw[-1]):
            records.append(['']*len(raw[1]))
        else:
            for row in range(2, int(len(raw))):
                data = [i.getText() for i in raw[row]]
                records.append(data)

        df = pd.DataFrame.from_records(records)
        df.columns = [i.getText().replace(' ','_') for i in raw[1]]
    else:
        df = pd.DataFrame()
    return df

## 3) PREP/FORMAT THE TAX ASSESSOR DATA FILE 
## the assessor's file starts out with just the short sbl, so first we have 
## to convert it to long, using the 'short_sbl_to_long' function defined above
sbls['LONG_SBL'] = sbls['SHORT_SBL'].apply(short_sbl_to_long)

## add the 'long form' sbl to the end of the lookup url string, to create 
## the actual full url where this building's parcel shows up online 
sbls['PARCEL_LKUP_URL'] = 'https://buffalo.oarsystem.com/assessment/r1parc.asp?swis=140200&sbl=' + sbls['LONG_SBL']


## 4) GET THE PARCEL IDS FROM THE WEB
## for each row in the starting data (ie each sbl extracted from the assessor's data)...
for row in range(0, len(sbls)):
    t1 = dt.datetime.now()
    
    ## use our 'get_parcel_id' function from above to look up that building's 
    ## parcel id on the OARS website, and add that parcel id to the data
    sbls.at[row,'PARCEL_ID'] = get_parcel_id(sbls.at[row,'PARCEL_LKUP_URL'])
    
    ## everything below is just to tell the person running the code
    ## how things are going, and how far along the process is as 
    ## we're going through, adding all the parcel ids
    t2 = dt.datetime.now()
    elapsed = str((t2-t1).seconds) + '.' + str((t2-t1).microseconds)
    print('')
    print('Parcel ' + str(row+1) + ' of ' + str(len(sbls)))
    print('From ' + sbls.at[row,'PARCEL_LKUP_URL'])
    print('Got parcel id ' + sbls.at[row,'PARCEL_ID'] + ' (' + elapsed + ' sec)')


## now that we have all the parcel id's we want, add those parcel ids to the end of the lookup url string to create 
## the actual full url where buildings' sales histories would actually show up online 
sbls['SALES_LKUP_URL'] = 'https://buffalo.oarsystem.com/assessment/sales.asp?swis=140200&parcelid=' + sbls['PARCEL_ID']


## 5) GET THE SALES HISTORIES FROM THE WEB
## start off with an empty dataframe called 'sales'
sales = pd.DataFrame()
count = 1

## for each row in the data (which at this point contains all the tax assessor's sbls, plus their parcel id)...
for row in range(0,len(sbls)):
    t1 = dt.datetime.now()

    ## use our 'get_sales_records' function from above to look up that building's 
    ## sales history on the OARS website, and add it to the sales dataframe
    data = get_sales_records(sbls.at[row,'SALES_LKUP_URL'])
    if len(data) == 0:
        data.at[row,'SHORT_SBL'] = sbls.loc[row,'SHORT_SBL']
        data.at[row,'LONG_SBL'] = sbls.loc[row,'LONG_SBL']
        data.at[row,'SALES_LKUP_URL'] = sbls.loc[row,'SALES_LKUP_URL']
        data.at[row,'PARCEL_LKUP_URL'] = sbls.loc[row, 'PARCEL_LKUP_URL']
    else:
        data['SHORT_SBL'] = sbls.loc[row,'SHORT_SBL']
        data['LONG_SBL'] = sbls.loc[row,'LONG_SBL']
        data['SALES_LKUP_URL'] = sbls.loc[row,'SALES_LKUP_URL']
        data['PARCEL_LKUP_URL'] = sbls.loc[row, 'PARCEL_LKUP_URL']
    sales = sales.append(data, sort=False)
    
    ## everything below is just to tell the person running the code
    ## how things are going, and how far along the process is as
    ## we're going through, adding all the sales records
    t2 = dt.datetime.now()
    elapsed = str((t2-t1).seconds) + '.' + str((t2-t1).microseconds)
    print('')
    print('Sales history ' + str(count) + ' of ' + str(len(sbls)))
    print('From ' + sbls.at[row,'SALES_LKUP_URL'])
    print('Got ' + str(len(data)) + ' data row(s) (' + elapsed + ' sec)')
    count += 1

## 6) FINISH
## once all the sale history data has been retrieved, and added to the sales dataframe,
## stop the process, and export the dataframe to a csv
print('')
print('DATA RETRIEVAL COMPLETE')
print('')
sales = sales[['SHORT_SBL', 'LONG_SBL', 'PARCEL_LKUP_URL', 'SALES_LKUP_URL',
               'Sale_Date', 'Price', 'Useable', "Arm's_Length", 'Prior_Owner',
               'Total_Assessed_Value', 'Total_Land_Value', 'Deed_Book',
               'Deed_Page']]
sales.to_csv('sales.csv', index=False)

