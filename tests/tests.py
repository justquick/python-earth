import unittest

class EarthTests(unittest.TestCase):
    def test_geo(self):
        from earth.geo import test
        test(self)
        
    def test_sun(self):
        from earth.sun import test
        test(self)
        
    def test_quake(self):
        from earth.quake import test
        test(self)
        
    def test_observations(self):
        from earth.weather.observations import test
        test(self)
        
    def test_forecasts(self):
        from earth.weather.forecasts import test
        test(self)
        
    def test_alerts(self):
        from earth.weather.alerts import test
        test(self)
        
    def test_radar(self):
        from earth.weather.radar import test
        test(self)
        
    def test_pollen(self):
        from earth.air.pollen import test
        test(self)
        
    def test_uv(self):
        from earth.air.uv import test
        test(self)

if __name__ == '__main__':
    unittest.main()
    

