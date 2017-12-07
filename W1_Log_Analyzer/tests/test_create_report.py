import unittest
from .context import log_analyzer
import logging
from collections import defaultdict


logging.disable(logging.CRITICAL)

class TestCreateReport(unittest.TestCase):

    """ Procedure:
        1. Create test dict with url and time
        2. initiate control tuple - this tuple should be as a result of create_report func
        3. Run create_report function and get tuple created by this function
        3.
        ---------
        Verification:
        3. Compare two tuples. Should be exact match
    """

    def setUp(self):
        # generate test_time_log this dict is input for the tested function. Set report_size = 0
        self.test_report_size = 0
        self.test_time_log = defaultdict(list)
        self.test_time_log['url1'] = ['50', '300', '200', '100', '250']
        self.test_time_log['url2'] = ['100', '100', '100']

        # generate control tuple with calculated statistic
        self.control_tuple = []

        sample = {"count": 5,
                  "time_avg": 180.0,
                  "time_max": 300.0,
                  "time_sum": 900.0,
                  "url": 'url1',
                  "time_med": 200.0,
                  "time_perc": 75.0,
                  "count_perc": 62.5
                  }
        self.control_tuple.append(sample)

        sample = {"count": 3,
                  "time_avg": 100.0,
                  "time_max": 100.0,
                  "time_sum": 300.0,
                  "url": 'url2',
                  "time_med": 100.0,
                  "time_perc": 25.0,
                  "count_perc": 37.5
                  }
        self.control_tuple.append(sample)


    def test_create_report(self):
        self.tuple_from_func = log_analyzer.create_report(self.test_time_log, self.test_report_size)
        self.assertEqual(self.control_tuple, self.tuple_from_func)


if __name__ == '__main__':
    unittest.main()
