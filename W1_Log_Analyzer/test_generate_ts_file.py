import unittest
from log_analyzer import generate_ts_file
import os, shutil, logging
import time, datetime

logging.disable(logging.CRITICAL)


class TestGenerateTsFile(unittest.TestCase):

    """ Procedure:
        1. Run generate_ts_file function with './test' path
        2. Extract timestamp from content and convert it to seconds
        3. Get modification time parameters from file properties (in seconds as a default)
        ---------
        Verification:
        3. Compare two times. The margin between these times should not exceed two seconds
    """

    def setUp(self):
        # define dir for test case, run generate_ts_file() func and store file path into variable
        self.dir = os.path.abspath('./tests')
        generate_ts_file(self.dir)
        self.ts_path = os.path.join(self.dir, 'log_analyzer.ts')

    def test_generate_ts_file(self):
        # extract date from file content
        ts_file = open(self.ts_path, 'r')
        ts_timestamp_inside = ts_file.read()
        ts_file.close()

        # convert to seconds since epoch
        ts_timestamp_inside = time.strptime(ts_timestamp_inside)
        ts_timestamp_inside = time.mktime(ts_timestamp_inside)

        # get file modification time
        ts_mtime = os.path.getmtime(self.ts_path)

        # testing for equality with possible margin 2 sec
        self.assertAlmostEqual(ts_timestamp_inside, ts_mtime, delta=2)

    def tearDown(self):
            # Remove ts-file after the test
            os.remove(self.ts_path)


if __name__ == '__main__':
    unittest.main()