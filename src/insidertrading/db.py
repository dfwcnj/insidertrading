
import os
import sys
import sqlite3
import datetime
import argparse
import urllib.request

try:
    from insidertrading import stockhistory
except ImportError as e:
    import stockhistory

class InsiderDB():

    def __init__(self):
        self.dbcon = None
        self.dbcur = None
        #self.ttbl = "CREATE TABLE IF NOT EXISTS %s ('Date','Open','High','Low','Close','Volume')"
        self.ttbl = "CREATE TABLE IF NOT EXISTS %s (%s)"
        self.tidx = "CREATE UNIQUE INDEX IF NOT EXISTS dtidx ON %s ('Date')"
        self.tins = 'INSERT OR IGNORE INTO %s VALUES (%s)'
        self.tsel = "SELECT * FROM %s WHERE Date BETWEEN date('%s') AND date('%s')"
        self.itbl = "CREATE TABLE IF NOT EXISTS insiders ('Accession_Number','CIK','Name','Dollars','Ticker','BDate','BOpen','BHigh','BLow','BClose','BVolume','Date','Open','High','Low','Close','Volume')"
        self.iidx = "CREATE UNIQUE INDEX IF NOT EXISTS insidx ON insiders ('Accession_Number')"
        self.ins = 'INSERT OR IGNORE INTO insiders VALUES (%s)'

        self.sh = stockhistory._StockHistory()
        # self.stooqurl = 'https://stooq.com/q/d/l/?s=%s.us&i=d'
        # symbol MM/DD/YYYY MM/DD/YYYY
        # self.mktwatchurl = 'https://www.marketwatch.com/investing/stock/{tckr}/downloaddatapartial?startdate={fdate}%2000:00:00&enddate={tdate}%2000:00:00&daterange=d30&frequency=p1d&csvdownload=true&downloadpartial=false&newdates=false'


    def query(self, url=None):
        """query(url) - query a url

         url - url of file to retrieve
        """
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req)
            return resp
        except urllib.error.URLError as e:
            print("Error %s(%s): %s" % ('query', url, e.reason),
            file=sys.stderr )
            sys.exit(1)

    def getyahootickerhistory(self, ticker):
        """ marketwatchtickerhistory(ticker)

        get stock price history for ticker
        ticker - ticker symbol for stock
        """
        return self.sh.getyahootickerhistory(ticker)

    def getmarketwatchtickerhistory(self, ticker):
        """ getmarketwatchtickerhistory(ticker)

        get stock price history for ticker
        ticker - ticker symbol for stock
        """
        return self.sh.getmarketwatchtickerhistory(ticker)

    def getstooqtickerhistory(self, ticker):
        """ getstooqtickerhistory(ticker)

        get stock price history for ticker
        ticker - ticker symbol for stock
        """
        return self.sh.getstooqtickerhistory(ticker)

    def gettickerhistory(self, ticker):
        """ gettickerhistory(ticker)

        get ticker history from yahoo, marketwatch, or stooq
        ticker - ticker symbol for the stock
        """
        lines = self.getyahootickerhistory(ticker)
        if len(lines):
            return lines
        lines = self.getmarketwatchtickerhistory(ticker)
        if len(lines):
            return lines
        lines = self.getstooqtickerhistory(ticker)
        if len(lines):
            return lines
        return []


    def selectndays(self, tblname, bdate, ndays):
        """ selectndays(dbfile, tblname, bdate, ndays)

        return ticker data for the ndays specified
        tblname - name of table containing the ticker data
        bdate - beginning date in iso format
        ndays - number of days to collect
        """
        bd = datetime.date.fromisoformat(bdate)
        td = datetime.timedelta(days=ndays+1)
        ed = bd + td
        bds = bd.strftime('%Y-%m-%d')
        eds = ed.strftime('%Y-%m-%d')
        dsql = self.tsel % (tblname, bds, eds)
        res = self.dbcur.execute(dsql)
        rowa = res.fetchall()
        return rowa

    def dbconnect(self, dbfile):
        """ dbconnect(dbfile)

        establish connection to sqlite3 database
        dbfile - name of the database file
        """
        self.dbcon = sqlite3.connect(dbfile)
        self.dbcur = self.dbcon.cursor()

    def tickerinsert(self, tblname, line):
        """ tickerinsert(tblname, line)

        insert a ticker row into the ticker table
        tblname - name of the table 
        line - ticker data for 1 day
        """
        isql = self.tins % (tblname, line)
        self.dbcur.execute(isql)

    def tickerinsertlines(self, tblname, lines):
        cols = lines[0]
        for line in lines:
            if 'Date' in line:
                continue
            lna = line.split(',')
            if len(lna) < 5:     # too short to fix
                print('ticker: %s %s %s' % (tblname, len(lna), line) )
                continue
            if len(lna) == 5:         # stooq - missing volume
                print('ticker: %s %s %s' % (tblname, len(lna), line) )
                lna.append('-1')
            # yahoo finance and exception having 7 columns
            if 'Adj' not in cols and len(lna) > 6:  # marketwatch , in Volume
                vol = ''.join(lna[5:])
                lna = lna[0:5] + [',%s' % vol]
            if '/' in lna[0]:                       # marketwatch MM/DD/YYYY
                mdy = lna[0].split('/')
                lna[0] = '%s-%s-%s' % (mdy[2],mdy[1],mdy[0])
            for i in range(len(lna) ):
                lna[i] = "'%s'" % (lna[i])
            self.tickerinsert(tblname, ','.join(lna))
        self.dbcon.commit()

    def newtickertable(self, tblname, hdr):
        dsql = 'DROP TABLE IF EXISTS %s' % (tblname)
        self.dbcur.execute(dsql)
        cn = "'%s'" % ("','".join(hdr.split(',') ) )
        nsql = self.ttbl % (tblname, cn)
        self.dbcur.execute(nsql)
        isql = self.tidx % (tblname)
        self.dbcur.execute(isql)
        self.dbcon.commit()

    def insiderinsert(self, rec):
        isql = self.ins % (rec)
        self.dbcur.execute(isql)
        self.dbcon.commit()

    def newinsidertable(self):
        self.dbcur.execute(self.itbl)
        self.dbcur.execute(self.iidx)
        self.dbcon.commit()

    def reporttable(self, table, fp):
        rsql = 'SELECT * FROM %s' % (table)
        self.dbcur.execute(rsql)
        hdr = [column[0] for column in self.dbcur.description]
        print('"%s"' % ('","'.join(hdr) ), file=fp )
        rows = self.dbcur.fetchall()
        for row in rows:
            print('"%s"' % ('","'.join(row) ), file=fp )

def main():
    argp = argparse.ArgumentParser(description="Maintain an sqlite db of stock price history and insider trading")
    argp.add_argument('--dbfile', default=':memory:',
           help='sqlite3 database file to use ¯ default in memory')
    argp.add_argument('--ticker', required=True,
        help='ticker sybbol of stock history to collect')

    args = argp.parse_args()

    SDB = InsiderDB()

    lines = SDB.gettickerhistory(args.ticker)
    if not lines:
        print('unable to get stock symbol history', file=sys.stderr)
        sys.exit()
    SDB.dbconnect(args.dbfile)
    SDB.newtickertable(args.ticker, lines[0])
    SDB.tickerinsertlines(args.ticker, lines)
    now = datetime.datetime.now()
    boy = datetime.date(now.year-1, 12, 12).isoformat()
    tres = SDB.selectndays(args.ticker, boy, 7)
    print(type(tres) )
    for trec in tres:
        print(type(trec) )
        print(trec)


if __name__ == '__main__':
    main()
