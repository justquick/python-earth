import re
import time
import urllib
from datetime import datetime, timedelta

try:
    from lxml import objectify
except ImportError:
    raise ImportError, "Missing dependency: lxml"

try:
    from SOAPpy import WSDL
except ImportError:
    raise ImportError, "Missing dependency: SOAPpy"

from earth.core import *

API_KEY = ''

def _requester(name, data):
    data.update({'ACode': API_KEY})
    url_data = urllib.urlencode(data)
    url = "http://%s.api.wxbug.net/%s.aspx?%s" % (API_KEY, name, url_data)
    return HTTPRequest().open(url).read()

def _ns(obj, search):
    """Makes searching via namespace slightly easier."""
    return obj.xpath(search, namespaces={'aws':'http://www.aws.com/aws'})
    
def _parse_date(ob_date):
    ob_year = int(ob_date.year.attrib.get('number'))
    ob_month = int(ob_date.month.attrib.get('number'))
    ob_day = int(ob_date.day.attrib.get('number'))
    ob_hour = int(ob_date.hour.attrib.get('hour-24'))
    ob_minute = int(ob_date.minute.attrib.get('number'))
    ob_second = int(ob_date.second.attrib.get('number'))
    return datetime(ob_year, ob_month, ob_day, ob_hour, ob_minute, ob_second)

def _proc_children(ob, ob_dict):
    for child in ob.getchildren():
        name = child.tag.split('}')[-1]
        if re.search('date|time|sunset|sunrise', name):
            value = _parse_date(child)
        else:
            value = child.text
            if value == 'N/A':
                value = None
        ob_dict.update({name.replace('-', '_'): value})
        ca = child.attrib
        for x in range(len(child.attrib)):
            a_name = "%s_%s" % (name, ca.keys()[x])
            a_value = ca.values()[x]
            ob_dict.update({a_name.replace('-', '_'): a_value})
    return ob_dict

# Locations ----------
def GetLocationList(search):
    name = 'getLocationsXML'
    data = {'SearchString': search}
    xmldom = objectify.fromstring(_requester(name, data))
    return [{'cityname': l.attrib.get('cityname'),
            'statename': l.attrib.get('statename'),
            'countryname': l.attrib.get('countryname'),
            'zipcode': l.attrib.get('zipcode'),
            'citycode': l.attrib.get('citycode'),
            'citytype': l.attrib.get('citytype')}
            for l in xmldom.locations.getchildren()]
    
# Stations ----------
def _process_station_list(xmldom):
    stations = xmldom.stations.getchildren()
    return [{'id': s.attrib.get('id'),
             'name': s.attrib.get('name'),
             'city': s.attrib.get('city'),
             'state': s.attrib.get('state'),
             'country': s.attrib.get('country'),
             'zipcode': s.attrib.get('zipcode'),
             'distance': s.attrib.get('distance'),
             'unit': s.attrib.get('unit'),
             'lat': s.attrib.get('latitude'),
             'lon': s.attrib.get('longitude')} for s in stations]    

def GetStationListByCityCode(search):
    name = 'getStationsXML'
    data = {'cityCode': search}
    return _process_station_list(objectify.fromstring(_requester(name, data)))

def GetStationListByUSZipCode(zip_code):
    name = 'getStationsXML'
    data = {'zipCode': zip_code}
    return _process_station_list(objectify.fromstring(_requester(name, data)))

def GetUSWorldCityByLatLong(lat, lon):
    name = 'getStationsXML'
    data = {'lat': lat, 'lon': lon}
    return _process_station_list(objectify.fromstring(_requester(name, data)))

# Live Weather ----------
def _proc_live_weather(xmldom):
    weather_elems = _ns(xmldom, '//aws:weather')
    weather_list = []
    for w in weather_elems:
        w_dict = {'url': w.WebURL.text}
        weather_list.append(_proc_children(w.ob, w_dict))
    return weather_list
    
def GetLiveWeatherByCityCode(city_code, unit_type=0):
    name = 'getLiveWeatherRSS'
    data = {'cityCode': city_code, 'UnitType': unit_type}
    return _proc_live_weather(objectify.fromstring(_requester(name, data)))

def GetLiveWeatherByStationID(station_ids, unit_type=0):
    """Returns weather data for one more more stations.
    
    station_ids must be a list of strings
     
    Handles a maximum of five stations.
    
    """
    name = 'getLiveWeatherRSS'
    data = {'stationid': ','.join(station_ids), 'UnitType': unit_type}
    return _proc_live_weather(objectify.fromstring(_requester(name, data)))

def GetLiveWeatherByUSZipCode(zip_code, unit_type=0):
    name = 'getLiveWeatherRSS'
    data = {'zipCode': zip_code, 'UnitType': unit_type}
    return _proc_live_weather(objectify.fromstring(_requester(name, data)))

def GetLiveWeatherByLatLon(lat, lon, unit_type=0):
    name = 'getLiveWeatherRSS'
    data = {'lat': lat, 'lon': lon, 'UnitType': unit_type}
    return _proc_live_weather(objectify.fromstring(_requester(name, data)))

# Compact Live Weather ----------
def _proc_clive_weather(xmldom):
    weather_elems = _ns(xmldom, '//aws:weather')
    weather_list = []
    for w in weather_elems:
        w_dict = {'url': w.WebURL.text}
        weather_list.append(_proc_children(w, w_dict))
    return weather_list
        
def GetLiveCompactWeatherByCityCode(length, city_code, unit_type=0):
    name = 'getLiveCompactWeatherRSS'
    data = {'cityCode': city_code, 'UnitType': unit_type}
    return _proc_clive_weather(objectify.fromstring(_requester(name, data)))

def GetLiveCompactWeatherByStationID(station_id, unit_type=0):
    name = 'getLiveCompactWeatherRSS'
    data = {'stationid': station_id, 'UnitType': unit_type}
    return _proc_clive_weather(objectify.fromstring(_requester(name, data)))

def GetLiveCompactWeatherByUSZipCode(zip_code, unit_type=0):
    name = 'getLiveCompactWeatherRSS'
    data = {'zipCode': zip_code, 'UnitType': unit_type}
    return _proc_clive_weather(objectify.fromstring(_requester(name, data)))

# Alerts ----------
def _proc_alerts(xmldom):
    alert_elems = _ns(xmldom, '//aws:alert')
    alert_list = []
    url = _ns(xmldom.channel, 'aws:weather')[0].WebURL.text
    for a in alert_elems:
        w_dict = {'url': url}
        alert_list.append(_proc_children(a, a_dict))
    return alert_list

def GetAlertsDataListByUSZipCode(zip_code, unit_type=0):
    name = 'getAlertsRSS'
    data = {'zipCode': zip_code, 'UnitType': unit_type}
    return _proc_alerts(objectify.fromstring(_requester(name, data)))

def GetAlertsDataListByLatLon(lat, lon, unit_type=0):
    name = 'getAlertsRSS'
    data = {'lat': lat, 'lon': lon, 'UnitType': unit_type}
    return _proc_alerts(objectify.fromstring(_requester(name, data)))

# Forecasts ----------
def _proc_forecasts(xmldom):
    forecast_elems = _ns(xmldom, '//aws:forecast')
    location_elem = _ns(xmldom, '//aws:location')[0]
    forecast_list = []
    url = _ns(xmldom.channel, 'aws:weather')[0].WebURL.text
    for f in forecast_elems:
        f_dict = {'url': url}
        forecast_list.append(_proc_children(f, f_dict))
    return forecast_list

def GetForecastByCityCode(city_code, unit_type=0):
    name = 'getForecastRSS'
    data = {'cityCode': city_code, 'UnitType': unit_type}
    return _proc_forecasts(objectify.fromstring(_requester(name, data)))

def GetForecastByUSZipCode(zip_code, unit_type=0):
    name = 'getForecastRSS'
    data = {'zipCode': zip_code, 'UnitType': unit_type}
    return _proc_forecasts(objectify.fromstring(_requester(name, data)))

def GetForecastByLatLon(lat, lon, unit_type=0):
    name = 'getForecastRSS'
    data = {'lat': lat, 'lon': lon, 'UnitType': unit_type}
    return _proc_forecasts(objectify.fromstring(_requester(name, data)))

# Cameras ----------
def _proc_cameras(xmldom):
    cameras = _ns(xmldom, 'descendant::aws:camera')
    cam_list = []
    for cam in cameras:
        a_dict = {}
        [a_dict.update({cam.attrib.keys()[x].lower(): cam.attrib.values()[x]})
                        for x in range(len(cam.attrib))]
        cam_list.append(a_dict)
    return cam_list
    
def GetCameraListByUSZipCode(zip_code, unit_type=0):
    name = 'getCamerasXML'
    data = {'zipCode': zip_code, 'UnitType': unit_type}
    return _proc_cameras(objectify.fromstring(_requester(name, data)))
    

def GetCameraListByLatLon(lat, lon, unit_type=0):
    name = 'getCamerasXML'
    data = {'lat': lat, 'lon': lon, 'UnitType': unit_type}
    return _proc_cameras(objectify.fromstring(_requester(name, data)))

# Custom ----------
# These methods are notoriously slow as they have to make a request
# for every five station ids as per an API limitation.

def _split_list(l, length):
    return [l[i:i+length] for i in range(0, len(l), length)]

def _proc_station_weather(stations, unit_type):
    split_stations = _split_list(stations, 5)
    return_data = []
    for l in split_stations:
        try:
            return_data.extend(GetLiveWeatherByStationID(l, unit_type))
        except: # TODO: Catch the 500 error that happens a lot
            print "API Broke"
            continue
    return return_data

def _proc_station_compact_weather(stations, unit_type):
    split_stations = _split_list(stations, 5)
    return_data = []
    for l in split_stations:
        return_data.extend(GetLiveCompactWeatherByStationID(l, unit_type))
    return return_data

def GetStationWeatherForUSZipCode(zip_code, unit_type=0):
    stations = [s['id'] for s in GetStationListByUSZipCode(zip_code)]
    return _proc_station_weather(stations, unit_type)

def GetStationWeatherForCityCode(city_code, unit_type=0):
    stations = [s['id'] for s in GetStationListByCityCode(city_code)]
    return _proc_station_weather(stations, unit_type)

def GetStationWeatherForLatLon(lat, lon, unit_type=0):
    stations = [s['id'] for s in GetUSWorldCityByLatLong(lat, lon)]
    return _proc_station_weather(stations, unit_type)

def GetStationWeatherForStationCodes(station_code_list, unit_type=0):
    return _proc_station_weather(station_code_list, unit_type)

def GetStationCompactWeatherForUSZipCode(zip_code, unit_type=0):
    stations = [s['id'] for s in GetStationListByUSZipCode(zip_code)]
    return _proc_station_compact_weather(stations, unit_type)

def GetStationCompactWeatherForCityCode(city_code, unit_type=0):
    stations = [s['id'] for s in GetStationListByCityCode(city_code)]
    return _proc_station_compact_weather(stations, unit_type)

def GetStationCompactWeatherForLatLon(lat, lon, unit_type=0):
    stations = [s['id'] for s in GetUSWorldCityByLatLong(lat, lon)]
    return _proc_station_compact_weather(stations, unit_type)

########
# 
# class CurrentConditions(object):
#     
#     """fill this out"""
#     
#     def __init__(self, api_key):
#         self.API_KEY = api_key
#         self.WDSL_FILE = \
#             'http://api.wxbug.net/weatherservice.asmx?WSDL'
#         self.client = WSDL.Proxy(self.WDSL_FILE)
#         time.sleep(0.02) # Give it time to connect.
#     
#     def _caller(self, *args):
#         args = args.__add__((self.API_KEY,))
#         name = get_fn_name(2)
#         call_fn = self.client.__getattr__(name)
#         xml_string = call_fn(*args)
#         return xml_string
#         
#     def GetLocationList(self, *args):
#         """
#         length, search_string
#         """
#         xmldom = objectify.fromstring(self._caller(*args))
#         print xmldom
# 
#     def GetStationListByCityCode(self, length, city_code,
#                                  unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetStationListByUSZipCode(self, length, zip_code,
#                                   unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetUSWorldCityByLatLong(self, length, lat, lon):
#         name = get_fn_name()
#         pass
# 
#     def GetLiveWeatherByCityCode(self, length, city_code,
#                                  unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetLiveWeatherByStationID(self, length, station_id,
#                                   unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetLiveWeatherByUSZipCode(self, length, zip_code,
#                                   unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetLiveCompactWeatherByCityCode(self, length, city_code,
#                                         unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetLiveCompactWeatherByStationID(self, length, station_id,
#                                          unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetLiveCompactWeatherByUSZipCode(self, length, zip_code,
#                                          unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetAlertsDataList(self, length, zip_code):
#         name = get_fn_name()
#         pass
# 
#     def GetForecastByCityCode(self, length, city_code,
#                               unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetForecastByUSZipCode(self, length, zip_code,
#                                unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass
# 
#     def GetForecastIssueDetailsByCityCode(self, length, city_code):
#         name = get_fn_name()
#         pass
# 
#     def GetForecastIssueDetailsByUSZipCode(self, length, zip_code):
#         name = get_fn_name()
#         pass
# 
#     def GetStationTempsInArea(self, length, tl_lat, tl_lon, br_lat, br_lon,
#                               unit_type=DEFAULT_UNIT_TYPE):
#         name = get_fn_name()
#         pass

if __name__ == '__main__':
    print GetLocationList('washington, dc')
