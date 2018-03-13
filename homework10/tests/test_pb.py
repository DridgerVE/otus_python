import os
import unittest
import gzip
import struct
import deviceapps_pb2
import pb

MAGIC = 0xFFFFFFFF
DEVICE_APPS_TYPE = 1
TEST_FILE = "test.pb.gz"


class TestPB(unittest.TestCase):
    deviceapps = [
        {"device": {"type": "idfa", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7a"},
         "lat": 67.7835424444, "lon": -22.8044005471, "apps": [1, 2, 3, 4, 5]},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7b"}, "lat": 42, "lon": -42, "apps": [1, 2]},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7c"}, "lat": 42, "lon": -42, "apps": []},
        {"device": {"type": "gaid", "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d"}, "apps": [1]},
    ]

    def tearDown(self):
        os.remove(TEST_FILE)

    def test_write(self):
        bytes_written = pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)
        self.assertTrue(bytes_written > 0)

    # check magic, type, etc.
    def test_write_all_params(self):
        bytes_written = pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)
        self.assertTrue(bytes_written > 0)

        with gzip.open(TEST_FILE, 'rb') as fd:
            for apps in self.deviceapps:
                header = fd.read(8)
                magic, device_type, length = struct.unpack('IHH', header)
                self.assertEquals(magic, MAGIC)
                self.assertEquals(device_type, DEVICE_APPS_TYPE)
                data = fd.read(length)
                device_apps = deviceapps_pb2.DeviceApps()
                device_apps.ParseFromString(data)
                self.assertEqual(device_apps.device.type, apps['device']['type'])
                self.assertEqual(device_apps.device.id, apps['device']['id'])
                self.assertEqual(device_apps.apps, apps['apps'])
                if device_apps.HasField('lat'):
                    self.assertEqual(device_apps.lat, apps['lat'])
                if device_apps.HasField('lon'):
                    self.assertEqual(device_apps.lon, apps['lon'])

    # @unittest.skip("Optional problem")
    def test_read(self):
        pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)
        for i, d in enumerate(pb.deviceapps_xread_pb(TEST_FILE)):
            self.assertEqual(d, self.deviceapps[i])
