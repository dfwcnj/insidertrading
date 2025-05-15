
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
        self.ttbl = "CREATE TABLE IF NOT EXISTS %s (%s)"
        self.tidx = "CREATE UNIQUE INDEX IF NOT EXISTS dtidx ON %s ('Date')"
        self.tins = 'INSERT OR IGNORE INTO %s VALUES (%s)'
        self.tsel = "SELECT * FROM %s WHERE Date BETWEEN date('%s') AND date('%s')"

        # from transaction, submission owner  with dollars computed without footnotes
        #
        self.itbl = "CREATE TABLE IF NOT EXISTS insiders ('ACCESSION_NUMBER', 'NONDERIV_TRANS_SK', 'SECURITY_TITLE', 'TRANS_DATE', 'DEEMED_EXECUTION_DATE', 'TRANS_FORM_TYPE', 'TRANS_CODE', 'EQUITY_SWAP_INVOLVED', 'TRANS_TIMELINESS', 'TRANS_SHARES', 'TRANS_PRICEPERSHARE', 'TRANS_ACQUIRED_DISP_CD', 'SHRS_OWND_FOLWNG_TRANS', 'VALU_OWND_FOLWNG_TRANS', 'DIRECT_INDIRECT_OWNERSHIP', 'NATURE_OF_OWNERSHIP', 'TRANSDOLLARS', 'FILING_DATE', 'NO_SECURITIES_OWNED', 'DOCUMENT_TYPE', 'ISSUERCIK', 'ISSUERNAME', 'ISSUERTRADINGSYMBOL', 'RPTOWNERCIK', 'RPTOWNERNAME', 'RPTOWNER_RELATIONSHIP', 'RPTOWNER_TITLE', 'RPTOWNER_TXT', 'FILE_NUMBER')"

        self.iidx = "CREATE UNIQUE INDEX IF NOT EXISTS insidx ON insiders ('ACCESSION_NUMBER')"
        self.ins = 'INSERT OR IGNORE INTO insiders VALUES (%s)'


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

    def selectdays(self, tblname, sdate, edate):
        """ selectndays(dbfile, tblname, sdate, edate)

        return ticker data for the days specified
        tblname - name of table containing the ticker data
        sdate - beginning date in iso format
        edate - end date in iso format
        """
        sd = datetime.date.fromisoformat(sdate)
        ed = datetime.date.fromisoformat(edate)
        bds = sd.strftime('%Y-%m-%d')
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

    def insiderinsert(self, rec):
        isql = self.ins % (rec)
        self.dbcur.execute(isql)
        self.dbcon.commit()

    def newtinsidertable(self):
        self.dbcur.execute(self.titbl)
        self.dbcur.execute(self.iidx)
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
