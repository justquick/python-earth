import re
import os
import time
from urllib import urlencode
from earth.core.config import conf
from datetime import datetime, timedelta
try:
    from lxml import objectify
except ImportError:
    raise ImportError, "Missing dependency: lxml"

from earth.core.iso8601 import parse_date as xml_time_parse
from earth.core import HTTPRequest, RequestError, ScrapeError

def get_cap_alert(region):
    url = 'http://www.weather.gov/alerts/%s.cap' % region
    try:
        xmldom = objectify.fromstring(HTTPRequest().open(url).read())
    except IOError, e:
        conf.log('warning','RequestError: %s'%e)
        raise RequestError, e
    area_re = re.compile(r'(.+) \((\D+)\)')
    sent = xmldom.sent.text
    sent_time,sent_tz = sent[:-6],sent[-6:].replace(':','')
    data = {'identifier': xmldom.identifier.text,
            'sender': xmldom.sender.text,
            'sent': xml_time_parse(sent_time + sent_tz),
            'status': xmldom.status.text,
            'msgType': xmldom.msgType.text,
            'scope': xmldom.scope.text,
            'note': xmldom.note.text.strip(),
            'references': xmldom.references.text,
            'info_list': {}}
    for info in xmldom.info:
        try:
            info.area
        except AttributeError:
            continue
        county = area_re.search(info.area.areaDesc.text.strip()).groups()[0]
        state = area_re.search(info.area.areaDesc.text.strip()).groups()[1]
        data['info_list'].update({
            'category': info.category.text,
            'event': info.event.text,
            'urgency': info.urgency.text,
            'severity': info.severity.text,
            'certainty': info.certainty.text,
            'effective': xml_time_parse(info.effective.text  + '+0000'),
            'expires': xml_time_parse(info.expires.text + '+0000'),
            'headline': info.headline.text,
            'description': info.description.text.strip(),
            'web': info.web.text.strip(),
            'area': {'geocode': info.area.geocode.text,
                     'areaDesc': info.area.areaDesc.text,
                     'state': state,
                     'county': county
                     }
            })
    return data

class CapAlert(dict):
    def __init__(self, region):
        if conf.resource_exists('alerts','%s.cap'%region):
            dict.__init__(self, conf.load('alerts','%s.cap'%region))
        else:
            dict.__init__(self, get_cap_alert(region))
            conf.dump('alerts', dict(self), '%s.cap'%region)

def get_zone_alert(zone):
    """Returns alert data for a particular County/Zone Code.
    
    The County/Zone codes can be found here: 
    http://www.weather.gov/alerts/
    
    This XML was formatted pretty badly (had extra spaces and
    newlines), so the .strip() was run on all string.
    """
    url = "http://www.weather.gov/alerts/wwarssget.php?zone=%s"%zone
    try:
        xml_string = HTTPRequest().open(url).read()
    except IOError, e:
        conf.log('warning','RequestError: %s'%e)
        raise RequestError, e
    xmldom = objectify.fromstring(xml_string)
    c = xmldom.channel
    return {'title': c.title.text.strip(),
    'link': c.link.text.strip(),
    'lastBuildDate': c.lastBuildDate.text.strip(),
    'lastBuildDate_parsed': datetime(*time.strptime(
                                     c.lastBuildDate.text.strip(),
                                     "%a, %d %b %Y %H:%M:%S")[:7]),
    'ttl': c.ttl.text.strip(),
    'language': c.language.text.strip(),
    'managingEditor': c.managingEditor.text.strip(),
    'webMaster': c.webMaster.text.strip(),
    'description': c.description.text.strip(),
    'image': {'url': c.image.url.text.strip(),
              'title': c.image.title.text.strip(),
              'link': c.link.text.strip()
              },
    'item': {'title': c.item.title.text.strip(),
             'link': c.item.link.text.strip(),
             'description': c.item.description.text.strip()
             }
    }
    
class ZoneAlert(dict):
    def __init__(self, zone):
        if conf.resource_exists('alerts','%s.zone' % zone):
            dict.__init__(self, conf.load('alerts','%s.zone' % zone))
        else:
            dict.__init__(self, get_zone_alert(zone))
            conf.dump('alerts', dict(self), '%s.zone' % zone)

def get_state_alert(state):
    """Returns alert data for a particular state.
    
    More information can be found here:
    http://www.weather.gov/alerts/
    """
    url = "http://www.weather.gov/alerts/%s.rss" % state.lower()
    try:
        xml_string = HTTPRequest().open(url).read()
    except IOError, e:
        conf.log('warning','RequestError: %s' % e)
        raise RequestError, e
    xmldom = objectify.fromstring(xml_string)
    title_re = re.compile(r'^(.*) - (.*) \((.*)\)')
    desc_re = re.compile(r'.* At:  (.*)\n.* At:  (.*)\n.* Homepage:  (.*)')
    xml_tf = "%Y-%m-%dT%H:%M:%S"
    c = xmldom.channel
    data = {'title': xmldom.channel.title.text.strip(),
            'link': xmldom.channel.link.text.strip(),
            'lastBuildDate': xmldom.channel.lastBuildDate.text.strip(),
            'lastBuildDate_parsed': datetime(*time.strptime(
                 xmldom.channel.lastBuildDate.text.strip(),
                 "%a, %d %b %Y %H:%M:%S")[:7]),
            'ttl': xmldom.channel.ttl.text.strip(),
            'language': xmldom.channel.language.text.strip(),
            'managingEditor': xmldom.channel.managingEditor.text.strip(),
            'webMaster': xmldom.channel.webMaster.text.strip(),
            'description': xmldom.channel.description.text.strip(),
            'image': {'url': xmldom.channel.image.url.text.strip(),
                      'title': xmldom.channel.image.title.text.strip(),
                      'link': xmldom.channel.image.link.text.strip()
                      },
            'items': {}
            }
    for item in xmldom.channel.item:
        try:
            issued, expired, link =\
                            desc_re.search(item.description.text).groups()
        except AttributeError:
            continue
        alert, county, state =\
                        title_re.search(item.title.text.strip()).groups()
        issued_date = datetime(*time.strptime(issued, xml_tf)[:7])
        expired_date = datetime(*time.strptime(expired, xml_tf)[:7])
        data['items'].update({'title': item.title.text.strip(),
                              'link': item.link.text.strip(),
                              'description': item.description.text.strip(),
                              'issued': issued_date,
                              'expires': expired_date,
                              'county': county,
                              'state': state,
                              'alert': alert,
                              'link': link})
    return data

class StateAlert(dict):
    def __init__(self, state):
        if conf.resource_exists('alerts','%s.state'%state):
            dict.__init__(self, conf.load('alerts','%s.state'%state))
        else:
            dict.__init__(self, get_state_alert(state))          
            conf.dump('alerts', dict(self), '%s.state'%state)

def test(unit):
    unit.assertEqual(CapAlert('ak')['info_list']['area'],
                {'county': 'Yukon Delta', 'state': 'Alaska',
                 'geocode': '002999', 'areaDesc': 'Yukon Delta (Alaska)'})
    unit.assertEqual(StateAlert('ak')['items']['state'], 'Alaska')
    unit.assert_(ZoneAlert('AKZ161')['title'].startswith(
        'Alaska - (Bristol Bay/AKZ161)')
    )
