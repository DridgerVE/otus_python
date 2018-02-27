## Домашнее задание 9

**Старт memcache**

```
docker run --name memcache-0 -p 33013:11211 -d --rm memcached
docker run --name memcache-1 -p 33014:11211 -d --rm memcached
docker run --name memcache-2 -p 33015:11211 -d --rm memcached
docker run --name memcache-3 -p 33016:11211 -d --rm memcached
```

**Примеры боевого запуска**

***Однопоточная версия***

```
time python3 memc_load_single.py --pattern './data/appsinstalled/*.tsv.gz'
[2018.02.20 15:29:37] I Memc loader started with options: {'test': False, 'log': None, 'dry': False, 'pattern': './data/appsinstalled/*.tsv.gz', 'idfa': '127.0.0.1:33013', 'gaid': '127.0.0.1:33014', 'adid': '127.0.0.1:33015', 'dvid': '127.0.0.1:33016'}
[2018.02.20 15:29:37] I Processing ./data/appsinstalled/20170929000000.tsv.gz
[2018.02.20 19:50:57] I Acceptable error rate (0.0). Successfull load

real    261m20.614s
user    51m43.523s
sys     8m54.036s
```

***Многопоточная версия (на каждый файл создается ThreadPool из 4 Thread на каждый memcache)***
```
time python3 memc_load.py --pattern './data/appsinstalled/*.tsv.gz'
[2018.02.20 12:06:24] I Memc loader started with options: {'test': False, 'log': None, 'dry': False, 'pattern': './data/appsinstalled/*.tsv.gz', 'idfa': '127.0.0.1:33013', 'gaid': '127.0.0.1:33014', 'adid': '127.0.0.1:33015', 'dvid': '127.0.0.1:33016', 'workers': 4}
[2018.02.20 12:06:24] I Worker count: 4.
[2018.02.20 12:06:24] I Processing ./data/appsinstalled/20170929000000.tsv.gz
[2018.02.20 12:06:24] I Processing ./data/appsinstalled/20170929000200.tsv.gz
[2018.02.20 12:06:24] I Processing ./data/appsinstalled/20170929000100.tsv.gz
[2018.02.20 14:09:36] I ForkPoolWorker-1 - Thread-4: records processed = 855504, records errors = 1143
[2018.02.20 14:12:52] I ForkPoolWorker-1 - Thread-3: records processed = 854139, records errors = 1188
[2018.02.20 14:18:19] I ForkPoolWorker-3 - Thread-1: records processed = 854022, records errors = 1251
[2018.02.20 14:18:35] I ForkPoolWorker-2 - Thread-1: records processed = 854922, records errors = 1269
[2018.02.20 14:19:29] I ForkPoolWorker-1 - Thread-1: records processed = 854734, records errors = 1251
[2018.02.20 14:20:45] I ForkPoolWorker-1 - Thread-2: records processed = 853749, records errors = 1287
[2018.02.20 14:20:45] I Acceptable error rate (0.0014244647505680013). Successfull load
[2018.02.20 14:20:45] I Renamed ./data/appsinstalled/20170929000000.tsv.gz.
[2018.02.20 14:21:16] I ForkPoolWorker-3 - Thread-2: records processed = 856477, records errors = 1287
[2018.02.20 14:23:17] I ForkPoolWorker-2 - Thread-4: records processed = 854489, records errors = 1314
[2018.02.20 14:24:06] I ForkPoolWorker-3 - Thread-4: records processed = 853582, records errors = 1314
[2018.02.20 14:24:51] I ForkPoolWorker-2 - Thread-3: records processed = 855936, records errors = 1332
[2018.02.20 14:24:55] I ForkPoolWorker-2 - Thread-2: records processed = 853874, records errors = 1341
[2018.02.20 14:24:55] I Acceptable error rate (0.0015371922434963988). Successfull load
[2018.02.20 14:24:55] I Renamed ./data/appsinstalled/20170929000100.tsv.gz.
[2018.02.20 14:25:20] I ForkPoolWorker-3 - Thread-3: records processed = 852752, records errors = 1341
[2018.02.20 14:25:20] I Acceptable error rate (0.0015198284493271987). Successfull load
[2018.02.20 14:25:20] I Renamed ./data/appsinstalled/20170929000200.tsv.gz.

real    138m57.023s
user    132m18.228s
sys     10m59.376s
```

**Тестирование**

1. test_fail_load

Создаем тестовые файлы для заливки с большим процентом ошибочных записей

Логгируем работу скрипта в файл

Сравниваем лог с ожидаемыми значениями

2. test_file_rename

Проверяем порядок переименования файлов согласно информации из файловой системы и записям логов