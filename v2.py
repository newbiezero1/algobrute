#V1. RSI ниже 30 тогда мы покупаем, если выше 70 тогда продаем.
#Тейк профит для позиции +0.5% движения цены, стоп лосс 5%
import os
import time
import ta
from tradesimulator import TradeSimulator
from multiprocessing import Pool, cpu_count, Manager
from concurrent.futures import ThreadPoolExecutor
import numpy as np

deposit = 10000
commission = 0.1

def test(cache, ohlc, rsi_length, rsi_overbought, rsi_oversold, name='15'):
    ohlc_history = []
    simulator = TradeSimulator(initial_balance=deposit, commission=commission)
    rsi_cache_key = f'rsi_{name}_{rsi_length}'
    if rsi_cache_key in cache:
        rsi = cache[rsi_cache_key]
    else:
        rsi = ta.calculate_rsi(ohlc, rsi_length, name)
        cache[rsi_cache_key] = rsi

    for i in range(len(ohlc)):
        if i < 1: continue
        closedBar = ohlc[i - 1]
        simulator.on_new_candle(index=closedBar['timestamp'], o=closedBar['open'], h=closedBar['high'],
                                l=closedBar['low'], c=closedBar['close'])
        ohlc_history.append(closedBar)
        if (i < 100):
            continue

        newBar = ohlc[i]

        longCondition = rsi[i - 1] < rsi_oversold
        shortCondition = rsi[i - 1] > rsi_overbought
        candlesize = ohlc[i-2]['high'] - ohlc[i-2]['low']

        if longCondition and simulator.get_current_position()['direction'] != 'long':
            if simulator.get_current_position()['direction'] is not None:
                simulator.close_position(index=newBar['timestamp'], close_price=newBar['open'])
            volume = simulator.balance / newBar['open']
            sl = newBar['open'] - candlesize
            tp = newBar['open'] + candlesize
            simulator.open_position(direction='long', entry_price=newBar['open'], volume=volume,
                                    index=newBar['timestamp'])
            simulator.set_stop_loss_and_take_profit(stop_loss=sl, take_profit=tp)

        if shortCondition and simulator.get_current_position()['direction'] != 'short':
            if simulator.get_current_position()['direction'] is not None:
                simulator.close_position(index=newBar['timestamp'], close_price=newBar['open'])
            volume = simulator.balance / newBar['open']
            sl = newBar['open'] + candlesize
            tp = newBar['open'] - candlesize
            simulator.open_position(direction='short', entry_price=newBar['open'], volume=volume,
                                    index=newBar['timestamp'])
            simulator.set_stop_loss_and_take_profit(stop_loss=sl, take_profit=tp)

    #ta.print_trades_history_as_table(simulator.get_trades_history())
    return simulator.get_final_report()


#ohlc = ta.get_ohlc("BTC", "15m")
# Функция для тестирования
def run_test(params):
    cache, ohlc, rsi, overbought, oversold = params
    report = test(cache, ohlc[-15000:], rsi, overbought, oversold, '15')
    with open('log_v2.txt', "w") as file:
        file.write(f'{rsi} {overbought} {oversold} {report["Net Profit"]}\n')
    if report['Net Profit'] < 0:
        return {}
    report30 = test(cache,ohlc[-30000:], rsi, overbought, oversold, '30')
    report45 = test(cache, ohlc, rsi, overbought, oversold, '45')
    report['Net Profit 30k'] = report30['Net Profit']
    report['Net Profit 45k'] = report45['Net Profit']
    report['params'] = f'{rsi} {overbought} {oversold}'
    return report

def threaded_run(params):
    """Выполняется в потоке."""
    try:
        return run_test(params)
    except Exception as e:
        return {"error": str(e), "params": params}

def process_batch(batch):
    """Обработка партии задач в потоке."""
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        return list(executor.map(threaded_run, batch))

if __name__ == "__main__":
    coins = ['BTC', 'AVAX', 'ETC', 'ETH', 'SOL', 'LINK']
    #coins = ['ADA']
    tfs = ['5m', '15m']
    for coin in coins:
        for tf in tfs:
            ta.flush_indicator_cache()
            cache = Manager().dict()
            # Параметры для перебора
            ohlc = ta.get_ohlc(coin, tf)
            start_time = time.time()
            rsi_range = range(14, 28)
            overbought_range = range(70, 91)
            oversold_range = range(10, 31)

            # Генерация всех комбинаций параметров
            param_combinations = [
                (cache, ohlc, rsi, overbought, oversold)
                for rsi in rsi_range
                for overbought in overbought_range
                for oversold in oversold_range
            ]

            report_history = []

            batch_size = 100  # Размер партии
            param_batches = [param_combinations[i:i + batch_size] for i in
                             range(0, len(param_combinations), batch_size)]

            with Pool(cpu_count()) as pool:
                results = pool.map(process_batch, param_batches)

            # Сбор и сохранение результатов
            for batch_result in results:
                report_history.extend(batch_result)
            end_time = time.time()
            print(f"Тест завершён за {end_time - start_time} секунд")
            ta.save_sorted_final_report_to_csv(report_history, f'res/v2_{coin}_{tf}.csv')
            ta.save_sorted_filtered_final_report_to_csv(report_history, f'res/v2_filtered_{coin}_{tf}.csv')
            print(f'test period: {ohlc[0]["timestamp"]} - {ohlc[-1]["timestamp"]}')
