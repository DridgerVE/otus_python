#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import abstractmethod, ABCMeta
import json
import datetime
import logging
import hashlib
import uuid
import collections
import random
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field(object, metaclass=ABCMeta):
    """Базовый класс для всех остальных полей."""

    def __init__(self, required=False, nullable=False):
        self.required, self.nullable = required, nullable

    @abstractmethod
    def validate(self, value):
        # обязательно реализовать в наследниках
        raise NotImplementedError


class CharField(Field):
    """Поле - строка"""
    ERROR = 'Must be a string'

    def validate(self, value):
        if not isinstance(value, (str, bytes)):
            raise ValueError(self.ERROR)
        return value


class ArgumentsField(Field):
    """ Поле - словарь"""
    ERROR = 'Must be a dict'

    def validate(self, value):
        if not isinstance(value, collections.Mapping):
            raise ValueError(self.ERROR)
        return value


class EmailField(CharField):
    """Строка, содержащая @"""
    ERROR = 'Must be valid email address'

    def validate(self, value):
        if '@' not in value:
            raise ValueError(self.ERROR)
        return value


class PhoneField(Field):
    """Поле должно быть строкой или числом.
    Длинной 11 символов, начинаться с 7.
    Опционально может быть пустым."""
    ERROR = 'Must be a string or number containing 11 digits and starting with 7'

    def validate(self, value):
        if len(str(value)) < 11 or not str(value).isdigit() or str(value)[0] != '7':
            raise ValueError(self.ERROR)
        return value


class DateField(Field):
    """Дата в формате DD.MM.YYYY"""
    ERROR = 'Must be date in DD.MM.YYYY format'

    def validate(self, value):
        try:
            date = datetime.datetime.strptime(value, '%d.%m.%Y').date()
            return date
        except ValueError:
            raise ValueError(self.ERROR)


class BirthDayField(DateField):
    """Дата в формате DD.MM.YYYY, с которой прошло не больше 70 лет"""
    ERROR = 'Must be date no more than 70 years'

    def validate(self, value):
        value = super(BirthDayField, self).validate(value)
        date_today = datetime.date.today()
        td = (date_today - value).days // 365
        if not (0 <= td <= 70):
            raise ValueError(self.ERROR)
        return value


class GenderField(Field):
    """Число 0, 1 или 2"""
    ERROR_INT = 'Must be integer'
    ERROR = 'Must be one of the values [0, 1, 2]'

    def validate(self, value):
        if not isinstance(value, int):
            raise ValueError(self.ERROR_INT)
        if not (0 <= value <= 2):
            raise ValueError(self.ERROR)
        return value


class ClientIDsField(Field):
    """Поле массив чисел, обязательно не пустое."""
    ERROR = 'Must be list of numbers'

    def validate(self, value):
        if not isinstance(value, collections.MutableSequence):
            raise ValueError(self.ERROR)
        for el in value:
            if not isinstance(el, int):
                raise ValueError(self.ERROR)
        return value


class MetaRequest(type):
    """Метакласс для запросов.
    Данный метакласс будем применять ко всем запросам: MethodRequest, OnlineScoreRequest, ClientsInterestsRequest.
    Перед созданием нового класса-запроса обходим все атрибуты, у которых базовый класс Field и
    создаем словарь имя атрибута-класс поле. Сохраняем словарь в атрибуте rq_fields.
    """

    def __new__(cls, name, bases, dicts):
        new_cls = super(MetaRequest, cls).__new__  # (cls, name, bases, dicts)
        rq_fields = {}
        for k, v in dicts.items():
            if isinstance(v, Field):
                rq_fields[k] = v
        dicts['rq_fields'] = rq_fields
        return new_cls(cls, name, bases, dicts)


class MainRequest(object, metaclass=MetaRequest):

    def __init__(self, **kwargs):
        self.errors = []
        self.request = kwargs
        self.is_parsed = False
        # self.rq_fields = {el: getattr(self, el) for el in dir(self) if isinstance(getattr(self, el), Field)}

    @abstractmethod
    def processing(self, request, ctx, store):
        raise NotImplementedError

    def validate_all(self):
        for name, _ in self.rq_fields.items():
            field = getattr(self, name)
            value = None
            try:
                value = self.request[name]
            except (KeyError, TypeError):
                if field.required:
                    self.errors.append('Field {} required.'.format(name))
                    continue
            if value in ([], {}, '', None):
                if field.nullable:
                    setattr(self, name, value)
                else:
                    self.errors.append('Field {} can not be nullable.'.format(name))
                continue
            try:
                setattr(self, name, field.validate(value))
            except ValueError as e:
                self.errors.append('Field {} validation error: {}.'.format(name, e))
        self.is_parsed = True

    def is_valid(self):
        if not self.is_parsed:
            self.validate_all()
        return not bool(self.errors)


class ClientsInterestsRequest(MainRequest):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def processing(self, request, ctx, store):
        """Обрабатываем метод clients_interests"""
        ctx['nclients'] = len(self.client_ids)
        response = {}
        for client in self.client_ids:
            response[client] = get_interests(store, 0)
        return response, OK


class OnlineScoreRequest(MainRequest):
    # пары полей, хотя бы одна из пар не должна быть пустой
    _pairs = (
        ('phone', 'email'),
        ('first_name', 'last_name'),
        ('gender', 'birthday')
    )
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def is_valid(self):
        check = super(OnlineScoreRequest, self).is_valid()
        if not check:
            return check
        fields = set(self.get_fill_fields())
        # для каждой пары полей, которые не должны быть пустыми
        # проверяем их наличие в множестве не пустых полей
        result = any(fields.issuperset(el) for el in self._pairs)
        if not result:
            self.errors.append('One of the pairs {} must not be empty.'.format(self._pairs))
            return False
        return True

    def processing(self, request, ctx, store):
        """Обработка метода online_score"""
        ctx['has'] = self.get_fill_fields()
        if request.is_admin:
            return {'score': 42}, OK
        return {'score': get_score(store, self.phone, self.email, self.birthday,
                                   self.gender, self.first_name, self.last_name)}, OK

    def get_fill_fields(self):
        """Получаем кортеж заполненных полей запроса"""
        exist_fields = [name for name, field in self.rq_fields.items() if field is not None]
        fill_fields = [name for name in exist_fields if getattr(self, name) not in ([], {}, '')]
        return fill_fields


class MethodRequest(MainRequest):

    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN

    def processing(self, request, ctx, store):
        pass


class Application(object):

    @abstractmethod
    def create_request(self, type_, kwargs):
        raise NotImplementedError


class RequestApplication(Application):

    def create_request(self, type_, kwargs):
        if type_ == "online_score":
            return OnlineScoreRequest(**kwargs)
        elif type_ == "clients_interests":
            return ClientsInterestsRequest(**kwargs)
        else:
            return None


def get_score(store, phone, email, birthday=None, gender=None, first_name=None, last_name=None):
    score = 0
    if phone:
        score += 1.5
    if email:
        score += 1.5
    if birthday and gender:
        score += 1.5
    if first_name and last_name:
        score += 0.5
    return score


def get_interests(store, cid):
    interests = ["cars", "pets", "travel", "hi-tech", "sport", "music", "books", "tv", "cinema", "geek", "otus"]
    return random.sample(interests, 2)


def check_auth(request):
    if request.login == ADMIN_LOGIN:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode('utf-8')).hexdigest()
        # digest = "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f24091386050205c324687a0"
    else:
        if not hasattr(request, 'account') or request.account is None:
            return False
        digest = hashlib.sha512((request.account + request.login + SALT).encode('utf-8')).hexdigest()
    if digest == request.token:
        return True
    return False


def make_errors(error_code, errors):
    return '{} - {}'.format(ERRORS.get(error_code, "Unknown Error"), ' '.join(errors)), error_code


def method_handler(request, ctx, store):
    body = request['body']
    if not isinstance(body, collections.Mapping):
        return None, INVALID_REQUEST
    request = MethodRequest(**body)
    if not request.is_valid():
        return make_errors(INVALID_REQUEST, request.errors)
    if not check_auth(request):
        return "Forbidden", FORBIDDEN
    app = RequestApplication()
    arguments = request.arguments
    handler = app.create_request(request.method, arguments)
    if handler is None:
        return "Method Not Found", NOT_FOUND
    if handler.is_valid():
        return handler.processing(request, ctx, store)
    else:
        return make_errors(INVALID_REQUEST, handler.errors)


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(bytes(json.dumps(r), encoding="utf-8"))
        return

if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
