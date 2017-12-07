import unittest
import os
import log_analyzer as la
from collections import namedtuple

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./test_reports",
    "LOG_DIR": "./test_log",
    "TEMPLATE": "./reports/report.html",
    "LOG_FILE": "log_analyzer.log",
    "TS_FILE": "log_analyzer.ts",
    "ERROR_TRESHOLD": 0.75
}


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
        self.assertEqual(la.get_last_log_file(config).fullname, "./test_log/nginx-access-ui.log-20170830")

    def test_make_report_name(self):
        """test log_analyzer.make_report_name"""
        files_dt = namedtuple("files_dt", "fullname date")
        file_dt = files_dt("nginx.log-20170730", 20170730)
        self.assertEqual(la.make_report_name(file_dt, config), "./test_reports/report-2017.07.30.html")

    def test_get_log_make_report(self):
        """test log_analyzer.get_last_log and log_analyzer.make_report_name together"""
        last_log = la.get_last_log_file(config)
        report_name = la.make_report_name(last_log, config)
        self.assertEqual(report_name, "./test_reports/report-2017.08.30.html")

    def test_parse_log(self):
        """test log_analyzer.parce_log"""
        last_log = la.get_last_log_file(config)
        result = la.parse_log(last_log.fullname, config)
        self.assertEqual(result[0], 5)
        total_sum = 0
        for el in result[2]:
            total_sum += sum(result[2][el])
        self.assertEqual(result[1], total_sum)
        self.assertEqual(result[1], 1.5)
        self.assertEqual(len(result[2]), 4)

    def test_process_data(self):
        """test log_analyzer.process_data"""
        last_log = la.get_last_log_file(config)
        data = la.parse_log(last_log.fullname, config)
        result = la.process_data(data, config)
        self.assertEqual(result[0]["count"], 2)
        self.assertEqual(result[0]["count_perc"], 40.000)
        self.assertEqual(result[0]["time_avg"], 0.450)
        self.assertEqual(result[0]["time_max"], 0.500)
        self.assertEqual(result[0]["time_sum"], 0.900)
        self.assertEqual(result[0]["time_perc"], 60.000)

    def test_parse_log_with_error(self):
        result = la.parse_log(os.path.join(config["LOG_DIR"], "nginx-access-ui.log-20170730"), config)
        total_sum = 0
        for el in result[2]:
            total_sum += sum(result[2][el])
        self.assertEqual(result[0], 4)
        self.assertEqual(result[1], total_sum)
        self.assertEqual(result[1], 1.1)
        self.assertEqual(len(result[2]), 3)

    def test_parse_log_with_fatal_error(self):
        result = la.parse_log(os.path.join(config["LOG_DIR"], "nginx-access-ui.log-20170630"), config)
        self.assertEqual(result, None)

    def test_parse_log_without_request_time(self):
        result = la.parse_log(os.path.join(config["LOG_DIR"], "nginx-access-ui.log-20170530"), config)
        self.assertEqual(result, None)

    def test_parse_log_with_error_treshold(self):
        result = la.parse_log(os.path.join(config["LOG_DIR"], "nginx-access-ui.log-20170430"), config)
        self.assertEqual(result, None)

    def test_parse_log_with_bad_requests(self):
        result = la.parse_log(os.path.join(config["LOG_DIR"], "nginx-access-ui.log-20170330"), config)
        self.assertEqual(result, None)

    def test_parse_log_without_uri(self):
        result = la.parse_log(os.path.join(config["LOG_DIR"], "nginx-access-ui.log-20170230"), config)
        self.assertEqual(result, None)

if __name__ == '__main__':
    unittest.main()
