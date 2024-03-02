#! env python

import os
import sys
import re
import argparse
import datetime
import time
import zipfile
import urllib.request
from html.parser import HTMLParser
from functools import partial
from xml.etree import ElementTree as ET

try:
    from insidertrading import db
except ImportError as e:
    import db

class EDGARInsiderTrading():
    def __init__(self):
        """ EDGARInsiderTrading

        attempt to connect EDGAR insider trading data with some data
        from other sources
        """
        if 'EQEMAIL' in os.environ:
            self.hdr     = {'User-Agent' : os.environ['EQEMAIL'] }
        else:
            print('EQEMAIL environmental variable must be set to a valid \
                   HTTP User-Agent value such as an email address')


        self.pause = 2

        self.cpat = 'AAPL|AMZN|BRK-B|GOOG|LLY|META|NVDA|JPM|TSLA'
        self.siturl = ''

        self.gatomurl = 'https://news.google.com/atom'
        self.grssargs = {'hl':'en-US','gl':'US','ceid':'US:en'}

        self.stooqurl = 'https://stooq.com/q/d/l/?s=%s.us&i=d'

        # symbol MM/DD/YYYY MM/DD/YYYY
        self.mktwatchurl = 'https://www.marketwatch.com/investing/stock/{tckr}/downloaddatapartial?startdate={fdate}%2000:00:00&enddate={tdate}%2000:00:00&daterange=d30&frequency=p1d&csvdownload=true&downloadpartial=false&newdates=false'

        # from https://www.sec.gov/dera/data/form-345
        self.iturl = 'https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets'
        self.topsubmissions={}
        self.transtop=[]
        self.bigtransdict={}
        self.threshold = 1.05
        self.interval = 7
        self.sdb = db.InsiderDB()

        self.chunksize =4294967296 # 4M

    def setthreshold(self, thresh):
        ti = int(thresh)
        if ti < 0 or ti > 50:
            print('setthreshold: range 0-50', file=sys.stderr)
            sys.exit(1)
        self.threshold = 1 + ti/100

    def setinterval(self, intvl):
        ti = int(intvl)
        if ti < 1 or ti > 14:
            print('setinterval: range 1-14', file=sys.stderr)
            sys.exit(1)
        self.interval = intvl

    def query(self, url=None):
        """query(url) - query a url

         url - url of file to retrieve
        """
        count = 0
        max   = 5
        paws = self.pause
        while True:
            try:
                req = urllib.request.Request(url, headers=self.hdr)
                resp = urllib.request.urlopen(req)
                return resp
            except urllib.error.URLError as e:
                if e.reason == 'Not Found':
                    print('%s: %s' % (url, e.reason), file=sys.stderr)
                    sys.exit(1)
                print("Error %s(%s): %s" % ('query', url, e.reason),
                     file=sys.stderr )
                count = count + 1
                if count < max:
                    time.sleep(paws)
                    print('pausing %d seconds' % (paws) )
                    paws = paws * 2
                    continue
                sys.exit(1)

    def storequery(self, qresp, file):
        """storequery(qresp, file)

        store the query response in a file
        resp - response object of the url retrieved
        file   - filename that will hold the query response
        """
        if not qresp:
            print('storequery: no content', file=sys.stderr)
            sys.exit(1)
        if not file:
            print('storequery: no output filename', file=sys.stderr)
            sys.exit(1)
        of = os.path.abspath(file)
        # some downloads can be somewhat large
        with open(of, 'wb') as f:
            parts = iter(partial(qresp.read, self.chunksize), b'')
            for c in parts:
                f.write(c)
            #if c: f.write(c)
            f.flush()
            os.fsync(f.fileno() )
            return

    def parseethtml(self, html):
        """ parseethtml(html)

        tease out urls from news.google.com/atom data
        html - html fragment to parse
        """
        if '<html>' not in html:
            html = '<html>%s</html>' % (html)

        class MyHTMLParser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                def __init__(self):
                    super().__init__()
                    self.src = None
                if tag == 'a':
                    for tpl in attrs:
                        if tpl[0] == 'href':
                            if hasattr(self, 'src'):
                                print("\t<a> '%s','%s'" % (self.src, tpl[1]) )
                            else:

                                print('\thtml %s' % (tpl[1]) )
            def handle_data(self, data):
                    print('\thtml data: %s' % (data) )
                    self.src = data

        parser = MyHTMLParser()
        parser.feed(html)

    def form345zipfileiter(self, fzpath, file):
        """ form345zipfileiter(fzpath, iter)

        return an iterator for lines from file in fzpath
        fzpath - form345 zip file from fred.stlouisfed.org
        file  - file in the zip file to read
        """
        try:
            lna = []
            with zipfile.ZipFile(fzpath, mode='r') as zfp:
                fstr = zfp.read(file).decode("utf-8")
                lge = (line for line in fstr.splitlines() )
                return lge
        except zipfile.BadZipfile as e:
            print('open %s: %s', (fzpath, e) )
            sys.exit(1)

    def form345largesttrades(self, fzpath, file):
        """ form345largesttrades(fzpath, file)

        collect form345 data from file in fzpath
        fzpath - form345 zip file from fred.stlouisfed.org
        file  - file in the zip file to read
        """
        lge = self.form345zipfileiter(fzpath, file)
        prtransdict = {}
        hdr=[]
        lna=[]
        trsidx = 0
        trpidx = 0
        trdidx = 0
        for ln in lge:
            #la =  re.split('\t+', ln)
            la =  re.split('\t', ln)
            if len(hdr) == 0:
                hdr = la
                for i in range(len(hdr) ):
                    if hdr[i] == 'TRANS_SHARES':        trsidx = i
                    if hdr[i] == 'TRANS_PRICEPERSHARE': trpidx = i
                    if hdr[i] == 'TRANS_DATE':          trdidx = i
                continue
            if len(la) < trpidx+1: continue
            if la[trsidx] == '' or la[trpidx] == '': continue

            transdollars = float(la[trsidx]) * float(la[trpidx])
            if transdollars == 0.0: continue

            if transdollars not in prtransdict.keys():
                prtransdict[transdollars] = []
            # TRANS_DATE is in a weird format
            mton = { 
            'JAN' : '01', 'FEB' : '01', 'MAR' : '01', 'APR' : '01',
            'MAY' : '01', 'JUN' : '01', 'JUL' : '01', 'AUG' : '01',
            'SEP' : '01', 'OCT' : '01', 'NOV' : '01', 'DEC' : '01',
            }
            th = {}
            for i in range(len(hdr) ):
                if la[i] == '':
                    continue
                th[hdr[i]] = la[i]
                if hdr[i] == 'TRANS_DATE':
                     da = la[i].split('-')
                     # YYYY-MM-DD
                     th[hdr[i]] = '%s-%s-%s' % (da[2],mton[da[1]], da[0])
            if not re.match('(Common|Shares|Stock*)*', th['SECURITY_TITLE']):
                continue
            th['TRANSDOLLARS'] = transdollars
            prtransdict[transdollars].append(th)
        skl = sorted(prtransdict.keys(), reverse=True )
        for i in range(128):
            self.transtop.append(prtransdict[skl[i] ] )
        # get accession numbers for submissions
        for amta in self.transtop:
            for amt in amta:
                an = amt['ACCESSION_NUMBER']
                self.bigtransdict[an] = amt


    def form345submissions(self, fzpath, file):
        """ form345submissions(self, fzpath, file)

        get submission associated with largest transactions
        fzpath - form345 zipfile to search
        file  - name of file to search
        lt    - list of largest transactions
        """
        # find transaction associated with submission
        lge = self.form345zipfileiter(fzpath, file)
        hdr = []
        for ln in lge:
            la = re.split('\t', ln)
            if len(hdr) == 0:
                hdr = la
                continue
            an = la[0]
            if len(la[11]) == 0:
                continue
            if an in self.bigtransdict.keys():
                self.bigtransdict[an]['ISSUERTRADINGSYMBOL'] = la[11]

    def form345owners(self, fzpath, file):
        """ form345owners(fzpath, file)

        match owner name and cik to a transaction
        fzpath - full path name to the form345.zip file
        file   - name of the file holding tranaction name and cik
        """
        lge = self.form345zipfileiter(fzpath, file)
        hdr = []
        for ln in lge:
            la = re.split('\t', ln)
            if len(hdr) == 0:
                hdr = la
                continue
            an = la[0]
            if an in self.bigtransdict.keys():
                self.bigtransdict[an]['RPTOWNERCIK'] = la[1]
                self.bigtransdict[an]['RPTOWNERNAME'] = la[2]

    def form345name(self, yq):
        """ form345name()

        construct the name of the most recent SEC EDGAR insider trading
        data. It consists of data from forms 2-5, hence the name
        """
        if yq:
            try:
                ys, qs = yq.split('Q')
                year = int(ys)
                qtr = int(qs)
            except Exception as e:
                print('yq %s: %s' % (yq, e) )
        else:
            now = datetime.datetime.now()
            year = now.year
            qtr = None
            # assuming a quarter delay
            if now.month < 6:
                qtr  = 4
                year = year -1
            elif now.month < 9: qtr = 1
            else:               qtr = 2

        fznm = '%dq%d_form345.zip' % (year, qtr)
        return fznm

    def getform345(self, file, directory):
        """ getform345(directory)

        get the most recent form345.zip file from stlouisfed.org
        """
        url = '%s/%s' % (self.iturl, file)
        resp = self.query(url)
        ofn = os.path.join(directory, file)
        self.storequery(resp, ofn)

    def constructurlargs(self, args):
        """ constructurlargs(args)

        construct a url argument string from an array of k=v pairs
        """
        aa = []
        for k in args.keys():
            aa.append('&%s=%s' % (k, args[k]))
        aa[0] = aa[0].replace('&', '?')
        return ''.join(aa)

    def getgnewsatom(self):
        """ getgnewsatom()

        get the current news.google.com/atom file
        """
        uargs = self.constructurlargs(self.grssargs)
        url = '%s%s' % (self.gatomurl, uargs)
        resp = self.query(self.gatomurl)
        rstr = resp.read().decode('utf-8')
        return rstr

    def searchgnewsatom(self, rstr, term):
        """ searchgnewsatom(rstr, term)

        search a news.google.com/atom file for term
        XXX not finished
        rstr - a string containing atom data
        term - term to search in the atom data
        """
        xroot = ET.fromstring(rstr)
        for chld in xroot:
            adict = chld.attrib
            for k in adict.keys():
                print('%s: %s' % (k, adict[k]) )

    def processform345(self, fzpath):
        self.form345largesttrades(fzpath, 'NONDERIV_TRANS.tsv')
        self.form345submissions(fzpath, 'SUBMISSION.tsv')
        self.form345owners(fzpath, 'REPORTINGOWNER.tsv')

    def processtickers(self, insiderdb):
        up = self.threshold
        dwn = 1/up
        self.sdb.insiderdbconnect(insiderdb)
        tset = set()
        for ak in self.bigtransdict.keys():
            ticker = self.bigtransdict[ak]['ISSUERTRADINGSYMBOL'].lower()
            if not ticker:
                continue
            action = self.bigtransdict[ak]['TRANS_ACQUIRED_DISP_CD']
            if ticker not in tset:
                self.sdb.newtickertable(ticker)
                self.sdb.newinsidertable()
                rstr = self.sdb.getstooqtickerhistory(ticker)
                if len(rstr.split('\n') ) ==1:
                    print('stooq %s %s' % (ticker, rstr), file=sys.stderr)
                    rstr = self.sdb.getmarketwatchtickerhistory(ticker)
                    if len(rstr.split('\n') ) ==1:
                        print('marketwatch %s %s' % (ticker, rstr),
                              file=sys.stderr)
                        continue
                self.sdb.tickerinsertblob(ticker, rstr)
                tset.add(ticker)
            trdate = self.bigtransdict[ak]['TRANS_DATE']
            tres = self.sdb.selectndays(insiderdb, ticker, trdate,
                    self.interval)
            day0 = None
            for trd in tres:
                tlst = list(trd)
                for i in range(len(tlst) ):
                    tlst[i] = re.sub('[",]', '', tlst[i])
                trd = tuple(tlst)
                if not day0:
                    day0 = trd
                    continue
                if action == 'A':
                    if float(trd[2]) >= float(day0[2])*up or \
                       float(trd[4]) >= float(day0[4])*up:
                        cik = self.bigtransdict[ak]['RPTOWNERCIK']
                        owner = self.bigtransdict[ak]['RPTOWNERNAME']
                        dollars = self.bigtransdict[ak]['TRANSDOLLARS']
                        brds = "'%s','%s','%s','%s','%s','%s'" % (day0[0],
                             day0[1], day0[2], day0[3], day0[4], day0[5])
                        trds = "'%s','%s','%s','%s','%s','%s'" % (trd[0],
                             trd[1], trd[2], trd[3], trd[4], trd[5])
                        rec = "'%s','%s','%s','%s','%s',%s,%s" % (ak, cik,
                              owner, ticker, dollars, brds, trds)
                        self.sdb.insiderinsert(rec)
                        #print(rec)
                elif action =='D':
                    if float(trd[3]) <= float(day0[3])*dwn or \
                       float(trd[4]) <= float(day0[4])*dwn:
                        cik = self.bigtransdict[ak]['RPTOWNERCIK']
                        owner = self.bigtransdict[ak]['RPTOWNERNAME']
                        dollars = self.bigtransdict[ak]['TRANSDOLLARS']
                        brds = "'%s','%s','%s','%s','%s','%s'" % (day0[0],
                             day0[1], day0[2], day0[3], day0[4], day0[5])
                        trds = "'%s','%s','%s','%s','%s','%s'" % (trd[0],
                            trd[1], trd[2], trd[3], trd[4], trd[5])
                        rec = "'%s','%s','%s','%s','%s',%s,%s" % (ak, cik,
                              owner, ticker, dollars, brds, trds)
                        self.sdb.insiderinsert(rec)
                        #print(rec)

    def reportinsiders(self, fp):
        self.sdb.reporttable('insiders', fp)


def main():
    EIT = EDGARInsiderTrading()
    argp = argparse.ArgumentParser(prog='edgarinsidertrading',
              description='report possibly illegal insider trading')

    argp.add_argument("--yq",
        help="year quarter in form YYYYQ[1-4]")
    argp.add_argument("--threshold", type=int,
        help="stock price change threshold - 0-50")
    argp.add_argument("--interval", type=int,
        help="number of days to consider for price movements 1-14")

    argp.add_argument("--insiderdb", default=':memory:',
        help="full path to the sqlite3  database - default in memory")
    argp.add_argument("--directory", default='/tmp',
        help="directory to store the output")
    argp.add_argument("--file",
        help="csv file to store the output - default stdout")

    args = argp.parse_args()

    if args.threshold:
        EIT.setthreshold(args.threshold)
    if args.interval:
        EIT.setinterval(args.threshold)

    fznm = EIT.form345name(args.yq)
    fzpath = os.path.join(args.directory, fznm)
    EIT.getform345(fznm, args.directory)

    EIT.processform345(fzpath)
    EIT.processtickers(args.insiderdb)

    fp = sys.stdout
    if args.file:
        try:
            fp = open(args.file, 'w')
        except Exception as e:
            print('' % (), file=sys.stderr)
            sys.exit(1)
    EIT.reportinsiders(fp)

    #xml = EIT.getgnewsatom()
    #res = EIT.searchgnewsatom(xml, 'Nvidia')


if __name__ == '__main__':
    main()
