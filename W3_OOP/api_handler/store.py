import MySQLdb
import logging
import json
import time
from contextlib import closing
import threading


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

    def get_connection(self, db_type):
        db = self.db_store if db_type == 'store' else self.db_cache
        return MySQLdb.connect(host=self.host,
                               user=self.user,
                               passwd=self.passwd,
                               db=db,
                               use_unicode=True,
                               charset="utf8",
                               connect_timeout=self.connect_timeout)

    def connect(self, db_type):
        attempt = 1
        connection = self.conn_store if db_type == 'store' else self.conn_cache
        while True:
            try:
                if not connection:
                    connection = self.get_connection(db_type)
                    connection.autocommit(True)

                    # with closing(self.conn[db_type].cursor()) as cursor:
                    #     cursor.execute("SELECT CONNECTION_ID()")
                    #     self.conn[db_type].id = cursor.fetchone()[0]
                    logging.info("Successfully connected to {} database".format(db_type,
                                                                                           # self.conn[db_type].id
                                                                                           )
                                 )
                    return connection
            except Exception as e:
                if attempt > self.reconnect_max_attempts:
                    raise
                logging.warning("{} : Reconnect to {} attempt {} of {}".format(str(e), self.host,
                                                                   attempt, self.reconnect_max_attempts))
                attempt += 1
                self.conn[db_type] = None
                # self.connect()

    # def _harakiri(self, conn_id, db_type):
    #     conn = self.get_connection(db_type)
    #     logging.warning("Killing {}".format(conn_id))
    #     with closing(conn.cursor()) as cursor:
    #         cursor.execute("KILL CONNECTION %s", (conn_id,))
    #     conn.close()

    def query(self, db_type, sql, type, params=()):

        connection = self.conn_store if db_type == 'store' else self.conn_cache
        try:
            connection.ping()
        except:
            if db_type == 'store':
                self.conn_store = self.connect(db_type)
                self.conn_store.autocommit(True)
                connection = self.conn_store
            else:
                self.conn_cache = self.connect(db_type)
                self.conn_cache.autocommit(True)
                connection = self.conn_cache

        # kill_query_timer = threading.Timer(self.query_timeout,
        #                                    # self._harakiri,
        #                                    args=(self.conn[db_type].id,))
        # kill_query_timer.start()
        try:
            with closing(connection.cursor()) as cursor:
                cursor.execute(sql, params)
                if type == "SELECT":
                    return self.dictfetchall(cursor)
        except Exception as e:
            raise e
        # finally:
        #     kill_query_timer.cancel()

    def get(self, cids):
        format_strings = ','.join(['%s'] * len(cids))
        query_text = 'SELECT client_id, GROUP_CONCAT(interest ORDER BY interest SEPARATOR " " ) AS interests ' \
                     'FROM cust_interests ' \
                     'GROUP BY client_id HAVING client_id IN (%s)' % format_strings

        return json.dumps(self.query(sql=query_text, params=cids, db_type='store', type="SELECT"))

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
            query_res = self.query(db_type='cache', params=[key], sql=query_text, type="SELECT")
        except:
            query_res = []
            logging.warning("cannot access to cache database")
        if len(query_res):
            if int(query_res[0]["timeout"]) < time.time():
                del_query = 'DELETE FROM cache_score WHERE key_score= "%s" '
                self.query(db_type='cache', params=[key], sql=del_query, type="DELETE")
                return None
            else:
                return query_res[0]["score"]
        else:
            return None

    def cache_set(self, key, score, timeout=60 * 60):
        try:
            query_text = 'INSERT INTO cache_score(key_score, score, timeout) VALUES ("%s", %s, %s);'
            self.query(db_type='cache', params=(key, score, time.time()+timeout), sql=query_text, type="INSERT")
        except:
            logging.warning("Cannot save to cache database")