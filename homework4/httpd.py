#!/usr/bin/env python
import argparse
import os
import logging
import socket
import threading
import queue
import request


class HTTPd(threading.Thread):
    """Python Web Server"""

    def __init__(self, host, port, doc_root, workers_count, **kwargs):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.doc_root = doc_root
        self.workers_count = workers_count
        self.queue = queue.Queue()
        self.listen_socket = None
        self.workers = []
        self._stop_signal = threading.Event()

    def run(self):
        """Run thread"""
        self._run_server()

    def _run_server(self):
        """Run server"""
        self.init_listen_socket()
        self._run_workers()
        self.listening_loop()

    def stop_server(self):
        """Stop Web server"""
        self._stop_signal.set()
        self.listen_socket.close()
        for w in self.workers:
            w.stop()
            w.join()

    def listening_loop(self):
        """Listen loop"""
        logging.info('Start listening loop.')
        while not self._stop_signal.is_set():
            connection, address = self.listen_socket.accept()
            self.queue.put(connection)

    def init_listen_socket(self):
        """Init listening socket"""
        ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ls.bind((self.host, self.port))
        ls.listen(4096)
        self.listen_socket = ls
        logging.info('Init listening socket.')

    def _run_workers(self):
        """Create and run workers"""
        for i in range(self.workers_count):
            w = Worker(self.queue, self.doc_root, name='WebServer worker#{}'.format(i))
            w.start()
            self.workers.append(w)


class Worker(threading.Thread):
    # Queue.get timeout in seconds
    Q_TIMEOUT = 5

    def __init__(self, q, doc_root, **kwargs):
        super().__init__(**kwargs)
        self.queue = q
        self._stop_event = threading.Event()
        self.doc_root = doc_root

    def process(self, connection):
        """Process connection"""
        rqst = request.create_request(connection)
        handler = request.RequestHandler(self.doc_root, rqst)
        response = handler.process()
        data = response.get_data_response()
        connection.sendall(data)
        logging.info(self._log_message(rqst, response, len(data)))

    def run(self):
        """Main loop of worker"""
        logging.info('{} started.'.format(self.name))
        while not self._stop_event.is_set():
            try:
                c = self.queue.get(True, self.Q_TIMEOUT)
                self.process(c)
                c.close()
            except queue.Empty:
                # continue, no data
                continue
        logging.info('{} stop.'.format(self.name))

    def stop(self):
        """Set flag for stopping worker loop"""
        self._stop_event.set()

    @staticmethod
    def _log_message(request, response, bytes_sent):
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

    httpd = HTTPd(args.host,
                  args.port,
                  os.path.realpath(args.doc_root),
                  args.workers_count)

    try:
        httpd.start()
    except KeyboardInterrupt:
        httpd.stop_server()
