import asyncio
import logging
import concurrent.futures
import os
import urllib.request as request
import urllib.parse as parse
import email
import mimetypes
import io
from datetime import datetime
import argparse


def parse_path(path):
    path_unquoted = parse.unquote(path)
    path_wo_args = path_unquoted.split('?', 1)[0]
    if path_wo_args.endswith('/'):
        path_wo_args += 'index.html'
    parsed_path = path_wo_args.split('/')
    return os.path.join(os.path.abspath(DOCUMENT_ROOT), *parsed_path)


class SimpleHTTPServer(object):
    """Server class"""

    def __init__(self, host, port, workers, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._server = asyncio.start_server(self.handle_connection, host=host, port=port, backlog=int(workers))

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
        data = ""
        while not reader.at_eof():
            try:
                data = yield from asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=.05)
            except concurrent.futures.TimeoutError:
                break
        request_line, headers_alone = data.decode('utf-8').split('\r\n', 1)
        headers = email.message_from_file(io.StringIO(headers_alone))
        try:
            path = request_line.split(" ")[1]
        except IndexError:
            path = ''

        try:
            method = request_line.split(" ")[0]
        except IndexError:
            method = 'Invalid'
        try:
            connection = headers["Connection"]
        except KeyError:
            connection = 'close'
        parsed_path = parse_path(path)

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
    server = SimpleHTTPServer('127.0.0.1', 80, workers=args.w)

    try:
        server.start()
    except KeyboardInterrupt:
        pass  # Press Ctrl+C to stop
    finally:
        server.stop()
