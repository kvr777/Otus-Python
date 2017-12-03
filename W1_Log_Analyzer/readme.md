# Log Analyzer

This repository contains a script for log files processing and html report generation.
As an input it gets the nginx log files (file structure is provided below), finds the last file,
calculates all required statistic and generates an html report
Input logfile structure is the following:
* '$remote_addr 
* $remote_user 
* $http_x_real_ip [$time_local] "
* $request" '
* '$status $body_bytes_sent "
* $http_referer" '
* '"$http_user_agent" 
* "$http_x_forwarded_for" 
* "$http_X_REQUEST_ID" 
* "$http_X_RB_USER" '
* '$request_time';

## Getting Started

At the first step it is necessary to copy and configure the following files:
1. log_analyzer.py - main script. Take --config as an optional parameter (please place full path + path name).
After copying this script it is necessary to setup initial configuration parameters inside the script (var "config", see parameters description below)
2. log_analyzer.conf - configuration file. You have to copy it in the directory with script file. File can be empty but
if it contains parameters with values they have priority under default config values. Also it is possible to put the conf file path as
with such as an --config parameter. In this case file located in this path has the highest priority. Config parameters are:
    * REPORT_SIZE - parameter to filter report data. Only urls with total request time > report_size are selected
    * REPORT_DIR - directory where reports are stored
    * LOG_DIR - directory with logfiles. These files are source for the script
    * LOGGING - directory where we store the file with all events occurred during the script execution
    * TSFILE - directory where special ts-file is stored. This file contains the timestamp when last html report was generated
3. report.html report template. You have to copy it in the directory with script file.
4. jquery.tablesorter.min.js js-script to process properly html reports. You have to copy it in the directory with reports.


### Prerequisites

Python version 3.6 and above

### Installing

No special installation procedure is required. You have to copy and setup the files from this repository as it was described above

## Running the tests

### Brief description

1. Unittest groups into four script. Each script is responsible for the testing of particular function of log_analyzer script. The name of testing script is "test_"+ function name
2. Below we provide the general logic of each test inside test script. If you need more detail you are welcome to read description within code:
    * **test_main**. This script tests general logic of log_analyzer script. Inside two tests:
        * test_no_exception_empty_log_dir - it checks whether the exceptions occur if the log dir is empty. If no exceptions, test pass
        * test_no_duplicate_report. This test check that log_analyzer doesn't create new report if the report with the latest date is already created
    * **test_parce_log**. This script check that function retrieve correct information from log
    * **test_create_report**. This script check that function generates correct statistic from url-time pair.
    * **test_create_ts_file** This script check that timestamp inside the ts file is the same as modification time of file

### Deployement testing environment
In order to run unittest you have to do the following steps:
1. Copy files with test_ mask and log_analyzer into same directory
2. Create folder 'tests' in this directory
3. Run tests. For example:

```
python -m unittest -v test_main
```


## License

This project is licensed under the MIT License
