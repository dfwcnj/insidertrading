

import re
import urllib.request

from html.parser import HTMLParser
from xml.etree import ElementTree as ET

class _RSS():

    def __init__(self):
        self.rdict={}
        self.rdict['items'] = []

    def channel(self, root):
        for child in root:
            taga = re.split('[{}]', child.tag)
            tag = taga[2]
            if tag == 'item':
                ih = self.item(child)
                self.rdict['items'].append(ih)

    def item(self, root):
        ih = {}
        for child in root:
            taga = re.split('[{}]', child.tag)
            tag = taga[2]
            if tag == 'media:content':
                continue
            else:
                ih[tag] = child.text
        return ih

    def feed(self, root):
        xroot = ET.fromstring(rstr)
        for child in xroot:
            taga = re.split('[{}]', child.tag)
            tag = taga[2]
            if tag == 'channel':
                self.channel(child)
            else: rdict[tag] = child.text


class _GNAtom():

    def __init__(self):
        self.adict = {}
        self.adict['entries'] = []

    def content(self, htmlfrag):
        html = htmlfrag
        if 'html' not in htmlfrag:
           html = '<html>%s</html>' % (htmlfrag)
        class MyHTMLParser(HTMLParser):
            def __init__(self):
                    super().__init__()
                    self.dicta = []
                    self.src = None

            def handle_starttag(self, tag, attrs):
                if tag == 'a':
                    for tpl in attrs:
                        if tpl[0] == 'href':
                            d={}
                            if hasattr(self, 'src'):
                                #print("\t<a> '%s','%s'" % (self.src, tpl[1]) )
                                d['data'] = self.src
                                d['href'] = tpl[1]
                            else:
                                #print('\thtml %s' % (tpl[1]) )
                                d['data'] = 'entry'
                                d['href'] = tpl[1]
                            self.dicta.append(d)
            def handle_data(self, data):
                    #print('\thtml data: %s' % (data) )
                    self.src = data
        parser = MyHTMLParser()
        parser.feed(html)
        return parser.dicta

    def entry(self, root):
        ea = []
        for child in root:
            taga = re.split('[{}]', child.tag)
            tag = taga[2]
            eh = {}
            if tag == 'content':
                eh['content'] = []
                dicta = self.content(child.text)
                eh['content'] = dicta
            else:
                eh[tag] = child.text
            ea.append(eh)
        return ea

    def feed(self, xmlstr):
        xroot = ET.fromstring(rstr)
        for child in xroot:
            taga = re.split('[{}]', child.tag)
            tag = taga[2]
            if tag == 'entry':
                stories = self.entry(child)
                self.adict['entries'].append(stories)
            else:
                self.adict[tag] = child.text
        return self.adict


def main():

    gurl = 'https://news.google.com/atom?hl=en-US&gl=US&ceid=US:en'
    req = urllib.request.Request(gurl)
    resp = urllib.request.urlopen(req)
    rstr = resp.read().decode('utf-8')
    gna = _GNAtom()
    fdict = gna.feed(rstr)
    print(fdict)

    mpurl = 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml'
    req = urllib.request.Request(mpurl)
    resp = urllib.request.urlopen(req)
    rstr = resp.read().decode('utf-8')
    mpr = _RSS()
    rdict = mpr.feed(rstr)
    print(rdict)

if __name__ == '__main__':
    main()


