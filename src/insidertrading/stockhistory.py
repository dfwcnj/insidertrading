
import os
import sys
import datetime
import argparse
import urllib.request

class _StockHistory():

    def __init__(self):
        """ _StcokHistory()

        retrieve stock price history from various sources
        """
        # symbol MM/DD/YYYY MM/DD/YYYY
        self.mktwatchurl = 'https://www.marketwatch.com/investing/stock/{tckr}/downloaddatapartial?startdate={sdate}%2000:00:00&enddate={edate}%2000:00:00&daterange=d30&frequency=p1d&csvdownload=true&downloadpartial=false&newdates=false'

        # symbol
        self.stooqurl = 'https://stooq.com/q/d/l/?s={tckr}.us&i=d'

        # symbol start timestamp end timestamp
        self.yhts1 = 946684800
        self.yhurl = 'https://query1.finance.yahoo.com/v7/finance/download/{tckr}?period1={startts}&period2={endts}&interval=1d&events=history&includeAdjustedClose=true'


    def query(self, url=None):
        """query(url) - query a url

         url - url of file to retrieve
        """
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req)
            return resp
        except urllib.error.URLError as e:
            #print("Error %s(%s): %s" % ('query', url, e.reason), file=sys.stderr )
            return None

    def getyahootickerhistory(self, ticker):
        """ getyahootickerhistory(ticker)

        get stock price history for ticker from yahoo finance
        ticker - ticker symbol for stock
        """
        ticker=ticker.upper()
        now = datetime.datetime.now()
        ets = int(now.timestamp() )
        #    yrsec = 60*60*24*365
        #    sts = ets - (yrsec * 10)
        sts = self.yhts1           # 2000-01-01
        url = self.yhurl.format(tckr=ticker, startts=sts, endts=ets)
        # print(url, file=sys.stderr)
        resp = self.query(url)
        if not resp:
            return []
        rstr = resp.read().decode('utf-8')
        lines = rstr.split()
        if len(lines) == 1:
            # print('yahoo: ' % lines[0])
            return []
        if 'Close' in lines[1]:
           alines=[]
           alines.append('Date,Open,High,Low,Close,AdjClose,Volume')
           for i in range(2, len(lines) ):
               alines.append(lines[i])
           # for line in alines: print(line)
           return alines
        return lines

    def getmarketwatchtickerhistory(self, ticker):
        """ getmarketwatchtickerhistory(ticker)

        get stock price history for ticker marketwatch investing
        ticker - ticker symbol for stock
        """
        now = datetime.datetime.now()
        day = ('%d' % (now.day) ).zfill(2)
        mon = ('%d' % (now.month) ).zfill(2)
        yr  = now.year
        odt = '%s/%s/%d' % (mon, day, yr-1)
        ndt = '%s/%s/%d' % (mon, day, yr)
        url = self.mktwatchurl.format( tckr=ticker, sdate=odt, edate=ndt)
        # print(url, file=sys.stderr)
        resp = self.query(url)
        if not resp:
            return []
        rstr = resp.read().decode('utf-8')
        lines = rstr.split()
        if len(lines) == 1:
            print('marketwatch: ' % lines[0])
            return []
        return lines


    def getstooqtickerhistory(self, ticker):
        """ getstooqtickerhistory(ticker)

        get stock price history for ticker
        ticker - ticker symbol for stock from stooq
        """
        url = self.stooqurl.format(tckr=ticker)
        # print(url, file=sys.stderr)
        resp = self.query(url)
        if not resp:
            return []
        rstr = resp.read().decode('utf-8')
        lines = rstr.split()
        if len(lines) == 1:
            # print('stooq: ' % lines[0])
            return []
        return lines

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

    def linestocsv(self, lines):
        """ linestocsv(lines)

        convert lines to quotes csv lines
        lines - list of likes to quote
        """
        qlines=[]
        for line in lines:
            line = "'%s'" % ("','".join(line.split(',') ) )
            qlines.append(line)
        return qlines


def main():
    argp = argparse.ArgumentParser(description="get stock price history")
    argp.add_argument('--ticker', required=True,
        help='ticker sybbol of stock history to collect')
    argp.add_argument('--site', default='yahoo',
        help='site to query - yahoo, marketwatch, or stooq')

    args = argp.parse_args()

    SH = _StockHistory()

    if args.site == 'yahoo':
        lines = SH.getyahootickerhistory(args.ticker)
    elif args.site == 'stooq':
        lines = SH.getstooqtickerhistory(args.ticker)
    elif args.site == 'marketwatch':
        lines = SH.getmarketwatchtickerhistory(args.ticker)
    else:
        lines = SH.gettickerhistory(args.ticker)

    if len(lines):
        qlines = SH.linestocsv(lines)
        for line in qlines:
            print(line)

if __name__ == '__main__':
    main()
