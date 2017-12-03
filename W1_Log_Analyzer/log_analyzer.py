#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import os
import re
import argparse
import configparser
import gzip
from collections import defaultdict, OrderedDict
from statistics import median
from shutil import copy2
import time
import logging

def_config = {
    "REPORT_SIZE": 555,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LOGGING": "./monitoring",
    "TSFILE": "./monitoring"
    }


def parse_config (config, config_path):
    # update default config from file
    file_config = configparser.ConfigParser()
    file_config.read(config_path)
    file_conf_args = [key for key in file_config['MAIN']]
    for file_conf_arg in file_conf_args:
        config[file_conf_arg.upper()] = file_config['MAIN'][file_conf_arg]

    # parse config
    try:
        report_size, report_dir, log_dir, logging_dir, ts_file_dir = int(config['REPORT_SIZE']), \
                                                                     config['REPORT_DIR'], \
                                                                     config['LOG_DIR'], \
                                                                     config['LOGGING'], \
                                                                     config['TSFILE']
        return report_size, report_dir, log_dir, logging_dir, ts_file_dir
    except:
        raise


def find_last_log(log_dir):
    """ Searching last log file. This file start with mask 'nginx-access-ui.log-' and contains the date in name.
    This date has a format YYYYMMDD.

    Args:
        log_dir: Directory path with log files

    Returns:
        last_log: the file name with the latest date
        last_log_date: the date in the found log file (as a string and in format YYYYMMDD
    """

    # find the log files by mask in name. Then select one with the last date
    mask = 'nginx-access-ui.log-'

    last_log = None
    last_log_date = 0

    for file in os.listdir(log_dir):
        if file.startswith(mask):
            log_temp = re.search(str(mask)+'(\d{4}\d{2}\d{2})\.?', file)
            if log_temp is not None:
                if int(log_temp.group(1)) > last_log_date:
                    last_log = file
                    last_log_date = int(log_temp.group(1))

    return last_log, last_log_date


def parse_log(log_dir, last_log):
    """ This func retrieve an url and its request time
    At the first step, depending on file format, we select a function for file opening (gz or standard).
    Then we process each line of the log and retrieve url(7-th column) and time (the last column) from the log.
    Args:
        log_dir: log directory
        last_log: log with the latest date in the name

    Returns:
        time_log: dict with url as a key and list of times as a values
    """
    if last_log.endswith(".gz"):
        myfile = gzip.open(os.path.join(log_dir, last_log), 'rb')
    else:
        try:
            myfile = open(os.path.join(log_dir, last_log),  'rb')
        except:
            logging.error("An Error Occurred While Opening the Log File")
            raise
    time_log = defaultdict(list)
    for line in myfile.readlines():
        splitted = line.split()
        url = splitted[6].decode("utf-8")
        url = url.strip('"')
        response_time = splitted[-1].decode("utf-8")
        time_log[url].append(response_time)
    # Closes the file
    myfile.close()
    return time_log


def create_report(time_log, report_size):

    """ This function generates the data which have to placed in html report
    At the first step we calculate the aggregated statistic for all urls:
        total number of pages' visits
        total time to process requests for all pages
    Then, line by line we calculate necessary statistic by every url:
        total time to process requests for this url
        total number of url's visits
        % of number url's visits to number of all pages' visits
        average, max and median time to process requests for this url
        % of total time to process requests for this url  to total request time for all pages
    After, we apply the filter by report_size parameter. Only urls with total request time > report_size are selected.
    For this column we apply descending sorting as well.
    Finally we save report data in the format which is suitable for placing in html template

    Args:
        report_size: parameter to filter report data. Only urls with total request time > report_size are selected
        time_log: dict with url as a key and list of times as a values

    Returns:
        filtered_report: data which have to be placed in html report
    """

    # calculate the statistic for all urls
    total_count = sum([len(v) for (k, v) in time_log.items()])
    total_sum = sum([sum([float(x) for x in v]) for (k, v) in time_log.items()])

    # create report as a dict. The key is an url, values is the target statistic for the report
    report = defaultdict(list)
    for log, times in time_log.items():
        time_sum = sum([float(x) for x in times])
        count = len(times)
        count_perc = (count / total_count) * 100
        time_avg = time_sum / count
        time_max = max([float(x) for x in times])
        time_med = median([float(x) for x in times])
        time_perc = (time_sum / total_sum) * 100
        report[log].append(count)
        report[log].append(round(count_perc, 3))
        report[log].append(round(time_avg, 3))
        report[log].append(round(time_max, 3))
        report[log].append(round(time_med, 3))
        report[log].append(round(time_perc, 3))
        report[log].append(round(time_sum, 3))

    # Filter and sort rows
    filtered_report_temp = OrderedDict((k, v) for k, v in report.items() if v[6] >= report_size)
    filtered_report_temp = OrderedDict(sorted(filtered_report_temp.items(), key=lambda k_v: k_v[1][6], reverse=True))

    # transform to format which is suitable for html report

    filtered_report = []
    for (k, v) in filtered_report_temp.items():
        sample = {}
        sample = {"count": v[0],
                  "time_avg": v[2],
                  "time_max": v[3],
                  "time_sum": v[6],
                  "url": k,
                  "time_med": v[4],
                  "time_perc": v[5],
                  "count_perc": v[1]
                  }
        filtered_report.append(sample)

    return filtered_report

def generate_html_report (filtered_report, report_dir,  last_report_name):
    """ Function to generate html report

    Args:
        report_dir: directory where reports are stored
        filtered_report: data which have to be placed in html report
        last_report_name: report filename (this reports is not exist and has to be generated)

    Returns:
        True if function successfully executed. Raise exception otherwise
    """

    # copy html template and create html file with '_temp' mask
    try:
        copy2('report.html', os.path.join(report_dir, str('temp_') + last_report_name))
    except:
        logging.error("Report template not found")
        raise

    # open temporary html file and copy his content
    html_report = open(os.path.join(report_dir, str('temp_') + last_report_name), 'r', encoding='utf-8')
    html_data = html_report.read()
    html_report.close()

    # replace '$table_json' placeholder by the data from filtered_report variable
    newdata = html_data.replace('$table_json', str(filtered_report))

    # open temporary html file and inject report data
    html_report = open(os.path.join(report_dir, str('temp_') + last_report_name), 'w')
    html_report.write(newdata)
    html_report.close()

    # if all was ok, remove temp_ mask from report's filename
    os.rename(os.path.join(report_dir, str('temp_') + last_report_name),
              os.path.join(report_dir, last_report_name))

    return True


def generate_ts_file(ts_file_dir):
    """ function to create ts-file with the timestamp when last html report was generated.

    Args:
        ts_file_dir: directory where log_analyzer.ts is stored

    Returns:
        True if function successfully executed. Raise exception otherwise
    """

    ts = time.asctime()
    try:
        file = open(os.path.join(ts_file_dir, "log_analyzer.ts"), 'w')
        file.write(ts)
        file.close()
        return True
    except:
        logging.error("An Error Occurred While Generating log_analyzer.ts")
        raise


def main(cmdline=None):

    config = def_config
    # set up arguments and argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to configuration file. Please use path+filename notation')

    # case of usual working: we pass config through command line or use default config file
    if cmdline is None:
        args = parser.parse_args()
        if args.config:
            config_path = config
        else:
            config_path = os.path.abspath('log_analyzer.conf')

    # in case if we use unittests, we pass cmd args as an usual function parameter
    else:
        args = parser.parse_args(cmdline)
        config_path = args.config

    report_size, \
    report_dir, \
    log_dir, \
    logging_dir, \
    ts_file_dir = parse_config(config, config_path)

    logging.basicConfig(filename=os.path.join(logging_dir, 'log_analyzer.log'),
                        level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')

    # Find the last log file. if file wasn't found, handle this situation
    last_log, last_log_date = find_last_log(log_dir)

    if not last_log:
        return logging.error("Last Log Report not found in log directory")

    # check does html report already exist and handle these situations
    last_report_name = 'report_' + str(last_log_date) + '.html'

    if os.path.isfile(os.path.join(report_dir, last_report_name)):
        return logging.info("Last Log Report Already Exists. Script Execution Will Be Stopped")
    else:
        logging.info("The Last Log Has Been Found. Report Creation Process Will Be Initiated")

    # extract data from the last log file.
    time_log = parse_log(log_dir, last_log)
    logging.info("Last Log Data Has Been Extracted")

    # Generate report data
    filtered_report = create_report(time_log, report_size)
    logging.info("Reports' Data Has Been Generated")

    # Get html template, copy the report data and generate the html-report
    generate_report_flag = generate_html_report(filtered_report, report_dir, last_report_name)
    if generate_report_flag:
        logging.info("New Report Has Been Generated")

    # ts-file generation
    if generate_ts_file(ts_file_dir):
        logging.info("log_analyzer.ts has been successfully updated")


if __name__ == "__main__":
    main()
