import re
import os

from earth.core import HTTPRequest, RequestError, ScrapeError
from urllib import urlencode
from earth.core.config import conf
from earth.geo import Location


def get_uv_index(zipcode='', city_name='', state_code=''):
    """Returns ultra violet index for a given city, state, or zipcode."""
    if not zipcode and not (city_name and state_code):
        raise TypeError('Pass a zipcode or a city and state')
    url = 'http://oaspub.epa.gov/enviro/uv_search?'+ urlencode(
        {'zipcode': zipcode,
         'city_name': city_name,
         'state_code': state_code})
    try:
        data = HTTPRequest().open(url).read()
    except IOError, e:
        conf.log('warning','RequestError: %s'%e)
        raise RequestError(e)
    match = re.search(r'alt="UVI (\d+)"', data)
    if match:
        return int(match.groups()[0])
    raise ScrapeError('Screen scrape failed: %s' % url)


class UV(object):
    def __init__(self, query):
        if conf.resource_exists('uv',query):
            self.value = conf.load('uv',query)
        else:
            loc = Location(query)
            self.value =  get_uv_index(**{
                'zipcode': loc.postal_code,
                'city_name': loc.locality,
                'state_code': loc.state
            })
            conf.dump('uv',self.value,query)
            
    def __repr__(self):
        return str(self.value)
        
def test(unit):
    unit.assert_('%d'%UV('albany, ny').value)
