#!/usr/bin/python3

## python3 -u get_sales_histories.py | less | tee log

import re, urllib.request, requests, time
import pandas as pd
import numpy as np
import bs4 as bs
import datetime as dt
pd.set_option('display.max_columns', None) 

## 1) READ IN STARTING DATA FILE
## the tax assessors keep a full list off all the sbl's in the city
## we'll strip just the sbl list out of their assessment roll data
ttax_18_19 = pd.read_csv('True_Tax_2018-2019.csv', dtype=object)
ttax_18_19.columns = [x.lower() for x in ttax_18_19.columns]

asmt_19_20 = pd.read_csv('2019-2020_Assessment_Roll.csv', dtype=object)
asmt_19_20 .columns = [x.lower() for x in asmt_19_20 .columns]

asmt_17_18 = pd.read_csv('2017-2018_Assessment_Roll.csv', dtype=object)
asmt_17_18.columns = [x.lower() for x in asmt_17_18.columns]

data_files = [asmt_17_18, asmt_19_20, ttax_18_19]

sbls = pd.concat(data_files, sort=False)
sbls = sbls[['print key']].drop_duplicates()
sbls.rename(columns={'print key':'SHORT_SBL'},inplace=True)

sbls = sbls.reset_index().drop(columns=['index'])

###########################
### ADDED FOR 2ND STAGE ###
log = pd.read_csv('success_asof_3.20.20', sep=" ", header=None)
log.rename(columns={0:'SHORT_SBL'},inplace=True)

log = log['SHORT_SBL']
sbls = sbls['SHORT_SBL']
sbls = sbls[~(sbls.isin(log))]
sbls = sbls.to_frame()
### ADDED FOR 2ND STAGE ###
###########################


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
def get_parcel_id(parcel_lkup_url):
    if requests.get(str(parcel_lkup_url)).status_code == 200:
        raw = urllib.request.urlopen(parcel_lkup_url).read().decode("utf8")
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
            records.append(['NA']*len(raw[1]))
        else:
            for row in range(2, int(len(raw))):
                data = [i.getText() for i in raw[row]]
                records.append(data)

        df = pd.DataFrame.from_records(records)
        df.columns = [i.getText().replace(' ','_') for i in raw[1]]
    return df

## given any random row from the SBLs df, try to look up the sales history for that SBL
def retreive_sales(rand_row):
    tmp = pd.DataFrame()
    tmp.at[0,'SHORT_SBL'] = rand_row['SHORT_SBL'].iloc[0]
    tmp.at[0,'LONG_SBL'] = rand_row['LONG_SBL'].iloc[0]
    tmp.at[0,'PARCEL_LKUP_URL'] = rand_row['PARCEL_LKUP_URL'].iloc[0]
    tmp['PARCEL_ID'] = tmp['PARCEL_LKUP_URL'].apply(get_parcel_id)
    tmp['SALES_LKUP_URL'] = 'https://buffalo.oarsystem.com/assessment/sales.asp?swis=140200&parcelid=' + tmp['PARCEL_ID']    
    tmp.at[0, 'ACCESSED'] = dt.datetime.now()
    data = get_sales_records(tmp['SALES_LKUP_URL'].iloc[0])
    tmp = pd.concat([tmp]*len(data), ignore_index=True)
    tmp = pd.concat([tmp, data], axis=1)
    return tmp


## 3) COMPLETE THE DF
sbls['LONG_SBL'] = sbls['SHORT_SBL'].apply(short_sbl_to_long)
sbls['PARCEL_LKUP_URL'] = 'https://buffalo.oarsystem.com/assessment/r1parc.asp?swis=140200&sbl=' + sbls['LONG_SBL']
sbls['RETRIEVED'] = 0
sbls['ATTEMPTS'] = 0


## 4) REFERENCE ONLINE DATA
retreived_count = 0
sbls_count = len(sbls)
while sum(sbls['RETRIEVED']) < sbls_count:
    if retreived_count == 0:
        rand_row = sbls[sbls['RETRIEVED'] == 0].sample(1)
        now = str(dt.datetime.now().month) + '/' + str(dt.datetime.now().day) + '/' +  str(dt.datetime.now().year) + ' ' + str(dt.datetime.now().hour) + ':' + str(dt.datetime.now().minute).zfill(2) + ':' + str(dt.datetime.now().second).zfill(2) + '.' + str(dt.datetime.now().microsecond)[0:3]
        sbls.at[rand_row.index.values[0], 'ATTEMPTS'] += 1
        t1 = dt.datetime.now()
        sales = retreive_sales(rand_row)
        sales.to_csv('sales.csv', index=False)
        retreived_count += 1
        t2 = dt.datetime.now()
        elapsed = str((t2-t1).seconds) + '.' + str((t2-t1).microseconds)[0:3]
        now = str(dt.datetime.now().month) + '/' + str(dt.datetime.now().day) + '/' +  str(dt.datetime.now().year) + ' ' + str(dt.datetime.now().hour) + ':' + str(dt.datetime.now().minute).zfill(2) + ':' + str(dt.datetime.now().second).zfill(2) + '.' + str(dt.datetime.now().microsecond)[0:3]
        print('\t'.join(['success', str(rand_row['SHORT_SBL'].iloc[0]), str(now), ('attempt ' + str(rand_row['ATTEMPTS'].iloc[0]+1)), ('in ' + str(elapsed) + ' secs'), (str(retreived_count) + ' of ' + str(sbls_count) + ' - ' + str(round(((retreived_count/sbls_count)*100),2)) + '%')]))
        sbls.at[rand_row.index.values[0], 'RETRIEVED'] = 1
    else:
        rand_row = sbls[sbls['RETRIEVED'] == 0].sample(1)
        sbls.at[rand_row.index.values[0], 'ATTEMPTS'] += 1
        now = str(dt.datetime.now().month) + '/' + str(dt.datetime.now().day) + '/' +  str(dt.datetime.now().year) + ' ' + str(dt.datetime.now().hour) + ':' + str(dt.datetime.now().minute).zfill(2) + ':' + str(dt.datetime.now().second).zfill(2) + '.' + str(dt.datetime.now().microsecond)[0:3]
        try:
            t1 = dt.datetime.now()
            sales = retreive_sales(rand_row)
            csv = pd.read_csv('sales.csv')
            csv = csv.append(sales, ignore_index = True, sort = False)
            csv.to_csv('sales.csv', index=False)
            retreived_count += 1
            t2 = dt.datetime.now()
            elapsed = str((t2-t1).seconds) + '.' + str((t2-t1).microseconds)[0:3]
            print('\t'.join(['success', str(rand_row['SHORT_SBL'].iloc[0]), str(now), ('attempt ' + str(rand_row['ATTEMPTS'].iloc[0]+1)), ('in ' + str(elapsed) + ' secs'), (str(retreived_count) + ' of ' + str(sbls_count) + ' - ' + str(round(((retreived_count/sbls_count)*100),2)) + '%')]))
            sbls.at[rand_row.index.values[0], 'RETRIEVED'] = 1
        except:
            wait_time = 10
            print('\t'.join(['failure', str(rand_row['SHORT_SBL'].iloc[0]), str(now), ('attempt ' + str(rand_row['ATTEMPTS'].iloc[0]+1)), ('wait ' + str(wait_time) + ' mins'), (str(retreived_count) + ' of ' + str(sbls_count) + ' - ' + str(round(((retreived_count/sbls_count)*100),2)) + '%')]))
            time.sleep(wait_time*60)
            pass

