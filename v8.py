import os
import time
import ta
from tradesimulator import TradeSimulator
from multiprocessing import Pool, cpu_count, Manager
from concurrent.futures import ThreadPoolExecutor
import numpy as np

deposit = 10000
commission = 0.1

def test(cache, ohlc, ifilterEma, takeProfit, stopLoss, name='15'):
    simulator = TradeSimulator(initial_balance=deposit, commission=commission)
    trendEma_cache_key = f'trendEma_{name}_{ifilterEma}'
    if trendEma_cache_key in cache:
        trendEma = cache[trendEma_cache_key]
    else:
        trendEma = ta.calculate_ema(ohlc, ifilterEma, name)
        cache[trendEma_cache_key] = trendEma

    for i in range(len(ohlc)):
        if i < 1: continue
        closedBar = ohlc[i-1]
        simulator.on_new_candle(index=closedBar['timestamp'], o=closedBar['open'], h=closedBar['high'], l=closedBar['low'], c=closedBar['close'])
        if i < max([ifilterEma, ifilterEma]):
            continue

        newBar = ohlc[i]
        crossover = ta.calculate_crossover([ohlc[i-2]['close'], ohlc[i-1]['close']], [trendEma[-2], trendEma[-2]])
        crossunder = ta.calculate_crossunder([ohlc[i-2]['close'], ohlc[i-1]['close']], [trendEma[-2], trendEma[-2]])
        longCondition = crossover[-1]
        shortCondition = crossunder[-1]

        if longCondition and simulator.get_current_position()['direction'] != 'long':
            if simulator.get_current_position()['direction'] is not None:
                simulator.close_position(index=newBar['timestamp'], close_price=newBar['open'])
            volume = simulator.balance / newBar['open']
            sl = newBar['open'] * (1 - stopLoss / 100)
            tp = newBar['open'] * (1 + takeProfit / 100)
            simulator.open_position(direction='long', entry_price=newBar['open'], volume=volume, index=newBar['timestamp'])
            simulator.set_stop_loss_and_take_profit(stop_loss=sl, take_profit=tp)

        if shortCondition and simulator.get_current_position()['direction'] != 'short':
            if simulator.get_current_position()['direction'] is not None:
                simulator.close_position(index=newBar['timestamp'], close_price=newBar['open'])
            volume = simulator.balance / newBar['open']
            sl = newBar['open'] * (1 + stopLoss / 100)
            tp = newBar['open'] * (1 - takeProfit / 100)
            simulator.open_position(direction='short', entry_price=newBar['open'], volume=volume, index=newBar['timestamp'])
            simulator.set_stop_loss_and_take_profit(stop_loss=sl, take_profit=tp)

    return simulator.get_final_report()

def threaded_run(params):
    """Выполняется в потоке."""
    try:
        return run_test(params)
    except Exception as e:
        return {"error": str(e), "params": params}

def run_test(params):
    cache, ohlc, filter_ema, takeProfit, stopLoss = params
    report = test(cache, ohlc[-15000:], filter_ema, takeProfit, stopLoss, '15')
    with open('log.txt', "w") as file:
        file.write(f'{filter_ema}  {takeProfit} {stopLoss} {report["Net Profit"]}\n')
    if report['Net Profit'] < 0:
        return {}
    report30 = test(cache, ohlc[-30000:], filter_ema, takeProfit, stopLoss, '30')
    report45 = test(cache, ohlc, filter_ema, takeProfit, stopLoss, '45')
    report['Net Profit 30k'] = report30['Net Profit']
    report['Net Profit 45k'] = report45['Net Profit']
    report['params'] = f'{filter_ema} {takeProfit} {stopLoss}'
    return report

def process_batch(batch):
    """Обработка партии задач в потоке."""
    with ThreadPoolExecutor(max_workers=11) as executor:
        return list(executor.map(threaded_run, batch))

if __name__ == "__main__":
    coins = ['ETC', 'ETH', 'AVAX', 'SOL', 'XRP', 'DOGE', 'LINK','ADA']
    tfs = ['5m', '15m']
    for coin in coins:
        for tf in tfs:
            ta.flush_indicator_cache()
            cache = Manager().dict()
            ohlc = ta.get_ohlc(coin, tf)
            start_time = time.time()
            filter_ema_range = range(50, 300)
            takeProfit_range = np.arange(1.0, 11.0, 0.5)
            stopLoss_range = np.arange(1.0, 11.0, 0.5)

            param_combinations = [
                (cache, ohlc, filter_ema, takeProfit, stopLoss)
                for filter_ema in filter_ema_range
                for takeProfit in takeProfit_range
                for stopLoss in stopLoss_range
            ]

            report_history = []

            # Используем multiprocessing.Pool для распределения партий
            batch_size = 100  # Размер партии
            param_batches = [param_combinations[i:i + batch_size] for i in range(0, len(param_combinations), batch_size)]

            with Pool(cpu_count()) as pool:
                results = pool.map(process_batch, param_batches)

            # Сбор и сохранение результатов
            for batch_result in results:
                report_history.extend(batch_result)

            ta.save_sorted_final_report_to_csv(report_history, f'res/v8_{coin}_{tf}.csv')
            ta.save_sorted_filtered_final_report_to_csv(report_history, f'res/v8_filtered_{coin}_{tf}.csv')
            end_time = time.time()
            print(f"Тест завершён за {end_time - start_time} секунд")
