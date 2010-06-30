#!/usr/bin/python
import logging

#----------------------------------------------------------------------
# Copyright (c) 2010 Raytheon BBN Technologies
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

""" The OMNI client
    This client is a GENI API client that is capable to connecting
    to the supported control frameworks for slice creation and deletion.
    It is also able to parse and create standard RSPECs of all supported 
    control frameworks.
    
    The currently supported control frameworks are SFA and GCF.
"""

import optparse
import sys
import os
import pprint
import json
import dateutil.parser
from copy import copy
from geni.omni.xmlrpc.client import make_client
from geni.omni.omnispec.translation import rspec_to_omnispec, omnispec_to_rspec
from geni.omni.omnispec.omnispec import OmniSpec

class CallHandler(object):
    def __init__(self, framework, frame_config, omni_config):
        self.framework = framework    
        self.frame_config = frame_config
        self.omni_config = omni_config
        frame_config['cert'] = os.path.expanduser(frame_config['cert'])
        frame_config['key'] = os.path.expanduser(frame_config['key'])

    def _handle(self, args):
        if len(args) == 0:
            sys.exit('Insufficient number of arguments')
        
        call = args[0].lower()
        if call.startswith('_'):
            return
        getattr(self,call)(args[1:])

    def _getclients(self):
        clients = []
        for (urn, url) in self._listaggregates([]).items():
            client = make_client(url, self.frame_config['key'], self.frame_config['cert'])
            client.urn = urn
            client.url = url
            clients.append(client)
        return clients    
        
    def _listaggregates(self, args):
        aggs = self.framework.list_aggregates()
        return aggs

    def listresources(self, args):
        rspecs = {}
        options = {}
        
        options['geni_compressed'] = True;
        # Get the credential for this query
        if len(args) == 0:
            cred = self.framework.get_user_cred()
        else:
            name = args[0]
            urn = self.framework.slice_name_to_urn(name)
            cred = self.framework.get_slice_cred(urn)
            options['geni_slice_urn'] = urn

        
        # Connect to each available GENI AM to list their resources
        for client in self._getclients():
            try:
                rspec = client.ListResources([cred], options)
                rspecs[(client.urn, client.url)] = rspec
            except Exception, exc:
                print "Failed to get resources from %s (%s)" % (client.urn, client.url)
                logger = logging.getLogger('omni')
                logger.debug(str(exc))
            
        # Convert the rspecs to omnispecs
        omnispecs = {}
        for ((urn,url), rspec) in rspecs.items():                        
            omnispecs[url] = rspec_to_omnispec(urn,rspec)
                        
        jspecs = json.dumps(omnispecs, indent=4)
        print jspecs
        return omnispecs
    
    
    def createsliver(self, args):
        name = args[0]
        urn = self.framework.slice_name_to_urn(name)
        slice_cred = self.framework.get_slice_cred(urn)
        
        # Load up the user's edited omnispec
        specfile = args[1]
        jspecs = json.loads(file(specfile,'r').read())
        omnispecs = {}
        for url, spec_dict in jspecs.items():
            omnispecs[url] = OmniSpec('','',dictionary=spec_dict)
        
        
        # Copy the user config and read the keys from the files into the structure
        slice_users = copy(self.omni_config['slice_users'])
        for user in slice_users:
            newkeys = []
            for f in user['keys']:
                newkeys.append(file(os.path.expanduser(f)).read())
            user['keys'] = newkeys
        
        # Anything we need to allocate?
        for (url, ospec) in omnispecs.items():
            allocate = False
            for (_, r) in ospec.get_resources().items():
                if r.get_allocate():
                    allocate = True
                    break
                
            # Okay, send a message to the AM this resource came from
            if allocate:
                try:
                    client = make_client(url, self.frame_config['key'], self.frame_config['cert'])
                    rspec = omnispec_to_rspec(ospec, True)
                    client.CreateSliver(urn, [slice_cred], rspec, slice_users)
                except Exception, exc:
                    print "Unable to allocate from: %s" % (url)
                    logger = logging.getLogger('omni')
                    logger.debug(str(exc))

    def deletesliver(self, args):
        name = args[0]
        urn = self.framework.slice_name_to_urn(name)
        slice_cred = self.framework.get_slice_cred(urn)
        # Connect to each available GENI AM 
        for client in self._getclients():
            try:
                client.DeleteSliver(urn, [slice_cred])
            except Exception, exc:
                print "Failed to delete sliver on %s (%s)" %(client.urn, client.url)
                logger = logging.getLogger('omni')
                logger.debug(str(exc))
            
    def renewsliver(self, args):
        name = args[0]
        urn = self.framework.slice_name_to_urn(name)
        slice_cred = self.framework.get_slice_cred(urn)
        time = dateutil.parser.parse(args[1])
        print time        

        for client in self._getclients():
            try:
                client.RenewSliver(urn, [slice_cred], time.isoformat())
            except:
                print "Failed to renew sliver on %s" % client.urn
    
    def sliverstatus(self, args):
        name = args[0]
        urn = self.framework.slice_name_to_urn(name)
        slice_cred = self.framework.get_slice_cred(urn)
        for client in self._getclients():
            try:
                status = client.SliverStatus(urn, [slice_cred])
                print "%s (%s):" % (client.urn, client.url)
                pprint.pprint(status)
            except Exception, exc:
                print "Failed to retrieve status for: %s" % client.urn
                logger = logging.getLogger('omni')
                logger.debug(str(exc))
                
    def shutdown(self, args):
        name = args[0]
        urn = self.framework.slice_name_to_urn(name)
        slice_cred = self.framework.get_slice_cred(urn)
        for client in self._getclients():
            try:
                client.Shutdown(urn, [slice_cred])
            except:
                print "Failed to shutdown: %s at %s" % (client.urn, client.url)
    
    def getversion(self, args):
        for client in self._getclients():
            try:
                print "%s (%s) %s" % (client.urn, client.url, client.GetVersion())
            except:
                print "Failed to get version information for %s at (%s)" % (client.urn, client.url)
                                
    def createslice(self, args):
        name = args[0]
        urn = self.framework.slice_name_to_urn(name)
        self.framework.create_slice(urn)
        
    def deleteslice(self, args):
        name = args[0]
        urn = self.framework.slice_name_to_urn(name)
        self.framework.delete_slice(urn)

    def getslicecred(self, args):
        name = args[0]
        urn = self.framework.slice_name_to_urn(name)
        cred = self.framework.get_slice_cred(urn)
        print cred


def parse_args(argv):
    parser = optparse.OptionParser()
    parser.add_option("-c", "--configfile", default="~/.omni/omni_config",
                      help="config file name", metavar="FILE")
    parser.add_option("-f", "--framework", default="",
                      help="control framework to use for creation/deletion of slices")
    parser.add_option("--debug", action="store_true", default=False,
                       help="enable debugging output")
    return parser.parse_args()

def configure_logging(opts):
    level = logging.INFO
    logging.basicConfig(level=level)
    if opts.debug:
        level = logging.DEBUG
    logger = logging.getLogger("omni")
    logger.setLevel(level)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    opts, args = parse_args(argv)
    configure_logging(opts)

    logger = logging.getLogger('omni')
    # Load up the JSON formatted config file
    filename = os.path.expanduser(opts.configfile)
    logger.debug("Loading config file %s", filename)
    config = json.loads(file(filename, 'r').read())
        
    if not opts.framework:
        opts.framework = config['omni']['default_cf']
        
    # Dynamically load the selected control framework
    cf = opts.framework.lower()
    framework_mod = __import__('geni.omni.frameworks.framework_%s' % cf, fromlist=['geni.omni.frameworks'])
    framework = framework_mod.Framework(config[cf])
        
    # Process the user's call
    handler = CallHandler(framework, config[cf], config['omni'])    
    handler._handle(args)
    
    
        

if __name__ == "__main__":
    sys.exit(main())
