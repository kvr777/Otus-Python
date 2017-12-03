import unittest
from log_analyzer import main as mn
import os
import logging

logging.disable(logging.CRITICAL)

class TestMain(unittest.TestCase):

    def setUp(self):

        # define directory where log and report files are located (only for test purposes)
        self.dir = os.path.abspath('./tests')

        # parameters to create fake log and report files (see description of test_no_duplicate_report function)
        self.last_log_date = '20171203'

        self.last_log_name = 'nginx-access-ui.log-' + str(self.last_log_date)
        self.log_file_path = os.path.join(self.dir, self.last_log_name)

        self.last_report_name = 'report_' + str(self.last_log_date) + '.html'
        self.report_file_path = os.path.join(self.dir, self.last_report_name)




    def test_no_exception_empty_log_dir(self):

        """ Procedure:
            1. remove log files from './tests' directory
            1. pass to main() function test_log_analyzer.conf as a config.
            In this config file directory for logs is './tests'
            2. run main() function and get result.
            ---------
            Verification:
            3. If an exception wasn't raised during script running, it handles correctly the cases when no logs
        """

        # remove log files from './tests' directory
        for file in os.listdir(self.dir):
            if file.startswith('nginx-access-ui.log-'):
                os.remove(os.path.join(self.dir, file))

        # run script
        try:
            mn(["--config", "test_log_analyzer.conf"])
        except:
            self.fail("script fail with empty log")


    def test_no_duplicate_report(self):

        """ Procedure:
                    1. remove log and reports files from './tests' directory
                    2. pass to main() function test_log_analyzer.conf as a config.
                    In this config file directories for logs and reports are './tests'
                    3. create empty log and reports files that processed by script as a natural log and report files
                    4. store modification time of fake report file
                    5. pass to main() function test_log_analyzer.conf as a config.
                    In this config file directory for logs is './tests'. Then run main func
                    6. store modification time of report file after script running
                    ---------
                    Verification:
                    3. Compare report file modification time before and after script running. If both are the same,
                    test passed
                """



        if os.path.isfile(self.log_file_path):
            os.remove(self.log_file_path)
        if os.path.isfile(self.report_file_path):
            os.remove(self.report_file_path)

        log_file = open(self.log_file_path, 'w')
        log_file.close()
        report_file = open(self.report_file_path, 'w')
        report_file.close()
        report_mtime_initial = os.path.getmtime(self.report_file_path)
        self.full_path = os.path.abspath('test_log_analyzer.conf')
        mn(["--config", "test_log_analyzer.conf"])
        report_mtime_after = os.path.getmtime(self.report_file_path)
        self.assertEqual(report_mtime_initial, report_mtime_after)

    def tearDown(self):
        if os.path.isfile(self.log_file_path):
            os.remove(self.log_file_path)
        if os.path.isfile(self.report_file_path):
            os.remove(self.report_file_path)

if __name__ == '__main__':
    unittest.main()
