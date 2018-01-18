#!/usr/bin/env python
import argparse
import logging
import os
import queue
import socket
import threading
from urllib.parse import unquote
from datetime import datetime

# supported status codes
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
NOT_ALLOWED = 405

STATUS_CODES = {
    OK: 'OK',
    FORBIDDEN: 'Forbidden',
    BAD_REQUEST: 'Bad Request',
    NOT_FOUND: 'Not Found',
    NOT_ALLOWED: 'Method Not Allowed'
}

# supported content types
CONTENT_TYPE = {
    'text': 'text/plain',
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'swf': 'application/x-shockwave-flash'
}

RECV_BUF = 1024


class HTTPResponse(object):

    def __init__(self, **kwargs):
        self.version = "HTTP/1.1"
        self.allowed_method = kwargs['allowed_method']
        self.method = kwargs['method']
        self.filename = kwargs['filename']
        self.code = kwargs['code']
        self.headers = dict()
        self.body = kwargs['body']
        self.response = None

    def _get_content_type(self):
        name, ext = os.path.splitext(self.filename)
        if ext:
            return CONTENT_TYPE.get(ext.strip('.'), CONTENT_TYPE['text'])
        return CONTENT_TYPE['text']

    def _write_data(self, string):
        """Function to write data into response"""
        if isinstance(string, str):
            string = string.encode('utf-8')
        if self.response is None:
            self.response = string
        else:
            self.response += string

    def write_response(self):
        """Write the response back to the client """
        # status line
        status = '{} {} {}\r\n'.format(self.version,
                                       self.code,
                                       STATUS_CODES[self.code])
        logging.debug("Responding status: {0}".format(status.strip()))
        self._write_data(status)
        if self.body is None or self.method not in self.allowed_method:
            self.headers['Content-Length'] = 0
        else:
            self.headers['Content-Length'] = len(self.body)
            self.headers['Content-type'] = self._get_content_type()

        self.headers['Date'] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
        self.headers['Connection'] = 'close'
        self.headers['Server'] = 'Python Simple Web Server'
        for (header, content) in self.headers.items():
            self._write_data('{}: {}\r\n'.format(header, content))
        self._write_data('\r\n')
        # body
        if self.body is not None and self.method == "GET":
            self._write_data(self.body)


class HTTPRequest(object):

    def __init__(self, data, doc_root):
        self.data = data
        self.allowed_method = {'HEAD', 'GET'}
        self.method = ""
        self.url = ""
        self.filename = ""
        self.doc_root = doc_root
        self.code = OK
        self.body = None

    def _read_file(self):
        """Reading file in binary mode"""
        with open(self.filename, mode='rb') as fd:
            return fd.read()

    def _invalid_request(self, code, msg):
        """Invalid request"""
        self.code = code
        self.body = str(msg)
        self.headers = {'Content-Type': 'text/plain'}

    def _check(self):
        """Check resource for access"""
        file_path = unquote(self.url.split('?')[0].strip('/'))
        filename = os.path.realpath(os.path.join(self.doc_root, file_path))
        long_prefix = os.path.commonprefix([self.doc_root, filename])
        # check root
        if long_prefix != self.doc_root:
            return FORBIDDEN
        if os.path.isdir(filename):
            # append index.html
            filename = os.path.join(filename, "index.html")
            error = FORBIDDEN
        else:
            error = NOT_FOUND
        if not os.path.exists(filename):
            return error
        self.filename = filename
        return OK

    def parse_data(self):
        logging.debug('Parsing headers')
        if not self.data:
            logging.info('Invalid http header')
            self._invalid_request(BAD_REQUEST, STATUS_CODES[BAD_REQUEST])
            return
        request_strings = self.data.splitlines()
        method_line = request_strings[0].split()
        if len(method_line) != 3:
            logging.info('Invalid http header')
            self._invalid_request(BAD_REQUEST, STATUS_CODES[BAD_REQUEST])
            return
        # method
        self.method = method_line[0]
        # URL
        self.url = method_line[1]
        if self.method not in self.allowed_method:
            self._invalid_request(NOT_ALLOWED, STATUS_CODES[NOT_ALLOWED])
            return
        self.code = self._check()
        if self.code != OK:
            self._invalid_request(self.code, STATUS_CODES[self.code])
            return
        self.body = self._read_file()

    def to_response(self):
        resp = dict()
        resp['allowed_method'] = self.allowed_method
        resp['method'] = self.method
        resp['filename'] = self.filename
        resp['code'] = self.code
        resp['body'] = self.body
        return resp


class TCPWorker(threading.Thread):

    def __init__(self, doc_root, q, q_timeout, **kwargs):
        super().__init__(**kwargs)
        self.doc_root = doc_root
        self.queue = q
        self.timeout = q_timeout
        self._stopped = False

    def _do_work(self, conn):
        """Processing: get request and send response"""
        data = ""
        while True:
            buf = conn.recv(RECV_BUF)
            if not buf:
                break
            data += buf.decode('utf-8')
            if data.find("\r\n\r\n") > 0 or data.find("\n\n") > 0:
                break
        if data:
            httpreq = HTTPRequest(data, self.doc_root)
            httpreq.parse_data()
            httpresp = HTTPResponse(**httpreq.to_response())
            httpresp.write_response()
            logging.info('{} {} {}'.format(httpreq.url, httpresp.code, len(httpresp.response)))
            conn.sendall(httpresp.response)

    def run(self):
        """Main loop for thread, trying queue.get and _do_work"""
        while not self._stopped:
            try:
                connect = self.queue.get(block=True, timeout=self.timeout)
                self._do_work(connect)
                connect.close()
                self.queue.task_done()
            except queue.Empty:
                continue
            except socket.error:
                connect.close()
                self.queue.task_done()
                continue

    def stop(self):
        self._stopped = True


class TCPServer(object):
    """Python Web Server"""

    def __init__(self, host, port, doc_root, cnt_threads):
        self.host = host
        self.port = port
        self.doc_root = doc_root
        self.cnt_threads = cnt_threads
        self._socket = None
        self.queue = queue.Queue()
        self.threads = []
        self.timeout = 0.1
        self._stopped = False

    def _bind_and_activate(self):
        """Bind server and make pool threads"""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self.host, self.port))
        self._socket.listen(1024)
        logging.info("Serving HTTP on {0} port {1} (http://{0}:{1}/) ...".format(self.host, self.port))
        self.threads = [TCPWorker(self.doc_root, self.queue, self.timeout, name="Thread {0}".format(i))
                        for i in range(self.cnt_threads)]

    def _start_threads(self):
        """Start all threads"""
        for th in self.threads:
            th.start()
            logging.info("Thread is started: {0}".format(th.name))

    def _run_server(self):
        """Run server"""
        self._bind_and_activate()
        self._start_threads()

    def stop_server(self):
        """Stop server"""
        for th in self.threads:
            th.stop()
            th.join()
            logging.info("Thread is stopped: {0}".format(th.name))
        self._stopped = True
        self._socket.close()
        logging.info("Serving HTTP is stopped")

    def serve_forever(self):
        """Main loop - listen socket"""
        self._run_server()
        while not self._stopped:
            # self._socket.settimeout(0.2)  # timeout for listening
            conn, addr = self._socket.accept()
            self.queue.put(conn, block=False)


def log_message(request, response, bytes_sent):
    """Create log message"""
    return '{} {} {}'.format(request.url, response.code, bytes_sent)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Python web server')
    parser.add_argument('-r', required=True, dest='doc_root', help='Document root')
    parser.add_argument('-w', default=1, type=int, dest='workers_count', help='Worker count')
    parser.add_argument('-a', default='localhost', dest='host', help='Web server bind address')
    parser.add_argument('-p', default=8080, type=int, dest='port', help='Web server port')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if not os.path.exists(args.doc_root):
        logging.error('Document root: {} does not exists.'.format(args.web_root))

    httpd = TCPServer(args.host,
                      args.port,
                      os.path.realpath(args.doc_root),
                      args.workers_count)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.stop_server()
