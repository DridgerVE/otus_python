## Домашнее задание 10

**Запуск тестирования**

```
python setup.py test
```

1. test_write

Тестирование записи данных файл методом deviceapps_xwrite_pb

2. test_write_all_params

Считываем созданный файл, разбираем protobuf сообщения с помощью python binding.

И проверям данные

3. test_read

Тестирование чтения данных из файла методом deviceapps_xread_pb