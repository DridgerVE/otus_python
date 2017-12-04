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
from collections import namedtuple
import argparse
import glob

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "TEMPLATE": "./reports/report.html",
    "LOG_FILE": "log_analyzer.log",
    "TS_FILE": "log_analyzer.ts"
}


def get_last_log_file():
    """Find last logfile"""
    last_files = []
    files_dt = namedtuple("files_dt", "fullname date")
    for fullname in glob.glob(os.path.join(config["LOG_DIR"], "nginx-access-ui.log-*")):
        if os.path.isfile(fullname):
            pos = fullname.rfind("-")
            dt = int(fullname[pos+1:pos+9])
            file_dt = files_dt(fullname, dt)
            last_files.append(file_dt)
    if not last_files:
        return None
    last_file = max(last_files, key=lambda f: f.date)
    return last_file


def make_report_name(log_lastfile, report_format='html'):
    """Make report name"""
    date = datetime.datetime.strptime(str(log_lastfile.date), "%Y%m%d")
    return os.path.join(config['REPORT_DIR'], date.strftime("report-%Y.%m.%d.") + report_format)


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
    for line in gen_readlog(filename):
        line = line.strip()
        # parse url and access time
        pos = line.find("]")
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
    return total_count, total_time, urls


def median(values):
    """Compute median for sorted list"""
    if len(values) % 2 == 0:
        return (values[(len(values) // 2) - 1] + values[len(values) // 2]) / 2.0

    elif len(values) % 2 != 0:
        return values[int((len(values) // 2))]


def process_data(data):
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
    result.sort(key=lambda f: f['time_avg'], reverse=True)
    if len(result) > config["REPORT_SIZE"]:
        result = result[:config["REPORT_SIZE"]]
    result.sort(key=lambda f: f['time_sum'], reverse=True)
    return result


def save_report(filename, data):
    """Save report"""
    with open(config['TEMPLATE'], 'r') as tmpl:
        with open(filename, 'w') as rpt:
            for line in tmpl:
                if "$table_json" in line:
                    rpt.write(line.replace("$table_json", json.dumps(data)))
                else:
                    rpt.write(line)


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


def main():
    """python log_analyzer.py --config filename.conf"""
    logging.info("Find last log")
    log = get_last_log_file()
    logging.info("Make report filename")
    report = make_report_name(log)
    if os.path.exists(report):
        logging.info('Report already exists \'{0}\'.'.format(report))
    else:
        logging.info("Parse log")
        data = parse_log(log.fullname)
        logging.info("Analyze start")
        result = process_data(data)
        logging.info("Save report")
        save_report(report, result)
        logging.info("log_analyzer is finished")
        ts = open(config["TS_FILE"], 'w')
        ts.write(str(datetime.datetime.now().timestamp()))
        ts.close()

if __name__ == "__main__":
    # parsing arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", dest="conf", type=str, default="log_analyzer.conf")
    args = parser.parse_args()
    conf_file = args.conf

    # Conf file not found or no parse
    try:
        config = read_config(conf_file)
    except:
        logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S',
                            level=logging.INFO)
        logging.error('Can\'t parse conf file \'{0}\'.'.format(conf_file))
        sys.exit(1)

    logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S',
                        level=logging.INFO, filename=config["LOG_FILE"])
    try:
        main()
    except:
        logging.exception("Run-time error", exc_info=True)
        sys.exit(1)
