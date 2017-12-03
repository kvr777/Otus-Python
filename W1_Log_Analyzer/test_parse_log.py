import unittest
from log_analyzer import parse_log
import os, shutil, logging
from collections import defaultdict

logging.disable(logging.CRITICAL)

class TestParseLog(unittest.TestCase):

    """ Procedure:
        1. Create test file for parsing in './test' dir. This file mimics structure of real log files
        2. initiate control dict - this dict should be as a result of testing file
        3. Run parse_log function and get dict created by this function
        3.
        ---------
        Verification:
        3. Compare two dicts. Should be exact match
    """

    def setUp(self):
        # generate test file with 2 test lines. Real data were obfuscated
        self.test_lines = [
            '1.19.32 -  - [29/Jun +0300] "GET /api/v2/ HTTP/1.1" 200 927 "-" "Lynx/2 libw GNU" "-" "149" "dc" 0.390',
            '1.99.17 3b88  - [29/Ju +0300] "GET /api/1/ HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "14970" "-" 0.133'
        ]
        self.log_dir = os.path.abspath('./tests')
        self.last_log = 'nginx-access-ui.log-20171203'
        self.log_file_path = os.path.join(self.log_dir, self.last_log)
        with open(self.log_file_path, 'w') as file:
            for line in self.test_lines:
                file.write(line+'\n')
        self.control_dict = defaultdict(list)
        self.control_dict['/api/v2/'].append('0.390')
        self.control_dict['/api/1/'].append('0.133')

    def test_parse_log(self):
        self.dict_from_func = parse_log(self.log_dir, self.last_log)
        self.assertDictEqual(self.control_dict, self.dict_from_func)

    def tearDown(self):
            # Remove test logfile after the test
            os.remove(self.log_file_path)


if __name__ == '__main__':
    unittest.main()
