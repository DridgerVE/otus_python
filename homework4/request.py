import os
import urllib.parse
from response import Response
from utils import OK, FORBIDDEN, BAD_REQUEST, NOT_ALLOWED, NOT_FOUND, get_content_type

BUFFER_SIZE = 1024


def create_request(sock):
    """Create request object"""
    data = sock.recv(BUFFER_SIZE)
    return Request.parse(data)


class Request(object):
    """Request object represent parsed raw HTTP request"""

    def __init__(self, method, url, version, headers):
        self.method = method
        self.url = url
        self.version = version
        self.headers = headers
        self.valid = False

    @staticmethod
    def parse(data):
        """Create Request object from raw data"""
        lines = data.splitlines()
        lines = [line.decode('utf-8') for line in lines]
        try:
            request_line = lines[0]
            method, url, version = Request._parse_request_line(request_line)
            headers = {}
            for line in lines[1:]:
                if not line:
                    break
                k, v = Request._parse_header(line)
                headers[k] = v
            request = Request(method, url, version, headers)
            request.valid = True
        except:
            request = Request(None, None, None, None)
        return request

    @staticmethod
    def _parse_request_line(line):
        """Parse request line"""
        p = [el.strip() for el in line.split()]
        return p[0], p[1], p[2]

    @staticmethod
    def _parse_header(line):
        """Parse header"""
        p = [el.strip() for el in line.split(':')]
        return p[0], p[1]


class RequestHandler(object):
    """Handle requests"""
    ALLOWED_METHODS = {'GET', 'HEAD'}
    INDEX = 'index.html'

    def __init__(self, doc_root, request):
        self.request = request
        self.doc_root = doc_root
        self.filename = None

    def process(self):
        """Processing request"""
        if not self.request.valid:
            return Response(None, BAD_REQUEST)
        if not self.is_method_allowed():
            return Response(self.request.method, NOT_ALLOWED)
        code = self._check_resource()
        if code != OK:
            return Response(self.request.method, code)
        data = self._read_file()
        response = Response(self.request.method, code)
        response.set_content_type(self._get_content_type())
        response.set_data(data)
        return response

    def _check_resource(self):
        """Check resource for access"""
        file_path = urllib.parse.unquote(self.request.url.split('?')[0].strip('/'))
        filename = os.path.realpath(os.path.join(self.doc_root, file_path))
        long_prefix = os.path.commonprefix([self.doc_root, filename])
        # check root
        if long_prefix != self.doc_root:
            return FORBIDDEN
        if os.path.isdir(filename):
            # append index if resource is directory
            filename = os.path.join(filename, self.INDEX)
            error = FORBIDDEN
        else:
            error = NOT_FOUND
        if not os.path.exists(filename):
            return error
        self.filename = filename
        return OK

    def _get_content_type(self):
        """Detect content type"""
        return get_content_type(self.filename)

    def _read_file(self):
        """Reading file in binary mode"""
        with open(self.filename, mode='rb') as fd:
            return fd.read()

    def is_method_allowed(self):
        """Checked is method allowed"""
        return self.request.method in self.ALLOWED_METHODS
