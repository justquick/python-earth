from urllib import urlopen, quote_plus, urlencode
from earth.core.config import conf
from earth.core import force_unicode
import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
    
URL = 'http://maps.google.com/maps/geo?'
URI_ROOT = os.path.join(conf.data_root,'geo')
ACCURACIES = {
    0:'Unknown accuracy.',
    1:'Country level accuracy.',
    2:'Region (state, province, prefecture, etc.) level accuracy.',
    3:'Sub-region (county, municipality, etc.) level accuracy.',
    4:'Town (city, village) level accuracy.',
    5:'Post code (zip code) level accuracy.',
    6:'Street level accuracy.',
    7:'Intersection level accuracy.',
    8:'Address level accuracy.',
    9:'Premise (building name, property name, shopping center, etc.) level accuracy.',
}

conf.mkdirs('geo')

def geocode(query):
    #http://code.google.com/apis/maps/documentation/geocoding/index.html
    params = {
        'sensor': conf.get('geo','sensor','false'),
        'output': 'json',
        'oe': 'utf8',
        'key': conf.api_key,
        'q': query,
    }
    gl = conf.get('geo','country')
    if len(gl):
        params['gl'] = gl
    ll = conf.get('geo','lat_lon')
    if len(ll):
        params['ll'] = ll
    spn = conf.get('geo','span')
    if len(spn):
        params['spn'] = spn
    params = urlencode(params)
    try:
        data = eval(urlopen(URL + params).read(), {}, {}) 
    except:
        raise TypeError('Bad data from google')
    best,result = -1,{}
    for place in data.get('Placemark',()):
        accuracy =  place['AddressDetails']['Accuracy'] 
        if accuracy > best:
            best,result = accuracy,place
        del accuracy,place
    del data,best
    return result

class Location(dict):
    def __init__(self, *args, **kwargs):
        sep = '+'
        if not args:
            raise TypeError('You must declare a location to geocode')
        if isinstance(args[0],float):
            sep = ','
        query = sep.join(map(lambda x: quote_plus(str(x)), args))
        live = kwargs.pop('live',None)
        if conf.resource_exists('geo',query) and not live:
            dict.__init__(self, conf.load('geo',query))
        else:
            data = geocode(query, **kwargs)
            conf.dump('geo', data, query)
            dict.__init__(self, data)
            del data
        del live

    @property
    def _AddressDetail(self):
        return self.get('AddressDetails',{})
    @property
    def _Country(self):
        return self._AddressDetail.get('Country',{})
    @property
    def _AdminArea(self):
        return self._Country.get('AdministrativeArea',{})
    @property
    def _Locality(self):
        return self._AdminArea.get('Locality',{})
            

    @property
    def address(self):
        return force_unicode(self.get('address',''))
    @property
    def accuracy(self):
        return int(self._AddressDetail.get('Accuracy',0))
    @property
    def accuracy_text(self):
        return ACCURACIES[self.accuracy]
    @property
    def country(self):
        return force_unicode(self._Country.get('CountryName',None))
    @property
    def country_code(self):
        return force_unicode(self._Country.get('CountryNameCode',None))
    @property
    def state(self):
        return self._AdminArea.get('AdministrativeAreaName',None)
    @property
    def locality(self):
        return self._Locality.get('LocalityName',None)
    @property
    def postal_code(self):
        return self._Locality.get('PostalCode',{}).get('PostalCodeNumber',None)
    @property
    def thoroughfare(self):        
        return force_unicode(self._Locality.get('Thoroughfare',{}).get('ThoroughfareName',None))
    @property
    def point(self):
        data = self.get('Point',{}).get('coordinates',[])
        if data:
            return data[1],data[0]
        return None,None
    @property
    def lat_lon_box(self):
        data = self.get('ExtendedData',{}).get('LatLonBox',{})
        return  data.get('north',None),data.get('south',None),\
            data.get('east',None),data.get('west',None)
        
    def __repr__(self):
        return self.address

def loc2str(*args,**kwargs):
    str = StringIO()
    location = Location(*args,**kwargs)
    print >>str, location
    print >>str, location.point
    print >>str, location.lat_lon_box
    print >>str, location.accuracy
    print >>str, location.accuracy_text
    print >>str, location.country
    print >>str, location.country_code
    print >>str, location.locality
    print >>str, location.state
    print >>str, location.postal_code
    print >>str, location.thoroughfare
    return str.getvalue()


def test(unit):
    for loc,text in [
((0.0, 0.0), '\n(None, None)\n(None, None, None, None)\n0\nUnknown accuracy.\nNone\nNone\nNone\nNone\nNone\nNone\n'),
(('Albany', 'NY'), 'Albany, NY, USA\n(42.651724999999999, -73.755093000000002)\n(42.722285999999997, 42.613791999999997, -73.722995999999995, -73.898009999999999)\n4\nTown (city, village) level accuracy.\nUSA\nUS\nAlbany\nNY\nNone\nNone\n'),
((14.48007, 8.9648439999999994), 'Zinder, Niger\n(15.1718881, 10.2600125)\n(17.488399999999999, 12.803599999999999, 12.0115, 7.2564000000000002)\n3\nSub-region (county, municipality, etc.) level accuracy.\nNiger\nNE\nNone\nNone\nNone\nNone\n'),
(('1600', 'Amphitheatre Parkway', 'Mountain View', 'CA', '94043'), '1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA\n(37.421971999999997, -122.084143)\n(37.425119600000002, 37.418824399999998, -122.08099540000001, -122.0872906)\n8\nAddress level accuracy.\nUSA\nUS\nMountain View\nCA\n94043\n1600 Amphitheatre Pkwy\n'),
(('State St, Troy, NY',), '2 2nd St, Troy, NY 12180, USA\n(42.731821400000001, -73.691436100000004)\n(42.734969, 42.728673800000003, -73.688288499999999, -73.694583699999995)\n8\nAddress level accuracy.\nUSA\nUS\nTroy\nNY\n12180\n2 2nd St\n'),
(('2nd st & State St, Troy, NY',), '26 Frear Alley, Troy, NY 12180, USA\n(42.7220905, -73.694215999999997)\n(42.725238099999999, 42.718942900000002, -73.691068400000006, -73.697363600000003)\n8\nAddress level accuracy.\nUSA\nUS\nTroy\nNY\n12180\n26 Frear Alley\n'),
(('7 State St, Troy, NY',), '7 2nd St, Troy, NY 12180, USA\n(42.731632300000001, -73.691478599999996)\n(42.734779899999999, 42.728484700000003, -73.688331000000005, -73.694626200000002)\n8\nAddress level accuracy.\nUSA\nUS\nTroy\nNY\n12180\n7 2nd St\n'),
    ]:
        #print '(%r, %r),'%(loc,loc2str(*loc,**{'live':True}))
        unit.assertEquals(text,loc2str(*loc,**{'live':True}))


if __name__ == '__main__':
    import cProfile
    import pstats
    locations = ('1600 Amphitheatre Parkway Mountain View','washington dc','moscow russia','new england usa','deep creek lake md','baltimore md','queensland australia','alaska','canada')
    def run():
        for loc in locations:
            geocode(loc)
    cProfile.runctx('run()',{'run':run},{},'test.prof')
    p = pstats.Stats('test.prof')
    p.sort_stats('time', 'cum').print_stats('.py')