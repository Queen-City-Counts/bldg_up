import urllib.request
import bs4 as bs
source = urllib.request.urlopen('https://buffalo.oarsystem.com/assessment/results.asp?swis=140200&rptname=rpt&page=1&cnty=,%20&tbox=,%20&startdate=2000-01-01&enddate=2019-10-02&lwrsaleprice=&uprsaleprice=&lwrasmt=&uprasmt=&oname1=&lwryrbuilt=&upryrbuilt=&lwrsqft=&uprsqft=&lwrbdrms=&uprbdrms=&lwrbaths=&uprbaths=&lwrfrplcs=&uprfrplcs=&searchtype=Sales&nghdcode=&prop_class=&sch_code=&hstyle=&waterfr_type=&rswis=&overall_desire=&stname=')
soup = bs.BeautifulSoup(source, 'lxml')


body = soup.body
b = list()
for row in body.find_all('td'):
	b.append(row)
	

