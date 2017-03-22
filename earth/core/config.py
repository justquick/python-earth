from ConfigParser import ConfigParser, RawConfigParser
try:
    import cPickle as pickle
except ImportError:
    import pickle
import sys
import os
import logging as log

# Override this to customize the config file path
CONFIG_FILE = ''

if not CONFIG_FILE:
    if sys.platform.startswith('win'):
        CONFIG_FILE = os.path.join(os.environ['APPDATA'],'.earth','.conf')
    else:
        CONFIG_FILE = os.path.join(os.path.expanduser('~'),'.earth','.conf')

if not os.path.isdir(os.path.dirname(CONFIG_FILE)):
    os.makedirs(os.path.dirname(CONFIG_FILE))

LOG_FILENAME = 'logging.out'

def create(**kwargs):
    config = RawConfigParser()
    config.add_section('earth')
    config.set('earth', 'data_root', kwargs.pop('earth.data_root', os.getcwd()))
    config.set('earth', 'log', kwargs.pop('earth.log', LOG_FILENAME))
    config.add_section('geo')
    config.set('geo', 'api_key', kwargs.pop('geo.api_key','ABQIAAAAtGw1MDAVWMO6QjAEb2-w_hQCULP4XOMyhPd8d_NrQQEO8sT8XBR4nl1tfW8GUiQ2uIWU8ASwZR6mXA7'))
    config.set('geo','sensor', kwargs.pop('geo.sensor','false'))
    config.set('geo','lat_lon',kwargs.pop('geo.lat_lon','40.479581,-117.773438'))
    config.set('geo','span',kwargs.pop('geo.span','11.1873,22.5'))
    config.set('geo','country', kwargs.pop('geo.country','us'))
    for k,v in kwargs.items():
        config.add_section(k)
        config.set(k,v)
    configfile = open(CONFIG_FILE, 'wb')
    config.write(configfile)
    configfile.close()

if not os.path.isfile(CONFIG_FILE):
    create()
    
class Config(object):
    def __init__(self):
        self.conf = ConfigParser()
        self.conf.read(CONFIG_FILE)
    @property
    def data_root(self):
        if self.conf.has_option('earth','data_root'):
            return self.conf.get('earth','data_root')
    @property
    def api_key(self):
        if self.conf.has_option('geo','api_key'):
            return self.conf.get('geo','api_key')
            
    def resource_exists(self, app, name):
        return os.path.isfile(os.path.join(self.data_root,app,'%s.obj'%name))
    def dump(self, app, obj, id):
        #print '%s > %s %s'%(obj,app,id)
        path = os.path.join(self.data_root, app, '%s.obj'%id)
        if not os.path.isdir(os.path.dirname(path)):
            self.mkdirs(app)
        pickle.dump(obj, open(path, 'wb'), pickle.HIGHEST_PROTOCOL)
    def load(self, app, id):
        #print '< %s %s'%(app,id)
        if os.path.isfile(os.path.join(self.data_root,app,'%s.obj'%id)):
            return pickle.load(open(os.path.join(self.data_root,app,'%s.obj'%id)))
    def log(self,type,message):
        log.basicConfig(filename=os.path.join(conf.data_root,
                    self.conf.get('earth','log',LOG_FILENAME)),level=log.DEBUG)
        return getattr(log,type)(message)
    def mkdirs(self, app):
        if not os.path.isdir(os.path.join(self.data_root,app)):
            os.makedirs(os.path.join(self.data_root,app))
    def get(self, *args, **kwargs):
        return self.conf.get(*args, **kwargs)
        
            
conf = Config()

if __name__ == '__main__':
    print dir(conf)
    print conf.data_root,conf.api_key
    
