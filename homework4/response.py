from time import strftime, gmtime
from utils import CRLF, STATUS_CODES


class Response(object):
    """Response class represent HTTP response"""
    def __init__(self, method, code):
        self.version = 'HTTP/1.1'
        self.method = method
        self.code = code
        self.headers = {}
        self._set_headers()
        self.data = None

    def set_data(self, data):
        """Set data and set Content-Length header"""
        self.data = data
        self.headers['Content-Length'] = len(data)

    def set_content_type(self, ct):
        """Set Content-Type header"""
        self.headers['Content-Type'] = ct

    def get_data_response(self):
        """Get data of Response"""
        result = (self._get_status_line() + self._get_headers() + (2 * CRLF)).encode('utf-8')
        if self.method == 'GET' and self.data is not None:
            result += self.data
        return result

    def _set_headers(self):
        """Set headers"""
        self.headers['Date'] = strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime())
        self.headers['Connection'] = 'close'
        self.headers['Server'] = 'Python Web Server'

    def _get_status_line(self):
        """Create status line"""
        return '{} {} {}{}'.format(self.version, self.code, STATUS_CODES[self.code], CRLF)

    def _get_headers(self):
        """Join headers"""
        return CRLF.join('{}: {}'.format(k, v) for k, v in self.headers.items())
