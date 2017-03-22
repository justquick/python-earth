import urllib
import xml
import time
from datetime import datetime

try:
    from SOAPpy import WSDL
except ImportError:
    raise ImportError, "Python Earth requires the SOAPpy library"

USER_AGENT = "Python Earth Library (http://launchpad.net/~python-earth/)"

def force_unicode(s):
    """It's very ugly, but it works
    If anybody has a better idea to turn '\u0026' into u'&' please let me know
    """
    exec 's = u"%s".encode("utf-8")' % s
    return s

class HTTPRequest(urllib.URLopener):
    
    """Same as URLopener, but with custom user-agent string"""
    
    def __init__(self):
        self.version = USER_AGENT
        urllib.URLopener.__init__(self)

class SoapClient(object):
    
    """Special class to make soap requests but handle response errors.
    
    If an error occurs, the request will be attempted two more times
    before finally raising an error.  This was created because of the
    sporadic instability of some SOAP API's.
    
    """
    
    def __init__(self, wsdl_file):
        self.client = WSDL.Proxy(wsdl_file)

    def __getattr__(self, name):
        def __call(*args, **kwargs):
            """Set up environment then let parent class handle call.

            Raises AttributeError is method name is not found."""

            if not self.client.methods.has_key(name):
                raise AttributeError, name
            callinfo = self.client.methods[name]
            self.client.soapproxy.proxy = \
                            WSDL.SOAPAddress(callinfo.location)
            self.client.soapproxy.namespace = callinfo.namespace
            self.client.soapproxy.soapaction = callinfo.soapAction
            for x in range(3):
                try:
                    return self.client.soapproxy.__getattr__(name)(
                                    *args, **kwargs)
                except xml.sax._exceptions.SAXParseException, e:
                    time.sleep(1)
                    if x == 2:
                        raise xml.sax._exceptions.SAXParseException, e
        return __call

class RequestError(Exception):
    """Error occured in HTTP Request"""
    pass

class ScrapeError(Exception):
    """Error occured in page scraping"""
    pass

def avg_for_the_day(data):
    """Retuns average values for each day in a list.

    Accepts a list of lists, each containing a datatime in position 0
    and a numerical (int or float) value in position 1.

    Returns a list of lists with a datetime in position 0 and a float
    in position 1.

    """
    new_list = []
    for entry in data:
        new_list.append([entry[0].date(), entry[1]])
    calc_dict = {}
    for entry in new_list:
        if not calc_dict.get(entry[0]):
            calc_dict[entry[0]] = entry[1]
        else:
            calc_dict[entry[0]] = round(((float(calc_dict[entry[0]]) + \
                                          float(entry[1])) / 2))
    return sorted(calc_dict.items())
