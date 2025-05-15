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
        self.verbose = False

        self.mn = {
            'JAN' : '1', 'FEB' : '2', 'MAR' : '3', 'APR' : '4',
            'MAY' : '5', 'JUN' : '6', 'JUL' : '7', 'AUG' : '8',
            'SEP' : '9', 'OCT' : '10', 'NOV' : '11', 'DEC' : '12'
        }
        # no longer used - all behind paywalls
        self.threshold = None
        self.interval = None

        # from https://www.sec.gov/dera/data/form-345
        self.itdslurl = 'https://www.sec.gov/dera/data/form-345'
        self.itlurl = 'https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets'

        self.iturl = 'https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets'

        self.submissions={}
        self.transactions={}
        self.owner={}

        self.transtop=[]
        self.sdb = db.InsiderDB()

        self.chunksize =4294967296 # 4M

    def setverbose(self):
        if self.verbose == False:
            self.verbose = True
        else: self.verbose = False

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
        if self.verbose:
            print('query: %s' % (url), file=sys.stderr)
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
        if self.verbose:
            print('storequery: %s' % (file), file=sys.stderr)
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

    def secdate2iso(self, sd):
        if '-' not in sd:
            return sd
        sda = sd.split('-')
        if not sda[1].isnumeric():
            sda[1] = self.mn[sda[1]]
        sda = [sda[2],sda[1],sda[0]]
        return ''.join(sda)

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

    def form345transactions(self, fzpath, file):
        """ form345transactions(fzpath, file)

        collect form345 data from file in fzpath
        fzpath - form345 zip file from fred.stlouisfed.org
        file  - file in the zip file to read
        """
        if self.verbose:
            fznm = os.path.basename(fzpath)
            print('getting trades from %s in %s' % (file, fznm), file=sys.stderr)
        lge = self.form345zipfileiter(fzpath, file)
        # dictionary of nonderivative transactions with dollar amount key
        prtransactions = {}
        hdr=[]
        lna=[]
        trsidx = 0
        trpidx = 0
        trdidx = 0
        for ln in lge:
            la =  re.split('\t', ln)
            # key on trade dollar amount
            if len(hdr) == 0:
                hdr = la
                for i in range(len(hdr) ):
                    if hdr[i] == 'TRANS_SHARES':        trsidx = i
                    if hdr[i] == 'TRANS_PRICEPERSHARE': trpidx = i
                continue

            if len(la) < len(hdr):
                print('trade len %s %d %d' % (la[0], len(hdr), len(la)), file=sys.stderr)
                continue
            if la[trsidx] == '' or la[trpidx] == '': continue

            th = {}
            for i in range(len(hdr) ):
                if '_FN' in hdr[i]:       # ignore footnotes
                    continue
                if 'DATE' in hdr[i]:      # convert to ISO format
                    la[i] = self.secdate2iso(la[i])
                th[hdr[i]] = la[i]
                if "'" in la[i]:
                    th[hdr[i]] = la[i].replace("'", "''")


            if not re.match('(Common|Shares|Stock*)*', th['SECURITY_TITLE']):
                continue

            transdollars = float(la[trsidx]) * float(la[trpidx])
            if transdollars == 0.0: continue

            if transdollars not in prtransactions.keys():
                prtransactions[transdollars] = []
            th['TRANSDOLLARS'] = transdollars
            prtransactions[transdollars].append(th)
        return prtransactions


    def form345submissions(self, fzpath, file):
        """ form345submissions(self, fzpath, file)

        get submission associated with largest transactions
        fzpath - form345 zipfile to search
        file  - name of file to search
        lt    - list of largest transactions
        """
        if self.verbose:
            fznm = os.path.basename(fzpath)
            print('getting submissions from %s in %s' % (file, fznm), file=sys.stderr)
        # find transaction associated with submission
        lge = self.form345zipfileiter(fzpath, file)
        hdr = []
        prsubmission={}
        for ln in lge:
            la = re.split('\t', ln)
            if len(hdr) == 0:
                hdr = la
                continue
            an = la[0]
            subm={}
            for i in range(len(hdr)):
                if 'DATE' in hdr[i] or hdr[i] == 'PERIOD_OF_REPORT':
                    la[i] = self.secdate2iso(la[i])
                subm[hdr[i]]=la[i]
                if "'" in la[i]:
                    subm[hdr[i]] = la[i].replace("'", "''")
            prsubmission[an]=subm
        return prsubmission

    def form345owners(self, fzpath, file):
        """ form345owners(fzpath, file)

        match owner name and cik to a transaction
        fzpath - full path name to the form345.zip file
        file   - name of the file holding tranaction name and cik
        """
        if self.verbose:
            fznm = os.path.basename(fzpath)
            print('getting submission owners from %s in %s' % (file, fznm), file=sys.stderr)
        lge = self.form345zipfileiter(fzpath, file)
        prowner={}
        hdr = []
        for ln in lge:
            la = re.split('\t', ln)
            if len(hdr) == 0:
                hdr = la
                continue
            an = la[0]
            ownr = {}
            for i in range(len(la)):
                if 'DATE' in hdr[i]:      # convert to ISO format
                    la[i] = self.secdate2iso(la[i])
                ownr[hdr[i]] = la[i]
                if "'" in la[i]:
                    ownr[hdr[i]] = la[i].replace("'", "''")
            prowner[an]=ownr
        return prowner

    def latestform345name(self, html):
        """ latestform345name(html)

        tease out url to latest form345 zip file 
        html - html fragment to parse
        """
        if '<html' not in html:
            html = '<html>%s</html>' % (html)

        class MyHTMLParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.src = None
                self.prev = None
                self.furl = None
            def handle_starttag(self, tag, attrs):
                if self.furl == None and tag == 'a' and self.prev == 'td':
                    for tpl in attrs:
                        if tpl[0] == 'href':
                            self.furl = '%s/%s' % ('https://www.sec.gov', tpl[1])
                self.prev = tag
            def handle_data(self, data):
                    # print('\thtml data: %s' % (data) )
                    self.src = data

        parser = MyHTMLParser()
        parser.feed(html)
        return parser.furl

    def form345name(self, yq):
        """ form345name()

        construct the name of the most recent SEC EDGAR insider trading
        data. It consists of data from forms 2-5, hence the name
        """
        fznm = None
        if yq:
            try:
                ys, qs = yq.split('Q')
                year = int(ys)
                qtr = int(qs)
                fznm = '%dq%d_form345.zip' % (year, qtr)
            except Exception as e:
                print('yq %s: %s' % (yq, e) )
        else:
            resp = self.query(self.itlurl)
            rstr = resp.read().decode('utf-8')
            fzurl = self.latestform345name(rstr)
            fznm = fzurl.split('/')[-1]


        return fznm

    def getform345(self, file, directory):
        """ getform345(directory)

        get the most recent form345.zip file from stlouisfed.org
        """
        if self.verbose:
            print('collecting %s' % (file), file=sys.stderr)
        ofn = os.path.join(directory, file)
        if os.path.exists(ofn):
            return
        url = '%s/%s' % (self.iturl, file)
        resp = self.query(url)
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

    def process345forms(self, fzpath):
        """ process345forms(fzpath)

        process form345.zip file for largest transactions
        fzpath - full path to the form345.zip file
        """
        trds = self.form345transactions(fzpath, 'NONDERIV_TRANS.tsv')
        self.transactions=trds
        subm = self.form345submissions(fzpath, 'SUBMISSION.tsv')
        self.submissions = subm
        ownr = self.form345owners(fzpath, 'REPORTINGOWNER.tsv')
        self.owner = ownr

    def processtransactions(self, insiderdb, sdate, edate):
        """ processtransactions(insiderdb)

        process transactions
        insiderdb - name of the insider database
        sdate     - first date
        edate     - last date
        """
        if self.verbose:
            print('checking history for big transactions', file=sys.stderr)
        self.sdb.dbconnect(insiderdb)
        self.sdb.newinsidertable()
        sdt = datetime.date.fromisoformat(sdate)
        edt = datetime.date.fromisoformat(edate)

        for amt in self.transactions.keys():
           tna = self.transactions[amt]
           for tn in tna:
               sub = self.submissions[tn['ACCESSION_NUMBER']]
               tn['FILING_DATE']         = sub['FILING_DATE']
               tn['NO_SECURITIES_OWNED'] = sub['NO_SECURITIES_OWNED']
               tn['DOCUMENT_TYPE']       = sub['DOCUMENT_TYPE']
               tn['ISSUERCIK']           = sub['ISSUERCIK']
               tn['ISSUERNAME']          = sub['ISSUERNAME']
               tn['ISSUERTRADINGSYMBOL'] = sub['ISSUERTRADINGSYMBOL']

               own = self.owner[tn['ACCESSION_NUMBER']]
               tn['RPTOWNERCIK']          = own['RPTOWNERCIK']
               tn['RPTOWNERNAME']         = own['RPTOWNERNAME']
               tn['RPTOWNER_RELATIONSHIP'] = own['RPTOWNER_RELATIONSHIP']
               tn['RPTOWNER_TITLE']        = own['RPTOWNER_TITLE']
               tn['RPTOWNER_TXT']        = own['RPTOWNER_TXT']
               tn['FILE_NUMBER']          = own['FILE_NUMBER']

               # print(tn)
               # print(tn.keys())
               rec = "'%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s'" % (tn['ACCESSION_NUMBER'],tn['NONDERIV_TRANS_SK'], tn['SECURITY_TITLE'], tn['TRANS_DATE'], tn['DEEMED_EXECUTION_DATE'], tn['TRANS_FORM_TYPE'], tn['TRANS_CODE'], tn['EQUITY_SWAP_INVOLVED'], tn['TRANS_TIMELINESS'], tn['TRANS_SHARES'], tn['TRANS_PRICEPERSHARE'], tn['TRANS_ACQUIRED_DISP_CD'], tn['SHRS_OWND_FOLWNG_TRANS'], tn['VALU_OWND_FOLWNG_TRANS'], tn['DIRECT_INDIRECT_OWNERSHIP'], tn['NATURE_OF_OWNERSHIP'], tn['TRANSDOLLARS'], tn['FILING_DATE'], tn['NO_SECURITIES_OWNED'], tn['DOCUMENT_TYPE'], tn['ISSUERCIK'], tn['ISSUERNAME'], tn['ISSUERTRADINGSYMBOL'], tn['RPTOWNERCIK'], tn['RPTOWNERNAME'], tn['RPTOWNER_RELATIONSHIP'], tn['RPTOWNER_TITLE'], tn['RPTOWNER_TXT'], tn['FILE_NUMBER'])
               self.sdb.insiderinsert(rec)

    def reportinsiders(self, fp):
        self.sdb.reporttable('insiders', fp)


def main():
    EIT = EDGARInsiderTrading()
    argp = argparse.ArgumentParser(prog='edgarinsidertrading',
              description='report possibly illegal insider trading')

    argp.add_argument("--yq", # default='2025Q2',
        help="year quarter in form YYYYQ[1-4]")


    # 2025/0511
    # 04/01/2025  04/09/2025
    argp.add_argument("--sdate",
        help="first day of trades to check")
    argp.add_argument("--edate",
        help="last day of trades to check")

    argp.add_argument("--insiderdb", default=':memory:',
        help="full path to the sqlite3  database - default in memory")
    argp.add_argument("--directory", default='/tmp',
        help="directory to store the output")
    argp.add_argument("--file",
        help="csv file to store the output - default stdout")

    argp.add_argument("--verbose", action='store_true', default=False,
        help="reveal some of the process")

    args = argp.parse_args()

    fznm = EIT.form345name(args.yq)
    fzpath = os.path.join(args.directory, fznm)
    EIT.getform345(fznm, args.directory)

    EIT.process345forms(fzpath)
    EIT.processtransactions(args.insiderdb, args.sdate, args.edate)

    fp = sys.stdout
    if args.file:
        try:
            fp = open(args.file, 'w')
        except Exception as e:
            print('' % (), file=sys.stderr)
            sys.exit(1)
    EIT.reportinsiders(fp)

if __name__ == '__main__':
    main()
