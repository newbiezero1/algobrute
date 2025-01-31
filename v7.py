import os
import time
import ta
from tradesimulator import TradeSimulator
from multiprocessing import Pool, cpu_count, Manager
from concurrent.futures import ThreadPoolExecutor
import numpy as np

deposit = 10000
commission = 0.1

def test(cache, ohlc, ifilterEma, ifastEma, islowEma, rsi_length, overbuy, oversell, takeProfit, stopLoss, name='15'):
    simulator = TradeSimulator(initial_balance=deposit, commission=commission)
    trendEma_cache_key = f'trendEma_{name}_{ifilterEma}'
    if trendEma_cache_key in cache:
        trendEma = cache[trendEma_cache_key]
    else:
        trendEma = ta.calculate_ema(ohlc, ifilterEma, name)
        cache[trendEma_cache_key] = trendEma

    slowEma_cache_key = f'slowEma_{name}_{islowEma}'
    if slowEma_cache_key in cache:
        slowEma = cache[slowEma_cache_key]
    else:
        slowEma = ta.calculate_ema(ohlc, islowEma, name)
        cache[slowEma_cache_key] = slowEma

    fastEma_cache_key = f'fastEma_{name}_{ifastEma}'
    if fastEma_cache_key in cache:
        fastEma = cache[fastEma_cache_key]
    else:
        fastEma = ta.calculate_ema(ohlc, ifastEma, name)
        cache[fastEma_cache_key] = fastEma

    rsi_cache_key = f'rsi_{name}_{rsi_length}'
    if rsi_cache_key in cache:
        rsi = cache[rsi_cache_key]
    else:
        rsi = ta.calculate_rsi(ohlc, rsi_length, name)
        cache[rsi_cache_key] = rsi
    crossover = ta.calculate_crossover(fastEma, slowEma)
    crossunder = ta.calculate_crossunder(fastEma, slowEma)

    for i in range(len(ohlc)):
        if i < 1: continue
        closedBar = ohlc[i-1]
        simulator.on_new_candle(index=closedBar['timestamp'], o=closedBar['open'], h=closedBar['high'], l=closedBar['low'], c=closedBar['close'])
        if i < max([ifilterEma, islowEma]):
            continue

        newBar = ohlc[i]

        longCondition = crossover[i-1] and newBar['open'] > trendEma[i-1] and rsi[i-1] < overbuy
        shortCondition = crossunder[i-1] and newBar['open'] < trendEma[i-1] and rsi[i-1] > oversell

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
    cache, ohlc, filter_ema,fast_ema, slow_ema, rsi_length, overbuy, oversell, takeProfit, stopLoss = params
    report = test(cache, ohlc[-15000:], filter_ema,fast_ema, slow_ema, rsi_length, overbuy, oversell, takeProfit, stopLoss, '15')
    with open('log.txt', "w") as file:
        file.write(f'{filter_ema} {fast_ema} {slow_ema} {rsi_length} {overbuy} {oversell} {takeProfit} {stopLoss} {report["Net Profit"]}\n')
    if report['Net Profit'] < 0:
        return {}
    report30 = test(cache, ohlc[-30000:], filter_ema,fast_ema, slow_ema, rsi_length, overbuy, oversell, takeProfit, stopLoss, '30')
    report45 = test(cache, ohlc, filter_ema,fast_ema, slow_ema, rsi_length, overbuy, oversell, takeProfit, stopLoss, '45')
    report['Net Profit 30k'] = report30['Net Profit']
    report['Net Profit 45k'] = report45['Net Profit']
    report['params'] = f'{filter_ema} {fast_ema} {slow_ema} {rsi_length} {overbuy} {oversell} {takeProfit} {stopLoss}'
    return report

def process_batch(batch):
    """Обработка партии задач в потоке."""
    with ThreadPoolExecutor(max_workers=11) as executor:
        return list(executor.map(threaded_run, batch))

if __name__ == "__main__":
    coins = ['BTC']
    tfs = ['5m', '15m']
    for coin in coins:
        for tf in tfs:
            ta.flush_indicator_cache()
            cache = Manager().dict()
            ohlc = ta.get_ohlc(coin, tf)
            start_time = time.time()
            filter_ema_range = range(200, 250, 5)
            fast_ema_range = range(10, 40, 5)
            slow_ema_range = range(20, 80, 5)
            rsi_range = range(14, 24,2)
            overbought_range = range(70, 81,2)
            oversold_range = range(20, 31,2)
            takeProfit_range = np.arange(1.0, 11.0, 1.0)
            stopLoss_range = np.arange(1.0, 11.0, 1.0)

            param_combinations = [
                (cache, ohlc, filter_ema, fast_ema, slow_ema, rsi_length, overbuy, oversell, takeProfit, stopLoss)
                for filter_ema in filter_ema_range
                for fast_ema in fast_ema_range
                for slow_ema in slow_ema_range
                for rsi_length in rsi_range
                for overbuy in overbought_range
                for oversell in oversold_range
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

            ta.save_sorted_final_report_to_csv(report_history, f'res/v7_{coin}_{tf}.csv')
            ta.save_sorted_filtered_final_report_to_csv(report_history, f'res/v7_filtered_{coin}_{tf}.csv')
            end_time = time.time()
            print(f"Тест завершён за {end_time - start_time} секунд")
