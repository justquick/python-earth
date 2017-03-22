import os,sys
import zipfile
from xml.parsers.expat import ParserCreate
from datetime import datetime
from urllib import urlretrieve
from earth.core.config import conf
from earth.geo import Location
    
URL = 'http://www.weather.gov/data/current_obs/all_xml.zip'
URI = os.path.join(conf.data_root, 'observations', 'all_xml.zip')

conf.mkdirs('observations')

def fetch():
    urlretrieve(URL,URI)
    
def parse():
    for station in get_weather_observations():
        station = Station(station)
        conf.dump('observations',dict(station),station.id)
        yield station

def cron():
    fetch()
    [x for x in parse()]

def get_weather_observations():
    vs = {'tagdata':{},'tag':None,'data':[]}
    
    def start(tag, attrs):
        if not tag == 'image':
            vs['tag'] = tag.lower()
            vs['tagdata'][vs['tag']] = None
    
    def dodata(text):
        text = text.strip()
        if vs['tag'] and text:
            if text in ('None','NA') or not text:
                del vs['tagdata'][vs['tag']]
            else:
                try:
                    vs['tagdata'][vs['tag']] = int(text)
                except ValueError:
                    try:
                        vs['tagdata'][vs['tag']] = float(text)
                    except ValueError:
                        vs['tagdata'][vs['tag']] = str(text)
                        
    def feed(text):
        vs['tagdata'],vs['tag'] = {},None
        if text:
            parser = ParserCreate()
            parser.StartElementHandler = start
            parser.CharacterDataHandler = dodata
            parser.Parse(text, 1)
            vs['data'].append(Station(vs['tagdata']))
            
    if not os.path.isfile(URI):
        fetch()
        
    zfile = zipfile.ZipFile(URI,'r')
    for name in zfile.namelist():
        if name.endswith('.xml') and not name.endswith('index.xml'):
            feed(zfile.read(name).strip())

    return vs['data']

        

        


class Station(dict):
    def __init__(self, data):
        if isinstance(data, basestring) and conf.resource_exists('observations',data):
            dict.__init__(self, conf.load('observations',data))
        else:
            dict.__init__(self, data)
        
    @property
    def datetime(self):
        if 'observation_time_rfc822' in self \
            and self['observation_time_rfc822']:
            return datetime.strptime(
                ' '.join(self['observation_time_rfc822'].split(' ')[:-2]),
                '%a, %d %b %Y %H:%M:%S'
            )
        elif 'observation_time' in self:
            return datetime.strptime(
                '%s %s' % (self['observation_time'], datetime.now().year),
                'Last Updated on %b %d, %H:%M %p %Z %Y'
            )
    @property
    def icon(self):
        return '%s%s' % (
            self.get('icon_url_base',''),
            self.get('icon_url_name','')
        )
    @property
    def point(self):
        return self.get('latitude',None),self.get('longitude',None)
    @property
    def location(self):
        if 'location' in self and self['location']:
            if self['location'].find(' - ')>-1:
                return self['location'].split(' - ')[1]
            return self['location']
        elif 'station_name' in self and self['station_name']:
            return self['station_name']
    @property
    def geo(self):
        if self.point:
            return Location(*self.point,**{'live':True})
        if self.location:
            return Location(self.location,**{'live':True})
    @property
    def id(self):
        return self.get('station_id',None)

    def __repr__(self):
        return '<Station %s>'%self.id

def stations(force_parse=False):
    files = []
    if os.path.isdir(os.path.join(conf.data_root, 'observations')):
        files = [os.path.splitext(file)[0] for file in \
            os.listdir(os.path.join(conf.data_root, 'observations')) \
            if file.endswith('.obj')]
    if not files or force_parse:
        for station in parse():
            yield station
    else:
        for file in files:
            yield Station(conf.load('observations',file))
    
def location2station(location):
    """
    Translate full location into Station tuple by closest match
    Locations can be in any Google friendly form like
    "State St, Troy, NY", "2nd st & State St, Troy, NY" & "7 State St, Troy, NY"
    """
    point = Location(location).point
    best,result = 99999999,None
    for station in stations():
        tpoint = station.point
        distance = ((tpoint[0]-point[0])**2 + (tpoint[1]-point[1])**2)**.5
        if distance < best:
            best,result = distance,station
    return result

def test(unit):
    for station in stations(True):
        unit.assertNotEqual(station.icon, '')
        unit.assertNotEqual(station.point, (None,None))
        unit.assertNotEqual(dict(station), {})

