
import MySQLdb
import logging
import json
import time

HOST = "localhost"
USER = ""               # delete for security reasons
PWD = ""                # delete for security reasons
DATABASE = "otus_db"
RECONNECT = 10


class Store:
    conn = None
    cache = {}

    def __init__(self, host= HOST, user= USER, passwd=PWD, db= DATABASE, reconnect=RECONNECT, cache=cache, conn=conn ):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.db = db
        self.reconnect = reconnect
        self.cache = cache
        self.conn = conn

    def connect(self):
        remains = self.reconnect
        while remains:
            try:
                self.conn = MySQLdb.connect(host = self.host, user = self.user,
                                          passwd= self.passwd, db= self.db,
                                          use_unicode=True,
                                          charset="utf8")
                return self.conn
            except:
                logging.exception("Cannot connect to {} database".format(self.db))
                remains -= 1

    def get(self, cid):
        query = 'SELECT client_id, GROUP_CONCAT(interest ORDER BY interest SEPARATOR " " ) AS interests ' \
                'FROM cust_interests ' \
                'GROUP BY client_id HAVING client_id IN (' + ','.join(map(str, cid)) + ')'

        results = {}

        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            for (client, interests) in cursor.fetchall():
                results[str(client)] = list(interests.split())
            return json.dumps(results)
        except(AttributeError, MySQLdb.OperationalError):
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute(query)
            for (client, interests) in cursor.fetchall():
                results[str(client)] = list(interests.split())
            return json.dumps(results)


    def cache_get(self, key):
        # dict.get(key, default=None)
        if self.cache.get(key, None):
            if self.cache[key][1] < time.time():
                del self.cache[key]
                return None
            else:
                return self.cache[key][0]
        else:
            return None

    def cache_set(self, key, score, timeout=60 * 60):
        self.cache[key] = [score, time.time()+timeout]
