# Parse a stitching enhanced rspec

#----------------------------------------------------------------------
# Copyright (c) 2013 Raytheon BBN Technologies
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and/or hardware specification (the "Work") to
# deal in the Work without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Work, and to permit persons to whom the Work
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Work.
#
# THE WORK IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE WORK OR THE USE OR OTHER DEALINGS
# IN THE WORK.
#----------------------------------------------------------------------

import sys
import logging
from xml.dom.minidom import parseString, getDOMImplementation
from objects import *

# XML tag constants
RSPEC_TAG = 'rspec'
LINK_TAG = 'link'
STITCHING_TAG = 'stitching'
PATH_TAG = 'path'

# This should go away, its value is no longer used
LAST_UPDATE_TIME_TAG = "lastUpdateTime"

class RSpecParser:

    def __init__(self, logger=None):
        self.logger = logger if logger else logging.getLogger('stitch')
        # The dom tree after parsing
        self.dom = None

    def parse(self, data):
        self.dom = parseString(data)
        rspecs = self.dom.getElementsByTagName(RSPEC_TAG)
        if len(rspecs) != 1:
            raise Exception("Expected 1 rspec tag, got %d" % (len(rpsecs)))
        return self.parseRSpec(rspecs[0])

    def parseRSpec(self, rspec_element):
        if rspec_element.nodeName != RSPEC_TAG:
            msg = "parseRSpec got unexpected tag %s" % (rspec_element.tagName)
            raise Exception(msg)
        links = []
        stitching = None
        for child in rspec_element.childNodes:
            if child.nodeName == LINK_TAG:
                self.logger.debug("Parsing Link")
                link = Link.fromDOM(child)
                links.append(link)
            elif child.nodeName == STITCHING_TAG:
                self.logger.debug("Parsing Stitching")
                stitching = self.parseStitching(child)
        rspec = RSpec(stitching)
        rspec.links = links
        return rspec

    def parseStitching(self, stitching_element):
        last_update_time = stitching_element.getAttribute(LAST_UPDATE_TIME_TAG)
        paths = []
        for child in stitching_element.childNodes:
            if child.nodeName == PATH_TAG:
                path = Path.fromDOM(child)
                paths.append(path)
        stitching = Stitching(last_update_time, paths)
        return stitching

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print "Usage RspecParser <file.xml> [<out.xml>]"
        sys.exit()

    filename = sys.argv[1]
    print "FN = " + filename
    file = open(filename, 'r')
    data = file.read()
    file.close()
    parser = RSpecParser(verbose=True)
    rspec = parser.parse(data)
    print "== RSPEC =="
    print "\t== NODES =="
    print rspec.nodes
    print "\t== LINKS =="
    print rspec.links
    cnt = 1
    for node in rspec.nodes:
        print "\t\t== NODE %s ==" % (str(cnt))
        cnt +=1
        print node
        cnt2 = 1
        for interface in node.interfaces:
            print "\t\t\t== INTERFACE %s ==" % (str(cnt2))
            cnt2 +=1
            print interface
    cnt = 1
    for link in rspec.links:
        print "\t\t== LINK %s ==" % (str(cnt))
        cnt +=1
        print link
    print "\t== STITCHING == " 
    print rspec.stitching
    cnt = 1
    for hop in rspec.stitching.path.hops:
        print "\t\t== HOP %s ==" % (str(cnt))
        cnt +=1
        print hop

# Now convert back to XML and print out
    impl = getDOMImplementation()
    doc = impl.createDocument(None, 'rspec', None)
    root = doc.documentElement
    rspec.toXML(doc, root)
    if len(sys.argv) > 2:
        outf = open(sys.argv[2], "w")
        doc.writexml(outf)
        outf.close()
    else:
        print doc.toprettyxml()
