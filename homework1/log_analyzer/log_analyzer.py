#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import os
import gzip
import json
import sys
import logging
import datetime
import argparse
import glob
from collections import namedtuple
from string import Template

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "TEMPLATE": "./reports/report.html",
    "LOG_FILE": "log_analyzer.log",
    "TS_FILE": "log_analyzer.ts"
}


def get_last_log_file(cfg):
    """Find last logfile"""
    last_files = []
    files_dt = namedtuple("files_dt", "fullname date")
    for fullname in glob.glob(os.path.join(cfg["LOG_DIR"], "nginx-access-ui.log-*")):
        if os.path.isfile(fullname):
            pos = fullname.rfind("-")
            dt = int(fullname[pos+1:pos+9])
            file_dt = files_dt(fullname, dt)
            last_files.append(file_dt)
    if not last_files:
        return None
    last_file = max(last_files, key=lambda f: f.date)
    return last_file


def make_report_name(log_lastfile, cfg, report_format='html'):
    """Make report name"""
    date = datetime.datetime.strptime(str(log_lastfile.date), "%Y%m%d")
    return os.path.join(cfg["REPORT_DIR"], date.strftime("report-%Y.%m.%d.") + report_format)


def gen_readlog(filename):
    """Generator for read log"""
    log = gzip.open(filename, 'rb') if filename.endswith(".gz") else open(filename, 'rb')
    for line in log:
        yield line.strip().decode('utf-8')
    log.close()


def parse_log(filename):
    """Parse log, fill dict {url->list(...)}"""
    urls = {}
    total_count = 0
    total_time = 0
    num_line = 0
    count_pass_line = 0
    # method = ("OPTIONS", "GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "TRACE", "CONNECT")
    for line in gen_readlog(filename):
        if line == "":
            continue
        num_line += 1
        pos = line.find("]")
        if pos == -1 or 'HTTP' not in line:
            count_pass_line += 1
            continue
        line = line[pos+1:]
        pos = line.find("\"")
        line = line[pos+1:]
        pos = line.find("/")
        line = line[pos:].split()
        url, acstime = line[0], float(line[-1])
        total_count += 1
        total_time += acstime
        if url not in urls:
            urls[url] = [acstime]
        else:
            urls[url].append(acstime)
    if num_line == count_pass_line:
        logging.error("Can't parse log {}".format(filename))
    return total_count, total_time, urls


def median(values):
    """Compute median for sorted list"""
    if len(values) % 2 == 0:
        return (values[(len(values) // 2) - 1] + values[len(values) // 2]) / 2.0

    elif len(values) % 2 != 0:
        return values[int((len(values) // 2))]


def process_data(data, cfg):
    """Process data"""
    count_digits = 3
    total_count, total_time, urls = data
    result = []
    for url in urls:
        count = len(urls[url])
        count_perc = round(100 * float(count) / total_count, count_digits)
        time_avg = round(sum(urls[url]) / count, count_digits)
        time_max = round(max(urls[url]), count_digits)
        time_med = round(median(sorted(urls[url])), count_digits)
        time_sum = round(sum(urls[url]), count_digits)
        time_perc = round(100 * time_sum / total_time, count_digits)
        result.append({
            "url": url,
            "count": count,
            "count_perc": count_perc,
            "time_avg": time_avg,
            "time_max": time_max,
            "time_med": time_med,
            "time_perc": time_perc,
            "time_sum": time_sum,
        })
    result.sort(key=lambda f: f['time_sum'], reverse=True)
    return result[:cfg["REPORT_SIZE"]]


def save_report(filename, data):
    """Save report"""
    if not data:
        return None
    with open(config['TEMPLATE'], 'r') as tmpl:
        lines = tmpl.read()
    s = Template(lines)
    s = s.safe_substitute(table_json=json.dumps(data))
    with open(filename, 'w') as rpt:
        rpt.write(s)


def read_config(filename):
    """Read config"""
    with open(filename, 'r') as conf:
        result = {}
        for line in conf:
            tmp = line.split(':')
            result[tmp[0]] = tmp[1].strip()
        if "REPORT_SIZE" in result:
            result["REPORT_SIZE"] = int(result["REPORT_SIZE"])
    return result


def main(cfg):
    """python log_analyzer.py --config filename.conf"""
    log = get_last_log_file(cfg)
    logging.info("Find last log: \'{}\'.".format(log.fullname))
    report = make_report_name(log, cfg)
    logging.info("Make report filename: \'{}\'.".format(report))
    if os.path.exists(report):
        logging.info('Report already exists \'{0}\'.'.format(report))
        return 0
    logging.info("Parse log")
    data = parse_log(log.fullname)
    logging.info("Analyze start")
    result = process_data(data, cfg)
    logging.info("Save report")
    save_report(report, result)
    logging.info("log_analyzer is finished")
    with open(cfg["TS_FILE"], 'w') as ts:
        ts.write(str(datetime.datetime.now().timestamp()))

if __name__ == "__main__":
    # parsing arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", dest="conf", type=str, default="log_analyzer.conf")
    args = parser.parse_args()

    # parse config
    config.update(read_config(args.conf))

    logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S',
                        level=logging.INFO, filename=config["LOG_FILE"])
    try:
        main(config)
    except:
        logging.exception("Runtime error", exc_info=True)
        sys.exit(1)
