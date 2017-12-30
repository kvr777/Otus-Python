import asyncio
import logging
import concurrent.futures
import os
import urllib.request as request
import urllib.parse as parse
import mimetypes
from datetime import datetime
import argparse


def parse_path(path):
    path_unqouted = parse.unquote(path)
    path_wo_args = path_unqouted.split('?', 1)[0]
    if path_wo_args.endswith('/'):
        path_wo_args +='index.html'
    parsed_path = path_wo_args.split('/')
    return os.path.join(os.path.abspath(DOCUMENT_ROOT), *parsed_path)


class EchoServer(object):
    """Server class"""

    def __init__(self, host, port, workers, loop=None):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=int(workers))
        self._loop = loop or asyncio.get_event_loop()
        self._loop.set_default_executor(self._executor)
        self._server = asyncio.async(asyncio.start_server(self.handle_connection, host=host, port=port))


    def start(self, and_loop=True):
        self._server = self._loop.run_until_complete(self._server)
        logging.info('Listening established on {0}'.format(self._server.sockets[0].getsockname()))
        if and_loop:
            self._loop.run_forever()

    def stop(self, and_loop=True):
        self._server.close()
        if and_loop:
            self._loop.close()

    @staticmethod
    def create_headers(writer, parsed_path, connection, long_version=False):
        writer.write(('Server: Asynchronous HTTP Server' + '\r\n').encode())
        writer.write(('Date: ' + str(datetime.now().strftime('%d-%m-%Y %H:%M:%S')) + '\r\n').encode())
        writer.write(('Connection: ' + str(connection) + '\r\n').encode())
        if not long_version:
            writer.write('\r\n'.encode())

        if long_version:
            path_as_url = request.pathname2url(parsed_path)
            writer.write(('Content-Length: ' + str(os.path.getsize(parsed_path)) + '\r\n').encode())
            writer.write(('Content-Type: ' + str(mimetypes.guess_type(path_as_url)[0]) + '\r\n').encode())
            writer.write('\r\n'.encode())
        return None


    @asyncio.coroutine
    def handle_connection(self, reader, writer):
        peername = writer.get_extra_info('peername')
        logging.info('Accepted connection from {}'.format(peername))
        full_data_list = []
        while not reader.at_eof():
            try:
                data = yield from asyncio.wait_for(reader.readline(), timeout=.05)
                full_data_list += data.decode().splitlines()
            except concurrent.futures.TimeoutError:
                break
        try:
            path = full_data_list[0].split(" ")[1]
        except: path = ''

        try:
            method = full_data_list[0].split(" ")[0]
        except:
            method = 'Invalid'
        try:
            connection = full_data_list[2].split(" ")[1]
        except:
            connection = 'close'
        parsed_path = parse_path(path)

        yield from self._loop.run_in_executor(None, self.method_handler,  writer, method, connection, parsed_path)
        # self.method_handler(writer, method, connection, parsed_path)

    def method_handler(self, writer, method, connection, parsed_path):
        if method in ['GET', 'HEAD']:
            if os.path.isfile(parsed_path):
                writer.write('HTTP/1.1 200 OK\r\n'.encode('utf-8'))
                self.create_headers(writer, parsed_path, connection, long_version=True)
                if method == 'GET':
                    with open(parsed_path, 'rb') as url_to_open:
                        writer.write(url_to_open.read())
            else:
                if parsed_path.endswith("index.html"):
                    writer.write('HTTP/1.1 403 ERROR\r\n'.encode('utf-8'))
                    self.create_headers(writer, parsed_path, connection, long_version=False)
                else:
                    writer.write('HTTP/1.1 404 ERROR\r\n'.encode('utf-8'))
                    self.create_headers(writer, parsed_path, connection, long_version=False)

        else:
            writer.write('HTTP/1.1 405 ERROR\r\n'.encode('utf-8'))
            self.create_headers(writer, parsed_path, connection, long_version=False)
        writer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', help='Number of workers', default=100)
    parser.add_argument('-r', help='document root', default=os.path.abspath(os.path.dirname(__file__)))
    args = parser.parse_args()

    DOCUMENT_ROOT = os.path.abspath(args.r)

    logging.basicConfig(level=logging.DEBUG)
    server = EchoServer('127.0.0.1', 80, workers=args.w)
    try:
        server.start()
    except KeyboardInterrupt:
        pass  # Press Ctrl+C to stop
    finally:
        server.stop()
