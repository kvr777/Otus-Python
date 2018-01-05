import MySQLdb
import logging
import json
import time
from contextlib import closing


class Store:
    conn_store = None
    conn_cache = None

    def __init__(self, db_config, conn_store=conn_store, conn_cache=conn_cache):
        self.host = db_config['MAIN']['host']
        self.user = db_config['MAIN']['user']
        self.passwd = db_config['MAIN']['password']
        self.db_store = db_config['MAIN']['db_store']
        self.db_cache = db_config['MAIN']['db_cache']
        self.reconnect = db_config['MAIN']['reconnect']
        self.query_timeout = int(db_config['MAIN']['query_timeout'])
        self.connect_timeout = int(db_config['MAIN']['db_connect_timeout'])
        self.reconnect_max_attempts = int(db_config['MAIN']['db_connect_timeout'])
        self.conn_store = conn_store
        self.conn_cache = conn_cache

    def get_connection(self, db):
        return MySQLdb.connect(host=self.host,
                               user=self.user,
                               passwd=self.passwd,
                               db=db,
                               use_unicode=True,
                               charset="utf8",
                               connect_timeout=self.connect_timeout)

    def connect(self, db, conn):
        attempt = 1
        while True:
            try:
                if not conn:
                    conn = self.get_connection(db)
                    conn.autocommit(True)
                    logging.info("Successfully connected to {} database".format("placehold"))
                    return conn
            except Exception as e:
                if attempt > self.reconnect_max_attempts:
                    raise
                logging.warning("{} : Reconnect to {} attempt {} of {}".format(str(e), self.host,
                                                                   attempt, self.reconnect_max_attempts))
                attempt += 1
                conn = None


    def query(self, db, conn, sql, type, params=()):
        try:
            conn.ping()
        except:
            conn = self.connect(db, conn)
        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute(sql, params)
                if type == "SELECT":
                    return self.dictfetchall(cursor), conn
                else:
                    return conn
        except Exception as e:
            raise e

    def get(self, cids):
        format_strings = ','.join(['%s'] * len(cids))
        query_text = 'SELECT client_id, GROUP_CONCAT(interest ORDER BY interest SEPARATOR " " ) AS interests ' \
                     'FROM cust_interests ' \
                     'GROUP BY client_id HAVING client_id IN (%s)' % format_strings

        query_result, conn = self.query(sql=query_text, params=cids,
                                     db=self.db_store,conn = self.conn_store, type="SELECT")
        self.conn_store = conn
        return json.dumps(query_result)

    @staticmethod
    def dictfetchall(cursor):
        "Returns all rows from a cursor as a dict"
        desc = cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
        ]

    def cache_get(self, key):
        query_text = 'SELECT score, timeout FROM cache_score WHERE key_score= "%s" '
        try:
            query_res, conn = \
                self.query(db=self.db_cache,conn = self.conn_cache, params=[key], sql=query_text, type="SELECT")
            self.conn_cache = conn
        except:
            query_res = []
            self.conn_cache = None
            logging.warning("cannot access to cache database")
        if len(query_res):
            if int(query_res[0]["timeout"]) < time.time():
                del_query = 'DELETE FROM cache_score WHERE key_score= "%s" '
                conn = self.query(db=self.db_cache,conn = self.conn_cache, params=[key], sql=del_query, type="DELETE")
                self.conn_cache = conn
                return None
            else:
                return query_res[0]["score"]
        else:
            return None

    def cache_set(self, key, score, timeout=60 * 60):
        try:
            query_text = 'INSERT INTO cache_score(key_score, score, timeout) VALUES ("%s", %s, %s);'
            conn = self.query(db=self.db_cache,conn = self.conn_cache, params=(key, score, time.time()+timeout),
                              sql=query_text, type="INSERT")
            self.conn_cache = conn
        except:
            logging.warning("Cannot save to cache database")