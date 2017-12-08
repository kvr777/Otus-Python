#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import os
import re
import sys
import argparse
import configparser
import gzip
from collections import defaultdict, namedtuple
from statistics import median
import time
import logging

def_config = {
    "REPORT_SIZE": 555,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LOGGING": 'Noe',
    "TSFILE": "./monitoring",
    "ERR_PARSE_RATE": 0.2
    }


def parse_config (config, config_path):
    # update default config from file
    file_config = configparser.ConfigParser()
    file_config.read(config_path)

    for file_conf_arg in file_config['MAIN'].keys():
        config[file_conf_arg.upper()] = file_config['MAIN'][file_conf_arg]

    # try to parse config. Though we pass dict as a result, it is useful to discover missing parameters in early stage
    try:
        report_size = int(config['REPORT_SIZE'])
        report_dir = config['REPORT_DIR']
        log_dir = config['LOG_DIR']
        logging_dir = config['LOGGING']
        ts_file_dir = config['TSFILE']
        err_parce_rate = int(config['ERR_PARSE_RATE'])
        return config
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
    LastLogFeatures = namedtuple('LastLogFeatures', ['last_log', 'last_log_date'])
    mask = 'nginx-access-ui.log-'

    last_log = None
    last_log_date = 0

    for dir_file in os.listdir(log_dir):
        if dir_file.startswith(mask):
            log_temp = re.search(mask+'(\d{4}\d{2}\d{2})\.?', dir_file)
            if log_temp is not None:
                if int(log_temp.group(1)) > last_log_date:
                    last_log = dir_file
                    last_log_date = int(log_temp.group(1))
    last_log_features = LastLogFeatures(last_log, last_log_date)
    return last_log_features


def parse_log(last_log_with_path, err_parse_rate):
    """ This func retrieve an url and its request time
    At the first step, depending on file format, we select a function for file opening (gz or standard).
    Then we process each line of the log and retrieve url(7-th column) and time (the last column) from the log.
    Args:
        last_log_with_path: path to logfile with the latest date in the name

    Returns:
        parsed line with url and processed times as well as number of good processed lines and total processed lines
    """
    if last_log_with_path.endswith(".gz"):
        last_log_file = gzip.open(last_log_with_path, 'rt', encoding='utf-8')
    else:
        try:
            last_log_file = open(last_log_with_path, encoding='utf-8')
        except:
            logging.error("An error occurred while opening the log file")
            raise
    processed_lines = 0
    total_lines = 0
    for line in last_log_file:
        try:
            splitted = line.split()
            url = splitted[6]
            url = url.strip('"')
            response_time = splitted[-1]
            total_lines += 1
            processed_lines += 1
            yield url, response_time
        except:
            total_lines += 1

    # Closes the file
    last_log_file.close()

    # compare current error rate with threshold. Stop if exceeded
    if (1 - processed_lines/float(total_lines)) > err_parse_rate:
        logging.error("Percentage of wrong lines in the file exceeded defined threshold. "
                      "Script execution will be stopped ")
        sys.exit()


def create_report(last_log_with_path,err_parse_rate, report_size):

    """ This function generates the data which have to placed in html report
    At the first step we calculate the aggregated statistic for all urls and form dict with url as a key
    and list of values as a time:
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
        last_log_with_path: path to logfile with the latest date in the name
        report_size: parameter to filter report data.
        Only urls with total request time > report_size are selected
        err_parse_rate: maximum number of wrong lines in log. If this threshold exceeds the execution will be stopped


    Returns:
        filtered_report: data which have to be placed in html report
    """

    # calculate the statistic for all urls
    total_count = total_sum = 0
    parsed_lines = parse_log(last_log_with_path,err_parse_rate)
    time_log = defaultdict(list)
    for url, response_time in parsed_lines:
        time_log[url].append(response_time)
        total_count += 1
        total_sum += float(response_time)

    # create report as a dict. The key is an url, values is the target statistic for the report
    report = []
    for log, times in time_log.items():
        time_sum = sum([float(x) for x in times])
        count = len(times)
        count_perc = (count / total_count) * 100
        time_avg = time_sum / count
        time_max = max([float(x) for x in times])
        time_med = median([float(x) for x in times])
        time_perc = (time_sum / total_sum) * 100
        if round(time_sum, 3) >= int(report_size):
            sample = {"count": count,
                      "time_avg": round(time_avg, 3),
                      "time_max": round(time_max, 3),
                      "time_sum": round(time_sum, 3),
                      "url": log,
                      "time_med": round(time_med, 3),
                      "time_perc": round(time_perc, 3),
                      "count_perc": round(count_perc, 3)
                      }
            report.append(sample)

    # Filter rows
    filtered_report = sorted(report, key=lambda k: k['time_sum'], reverse=True)

    return filtered_report


def generate_html_report(filtered_report, report_dir,  last_report_name):

    """ Function to generate html report

    Args:
        report_dir: - directory where reports are stored
        filtered_report: data which have to be placed in html report
        last_report_name: report filename (this reports is not exist and has to be generated)

    Returns:
        True if function successfully executed. Raise exception otherwise
    """

    try:
        # open temporary html file and copy his content
        with open('report.html', 'r', encoding='utf-8') as html_template:
            html_data = html_template.read()
    except:
        logging.error("Report template not found")
        raise
    try:
        # replace '$table_json' placeholder by the data from filtered_report variable
        newdata = html_data.replace('$table_json', str(filtered_report))

        # create temporary html file and inject report data
        with open(os.path.join(report_dir, str('temp_') + last_report_name), 'w', encoding='utf-8') as html_report:
            html_report.write(newdata)

        # if all was ok, remove temp_ mask from report's filename
        os.rename(os.path.join(report_dir, str('temp_') + last_report_name),
                  os.path.join(report_dir, last_report_name))

        logging.info("New report has been generated")
    except:
        logging.error("An error occurred while creating the html-report")


def generate_ts_file(ts_file_dir):
    """ function to create ts-file with the timestamp when last html report was generated.

    Args:
        ts_file_dir: directory where log_analyzer.ts is stored

    Returns:
        None if function successfully executed. Raise exception otherwise
    """

    ts = time.asctime()
    try:
        with open(os.path.join(ts_file_dir, "log_analyzer.ts"), 'w', encoding='utf-8') as file:
            file.write(ts)
        logging.info("log_analyzer.ts has been successfully updated")
    except:
        logging.error("An error occurred while generating log_analyzer.ts")
        raise


def main(config):

    # Find the last log file. if file wasn't found, handle this situation
    last_log_features = find_last_log(config['LOG_DIR'])

    if not last_log_features.last_log:
        return logging.info("Any logfile wasn't found in log directory")

    # check does html report already exist and handle these situations
    last_report_name = 'report_' + str(last_log_features.last_log_date) + '.html'

    if os.path.isfile(os.path.join(config['REPORT_DIR'], last_report_name)):
        return logging.info("Last log report already exists. Script execution will be stopped")
    else:
        logging.info("The last log has been found. Report creation process will be initiated")

    # Generate report data
    filtered_report = create_report(os.path.join(config['LOG_DIR'], last_log_features.last_log),
                                    config['ERR_PARSE_RATE'], config['REPORT_SIZE'])
    logging.info("Reports' data has been generated")

    # Get html template, copy the report data and generate the html-report
    generate_html_report(filtered_report, config['REPORT_DIR'], last_report_name)

    # ts-file generation
    generate_ts_file(config['TSFILE'])


if __name__ == "__main__":

    # set up arguments and argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',
                        help='Path to configuration file. Please use path+filename notation',
                        default=os.path.abspath('log_analyzer.conf'))

    # parse config file
    args = parser.parse_args()
    config_path = args.config
    config = parse_config(def_config, config_path)

    # set up logging. If directory for logging is not defined, use stdout
    logging.basicConfig(filename=config['LOGGING'] if len(str(config['LOGGING'])) > 4 else None,
                        level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    try:
        main(config)
    except Exception:
        logging.exception("Unexpected error occurred")
        raise
