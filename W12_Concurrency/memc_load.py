#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import sys
import glob
import logging
import collections
from optparse import OptionParser
from functools import partial
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2
# pip install python-memcached
import memcache
import threading
import multiprocessing as mp
import queue

logging.basicConfig(filename=None, level=logging.INFO,
                    format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')


NORMAL_ERR_RATE = 0.01
CONNECTION_TIMEOUT = 1
INSERTION_RETRIES = 5
WORKER_BATCH_SIZE = 100
READ_LOG_SIZE = 200000
WRITE_LOG_SIZE = 10000

AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])

lock = threading.Lock()


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    # t = str(int(time.time()))+'.'
    # os.rename(path, os.path.join(head, t+fn))
    # os.rename(path, os.path.join(head, "." + fn))


def get_packed (appsinstalled):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    return {key: packed}


def insert_appsinstalled(memc, packed_dict, dry_run=False):

    memc_addr = memc.servers[0].address

    if dry_run:
        for key in packed_dict.keys():
            logging.debug("%s - %s -> %s" % (memc_addr, key, str(packed_dict[key]).replace("\n", " ")))
    else:
        set_counter = 1
        notset_keys = list(packed_dict.keys())
        total_rows = len(notset_keys)
        while (set_counter <= INSERTION_RETRIES) and (len(notset_keys) > 0):
            try:
                filtered_packed_dict = {key: packed_dict[key] for key in notset_keys}
                notset_keys = memc.set_multi(filtered_packed_dict)

                if len(notset_keys) > 0:
                    logging.info("Attempt {} of {}".format(set_counter, INSERTION_RETRIES))
                    set_counter += 1

            except Exception as e:
                logging.exception("Cannot write to memc %s: %s" % (memc_addr, e))
                return [total_rows, len(notset_keys)]
        return [total_rows, len(notset_keys)]


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


def do_work(memc_addr, input_q, result_q, dry_run):
    w_process = w_error = 0
    insertion_counter = 1
    addr, port = memc_addr.split()
    memc = memcache.Client([(str(addr), int(port))], socket_timeout=CONNECTION_TIMEOUT, dead_retry=CONNECTION_TIMEOUT)
    while True:
        packed_dict = input_q.get()
        if packed_dict == 'end':
            result_q.put([w_process, w_error])
            logging.info('Finally processed {} rows in address {}'.format((w_process + w_error), memc_addr))
            input_q.task_done()
            return
        packed_dict_res = insert_appsinstalled(memc, packed_dict, dry_run)
        w_process += packed_dict_res[0]
        w_error += packed_dict_res[1]
        if (w_process + w_error) >= insertion_counter*WRITE_LOG_SIZE:
            logging.info('Processed {} rows in address {}'.format((w_process + w_error), memc_addr))
            insertion_counter += 1
        input_q.task_done()


def process_lines_in_files(fname, fd, device_memc, lines_batch_dict, workers_queue_dict):
    errors = 0
    a = 0
    for line in fd:
        line = line.strip()
        if not line:
            continue
        appsinstalled = parse_appsinstalled(line)
        packed_with_key = get_packed(appsinstalled)

        if not appsinstalled:
            errors += 1
            continue
        memc_addr = device_memc.get(appsinstalled.dev_type)
        if not memc_addr:
            errors += 1
            logging.error("Unknown device type: %s" % appsinstalled.dev_type)
            continue

        lines_batch_dict.get(appsinstalled.dev_type).update(packed_with_key)

        if len(lines_batch_dict.get(appsinstalled.dev_type)) >= WORKER_BATCH_SIZE:
            appsinstalled_dict = lines_batch_dict.get(appsinstalled.dev_type)
            workers_queue_dict.get(appsinstalled.dev_type).queue_in.put(appsinstalled_dict)
            lines_batch_dict[appsinstalled.dev_type] = {}

        a += 1
        if a % READ_LOG_SIZE == 0:
            logging.info('Read {} rows in file {}'.format(a, fname))

    return lines_batch_dict, errors


def process_file(options, fn):
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    processed = 0
    workers_queue_dict = {}
    WorkersQueueObj = collections.namedtuple('WorkersQueueObj', 'name queue_in queue_out')
    lines_batch_dict = {}

    for key in device_memc.keys():
        # create queue for writing rows in memcache and queue to store the results of writing
        wo = WorkersQueueObj(name=key, queue_in=queue.Queue(), queue_out=queue.Queue())
        workers_queue_dict[key] = wo
        lines_batch_dict[key] = dict()

        # launch thread for every thread
        t = threading.Thread(target=do_work, args=(device_memc.get(key), wo.queue_in, wo.queue_out, options.dry))
        t.daemon = True
        t.start()

    head, fname = os.path.split(fn)
    logging.info('Processing %s' % fname)
    fd = gzip.open(fn, 'rt')

    lines_batch_dict, errors = process_lines_in_files(fname, fd, device_memc, lines_batch_dict, workers_queue_dict)

    for key in lines_batch_dict.keys():
        appsinstalled_dict = lines_batch_dict.get(key)
        if len(appsinstalled_dict.keys()):
            workers_queue_dict.get(key).queue_in.put(appsinstalled_dict)
            lines_batch_dict[key] = {}
        workers_queue_dict.get(key).queue_in.put('end')

    for value in workers_queue_dict.values():
        w_line_process = value.queue_out.get()
        processed += w_line_process[0]
        errors += w_line_process[1]

    if not processed:
        fd.close()
        return fn

    err_rate = float(errors) / processed
    if err_rate < NORMAL_ERR_RATE:
        logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
    else:
        logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))
    fd.close()
    return fn


def main(options):

    logging.info("Memc loader started with options: %s" % options)
    files_to_process = glob.iglob(options.pattern)

    try:
        with mp.Pool(int(options.w)) as p:
            for x in p.imap(partial(process_file, options), files_to_process):
                dot_rename(x)

    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)


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
    op.add_option("--pattern", action="store", default="./data/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1 11212")
    op.add_option("--gaid", action="store", default="127.0.0.1 11212")
    op.add_option("--adid", action="store", default="127.0.0.1 11213")
    op.add_option("--dvid", action="store", default="127.0.0.1 11214")
    op.add_option('-w', help='Number of workers', default=None)
    (opts, args) = op.parse_args()
    if not opts.w:
        # assume we have two virtual cores per one physical. Spread process across virtual cores is inefficient, so we
        # use only physical cores
        opts.w = max(1, int(mp.cpu_count() / 2))

    logger = logging.getLogger(__name__)
    logger.setLevel(level=logging.INFO if not opts.dry else logging.DEBUG)

    if opts.test:
        prototest()
        sys.exit(0)

    main(opts)