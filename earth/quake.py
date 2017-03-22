from xml.parsers.expat import ParserCreate
from datetime import datetime
from urllib import urlretrieve
from earth.core.config import conf
from earth.geo import Location
import os
import gzip

URL = 'http://earthquake.usgs.gov/eqcenter/catalogs/merged_catalog.xml.gz'
URI = os.path.join(conf.data_root, 'earthquake', 'merged_catalog.xml')

conf.mkdirs('earthquake')

def fetch():
    f = open(URI,'w')
    f.write(gzip.open(urlretrieve(URL)[0],'rb').read())
    f.close()
    
def get_quake_events():
    data = []
    def start(name, attrs):
        if name == 'event':
            data.append(attrs)
        elif name == 'param':
            data[-1][attrs['name']] = attrs['value']
    parser = ParserCreate()
    parser.StartElementHandler = start
    if not os.path.isfile(URI):
        fetch()
    parser.Parse(open(URI).read(), 1)
    return data

def parse():
    for event in get_quake_events():
        event = Event(event)
        conf.dump('earthquake', dict(event), event.id)
        yield event

def cron():
    fetch()
    [x for x in parse()]

class Event(dict):
    def __init__(self, data):
        dict.__init__(self, data)
    
    @property
    def time_stamp(self):
        return self.get('time-stamp',None)
    @property
    def network_code(self):
        return self.get('network-code',None)
    @property
    def id(self):
        return self.get('id',None)
    @property
    def version(self):
        return self.get('version',None)
    @property
    def datetime(self):
        floatsecs = float(self.get('second',0.0))
        return datetime(
            int(self.get('year')),
            int(self.get('month')),
            int(self.get('day')),
            int(self.get('hour',0)),
            int(self.get('minute',0)),
            int(floatsecs),
            int((floatsecs - int(floatsecs)) * 10**6)
        )
    @property
    def location(self):
        return (
            float(self.get('latitude',None)),
            float(self.get('longitude',None))
        )
    @property
    def geo(self):
        if not self.location == (None,None):
            return Location(*self.location)
    @property
    def magnitude(self):
        return float(self.get('magnitude',None))
    
    def __repr__(self):
        return u'<Event %s>'%self.id

def events(force_parse=False):
    files = [os.path.splitext(file)[0] for file in \
             os.listdir(os.path.join(conf.data_root,'earthquake')) \
            if file.endswith('.obj')]
    if not files or force_parse:
        for event in parse():
            yield event
    else:
        for file in files:
            yield Event(conf.load('earthquake',file))

def test(unit):
    for event in events(True):
        unit.assertEqual(len(event.location), 2)
        unit.assertNotEqual(event.location, (None,None))
        unit.assertNotEqual(event.magnitude, None)
        unit.assertNotEqual(event.network_code, None)
        unit.assertNotEqual(event.version, None)
        unit.assertNotEqual(event.id, None)
        unit.assertNotEqual(dict(event), {})
