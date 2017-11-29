#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import os
import re
import sys
import configparser
import gzip
from collections import defaultdict,OrderedDict
from statistics import median
from shutil import copy2
import time
import logging

logging.basicConfig(filename=None, level=logging.INFO,
                    format='[%(asctime)s] %(levelname).1s %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S')

# класс, для возможности получения результатов работы функции с генератором
class Generator:
    def __init__(self, gen):
        self.gen = gen

    def __iter__(self):
        self.value = yield from self.gen


def check_log(log_path):
    """ Проверка существования пути к конф.файлу и наличия обязательных
    параметров. Под обязательными принимаются параметры в переменной
    conf_mandatory_args

    Args:
        log_path: путь к конфигурационному файлу

    Returns:
        Код статуса: [0 - не найден конфигурационный файл
                      1- конфигурационный файл найден, но обязательные параметры не прочитать
                      2 - найден конфигурационный файл и обязательные параметры соответсвуют требованиям]
        config: При статусе 2 передается считанный кофигурационный файл, при прочих статусах пустое значение
    """

    conf = {}

    try:
        config = configparser.ConfigParser()
        config.read(log_path)
        conf_curr_args = [key for key in config['MAIN']]
        conf_mandatory_args = ['report_size', 'report_dir', 'log_dir']
        flag_params = set(conf_mandatory_args).issubset(set(conf_curr_args))
        if flag_params:
            if os.path.isdir(config['MAIN']['report_dir']) & \
                    os.path.isdir(config['MAIN']['log_dir']) & \
                    (int(config['MAIN']['report_size']) >= 0):
                return 2, config
            else:
                return 1, conf
        else:
            return 1, conf
    except:
        return 0, conf


def logger_reconfig (config):
    try:
        if os.path.isdir(config['MAIN']['logging']):
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
                logging.basicConfig(handlers=
                                    [logging.FileHandler(os.path.join(config['MAIN']['logging'], 'log_analyzer.log'),
                                                         'w', 'utf-8')],
                                    level=logging.INFO,
                                    format='[%(asctime)s] %(levelname).1s %(message)s',
                                    datefmt='%Y.%m.%d %H:%M:%S')
            return logging.info("Логирование в файл успешно подключено")
    except:
        return None

def check_other_reqs(config):
    reqs_glag = True
    if not os.path.isfile(os.path.join(config['MAIN']['report_dir'], 'jquery.tablesorter.min.js')):
        logging.warning("В папке c отчетами нет файла 'jquery.tablesorter.min.js'."
                        "Для корректной работы отчетов потребуется установить данный файл ")
    if sys.version_info < (3, 6):
        logging.error("Версия Python ниже 3.6 возможны ошибки при дальнейшей работе")
        reqs_glag = False
    if not os.path.isfile("report.html"):
        logging.error("В папке нет шаблона отчета. Работа будет остановлена")
        reqs_glag = False
    return reqs_glag


def find_last_log(config):
    """ Поиск последнего файла в каталоге логов. Поиск идет по дате в названии
    и с учетом маски заданной маски в имени 'nginx-access-ui.log-'

    Args:
        config: данные из конфигурационного файла с именем каталога где хранятся логи

    Returns:
        last_log: имя файла с наибольшей датой в названии
        last_log_date: наибольшая дата из названия файла
    """

    # формируем список файлов в каталоге с нужной маской
    mask = 'nginx-access-ui.log-'
    log_files_list = []

    for file in os.listdir(config['MAIN']['log_dir']):
        if file.startswith(mask):
            log_files_list.append(file)

    # находим последний по дате в названии
    last_log = None
    last_log_date = 0

    for l in log_files_list:
        log_temp = re.search('nginx-access-ui.log-(\d{4}\d{2}\d{2})\.?', l)
        if log_temp is not None:
            if int(log_temp.group(1)) > last_log_date:
                last_log = l
                last_log_date = int(log_temp.group(1))

    last_report_name = 'report_' + str(last_log_date) + '.html'
    full_rep_path = os.path.abspath(config['MAIN']['report_dir'])

    report_exist = os.path.isfile(os.path.join(full_rep_path, last_report_name))

    return last_log, last_log_date, report_exist


def process_line(line):
    """ Функуция для получения параметров url и время запроса из
    одной строки журнала доступа. Если строка получена (длина больше 1),
    то данная строка разбивается и соответствующие записи
    (7 и последняя позиция) записываются в журнал time_log (url - ключ)
    Args:
        line: одна строка из журнала доступа
    Returns:
        True/False обработана или нет строка
        url - url из обработанной строки (если строка не обработана пустое значение)
        response_time - время загрузки страницы (если строка не обработана пустое значение)
    """
    if len(line) > 1:
        try:
            splitted = line.split()
            url = splitted[6].decode("utf-8")
            response_time = splitted[-1].decode("utf-8")
            return True, url, response_time
        except:
            return False, None, None
    else:
        return False, None, None


def parce_log(config, last_log):
    """ Функуция для получения параметров url и время запроса из журнала
    доступа. Сначала, в зависимости от формата файла лога идет открытие либо стандартным способом,
    либо через обработчик gz. Затем через итератор последовательая отработка строк.
    Args:
        config: данные из конфигурационного файла с именем каталога где хранятся логи
        last_log: имя файла с наибольшей датой в названии

    Returns:
        time_log: словарь в котором код - url из журнала, а значения сгруппированный по коду
        список из времен загрузки страницы
    """
    if last_log.endswith(".gz"):
        myFile = gzip.open(os.path.join(config['MAIN']['log_dir'],last_log),'rb')
    else:
        try:
            myFile = open(os.path.join(config['MAIN']['log_dir'],last_log))
        except:
            return False
    time_log = defaultdict(list)
    total = processed = 0
    for s in myFile:
        parsed_line, url, response_time = process_line(s)
        total += 1
        if parsed_line:
            time_log[url].append(response_time)
            processed += 1
            yield parsed_line
    #         if (total % 500000) == 0:
    #             print("%s of %s lines processed" % (processed, total))
    # print("%s of %s lines processed" % (processed, total))
    myFile.close()
    return time_log


def create_report(time_log, config):

    """ Функуция для формирования отчета с рассчитанной статистикой сначала по всем записям считается общее кол-во
    обращений к страницам и суммарное время загрузки всех страниц по всем обращениям. Далее последовательно для каждой
    страницы считается остальная статистика - суммарное время загрузки данной страницы по всем заходам,
    кол-во заходов на страницу, процент заходов на данную страницу от общих заходов на все страницы,
    среднее время загрузки страницы, максимальное и медианное время загрузки, процент суммарного времени всех загрузок
    данной страницы от суммарного времени загрузок всех страниц
    Далее строки отчета фильтруются по параметру- трешхолду на суммарное время загрузок страницы, по данному же полю
    устанавливается сортировка по убыванию и записи сохраняются в тот вид, который затем удобно передавать в шаблон

    Args:
        config: данные из конфигурационного файла с именем каталога где хранятся логи
        time_log: словарь в котором код - url из журнала, а значения сгруппированный по коду

    Returns:
        filtered_report: сформированные данные для последующей передачи в html отчет
    """

    # считаем глобальные сумму и кол-во записей в логе
    total_count = sum([len(v) for (k, v) in time_log.items()])
    total_sum = sum([sum([float(x) for x in v]) for (k, v) in time_log.items()])

    # создание отчета в виде словаря, где ключ это страница, а значения - целевые показатели отчета
    report = defaultdict(list)
    for log, times in time_log.items():
        time_sum = sum([float(x) for x in times])
        count = len(times)
        count_perc = (count / total_count) * 100
        time_avg = time_sum / count
        time_max = max([float(x) for x in times])
        time_med = median([float(x) for x in times])
        time_perc = (time_sum / total_sum) * 100
        report[log].append(count)
        report[log].append(round(count_perc, 3))
        report[log].append(round(time_avg, 3))
        report[log].append(round(time_max, 3))
        report[log].append(round(time_med, 3))
        report[log].append(round(time_perc, 3))
        report[log].append(round(time_sum, 3))

    # фильтрование записей отчета на основании кол-ва заходов на страницу, установленных как параметр и сортировка
    # по суммарному времени загрузок страницы
    filtered_report_temp = OrderedDict((k, v) for k, v in report.items() if v[6] >= int(config["MAIN"]["report_size"]))
    filtered_report_temp = OrderedDict(sorted(filtered_report_temp.items(), key=lambda k_v: k_v[1][6], reverse=True))

    # преобразовываем временный словарь в вид, требуемый для вставки в отчет

    filtered_report = []
    for (k, v) in filtered_report_temp.items():
        sample = {}
        sample = {"count": v[0],
                  "time_avg": v[2],
                  "time_max": v[3],
                  "time_sum": v[6],
                  "url": k,
                  "time_med": v[4],
                  "time_perc": v[5],
                  "count_perc": v[1]
                  }
        filtered_report.append(sample)

    return filtered_report

def generate_html_report (filtered_report, config, last_log_date):
    """ Функуция для передачи ранее сформированного отчета в html файл и формирование html отчета на базе шаблона

    Args:
        config: данные из конфигурационного файла с именем каталога где хранятся логи
        filtered_report: сформированные данные для последующей передачи в html отчет
        last_log_date: маска даты, для формирования имени отчета

    Returns:
        true/false - метка, которая показывает успешность формирования отчета.
    """

    # сначала копируем шаблон отчета и на время манипуляций присваиваем ему префикс temp_
    last_report_name = 'report_' + str(last_log_date) + '.html'
    full_rep_path = os.path.abspath(config['MAIN']['report_dir'])
    try:
        copy2('report.html', os.path.join(full_rep_path, str('temp_') + last_report_name))
    except:
        logging.error("не найден шаблон отчета")
        return False

    # открываем временный отчет (который еще по содержанию шаблон) и копируем из него содержимое
    html_report = open(os.path.join(full_rep_path, str('temp_') + last_report_name), 'r', encoding='utf-8')
    html_data = html_report.read()
    html_report.close()


    # заменяем в переменной с содержимым шаблона отчета строку '$table_json' на данные
    newdata = html_data.replace('$table_json', str(filtered_report))
    # print(newdata)

    # открываем временный отчет (который еще по содержанию шаблон) и вставляем в него новые данные
    html_report = open(os.path.join(full_rep_path, str('temp_') + last_report_name), 'w')
    html_report.write(newdata)
    html_report.close()

    # если замена прошла успешно, убираем префикс temp_ из отчета
    os.rename(os.path.join(full_rep_path, str('temp_') + last_report_name),
              os.path.join(full_rep_path, last_report_name))

    return True


def generate_ts_file(config, last_log_date):
    """ Функуция для создания файла-метки с временем последнего удачного формирования отчета.
    Если в конфигурационном файле есть параметры пути, сохраняем по нему. Если нет, просто выводим на экран
    сообщение, а файл не сохраняем

    Args:
        config: данные из конфигурационного файла с именем каталога где хранятся логи
        last_log_date: маска даты, для формирования имени отчета

    Returns:
        результат либо сформированный файл, либо сообщение на экран
    """
    good_log_date = str(last_log_date)[-2:] + '.' + str(last_log_date)[4:6] + '.' + str(last_log_date)[:4]
    ts = time.asctime()
    try:
        if os.path.isdir(config['MAIN']['tsfile']):
            file = open(os.path.join(config['MAIN']['tsfile'], "log_analyzer.ts"), 'w')
            file.write(ts)
            file.close()
            logging.info("Файл log_analyzer.ts успешно создан")
        else:
            sys.stdout.write(
                'log analyzer по формированию отчета за {} успешно завершил работу {}'.format(good_log_date, ts))
    except:
        sys.stdout.write(
            'log analyzer по формированию отчета за {} успешно завершил работу {}'.format(good_log_date, ts))


def main(log_path):

    # Проверка корректности конфигурационного файла
    check_log_status, config = check_log(log_path)
    if check_log_status == 0:
        return logging.error("Hе удалось найти конфигурационный файл")
    elif check_log_status == 1:
        return logging.error("Не удалось найти все обязательные параметры в конфигурационном файле")
    else:
        logger_reconfig(config)
        logging.info("Проверка конфигурационного файла прошла успешно")

    # Проверка соответствия другим требованиям (версия программы, наличие нужных файлов)
    other_reqs_flag = check_other_reqs(config)

    if other_reqs_flag:
        logging.info("Проверка соответствия прочим требованиям прошла успешно")
    else:
        return logging.error("Программа остановлена, так как не выполнены необходимые требования для работы")

    # Поиск последнего журнала доступа и проверка есть ли уже для него отчет
    last_log, last_log_date, full_rep_path = find_last_log(config)

    if full_rep_path:
        return logging.error("У последнего лог-файла уже есть отчет. Работа программы остановлена")
    else:
        logging.info("Найден последний журнал доступа и у него нет отчета")

    # получение данных из последнего журнала доступа через генераторы.
    gen = Generator(parce_log(config, last_log))
    for x in gen:
        x
    time_log = gen.value
    logging.info("Успешно получены данные из журнала доступа")

    # подготовка данных для htm - отчета
    filtered_report = create_report(time_log, config)
    logging.info("Успешно сформированы данные для отчета")

    # Передача данных шаблон html и формирование  html- отчета
    generate_report_flag = generate_html_report(filtered_report, config, last_log_date)
    if generate_report_flag:
        logging.info("Новый отчет успешно создан")
        # создание ts-файла. Если нет пути в конфигурационном файле, то вывод на экран сообщения о завершении работы
        generate_ts_file(config, last_log_date)
    else:
        logging.info("При формировании нового отчета произошла ошибка. Не удалось сформировать отчет")


if __name__ == "__main__":
    # проверка переданы ли параметры пути кофигурационного файла
    try:
        log_path = sys.argv[1]
    # если нет, конфигурационный файл должен быть в катологе из которого запускается скрипт
    except:
        log_path = 'log_analyzer.conf'
    main(log_path)