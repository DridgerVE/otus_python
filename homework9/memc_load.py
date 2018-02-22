#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import sys
import glob
import logging
import collections
from optparse import OptionParser
import threading
import multiprocessing as mp
import time
import queue
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2
# pip install python-memcached
import memcache

NORMAL_ERR_RATE = 0.01
MEMCACHE_TIMEOUT = 1
_sentinel = object()
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])


class MemcacheWorker(threading.Thread):

    def __init__(self, queue, stats_queue, memc_addr, dry_run):
        threading.Thread.__init__(self)
        self._queue = queue
        self._stats_queuy = stats_queue
        self._memc_addr = memc_addr
        self._dry_run = dry_run
        self._errors = 0
        self._processed = 0
        self.daemon = True

    def run(self):
        memcache_connection = memcache.Client([self._memc_addr], socket_timeout=MEMCACHE_TIMEOUT)
        while True:
            try:
                task = self._queue.get(timeout=0.1)
                if task == _sentinel:
                    logging.info("{0} - {1}: records processed = {2}, records errors = {3}".format(
                        mp.current_process().name,
                        threading.current_thread().name,
                        self._processed, self._errors
                    ))
                    self._stats_queuy.put((self._processed, self._errors))
                    self._queue.task_done()
                    break
                else:
                    self._processed += 1
                    apps = parse_appsinstalled(task)
                    if not apps:
                        self._errors += 1
                        continue
                    if not insert_appsinstalled(memcache_connection, apps, self._dry_run):
                        self._errors += 1
                    self._queue.task_done()
            except queue.Empty:
                continue


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def insert_appsinstalled(memc, appsinstalled, dry_run=False):
    attempts = 5
    delay = 0.2
    cur_attempt = 1
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    # @TODO persistent connection
    # @TODO retry and timeouts!
    try:
        if dry_run:
            logging.debug("%s - %s -> %s" % (memc.servers[0], key, str(ua).replace("\n", " ")))
        else:
            result = memc.set(key, packed)
            while result == 0 and cur_attempt < attempts:
                time.sleep(delay)
                cur_attempt += 1
                result = memc.set(key, packed)
                delay *= 2
            return result != 0
    except Exception as e:
        logging.exception("Cannot write to memc %s: %s" % (memc.servers[0], e))
        return False
    return True


def parse_appsinstalled(line):
    line_parts = line.strip().split("\t")
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def process_handler(options):
    fn, device_memc, dry = options
    statistic = queue.Queue()
    workers = []
    pool_queue = {}

    for d_type, addr in device_memc.items():
        pool_queue[d_type] = queue.Queue()
        worker = MemcacheWorker(pool_queue[d_type], statistic, addr, dry)
        workers.append(worker)

    for worker in workers:
        worker.start()

    processed = errors = 0
    logging.info('Processing %s' % fn)
    with gzip.open(fn, mode="rt") as fd:
        for line in fd:
            line = line.strip()
            if not line:
                continue
            d_type = line.split()[0]
            if d_type not in device_memc:
                errors += 1
                processed += 1
                logging.error("Unknown device type: %s" % d_type)
                continue
            pool_queue[d_type].put(line)

    for d_type in device_memc:
        pool_queue[d_type].put(_sentinel)

    for worker in workers:
        worker.join()

    while not statistic.empty():
        p, e = statistic.get()
        processed += p
        errors += e
    if processed:
        err_rate = float(errors) / processed
        if err_rate < NORMAL_ERR_RATE:
            logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
        else:
            logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))
    return fn


def main(options):
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }
    logging.info("Worker count: {0}.".format(options.workers))
    th_pool = mp.Pool(int(options.workers))
    th_args = []
    for fn in glob.iglob(options.pattern):
        th_args.append((fn, device_memc, options.dry))
    for fn in th_pool.imap(process_handler, sorted(th_args, key=lambda x: x[0])):
        dot_rename(fn)
        logging.info("Renamed {0}.".format(fn))


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--pattern", action="store", default="/appsinstalled/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    op.add_option("-w", "--workers", action="store", default=4)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)
    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
