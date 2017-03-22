import re
import urllib
import socket

try:
    from lxml import html
except ImportError:
    raise ImportError, "Missing dependency: lxml"

#socket.setdefaulttimeout(5)

BASE_URL = "http://www.aaaai.org/nab/index.cfm?"
ARGS = "p=allergenreport&stationid=%s"

STATIONS = {
    171: 'AK - Anchorage',
    55: 'AL - Huntsville',
    186: 'AL - Oxford',
    161: 'AR - Little Rock',
    38: 'AR - Rogers',
    185: 'CA - Crescent City',
    8: 'CA - Orange',
    9: 'CA - Pleasanton (Station 1)',
    183: 'CA - Pleasanton (Station 2)',
    10: 'CA - Roseville',
    159: 'CA - San Diego',
    85: 'CA - San Jose (Station 1)',
    108: 'CA - San Jose (Station 2)',
    14: 'CA - Santa Barbara',
    4: 'CO - Colorado Springs (Station 1)',
    174: 'CO - Colorado Springs (Station 2)',
    94: 'CT - Waterbury',
    60: 'DC - Washington',
    169: 'DE - New Castle',
    57: 'FL - Sarasota',
    59: 'FL - Tampa',
    49: 'GA - Atlanta',
    138: 'GA - Savannah',
    182: 'ID - Coeur d\'Alene',
    142: 'ID - Twin Falls',
    147: 'IL - Melrose Park',
    187: 'IN - Evansville',
    26: 'IN - Indianapolis',
    41: 'KY - Lexington',
    102: 'KY - Louisville (Station 2)',
    162: 'LA - New Orleans',
    61: 'MA - Salem',
    51: 'MD - Baltimore',
    148: 'MI - St. Clair Shores',
    97: 'MO - Kansas City',
    35: 'MO - St. Louis',
    133: 'NC - Durham',
    24: 'ND - Fargo',
    166: 'NE - Lincoln',
    33: 'NE - Omaha',
    64: 'NJ - Cherry Hill',
    70: 'NJ - Newark',
    153: 'NM - Los Alamos',
    112: 'NV - Las Vegas',
    86: 'NV - Sparks (Reno)',
    134: 'NY - Albany',
    146: 'NY - Armonk',
    62: 'NY - Brooklyn',
    66: 'NY - Olean',
    69: 'NY - Rochester',
    21: 'OH - Dayton',
    103: 'OK - Oklahoma City (Station 1)',
    104: 'OK - Oklahoma City (Station 2)',
    47: 'OK - Tulsa 1',
    156: 'OK - Tulsa 2',
    110: 'ON - London',
    141: 'ON - Niagara Falls',
    1: 'OR - Eugene',
    65: 'PA - Erie',
    163: 'PA - Pittsburgh (Station 2)',
    157: 'PA - York',
    168: 'PR - San Juan',
    154: 'SC - Greenville',
    39: 'TN - Knoxville (Station 1)',
    100: 'TX - College Station',
    37: 'TX - Dallas',
    181: 'TX - Flower Mound',
    111: 'TX - Georgetown (Austin)',
    167: 'TX - Houston (Station 1)',
    188: 'TX - Houston (Station 2)',
    105: 'TX - Waco (Station 1)',
    106: 'TX - Waco (Station 2)',
    11: 'UT - Draper',
    3: 'WA - Seattle',
    2: 'WA - Vancouver',
    28: 'WI - La Crosse',
    151: 'WI - Madison',
    137: 'WI - Waukesha',
}

def state2stations(state):
    """
    Returns a generator of all stations in any given state
    """
    for id,value in STATIONS.items():
        if value.startswith(state.upper()):
            yield id
            
def location2station(location):
    """
    Generates all stations that match the given location
    Matches are determined by simple case insensitive search
    """
    for id,value in STATIONS.items():
        if value.lower().find(location.lower())>-1:
            yield id
    
def find_page(station_id):
    """Finds the latest pollen count.
    
    Checks the base page, then determines whether it can scrape the needed
    date from that page or if it needs to follow a link to the appropriate
    page for past data.
    
    """
    
    link_re = re.compile(r'<a href="index.cfm\?(p=allergenreport&stationid=\d+&datecount=\d\d%2F\d\d%2F\d\d\d\d)">', re.DOTALL)
    html = urllib.urlopen(BASE_URL + ARGS % station_id).read()
    search = link_re.search(html)
    if search:
        html = urllib.urlopen(BASE_URL + search.groups()[0]).read()
    return html

def get_pollen_counts(station_id):
    """Retrieves pollen information from aaaai.org.
    
    Returns a list of integers containing the four different pollen counts:
        - [Trees, Weeds, Grass, Mold]
    """
    
    page_html = html.document_fromstring(find_page(station_id))
    td_list = filter(lambda x:'133' in x.values(),
                     page_html.find_class('title'))
    name_re = re.compile(r'images/report(low|moderate|high|veryhigh)\.gif')
    results = []
    for td in td_list:
        search = name_re.search(html.tostring(td))
        if search:
            results.append(search.groups()[0])
        else:
            results.append('absent')
    return results

def test(unit):
    for id in state2stations('MD'):
        for report in get_pollen_counts(id):
            unit.assert_(report in ['low','moderate','high','veryhigh','absent'])