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


# config = {
#     "REPORT_SIZE": 1000,
#     "REPORT_DIR": "./reports",
#     "LOG_DIR": "./log",
#     "TEMPLATE": "./reports/report.html"
# }


def get_last_log_file():
    """Find last logfile"""
    last_files = []
    for root, dirs, files in os.walk(config["LOG_DIR"]):
        for name in files:
            fullname = os.path.join(root, name)
            if "nginx" in name and "access" in name and "log" in name:
                # find last symbol '-'
                pos = name.rfind("-")
                if pos == -1:
                    return None
                dt = int(name[pos+1:pos+9])
                last_files.append({"fullname": fullname, "date": dt})
    if last_files == []:
        return None
    last_file = max(last_files, key=lambda f: f["date"])
    return last_file["fullname"]


def get_open_func(filename):
    """Get open func depend on ext file"""
    if filename.endswith(".gz"):
        return gzip.open
    else:
        return open


def make_report_name(log_filename, report_format='html'):
    """Make report name"""
    pos = log_filename.rfind("-")
    if pos == -1:
        return None
    try:
        dt = [log_filename[pos + 1:pos + 5], log_filename[pos + 5:pos + 7], log_filename[pos + 7:pos + 9]]
        report_name = 'report-{0}.{1}.{2}.{3}'.format(dt[0],  dt[1], dt[2], report_format)
        return os.path.join(config['REPORT_DIR'], report_name)
    except Exception:
        return None


def gen_readlog(filename):
    """Generator for read log"""
    open_func = get_open_func(filename)
    log = open_func(filename, 'r')
    for line in log:
        yield line
    log.close()


def parse_log(filename):
    """Parse log, fill dict {url->list(...)}"""
    urls = {}
    total_count = 0
    total_time = 0
    for line in gen_readlog(filename):
        line = line.decode('utf-8').strip()
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
    """Compute median"""
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
    result.sort(key=lambda f: f['time_sum'], reverse=True)
    return result


def save_report(filename, data):
    """Save report"""
    tmpl = open(config['TEMPLATE'], 'r')
    rpt = open(filename, 'w')
    for line in tmpl:
        if "$table_json" in line:
            rpt.write(line.replace("$table_json", json.dumps(data)))
        else:
            rpt.write(line)
    rpt.close()
    tmpl.close()


def read_config(filename):
    conf = open(filename, 'r')
    result = {}
    for line in conf:
        tmp = line.split(':')
        result[tmp[0]] = tmp[1].strip()
    conf.close()
    if "REPORT_SIZE" in result:
        result["REPORT_SIZE"] = int(result["REPORT_SIZE"])
    return result


def main(log, report):
    """python log_analyzer.py --config filename.conf"""
    data = parse_log(log)
    result = process_data(data)
    save_report(report, result)

if __name__ == "__main__":
    # default log
    conf_file = "log_analyzer.conf"
    if len(sys.argv) == 3:
        if sys.argv[1] == "--config":
            conf_file = sys.argv[2]

    # Conf file not found
    if not os.path.isfile(conf_file):
        sys.stderr.write('Can\'t find conf file {0}.\n'.format(conf_file))
        sys.stderr.flush()
        sys.exit(1)

    config = read_config(conf_file)
    if "TEMPLATE" not in config:
        config["TEMPLATE"] = "./reports/report.html"

    last_log = get_last_log_file()
    report_filename = make_report_name(last_log)

    # can't find date in log filename
    if not report_filename:
        sys.stderr.write('Can\'t find date in {0} filename.\n'.format(last_log))
        sys.stderr.flush()
        sys.exit(1)

    # report already exists
    if os.path.isfile(report_filename):
        sys.stderr.write('Report {0} already exist.\n'.format(report_filename))
        sys.stderr.flush()
        sys.exit(1)

    main(last_log, report_filename)
