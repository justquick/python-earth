from urllib import urlencode
import urllib2
from earth.geo import Location
from earth.core.config import conf
from earth.core import RequestError
from datetime import date,time,datetime
import os,sys
import re

REPORT_TYPES = (
    (0, 'sunrise-sunset' ),
    (1, 'moonrise-moonset'),
    (2, 'civil-twilight'),
    (3, 'nautical-twilight'),
    (4, 'astronomical-twilight'),
)

URL = 'http://aa.usno.navy.mil/cgi-bin/aa_rstablew.pl'
NOW = datetime.now()

def reports(query):
    for id,type in REPORT_TYPES:
        yield SunReport(query,report_type=id)

def get_sun_report(**kwargs):
    """
    Basic function for fetching sun report data
    """
    vars = {'FFX' : 1,  'ZZZ' : 'END',
            'xxy' : kwargs['year'], 'type' : kwargs['report_type']}
    if 'location' in kwargs:
        if kwargs['location'].state:
            vars['st'] = kwargs['location'].state.upper()
        if kwargs['location'].locality:
            vars['place'] = kwargs['location'].locality
    else:
        vars['st'] = kwargs.pop('st','')
        vars['place'] = kwargs.pop('place','')
    vars = urlencode(vars)
    try:
        lines = urllib2.urlopen(urllib2.Request(URL, vars)).readlines()
    except IOError, e:
        conf.log('warning','RequestError: %s'%e)
        raise RequestError, e

    data = {}
    def liner(line):
        while 1:
            if not line: break
            part = line[:9].replace('    ','None').replace(' ','')
            rise,set = part[:4],part[4:]
            if rise == 'None' or not rise: rise = None
            else: rise = time(int(rise[:2]),int(rise[2:]))
            if set == 'None' or not set: set = None
            else: set = time(int(set[:2]),int(set[2:]))
            yield rise,set
            line = line[11:]
    for l in lines:
        l = l.strip()
        if not l: continue
        try:
            day = int(l[:2])
        except ValueError:
            continue
        for i,(r,s) in enumerate(liner(l[2:].strip())):
            try:
                data[( date(int(kwargs['year']), i, int(day)) )] = ( r, s )
            except ValueError:
                continue
    return data

class SunReport(dict):
    def __init__(self, query, **kwargs):
        self.location = Location(query)
        self.year = kwargs.get('year',NOW.year)
        self.report_type = kwargs.get('report_type',0)
        assert self.report_type in range(5), 'Invalid report type'
        self.id = '%s.%s.%s'%(self.location,self.year,self.report_type_text)
        if conf.resource_exists('sun',self.id):
            dict.__init__(self, conf.load('sun',self.id))
        else:
            data = get_sun_report(year=self.year,location=self.location,**kwargs)
            conf.dump('sun', data, self.id)
            dict.__init__(self, data)
    @property
    def report_type_text(self):
        return REPORT_TYPES[self.report_type][1]


def test(unit):
    for report in reports('st louis, mo'):
        unit.assertEqual(len(report), 334)
        for day,(rise,set) in report.items():
            unit.assert_(type(rise) in (type(None),type(NOW.time())))
            unit.assert_(type(set) in (type(None),type(NOW.time())))
            unit.assertEqual(type(day), type(NOW.date()))
