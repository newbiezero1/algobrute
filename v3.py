import os
import time
import ta
from tradesimulator import TradeSimulator
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor
import numpy as np

deposit = 10000
commission = 0.1

def test(ohlc,ema, rsi_length,takeProfit, stopLoss, name='15'):
    ohlc_history = []
    simulator = TradeSimulator(initial_balance=deposit, commission=commission)
    rsi = ta.calculate_rsi(ohlc, rsi_length, name)
    ema = ta.calculate_ema(ohlc, ema, name)
    for i in range(len(ohlc)):
        if i < 1: continue
        closedBar = ohlc[i - 1]
        simulator.on_new_candle(index=closedBar['timestamp'], o=closedBar['open'], h=closedBar['high'],
                                l=closedBar['low'], c=closedBar['close'])
        ohlc_history.append(closedBar)
        if (i < 100):
            continue

        newBar = ohlc[i]
        two_day_rsi_avg = (rsi[i-1] + rsi[i-2]) / 2
        longCondition = newBar['open'] > ema[i-1] and two_day_rsi_avg < 33
        shortCondition = False

        if longCondition and simulator.get_current_position()['direction'] != 'long':
            if simulator.get_current_position()['direction'] is not None:
                simulator.close_position(index=newBar['timestamp'], close_price=newBar['open'])
            volume = simulator.balance / newBar['open']
            sl = newBar['open'] * (1 - stopLoss / 100)
            tp = newBar['open'] * (1 + takeProfit / 100)
            simulator.open_position(direction='long', entry_price=newBar['open'], volume=volume,
                                    index=newBar['timestamp'])
            simulator.set_stop_loss_and_take_profit(stop_loss=sl, take_profit=tp)


    #ta.print_trades_history_as_table(simulator.get_trades_history())
    return simulator.get_final_report()


#ohlc = ta.get_ohlc("BTC", "15m")
# Функция для тестирования
def run_test(params):
    ohlc, ema, rsi, takeProfit, stopLoss = params
    report = test(ohlc[-15000:], ema, rsi, takeProfit, stopLoss, '15')
    with open('log_v2.txt', "w") as file:
        file.write(f'{ema} {rsi} {takeProfit} {stopLoss} {report["Net Profit"]}\n')
    if report['Net Profit'] < 0:
        return {}
    report30 = test(ohlc[-30000:], ema, rsi, takeProfit, stopLoss, '30')
    report45 = test(ohlc, ema, rsi, takeProfit, stopLoss, '45')
    report['Net Profit 30k'] = report30['Net Profit']
    report['Net Profit 45k'] = report45['Net Profit']
    report['params'] = f'{ema} {rsi} {takeProfit} {stopLoss}'
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
            # Параметры для перебора
            ohlc = ta.get_ohlc(coin, tf)
            rsi_range = range(14, 15)
            ema_range = range(200, 201)
            takeProfit_range = np.arange(1.0, 16.0, 0.5)
            stopLoss_range = np.arange(1.0, 16.0, 0.5)

            # Генерация всех комбинаций параметров
            param_combinations = [
                (ohlc, ema, rsi, takeProfit, stopLoss)
                for ema in ema_range
                for rsi in rsi_range
                for takeProfit in takeProfit_range
                for stopLoss in stopLoss_range
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
            ta.save_sorted_final_report_to_csv(report_history, f'res/v3_{coin}_{tf}.csv')
            ta.save_sorted_filtered_final_report_to_csv(report_history, f'res/v3_filtered_{coin}_{tf}.csv')
            print(f'test period: {ohlc[0]["timestamp"]} - {ohlc[-1]["timestamp"]}')