import re
import os
from urllib import urlopen
from earth.core.config import conf
from earth.core import RequestError
from datetime import datetime
from dateutil.tz import tzutc

RADAR_TYPES = ('N0R', 'N0S', 'N0V', 'N1P', 'NCR', 'NTP', 'N0Z')
URL = "http://radar.weather.gov/ridge/RadarImg/%s"
    
def get_radar_report(station_id, radar_id='N0R'):
    data = {}
    url = URL % ("%s/%s_%s_0.gfw" % (radar_id.upper(), station_id.upper(), radar_id.upper()))
    try:
        data['world_file'] = map(lambda x: float(x.strip()),urlopen(url).readlines())
    except IOError, e:
        conf.log('warning','RequestError: %s'%e)
        raise RequestError, e
    url = URL % ("%s/%s/" % (radar_id.upper(), station_id.upper()))
    try:
        domreader = urlopen(url)
    except IOError, e:
        conf.log('warning','RequestError: %s'%e)
        raise RequestError, e
    data['file_list'] = []
    r = re.compile(r'.*<img src="/icons/image2.gif".*<a href="(.*?)">.*')
    for x in domreader:
        search = r.search(x)
        if search:
            filename = search.groups()[0]
            date = filename.split('_')[1]
            time = filename.split('_')[2]
            data['file_list'].append({
                'image': url+search.groups()[0],
                'datetime': datetime(int(date[:4]), int(date[4:6]), int(date[6:]),
                                    int(time[:2]), int(time[2:]), tzinfo=tzutc())
            })
    return data

class RadarStation(dict):
    def __init__(self, station_id, radar_id):
        assert radar_id in RADAR_TYPES, 'Unknown radar type %s'%radar_id
        data = {'station_id':station_id,'radar_id':radar_id}
        if conf.resource_exists('radar','%s.%s'%(station_id,radar_id)):
            data.update(conf.load('radar','%s.%s'%(station_id,radar_id)))
        else:
            data.update(get_radar_report(station_id, radar_id))
            conf.dump('radar', dict(data), '%s.%s'%(station_id,radar_id))
        dict.__init__(self, data)
                      
def test(unit):
    for rtype in RADAR_TYPES:
        station = RadarStation('lwx',rtype)
        for i in station['file_list']:
            unit.assert_(i['image'].endswith('.gif'))
            unit.assertEqual(type(i['datetime']), type(datetime.now()))
        unit.assert_(station['station_id'] and station['radar_id'])
