import unittest
import os
import gzip
from optparse import OptionParser
import memc_load
import logging

TEST_FILE = "test.tsv.gz"


class TestMemcLoad(unittest.TestCase):

    def setUp(self):
        self.op = OptionParser()
        self.op.add_option("-t", "--test", action="store_true", default=False)
        self.op.add_option("-l", "--log", action="store", default="memc_load.log")
        self.op.add_option("--dry", action="store_true", default=False)
        self.op.add_option("--pattern", action="store", default="*.tsv.gz")
        self.op.add_option("--idfa", action="store", default="127.0.0.1:33013")
        self.op.add_option("--gaid", action="store", default="127.0.0.1:33014")
        self.op.add_option("--adid", action="store", default="127.0.0.1:33015")
        self.op.add_option("--dvid", action="store", default="127.0.0.1:33016")
        self.op.add_option("-w", "--workers", action="store", default=4)
        (self.opts, args) = self.op.parse_args()

        deviceapps = list()
        deviceapps.append("idfa\te7e1a50c0ec2747ca56cd9e1558c0d7c\t67.7835424444\t-22.8044005471\t1, 2, 3, 4\n")
        deviceapps.append("idfa\te7e1a50c0ec2747ca56cd9e1558c0d7d\t42\t-42\n")
        deviceapps.append("idfa\te7e1a50c0ec2747ca56cd9e1558c0d7d\t1\n")
        deviceapps.append("gaid\te7e1a50c0ec2747ca56cd9e1558c0d7c\t67.7835424444\t-22.8044005471\t1, 2, 3, 4\n")
        deviceapps.append("gaid\te7e1a50c0ec2747ca56cd9e1558c0d7d\t42\t-42\n")
        deviceapps.append("gaid\te7e1a50c0ec2747ca56cd9e1558c0d7d\t1\n")
        deviceapps.append("adid\te7e1a50c0ec2747ca56cd9e1558c0d7c\t67.7835424444\t-22.8044005471\t1, 2, 3, 4\n")
        deviceapps.append("adid\te7e1a50c0ec2747ca56cd9e1558c0d7d\t42\t-42\n")
        deviceapps.append("adid\te7e1a50c0ec2747ca56cd9e1558c0d7d\t1\n")
        deviceapps.append("dvid\te7e1a50c0ec2747ca56cd9e1558c0d7c\t67.7835424444\t-22.8044005471\t1, 2, 3, 4\n")
        deviceapps.append("dvid\te7e1a50c0ec2747ca56cd9e1558c0d7d\t42\t-42\n")
        deviceapps.append("dvid\te7e1a50c0ec2747ca56cd9e1558c0d7d\t1\n")
        deviceapps.append("dzid\te7e1a50c0ec2747ca56cd9e1558c0d7c\t67.7835424444\t-22.8044005471\t1, 2, 3, 4\n")
        # make test.tsv.gz file
        with gzip.open(TEST_FILE, mode="wt") as fd:
            for device in deviceapps:
                fd.write(device)

    def tearDown(self):
        os.remove("."+TEST_FILE)

    def test_fail_load(self):
        logging.basicConfig(filename=self.opts.log, filemode="wt",
                            level=logging.INFO if not self.opts.dry else logging.DEBUG,
                            format='%(levelname).1s %(message)s')
        memc_load.main(self.opts)
        # compare log
        etalon_lines = {0: "I Worker count: 4.",
                        1: "I Processing test.tsv.gz",
                        2: "E Unknown device type: dzid",
                        7: "E High error rate (0.6923076923076923 > 0.01). Failed load",
                        8: "I Renamed test.tsv.gz."}
        log = []
        with open(self.opts.log, mode="rt") as logfile:
            for line in logfile:
                log.append(line.rstrip())
        for key, val in etalon_lines.items():
            self.assertEqual(val, log[key])


if __name__ == "__main__":
    unittest.main()