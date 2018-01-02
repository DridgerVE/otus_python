import os

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

CRLF = '\r\n'


def get_content_type(filename):
    name, ext = os.path.splitext(filename)
    if ext:
        return CONTENT_TYPE.get(ext.strip('.'), CONTENT_TYPE['text'])
    return CONTENT_TYPE['text']
