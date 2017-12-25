import MySQLdb
import logging
import json
import time
from contextlib import closing
import threading


class Store:
    conn = None

    def __init__(self, db_config, conn=conn):
        self.host = db_config['MAIN']['host']
        self.user = db_config['MAIN']['user']
        self.passwd = db_config['MAIN']['password']
        self.db = db_config['MAIN']['database']
        self.reconnect = db_config['MAIN']['reconnect']
        self.query_timeout = int(db_config['MAIN']['query_timeout'])
        self.connect_timeout = int(db_config['MAIN']['db_connect_timeout'])
        self.reconnect_max_attempts = int(db_config['MAIN']['db_connect_timeout'])
        self.conn = conn

    def get_connection(self):
        return MySQLdb.connect(host=self.host,
                               user=self.user,
                               passwd=self.passwd,
                               db=self.db,
                               use_unicode=True,
                               charset= "utf8",
                               connect_timeout=self.connect_timeout)

    def connect(self):
        attempt = 1
        while True:
            try:
                if not self.conn:
                    self.conn = self.get_connection()
                    self.conn.autocommit(True)
                    with closing(self.conn.cursor()) as cursor:
                        cursor.execute("SELECT CONNECTION_ID()")
                        self.conn.id = cursor.fetchone()[0]
                    logging.info("Successfully connected with id {}".format(self.conn.id))
                    break
            except Exception as e:
                if attempt > self.reconnect_max_attempts:
                    raise
                logging.warning("{} : Reconnect to {} attempt {} of {}".format(str(e), self.host,
                                                                   attempt, self.reconnect_max_attempts))
                attempt += 1
                self.conn = None
                # self.connect()

    def _harakiri(self, conn_id):
        conn = self.get_connection()
        logging.warning("Killing {}".format(conn_id))
        with closing(conn.cursor()) as cursor:
            cursor.execute("KILL CONNECTION %s", (conn_id,))
        conn.close()

    def query(self, sql, type = None):
        try:
            self.conn.ping()
        except:
            self.connect()

        kill_query_timer = threading.Timer(self.query_timeout, self._harakiri, args=(self.conn.id,))
        kill_query_timer.start()
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute(sql)
                if type == "SELECT":
                    return self.dictfetchall(cursor)
        except Exception as e:
            raise e
        finally:
            kill_query_timer.cancel()

    def get(self, cids):
        query_text = 'SELECT client_id, GROUP_CONCAT(interest ORDER BY interest SEPARATOR " " ) AS interests ' \
                     'FROM cust_interests ' \
                     'GROUP BY client_id HAVING client_id IN (' + ','.join(map(str, cids)) + ')'

        return json.dumps(self.query(query_text, type="SELECT"))

    @staticmethod
    def dictfetchall(cursor):
        "Returns all rows from a cursor as a dict"
        desc = cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
        ]

    def cache_get(self, key):
        query_text = 'SELECT score, timeout FROM cache_score WHERE key_score= "%s" ' % key
        query_res = self.query(query_text, type="SELECT")
        print(query_res)
        if len(query_res):
            if int(query_res[0]["timeout"]) < time.time():
                del_query = 'DELETE FROM cache_score WHERE key_score= "%s" ' % key
                self.query(del_query, "DELETE")
                # del self.cache[key]
                return None
            else:
                return query_res[0]["score"]
        else:
            return None

    def cache_set(self, key, score, timeout=60 * 60):
        query_text = 'INSERT INTO cache_score(key_score, score, timeout) VALUES ("%s", %s, %s);' % (key, score, time.time()+timeout)
        self.query(query_text, "INSERT")