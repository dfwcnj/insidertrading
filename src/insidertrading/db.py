
import os
import sys
import sqlite3
import datetime
import argparse
import urllib.request

class InsiderDB():

    def __init__(self):
        self.dbcon = None
        self.dbcur = None
        self.ttbl = "CREATE TABLE IF NOT EXISTS %s ('Date','Open','High','Low','Close','Volume')"
        self.tidx = "CREATE UNIQUE INDEX IF NOT EXISTS dtidx ON %s ('Date')"
        self.tins = 'INSERT OR IGNORE INTO %s VALUES (%s)'
        self.tsel = "SELECT * FROM %s WHERE Date BETWEEN date('%s') AND date('%s')"
        self.itbl = "CREATE TABLE IF NOT EXISTS insiders ('Accession_Number','CIK','Name','Dollars','Ticker','BDate','BOpen','BHigh','BLow','BClose','BVolume','Date','Open','High','Low','Close','Volume')"
        self.iidx = "CREATE UNIQUE INDEX IF NOT EXISTS insidx ON insiders ('Accession_Number')"
        self.ins = 'INSERT OR IGNORE INTO insiders VALUES (%s)'
        self.stooq = 'https://stooq.com/q/d/l/?s=%s.us&i=d'

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

    def gettickerts(self, ticker):
        url = self.stooq % (ticker)
        resp = self.query(url)
        rstr = resp.read().decode('utf-8')
        return rstr

    def selectndays(self, dbfile, tblname, bdate, ndays):
        bd = datetime.date.fromisoformat(bdate)
        td = datetime.timedelta(days=ndays+1)
        ed = bd + td
        bds = bd.strftime('%Y-%m-%d')
        eds = ed.strftime('%Y-%m-%d')
        dsql = self.tsel % (tblname, bds, eds)
        res = self.dbcur.execute(dsql)
        rowa = res.fetchall()
        return rowa

    def insiderdbconnect(self, dbfile):
        self.dbcon = sqlite3.connect(dbfile)
        self.dbcur = self.dbcon.cursor()

    def tickerinsert(self, tblname, line):
        isql = self.tins % (tblname, line)
        self.dbcur.execute(isql)

    def tickerinsertblob(self, tblname, blob):
        lines = blob.split()
        for line in lines:
            if 'Date' in line:
                continue
            lna = line.split(',')
            if len(lna) != 6:
                print('%s %s %s' % (tblname, len(lna), line) )
                lna.append('-1')
            for i in range(len(lna) ):
                lna[i] = "'%s'" % (lna[i])
            self.tickerinsert(tblname, ','.join(lna))
        self.dbcon.commit()

    def newtickertable(self, tblname):
        dsql = 'DROP TABLE IF EXISTS %s' % (tblname)
        self.dbcur.execute(dsql)
        nsql = self.ttbl % (tblname)
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



def main():
    argp = argparse.ArgumentParser(description="Maintain an sqlite db of stock price history and insider trading")
    argp.add_argument('--dbfile', required=True,
           help='sqlite3 database file to use')
    argp.add_argument('--ticker', required=True,
        help='ticker sybbol of stock history to collect')

    args = argp.parse_args()

    SDB = InsiderDB()

    rstr = SDB.gettickerts(args.ticker)
    SDB.insiderdbconnect(args.dbfile)
    SDB.newtickertable(args.ticker)
    SDB.tickerinsertblob(args.ticker, rstr)
    tres = SDB.selectndays(args.dbfile, args.ticker, '2022-07-09', 7)
    print(type(tres) )
    for trec in tres:
        print(type(trec) )
        print(trec)


if __name__ == '__main__':
    main()
