import pandas as pd
import requests
from datetime import datetime
from tabulate import tabulate
import csv

ema_cache = {}
def calculate_ema(ohlc, period, name):
    cache_key = f'{name}_{period}'
    if cache_key in ema_cache:
        return ema_cache[cache_key]
    prices = []
    for line in ohlc:
        prices.append(line["close"])
    prices_series = pd.Series(prices)
    ema = prices_series.ewm(span=period, adjust=False).mean()
    res = ema.tolist()
    ema_cache[cache_key] = res
    return res

def calculate_rsi(ohlc, period):
    prices = []
    for line in ohlc:
        prices.append(line["close"])

    prices_series = pd.Series(prices).astype(float)

    # Расчет изменения цен
    delta = prices_series.diff()

    # Вычисление прироста и убытка
    gain = delta.where(delta > 0, 0)  # Прирост
    loss = -delta.where(delta < 0, 0)  # Убыток (в положительных значениях)

    # Вычисление средних прироста и убытка за период
    avg_gain_initial = gain.rolling(window=period, min_periods=period).mean()
    avg_loss_initial = loss.rolling(window=period, min_periods=period).mean()

    # После первого периода используем формулу EMA для среднего прироста и убытка
    avg_gain = pd.concat([avg_gain_initial.iloc[:period], gain[period:].ewm(alpha=1 / period, adjust=False).mean()])
    avg_loss = pd.concat([avg_loss_initial.iloc[:period], loss[period:].ewm(alpha=1 / period, adjust=False).mean()])

    # Рассчет RS (отношение средних прироста к среднему убытку)
    rs = avg_gain / avg_loss

    # Рассчет RSI
    rsi = 100 - (100 / (1 + rs))

    # Возвращаем RSI в виде списка, где значения до периода заполнены NaN
    rr = rsi.tolist()
    rounded_rsi = []
    for i in rr:
        if i > 0:
            rounded_rsi.append(round(i,2))
        else:
            rounded_rsi.append(0)
    return rounded_rsi

ohlc_cache = {}
def get_ohlc(coin, tf):
    cache_key = f'{coin}_{tf}'
    if cache_key in ohlc_cache:
        print('from cache')
        return ohlc_cache[cache_key]
    limit = 1500;
    interval = tf
    ohlc = []
    umnozhitel = 5
    if tf == '5m':
        umnozhitel = 5
    if tf == '10m':
        umnozhitel = 5
    if tf == '15m':
        umnozhitel = 15
    if tf == '30m':
        umnozhitel = 30
    if tf == '1h':
        umnozhitel = 60
    if tf == '4h':
        umnozhitel = 240

    unix_time = int(datetime.now().timestamp())
    i = 30
    while i > 1:
        print(f'Load klines [{i}/30]')
        date_start = (unix_time - (limit * umnozhitel * 60) * i) * 1000
        response = requests.get(
            f'https://fapi.binance.com/fapi/v1/klines?symbol={coin}USDT&interval={interval}&limit={limit}&startTime={date_start}')
        kline = response.json()
        for line in kline:
            unix_time_sec = line[0] / 1000.0
            dt = datetime.fromtimestamp(unix_time_sec)
            data = {"timestamp": dt.strftime('%Y-%m-%d %H:%M:%S'), "open": float(line[1]),
                    "high": float(line[2]),
                    "low": float(line[3]),
                    "close": float(line[4])}
            ohlc.append(data)
        i = i-1

    response = requests.get(f'https://fapi.binance.com/fapi/v1/klines?symbol={coin}USDT&interval={interval}&limit={limit}')
    kline = response.json()
    for line in kline:
        unix_time_sec = line[0] / 1000.0
        dt = datetime.fromtimestamp(unix_time_sec)
        data = {"timestamp": dt.strftime('%Y-%m-%d %H:%M:%S'), "open": float(line[1]),
                "high": float(line[2]),
                "low": float(line[3]),
                "close": float(line[4])}
        ohlc.append(data)
    ohlc_cache[cache_key] = ohlc
    return ohlc

def print_trades_history_as_table(trades_history):
    """
    Преобразует и выводит историю сделок в виде таблицы с цветным фоном для прибыли:
    - Красный фон для отрицательной прибыли, белый текст.
    - Зелёный фон для положительной прибыли, белый текст.

    :param trades_history: список словарей с данными о сделках.
    """
    if not trades_history:
        print("История сделок пуста.")
        return
    trades_history.reverse()
    # Обрабатываем данные для выделения прибыли
    processed_trades = []
    for trade in trades_history:
        processed_trade = {}
        for key, value in trade.items():
            if key == "profit" and isinstance(value, (int, float)):
                if value < 0:
                    # Красный фон, белый текст
                    processed_trade[key] = f"\033[41m{value}\033[0m"
                elif value > 0:
                    # Зелёный фон, белый текст
                    processed_trade[key] = f"\033[42m{value}\033[0m"
                else:
                    processed_trade[key] = value  # Нейтральное значение
            elif key == "direction":
                if value =='short':
                    # Красный фон, белый текст
                    processed_trade[key] = f"\033[41m{value}\033[0m"
                elif value == 'long':
                    # Зелёный фон, белый текст
                    processed_trade[key] = f"\033[42m{value}\033[0m"
                else:
                    processed_trade[key] = value  # Нейтральное значение
            else:
                processed_trade[key] = value
        processed_trades.append(processed_trade)

    # Преобразуем в табличный вид
    headers = processed_trades[0].keys()
    table = [trade.values() for trade in processed_trades]

    # Печатаем таблицу
    print(tabulate(table, headers=headers, tablefmt="grid"))


def print_sorted_reports(reports, file_path):
    """
    Выводит список итоговых отчётов в виде таблицы, отсортированный по 'Net Profit'.

    :param reports: список словарей с итоговыми данными.
    """
    if not reports:
        print("Список отчётов пуст.")
        return

    # Сортируем отчёты по 'Net Profit' в порядке убывания
    sorted_reports = sorted(
        reports,
        key=lambda x: (x.get('Net Profit', 0), x.get('Net Profit 30k', 0), x.get('Net Profit 45k', 0)),
        reverse=True
    )
    # Новый порядок колонок
    column_order = [
        "Net Profit",
        "Net Profit 30k",
        "Net Profit 45k",
        "Percent Profitable",
        "Total Trades",
        "Profit Factor",
        "Max Drawdown",
        "Avg Trade (%)",
        "params"
    ]

    # Преобразуем каждый отчёт в соответствии с новым порядком колонок
    reordered_reports = [
        {key: report.get(key, "") for key in column_order} for report in sorted_reports
    ]

    # Заголовки таблицы
    headers = reordered_reports[0].keys()

    # Преобразуем данные в строку таблицы
    table_str = tabulate(
        [list(report.values()) for report in reordered_reports],
        headers=headers,
        tablefmt="grid"
    )

    # Записываем таблицу в файл
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(table_str)
    # Печатаем таблицу
    #print(tabulate(table_str, headers=headers, tablefmt="grid"))


def save_sorted_final_report_to_csv(reports, file_path):
    """
    Сохраняет список итоговых отчётов в CSV файл, сортируя по убыванию 'Net Profit',
    и учитывая указанный порядок колонок.

    :param reports: список словарей с итоговыми данными.
    :param file_path: путь к CSV файлу для сохранения.
    """
    if not reports:
        print("Список отчётов пуст.")
        return

    # Порядок колонок
    column_order = [
        "Net Profit",
        "Net Profit 30k",
        "Net Profit 45k",
        "Percent Profitable",
        "Total Trades",
        "Profit Factor",
        "Max Drawdown",
        "Avg Trade (%)",
        "params"
    ]

    # Фильтруем записи, исключая строки с пустыми ключевыми значениями
    filtered_reports = [
        report for report in reports if report.get("Net Profit") is not None
    ]

    if not filtered_reports:
        print("Нет данных для сохранения.")
        return

    # Сортируем отчёты по 'Net Profit' в порядке убывания
    sorted_reports = sorted(filtered_reports, key=lambda x: x.get("Net Profit", 0), reverse=True)

    # Сохраняем в CSV
    with open(file_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=column_order)

        # Записываем заголовки
        writer.writeheader()

        # Записываем строки в нужном порядке колонок
        for report in sorted_reports:
            # Используем .get для ключей, чтобы не было ошибок, если данных не хватает
            writer.writerow({col: report.get(col, "") for col in column_order})

def calculate_crossover(v_fastEMA, v_slowEMA):
    bullSignal = []
    for i in range(len(v_fastEMA)):
        bullSignal.append(False)
        if i == 0:
            continue
        if v_fastEMA[i - 1] < v_slowEMA[i - 1] and v_fastEMA[i] > v_slowEMA[i]:
            bullSignal[i] = True
    return bullSignal

def calculate_crossunder(v_fastEMA, v_slowEMA):
    bearSignal = []
    for i in range(len(v_fastEMA)):
        bearSignal.append(False)
        if i == 0:
            continue
        if v_fastEMA[i - 1] > v_slowEMA[i - 1] and v_fastEMA[i] < v_slowEMA[i]:
            bearSignal[i] = True
    return bearSignal