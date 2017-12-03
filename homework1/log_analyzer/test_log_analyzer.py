import unittest
import log_analyzer as la
from collections import namedtuple


class TestLogAnalyzer(unittest.TestCase):

    def test_median(self):
        """test log_analyzer.median"""
        self.assertEqual(la.median([1, 2, 3, 4, 5]), 3)
        self.assertEqual(la.median([1, 2, 3, 4, 5, 6]), 3.5)
        self.assertNotEqual(la.median([1, 2, 3, 4, 5]), 5)
        self.assertNotEqual(la.median([1, 2, 3, 4, 5, 6]), 4.5)
        self.assertEqual(la.median(sorted([3, 2, 1, 4, 5])), 3)

    def test_get_last_log_file(self):
        """test log_analyzer.get_last_log"""
        la.config["LOG_DIR"] = "./test_log"
        self.assertEqual(la.get_last_log_file().fullname, "./test_log/nginx-access-ui.log-20170830")

    def test_make_report_name(self):
        """test log_analyzer.make_report_name"""
        files_dt = namedtuple("files_dt", "fullname date")
        file_dt = files_dt("nginx.log-20170730", 20170730)
        la.config["REPORT_DIR"] = "./test_reports"
        self.assertEqual(la.make_report_name(file_dt), "./test_reports/report-2017.07.30.html")

    def test_get_log_make_report(self):
        """test log_analyzer.get_last_log and log_analyzer.make_report_name together"""
        la.config["LOG_DIR"] = "./test_log"
        la.config["REPORT_DIR"] = "./test_reports"
        last_log = la.get_last_log_file()
        report_name = la.make_report_name(last_log)
        self.assertEqual(report_name, "./test_reports/report-2017.08.30.html")

    def test_parse_log(self):
        """test log_analyzer.parce_log"""
        la.config["LOG_DIR"] = "./test_log"
        last_log = la.get_last_log_file()
        result = la.parse_log(last_log.fullname)
        self.assertEqual(result[0], 5)
        self.assertEqual(result[1], 1.5)
        self.assertEqual(len(result[2]), 4)

    def test_process_data(self):
        """test log_analyzer.process_data"""
        la.config["LOG_DIR"] = "./test_log"
        last_log = la.get_last_log_file()
        data = la.parse_log(last_log.fullname)
        result = la.process_data(data)
        self.assertEqual(result[0]["count"], 2)
        self.assertEqual(result[0]["count_perc"], 40.000)
        self.assertEqual(result[0]["time_avg"], 0.450)
        self.assertEqual(result[0]["time_max"], 0.500)
        self.assertEqual(result[0]["time_sum"], 0.900)
        self.assertEqual(result[0]["time_perc"], 60.000)


if __name__ == '__main__':
    unittest.main()
