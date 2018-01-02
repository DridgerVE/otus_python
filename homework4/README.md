## Домашнее задание 5

### Задача

Задание: Разработать веб-сервер. Разрешается использовать библиотеки помогающие
реализовать асинхронную обработку соединений, запрещается использовать библиотеки
реализующие какую-либо часть обработки HTTP. Провести нагрузочное тестирование,
проверку стабильности и корректности работы. Если сервер асинхронный, то
обязательно использовать [epoll](https://github.com/m13253/python-asyncore-epoll).

Веб-сервер должен уметь:

* Масштабироваться на несколько worker'ов
* Числов worker'ов задается аргументом командной строки -w
* Отвечать 200 или 404 на GET-запросы и HEAD-запросы
* Отвечать 405 на прочие запросы
* Возвращать файлы по произвольному пути в DOCUMENT_ROOT.
* Вызов /file.html должен возвращать содердимое DOCUMENT_ROOT/file.html
* DOCUMENT_ROOT задается аргументом командной строки -r
* Возвращать index.html как индекс директории
* Вызов /directory/ должен возвращать DOCUMENT_ROOT/directory/index.html
* Отвечать следующими заголовками для успешных GET-запросов:
  Date, Server, Content-Length, Content-Type, Connection
* Корректный Content-Type для: .html, .css, .js, .jpg, .jpeg, .png, .gif, .swf
* Понимать пробелы и %XX в именах файлов


### Что проверять?

* [Проходят тесты](https://github.com/s-stupnikov/http-test-suite).
* http://localhost/httptest/wikipedia_russia.html корректно показывается в браузере.
* Нагрузочное тестирование: запускаем ab -n 50000 -c 100 -r http://localhost:8080/
  и смотрим результат (опционально: вместо ab воспользоваться wrk)

### Что на выходе?

* сам сервер в httpd.py. Это точка входа (т.е. этот файлик обязательно
  должен быть), можно разбить на модули.
* README.md с описанием использованной архитектуры (в двух словах:
  asynchronous/thread pool/prefork/...) и результатами нагрузочного тестирования

## Описание решения

### Необходимая литература

* [Hypertext Transfer Protocol -- HTTP/1.0](https://tools.ietf.org/html/rfc1945)
* [Hypertext Transfer Protocol -- HTTP/1.1](https://tools.ietf.org/html/rfc2616)

## Результаты

### Архитектура

ThreadPool с N воркерами.

### Параметры сервера

```
usage: httpd.py [-h] -r DOC_ROOT [-w WORKERS_COUNT] [-a HOST] [-p PORT]

Web server

optional arguments:
  -h, --help            show this help message and exit
  -r DOC_ROOT           Document root
  -w WORKERS_COUNT      Worker count
  -a HOST               Web server bind address
  -p PORT               Web server port
```

### Тестовый стенд (сервер запущен с 1 потоком)

```MacBook Pro (2,4 GHz Intel Core i5, 8 ГБ 1333 MHz DDR3)```

```
ab -n 50000 -c 100 -r -s 60 http://127.0.0.1:8080/
```

```
Benchmarking 127.0.0.1 (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        Python
Server Hostname:        127.0.0.1
Server Port:            8080

Document Path:          /
Document Length:        138 bytes

Concurrency Level:      100
Time taken for tests:   136.442 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      14300000 bytes
HTML transferred:       6900000 bytes
Requests per second:    484.79 [#/sec] (mean)
Time per request:       206.273 [ms] (mean)
Time per request:       2.063 [ms] (mean, across all concurrent requests)
Transfer rate:          135.40 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0  120 1537.3      0   20079
Processing:     1   86  64.3     76     822
Waiting:        0   86  64.1     76     822
Total:          1  206 1535.2     77   20088

Percentage of the requests served within a certain time (ms)
  50%     77
  66%     78
  75%     79
  80%     80
  90%     83
  95%     88
  98%    411
  99%    474
 100%  20088 (longest request)
```

*** Тестирование

Тесты пришлось подкорректировать в связи с тем, что использую Python 3
и методы socket.send, socket.sendall принимают данные только bytes,
и метод socket.read возвращает bytes

Отредактированный httptest.py тоже включил в коммит