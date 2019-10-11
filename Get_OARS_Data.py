import urllib.request
import bs4 as bs
source = urllib.request.urlopen('https://buffalo.oarsystem.com/assessment/results.asp?swis=140200&rptname=rpt&page=1&cnty=,%20&tbox=,%20&startdate=2000-01-01&enddate=2019-10-02&lwrsaleprice=&uprsaleprice=&lwrasmt=&uprasmt=&oname1=&lwryrbuilt=&upryrbuilt=&lwrsqft=&uprsqft=&lwrbdrms=&uprbdrms=&lwrbaths=&uprbaths=&lwrfrplcs=&uprfrplcs=&searchtype=Sales&nghdcode=&prop_class=&sch_code=&hstyle=&waterfr_type=&rswis=&overall_desire=&stname=')
soup = bs.BeautifulSoup(source, 'lxml')

raw=list()
for tr in soup.find_all("tr"):
    tds = tr.find_all("td")
    raw.append(tds)

data=list()
for r in range(3,int(len(raw)-1)):
    address = str(raw[r][1].find('span').getText())
    sbl_long = str(raw[r][1]).split(' ')[2].split('=')[-1].replace("'",'').replace('"','')
    sbl_short = str(raw[r][2].getText())
    sale_price = str(raw[r][3].getText().split(" - ")[0])
    sale_date = str(raw[r][3].getText().split(" - ")[1])
    assessment = str(raw[r][4].getText())
    prop_type = str(raw[r][5].getText())
    lot_size = str(raw[r][6].getText())
    yr_blt = str(raw[r][7].getText())
    sqft = str(raw[r][8].getText())
    try:
        bedrooms = str(raw[r][9].getText().split(" / ")[0])
    except:
        bedrooms = ""
    try:    
        baths = str(raw[r][9].getText().split(" / ")[1])
    except:
        baths = ""
    try:
        fireplaces = str(raw[r][9].getText().split(" / ")[2])
    except:
        fireplaces = ""
    tmp = [address, sbl_long, sbl_short, sale_price, sale_date, assessment, prop_type, lot_size, yr_blt, sqft, bedrooms, baths, fireplaces]
    data.append(tmp)
