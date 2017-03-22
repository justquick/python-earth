"""A module for retrieving forecast data from the National Oceanic and
Atmospheric Administration's SOAP API U{http://www.weather.gov/xml/}

The idea was to keep this library as close to a 1-to-1 relationship with the
API as possible.  The methods found in the API are also found in this library.
Keeping with this trend, the NOAA API documentation is also applicable to this
library with only a few exceptions:

    - Parameter lists should be passed as a pythonic list of strings.
        - Ex: ['maxt', 'mint', 'pop12', 'wx']

    - Coordinate lists should be structured as a list of lists. Both floats and strings are accepted.
        - Ex: [[38.88, -77.10], ['37.1764', '-101.347']]


In addition to standard methods, this library contains other convenience
methods written to ease the retrieval of the most commonly used data.


Possible Weather Parameters
===========================
maxt         Maximum Temperature
mint         Minimum Temperature
temp         3 Hourly Temperature
dew          Dewpoint Temperature
appt         Apparent Temperature
pop12        12 Hour Probability of Precipitation
qpf          Liquid Precipitation Amount
snow         Snowfall Amount
sky          Cloud Cover Amount
rh           Relative Humidity
wspd         Wind Speed
wdir         Wind Direction
wx           Weather
icons        Weather Icons
waveh        Wave Height
incw34       Probabilistic Tropical Cyclone Wind Speed >34 Knots (Incremental)
incw50       Probabilistic Tropical Cyclone Wind Speed >50 Knots (Incremental)
incw64       Probabilistic Tropical Cyclone Wind Speed >64 Knots (Incremental)
cumw34       Probabilistic Tropical Cyclone Wind Speed >34 Knots (Cumulative)
cumw50       Probabilistic Tropical Cyclone Wind Speed >50 Knots (Cumulative)
cumw64       Probabilistic Tropical Cyclone Wind Speed >64 Knots (Cumulative)
wgust        Wind Gust
conhazo      Convective Hazard Outlook
ptornado     Probability of Tornadoes
phail        Probability of Hail
ptstmwinds   Probability of Damaging Thunderstorm Winds
pxtornado    Probability of Extreme Tornadoes
pxhail       Probability of Extreme Hail
pxtstmwinds  Probability of Extreme Thunderstorm Winds
ptotsvrtstm  Probability of Severe Thunderstorms
pxtotsvrtstm Probability of Extreme Severe Thunderstorms
tmpabv14d    Probability of 8- To 14-Day Average Temperature Above Normal
tmpblw14d    Probability of 8- To 14-Day Average Temperature Below Normal
tmpabv30d    Probability of One-Month Average Temperature Above Normal
tmpblw30d    Probability of One-Month Average Temperature Below Normal
tmpabv90d    Probability of Three-Month Average Temperature Above Normal
tmpblw90d    Probability of Three-Month Average Temperature Below Normal
prcpabv14d   Probability of 8- To 14-Day Total Precipitation Above Median
prcpblw14d   Probability of 8- To 14-Day Total Precipitation Below Median
prcpabv30d   Probability of One-Month Total Precipitation Above Median
prcpblw30d   Probability of One-Month Total Precipitation Below Median
prcpabv90d   Probability of Three-Month Total Precipitation Above Median
prcpblw90d   Probability of Three-Month Total Precipitation Below Median
precipa_r    Real-time Mesoscale Analysis Precipitation
sky_r        Real-time Mesoscale Analysis GOES Effective Cloud Amount
td_r         Real-time Mesoscale Analysis Dewpoint Temperature
temp_r       Real-time Mesoscale Analysis Temperature
wdir_r       Real-time Mesoscale Analysis Wind Direction
wspd_r       Real-time Mesoscale Analysis Wind Speed
"""

import re
from datetime import datetime, timedelta

try:
    from lxml import etree
except ImportError:
    raise ImportError, "Missing dependency: lxml"

from earth.core.iso8601 import parse_date as xml_time_parse
from earth.core import HTTPRequest, SoapClient

WSDL_FILE = 'http://www.weather.gov/forecasts/xml/DWMLgen/wsdl/ndfdXML.wsdl'
GLANCE_PARAMS = ('maxt', 'mint', 'sky', 'wx', 'icons')

class Forecast(object):

    """Fill this in."""

    def __init__(self):
        self.client = SoapClient(WSDL_FILE)
        self.today = datetime.now()
        self.low_date = datetime(2000, 01, 01)
        self.high_date = self.today + timedelta(days=100)

    # Internal Methods

    def _get_points(self, xmldom):
        """Extracts the points (places) from the xml."""
        loc_tags = xmldom.xpath('//location')
        locations = {}
        for loc in loc_tags:
            name = loc.findall('location-key')[0].text
            point = loc.findall('point')[0]
            lat = point.attrib['latitude']
            lon = point.attrib['longitude']
            locations[name] = {'lat': lat, 'lon': lon, 'params': {}}
        self.locations = locations
        self._get_more_weather_infomation(xmldom)

    def _get_more_weather_infomation(self, xmldom):
        """Appends the 'more weather' URL to each saved point."""
        parts = xmldom.xpath('//moreWeatherInformation')
        for part in parts:
            point = part.attrib['applicable-location']
            link = part.text
            self.locations[point].update({'link': link})

    def _get_time_layouts(self, xmldom):
        """Extracts the 'time layouts' from the xml."""
        hour_re = re.compile(r'p(\d{1,2})h')
        time_layouts = {}
        time_layout_list = xmldom.xpath('//time-layout')
        for t in time_layout_list:
            key = t.findall('layout-key')[0].text
            valid_times_list = t.findall('start-valid-time')
            end_time_test = t.findall('end-valid-time')
            if end_time_test:
                dt_list = [(xml_time_parse(vt.text),
                            vt.getnext().tag == 'end-valid-time' and \
                            xml_time_parse(vt.getnext().text) or None) \
                           for vt in valid_times_list]
            else:
                dt_list = [(xml_time_parse(vt.text), None) \
                           for vt in valid_times_list]
            time_layouts[key] = dt_list
        self.time_layouts = time_layouts

    def _get_lat_lon_points(self, xml_string):
        """Extracts single or multiple lat/lon from the xml."""
        tree = etree.fromstring(xml_string)
        lat_lon_string = tree.xpath('//latLonList')[0].text
        return [x.split(',') for x in lat_lon_string.split(' ')]

    def _combine_list_with_time_layout(self, time_layout_key, val_list):
        """Combines a list of values with their appropriate time layout."""
        tl = self.time_layouts[time_layout_key]
        if len(tl) != len(val_list):
            raise Exception, "Lists must be the same length"
        return_list = []
        for x in range(len(tl)):
            # This takes the ranges and turns them into real readings (3 hr)
            if tl[x][1]:
                s, e = tl[x]
                while s <= e:
                    return_list.append((s, val_list[x]))
                    s = s + timedelta(hours=3)
            else:
                return_list.append((tl[x][0], val_list[x]))
        return sorted(return_list)

    def _generic_param_retriever(self, name, location, val_tag, xml_string):
        """Extracts values from xml based on a passed parameter.

        This is used for most parameters as their structures are identical.

        """
        tree = etree.fromstring(xml_string)
        point = tree.xpath('//parameters[@applicable-location="%s"]' %
                location)[0]
        # Find the appropriate name tag
        name_tag = point.xpath("//name[child::text() = '%s']" % name)[0]
        parent = name_tag.getparent()
        val_list = []
        for x in parent.findall(val_tag):
            try:
                val = int(x.text)
            except ValueError:
                try:
                    val = float(x.text)
                except ValueError:
                    val = x.text
            except TypeError:
                val = x.text
            val_list.append(val)
        tl_key = parent.attrib['time-layout']
        return self._combine_list_with_time_layout(tl_key, val_list)

    def _rtma_param_retriever(self, name, location, xml_string):
        """Extracts values from xml based on special parameters.

        This is used for the RTMA parameters as the structure of their xml is
        slightly different than normal.

        """
        
        tree = etree.fromstring(xml_string)
        point = tree.xpath('//parameters[@applicable-location="%s"]' %
                location)[0]
        # Find the appropriate name tag
        name_tag = point.xpath("//name[child::text() = '%s']" % name)[0]
        parent = name_tag.getparent()
        vwu = parent.findall('valueWithUncertainty')
        val_list = [{'value': x.xpath('value')[0].text,
                    'error': x.xpath('uncertainty/error')[0].text}
                    for x in vwu]
        tl_key = parent.attrib['time-layout']
        return self._combine_list_with_time_layout(tl_key, val_list)

    def _process_returned_xml(self, weather_params, xml_string):
        """Proccesses the xml_string firing the appropriate parameter methods.
        
        """
        
        xmldom = etree.fromstring(xml_string)
        self._get_points(xmldom)
        self._get_time_layouts(xmldom)
        if not weather_params:
            weather_params = GLANCE_PARAMS
        returnable = {}
        for p in weather_params:
            for loc in self.locations.keys():
                param = self.__getattribute__('_%s' % p)(loc, xml_string)
                self.locations[loc]['params'][p] = param
        return self.locations

    def _lat_lon_list_to_string(self, lat_lon_list):
        """Turns a list of lat/lon into the string format the API accepts."""
        return ' '.join([','.join([str(x) for x in y]) for y in lat_lon_list])

    # Parameter Methods
    # These are called based on either the parameters passed to an API method
    # or the default parameters associated with a parameterless method.

    def _maxt(self, location, xml_string):
        name = "Daily Maximum Temperature"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _mint(self, location, xml_string):
        name = "Daily Minimum Temperature"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _temp(self, location, xmldom):
        name = "Temperature"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _dew(self, location, xml_string):
        name = "Dew Point Temperature"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _appt(self, location, xml_string):
        name = "Apparent Temperature"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _pop12(self, location, xml_string):
        name = "12 Hourly Probability of Precipitation"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _qpf(self, location, xml_string):
        name = "Liquid Precipitation Amount"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _snow(self, location, xml_string):
        name = "Snow Amount"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _sky(self, location, xml_string):
        name = "Cloud Cover Amount"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _rh(self, location, xml_string):
        name = "Relative Humidity"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _wspd(self, location, xml_string):
        name = "Wind Speed"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _wdir(self, location, xml_string):
        name = "Wind Direction"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _wx(self, location, xml_string):
        name = "Weather Type, Coverage, and Intensity"
        vis_re = re.compile(r'.*(\d+).*')
        tree = etree.fromstring(xml_string)
        point = tree.xpath('//parameters[@applicable-location="%s"]' %
                location)[0]
        name_tag = point.xpath("//name[child::text() = '%s']" % name)[0]
        parent = name_tag.getparent()
        val_list = []
        for x in parent.xpath('weather-conditions'):
            summary_attrib = x.get('weather-summary', '')
            if summary_attrib and  len(x.getchildren()) <= 1:
                w_dict = {'summary': summary_attrib,
                          'coverage': None,
                          'intensity': None,
                          'weather-type': None,
                          'additive': None,
                          'value': None,
                          'visibility': None
                          }
                val_list.append([w_dict,])
            elif x.getchildren():
                value_tag_list = x.xpath('value')
                sub_val_list = []
                for value_tag in value_tag_list:
                    vis_tag_list = value_tag.xpath('visibility')
                    vis_tag = ''
                    if vis_tag_list and 'nil' not in vis_tag_list[0].keys()[0]:
                        vis_tag_search = vis_re.search(vis_tag_list[0].text)
                        if vis_tag_search:
                            vis_tag = vis_tag_search.groups()[0]
                    w_dict = {'summary': value_tag.get('weather-type', ''),
                              'coverage': value_tag.get('coverage', ''),
                              'intensity': value_tag.get('intensity', ''),
                              'weather-type': value_tag.get('weather-type',
                                                            ''),
                              'additive': value_tag.get('additive', ''),
                              'qualifier': value_tag.get('qualifier', ''),
                              'visibility': vis_tag and int(vis_tag)
                                            or None
                              }
                    sub_val_list.append(w_dict)
                else:
                    # Make up a summary using all the weather types
                    if any([x['weather-type'] for x in sub_val_list]):
                        summary_text = ''
                        # Get all the weather types and make a summary
                        for x in sub_val_list:
                            wt = x.get('weather-type')
                            additive = x.get('additive', '')
                            if wt is not None:
                                if additive:
                                    summary_text = summary_text.__add__(' ' +
                                                    additive + ' ')
                                summary_text = summary_text.__add__(
                                                    wt.title())
                        # Loop again to set all the summaries
                        for x in sub_val_list:
                            x['summary'] = summary_text             
                val_list.append(sub_val_list)
            else:
                w_dict = {'summary': None,
                          'coverage': None,
                          'intensity': None,
                          'weather-type': None,
                          'additive': None,
                          'qualifier': None,
                          'visibility': None
                          }
                val_list.append([w_dict,])
        tl_key = parent.attrib['time-layout']
        return self._combine_list_with_time_layout(tl_key, val_list)

    def _icons(self, location, xml_string):
        name = "Conditions Icons"
        return self._generic_param_retriever(name, location, 'icon-link',
                                             xml_string)

    def _waveh(self, location, xml_string):
        name = "Wave Height"
        tree = etree.fromstring(xml_string)
        point = tree.xpath('//parameters[@applicable-location="%s"]' %
                location)[0]
        # Find the appropriate name tag
        name_tag = point.xpath("//name[child::text() = '%s']" % name)[0]
        parent = name_tag.getparent()
        key_parent = parent.getparent()
        val_list = []
        for x in parent.findall('value'):
            try:
                val = int(x.text)
            except ValueError:
                try:
                    val = float(x.text)
                except ValueError:
                    val = x.text
            except TypeError:
                val = x.text
            val_list.append(val)
        tl_key = key_parent.attrib['time-layout']
        return self._combine_list_with_time_layout(tl_key, val_list)

    def _incw34(self, location, xml_string):
        name = "Probability of a Tropical Cyclone Wind Speed above 34 Knots \
                (Incremental)"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _incw50(self, location, xml_string):
        name = "Probability of a Tropical Cyclone Wind Speed above 50 Knots \
                (Incremental)"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _incw64(self, location, xml_string):
        name = "Probability of a Tropical Cyclone Wind Speed above 64 Knots \
                (Incremental)"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _cumw34(self, location, xml_string):
        name = "Probability of a Tropical Cyclone Wind Speed above 34 Knots \
                (Incremental)"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _cumw50(self, location, xml_string):
        name = "Probability of a Tropical Cyclone Wind Speed above 50 Knots \
                (Incremental)"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _cumw64(self, location, xml_string):
        name = "Probability of a Tropical Cyclone Wind Speed above 64 Knots \
                (Incremental)"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _wgust(self, location, xml_string):
        name = "Wind Speed Gust"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _conhazo(self, location, xml_string):
        name = "Convective Hazard Outlook"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _ptornado(self, location, xml_string):
        name = "Probability of Tornadoes"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _phail(self, location, xml_string):
        name = "Probability of Hail"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _ptstmwinds(self, location, xml_string):
        name = "Probability of Damaging Thunderstorm Winds"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _pxtornado(self, location, xml_string):
        name = "Probability of Extreme Tornadoes"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _pxhail(self, location, xml_string):
        name = "Probability of Extreme Hail"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _pxtstmwinds(self, location, xml_string):
        name = "Probability of Extreme Thunderstorm Winds"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _ptotsvrtstm(self, location, xml_string):
        name = "Total Probability of Severe Thunderstorms"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _pxtotsvrtstm(self, location, xml_string):
        name = "Total Probability of Extreme Severe Thunderstorms"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _tmpabv14d(self, location, xml_string):
        name = "Probability of 8-14 Day Average Temperature Above Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _tmpblw14d(self, location, xml_string):
        name = "Probability of 8-14 Day Average Temperature Below Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _tmpabv30d(self, location, xml_string):
        name = "Probability of One-Month Average Temperature Above Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _tmpblw30d(self, location, xml_string):
        name = "Probability of One-Month Average Temperature Below Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _tmpabv90d(self, location, xml_string):
        name = "Probability of Three-Month Average Temperature Above Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _tmpblw90d(self, location, xml_string):
        name = "Probability of Three-Month Average Temperature Below Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _prcpabv14d(self, location, xml_string):
        name = "Probability of 8-14 Day Average Precipitation Above Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _prcpblw14d(self, location, xml_string):
        name = "Probability of 8-14 Day Average Precipitation Below Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _prcpabv30d(self, location, xml_string):
        name = "Probability of One-Month Average Precipitation Above Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _prcpblw30d(self, location, xml_string):
        name = "Probability of One-Month Average Precipitation Below Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _prcpabv90d(self, location, xml_string):
        name = "Probability of Three-Month Average Precipitation Above Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _prcpblw90d(self, location, xml_string):
        name = "Probability of Three-Month Average Precipitation Below Normal"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _precipa_r(self, location, xml_string):
        name = "RTMA Liquid Precipitation Amount"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _sky_r(self, location, xml_string):
        name = "RTMA Cloud Cover Amount"
        return self._generic_param_retriever(name, location, 'value',
                                             xml_string)

    def _td_r(self, location, xml_string):
        name = "RTMA Dew Point Temperature"
        return self._rtma_param_retriever(name, location, xml_string)

    def _temp_r(self, location, xml_string):
        name = "RTMA Temperature"
        return self._rtma_param_retriever(name, location, xml_string)

    def _wdir_r(self, location, xml_string):
        name = "RTMA Wind Direction"
        return self._rtma_param_retriever(name, location, xml_string)

    def _wspd_r(self, location, xml_string):
        name = "RTMA Wind Speed"
        return self._rtma_param_retriever(name, location, xml_string)

    # Main Methods

    def NDFDgen(self, lat, lon, product, start_time=None,
                end_time=None, weather_params=[]):
        """Retrieves data for a single point based on a set of parameters.

        Positional arguments:
        lat -- a string or float (37.1764) (required)
        lon -- a string or float (-101.347) (required)
        product -- either 'time-series' or 'glance' (required)

        Keyword arguments:
        start_time -- a datetime object (optional)
        end_time -- a datetime object (optional)
        weather_params -- a list of weather parameters (optional if product == 'glance')

        Returns a hierarchical dict tree containing the location, lat, lon,
        URL and parameter data.

        """
        
        if product == "time-series" and not weather_params:
            raise "You must provide weather_parameters when using \
                    time-series."
        xml_string = self.client.NDFDgen(lat, lon, product,
                                      start_time or self.low_date,
                                      end_time or self.high_date,
                                      weather_params)
        return self._process_returned_xml(weather_params, xml_string)

    def NDFDgenLatLonList(self, lat_lon_list, product, start_time=None,
                          end_time=None, weather_params=[]):
        """Retrieves data for a multiple points based on a set of parameters.

        Positional arguments:
        lat_lon_list -- a list of strings or floats (required)
            - Ex. [[38.88, -77.10], ['37.1764', '-101.347']] 
        product -- either 'time-series' or 'glance' (required)

        Keyword arguments:
        start_time -- a datetime object (optional)
        end_time -- a datetime object (optional)
        weather_params -- a list of weather parameters (optional if product == 'glance')

        Returns a hierarchical dict tree containing the location, lat, lon,
        URL and parameter data.

        """
        
        if product == "time-series" and not weather_params:
            raise "You must provide weather_parameters when using \
                    time-series."
        ll_list = self._lat_lon_list_to_string(lat_lon_list)
        xml_string = self.client.NDFDgenLatLonList(ll_list, product,
                    start_time and start_time.isoformat() or self.low_date,
                    end_time and end_time.isoformat() or self.high_date,
                    weather_params)
        return self._process_returned_xml(weather_params, xml_string)

    def NDFDgenZipCode(self, zip_code, product, start_time=None,
                        end_time=None, weather_params=[]):
        """Retrieves data for single zip code.

        Positional arguments:
        zip_code -- a single string or int (22201) (required)
        product -- either 'time-series' or 'glance' (required)

        Keyword arguments:
        start_time -- a datetime object (optional)
        end_time -- a datetime object (optional)
        weather_params -- a list of weather parameters (optional if product == 'glance')

        Returns a hierarchical dict tree containing the location, lat, lon,
        URL and parameter data.

        """
        
        return self.NDFDgenZipCodeList([zip_code,], product,
                                       start_time or self.low_date,
                                       end_time or self.high_date,
                                       weather_params)

    def NDFDgenZipCodeList(self, zip_code_list, product, start_time=None,
                           end_time=None, weather_params=[]):
        """Retrieves data for a list of zip codes.

        Positional arguments:
        zip_code_list -- a list of strings or ints (required)
            - Ex.  (22201, '67951') 
        product -- either 'time-series' or 'glance' (required)

        Keyword arguments:
        start_time -- a datetime object (optional)
        end_time -- a datetime object (optional)
        weather_params -- a list of weather parameters (optional if product == 'glance')

        Returns a hierarchical dict tree containing the location, lat, lon,
        URL and parameter data.

        """
        
        zc_list  = ' '.join([str(x) for x in zip_code_list])
        lat_lon_list = self.LatLonListZipCode(zc_list)
        return self.NDFDgenLatLonList(lat_lon_list, product,
                                      start_time or self.low_date,
                                      end_time or self.high_date,
                                      weather_params or {})

    def NDFDgenByDay(self, lat, lon, start_date=None, num_days=7,
                     format="24 hourly"):
        """Retrieves data based on a start date, number of days and a format.

        Positional arguments:
        lat -- a string or float (37.1764) (required)
        lon -- a string or float (-101.347) (required)

        Keyword arguments:
        start_time -- a datetime object (optional)
        num_days -- an int (optional)
        format -- either '12 hourly' or '24 hourly' (required)

        Returns a hierarchical dict tree containing the location, lat, lon,
        URL and data for the following parameters:

        ['maxt', 'mint', 'pop12', 'wx', 'icons']

        """
        
        weather_params = ['maxt', 'mint', 'pop12', 'wx', 'icons']
        xml_string = self.client.NDFDgenByDay(lat, lon,
                                              start_date and start_date.date()
                                              or self.today.date(),
                                              num_days, format)
        return self._process_returned_xml(weather_params, xml_string)

    def NDFDgenByDayLatLonList(self, lat_lon_list, start_date=None,
                               num_days=7, format="24 hourly"):
        """Retrieves data based on a start date, number of days and a format.

        Positional arguments:
        lat_lon_list -- a list of strings or floats(required)
            - Ex. [[38.88, -77.10], ['37.1764', '-101.347']]
            
        Keyword arguments:
        start_time -- a datetime object (optional)
        num_days -- an int (optional)
        format -- either '12 hourly' or '24 hourly' (required)

        Returns a hierarchical dict tree containing the location, lat, lon,
        URL and data for the following parameters:

        ['maxt', 'mint', 'pop12', 'wx', 'icons']

        """
        
        ll_list = self._lat_lon_list_to_string(lat_lon_list)
        weather_params = ['maxt', 'mint', 'pop12', 'wx', 'icons']
        xml_string = self.client.NDFDgenByDayLatLonList(ll_list,
                                              start_date and start_date.date()
                                              or self.today.date(),
                                              num_days, format)
        return self._process_returned_xml(weather_params, xml_string)

    def LatLonListSubgrid(self, ll_lat, ll_lon, ur_lat, ur_lon, res):
        """Retrieves lat/lon for all points in a subgrid.

        Positional arguments:
        ll_lat -- a string or float (33.8835) (required)
        ll_lon -- a string or float (-80.0679) (required)
        ur_lat -- a string or float (33.8835) (required)
        ur_lon -- a string or float (-80.0679) (required)
        res -- a string or int (20) (required)

        Returns the WGS84 latitude and longitude values of all the NDFD grid
        points within a rectangular subgrid as defined by points at the lower
        left and upper right corners of the rectangle.

        """

        #TODO: Test this!

        xml_string = self.client.LatLonListSubgrid(ll_lat, ll_lon, ur_lat,
                                                   ur_lon, res)
        return self._get_lat_lon_points(xml_string)

    def LatLonListLine(self, ep_1_lat, ep_1_lon, ep_2_lat, ep_2_lon):
        """Retrieves lat/lon for all points in a line.

        Positional arguments:
        ep_1_lat -- a string or float (33.8835) (required)
        ep_1_lon -- a string or float (-80.0679) (required)
        ep_2_lat -- a string or float (33.8835) (required)
        ep_2_lon -- a string or float (-80.0679) (required)

        Returns the WGS84 latitude and longitude values for all points on a
        line defined by the line's end points.

        """

        #TODO: Test this!

        xml_string = self.client.LatLonListLine(ep_1_lat, ep_1_lon, ep_2_lat,
                                                ep_2_lon)
        return self._get_lat_lon_points(xml_string)

    def LatLonListZipCode(self, zip_codes):
        """Retrieves lat/lon for each zip code in a given list.

        Positional arguments:
        zip_codes -- a single string (for a single zip code) or a list of 
        strings or int (for multiple zip codes) (required)

        Returns the WGS84 latitude and longitude values for one or more zip
        codes (50 United States and Puerto Rico).

        """
        
        if isinstance(zip_codes, int):
            zip_codes = str(zip_codes)
        elif isinstance(zip_codes, str):
            pass
        elif isinstance(zip_codes, list) or isinstance(zip_codes, tuple):
            zip_codes = ' '.join([str(x) for x in zip_codes])
        xml_string = self.client.LatLonListZipCode(zip_codes)
        return self._get_lat_lon_points(xml_string)

    #TODO: Add LatLonListCityNames method

    def LatLonListSquare(self, cp_lat, cp_lon, dist_lat, dist_lon, res):
        """Retrieves lat/lon for all points in a square.

        Positional arguments:
        cp_lat -- a string or float (33.8835) (required)
        cp_lon -- a string or float (-80.0679) (required)
        dist_lat -- an int (50) (required)
        dist_lon -- an int (50) (required)
        res -- an int (20) (required)

        Returns the WGS84 latitude and longitude values for a rectangle
        defined by a center point and distances in the latitudinal and
        longitudinal directions.

        """
        
        xml_string = self.client.LatLonListSquare(cp_lat, cp_lon, dist_lat,
                                                  dist_lon, res)
        return self._get_lat_lon_points(xml_string)

    def CornerPoints(self, sector):
        """Retrieves lat/lon for points in a sector.

        Positional arguments:
        sector -- One of the NDFD grids (conus, alaska, nhemi, guam, hawaii, and puertori). 

        Returns the WGS84 latitude and longitude values for the corners of an
        NDFD grid as well as the resolution required to retrieve the entire
        grid and still stay under the maximum allowed point restriction.

        """
        
        xml_string = self.client.CornerPoints(sector)
        return self._get_lat_lon_points(xml_string)

def full_text_forecast(state_abbr, zone):
    URL_TEMPLATE = 'http://weather.noaa.gov/pub/data/forecasts/zone/%s/%s'
    filename = '%sz%s.txt' % (state_abbr.lower(), zone)
    url = URL_TEMPLATE % (state_abbr.lower(), filename)
    forecast = HTTPRequest().open(url).read().split('\n')
    dl = forecast[0]
    expires = datetime(int(dl[8:12]), int(dl[12:14]), int(dl[14:16]), 
                       int(dl[16:18]), int(dl[18:20]))
    issued = datetime.strptime(forecast[5], "%I%M %p %Z %a %b %d %Y")
    text = '\n'.join(forecast[12:]).strip()
    return {'issued_date': issued,
            'expires_date': expires,
            'text': text
            }
    
def test(unit): pass
    #print full_text_forecast('ks','009')
