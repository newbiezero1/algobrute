import os
import time
import ta
from tradesimulator import TradeSimulator
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor
import numpy as np

deposit = 10000
commission = 0.1

def test(ohlc, rsi_length, overbuy, oversell, takeProfit, name='15'):
    simulator = TradeSimulator(initial_balance=deposit, commission=commission)
    rsi = ta.calculate_rsi(ohlc, rsi_length)

    for i in range(len(ohlc)):
        if i < 1: continue
        closedBar = ohlc[i-1]
        simulator.on_new_candle(index=closedBar['timestamp'], o=closedBar['open'], h=closedBar['high'], l=closedBar['low'], c=closedBar['close'])
        if i < rsi_length*10:
            continue

        newBar = ohlc[i]
        crossover = ta.calculate_crossover([rsi[i-2], rsi[i-1]], [oversell, oversell])
        crossunder = ta.calculate_crossunder([rsi[i-2], rsi[i-1]], [overbuy, overbuy])
        longCondition = crossover[-1]
        shortCondition = crossunder[-1]

        if longCondition and simulator.get_current_position()['direction'] != 'long':
            if simulator.get_current_position()['direction'] is not None:
                simulator.close_position(index=newBar['timestamp'], close_price=newBar['open'])
            volume = simulator.balance / newBar['open']
            sl = closedBar['low']
            tp = newBar['open'] * (1 + takeProfit / 100)
            simulator.open_position(direction='long', entry_price=newBar['open'], volume=volume, index=newBar['timestamp'])
            simulator.set_stop_loss_and_take_profit(stop_loss=sl, take_profit=tp)

        if shortCondition and simulator.get_current_position()['direction'] != 'short':
            if simulator.get_current_position()['direction'] is not None:
                simulator.close_position(index=newBar['timestamp'], close_price=newBar['open'])
            volume = simulator.balance / newBar['open']
            sl = closedBar['high']
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
    ohlc, rsi_length, overbuy, oversell, takeProfit = params
    report = test(ohlc[:-15000], rsi_length, overbuy, oversell, takeProfit, '15')
    with open('log_v2.txt', "w") as file:
        file.write(f'{rsi_length} {overbuy} {oversell} {takeProfit} {report["Net Profit"]}\n')
    if report['Net Profit'] < 0:
        return {}
    report30 = test(ohlc[:-30000],rsi_length, overbuy, oversell, takeProfit, '30')
    report45 = test(ohlc, rsi_length, overbuy, oversell, takeProfit, '45')
    report['Net Profit 30k'] = report30['Net Profit']
    report['Net Profit 45k'] = report45['Net Profit']
    report['params'] = f'{rsi_length} {overbuy} {oversell} {takeProfit}'
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
            ohlc = ta.get_ohlc(coin, tf)
            start_time = time.time()
            rsi_range = range(14, 28)
            overbought_range = range(70, 91)
            oversold_range = range(10, 31)
            takeProfit_range = np.arange(1.0, 16.0, 0.5)

            param_combinations = [
                (ohlc, rsi, overbought, oversold, takeProfit)
                for rsi in rsi_range
                for overbought in overbought_range
                for oversold in oversold_range
                for takeProfit in takeProfit_range
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

            ta.save_sorted_final_report_to_csv(report_history, f'res/v6_{coin}_{tf}.csv')
            end_time = time.time()
            print(f"Тест завершён за {end_time - start_time} секунд")
