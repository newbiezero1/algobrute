#V1. RSI ниже 30 тогда мы покупаем, если выше 70 тогда продаем.
#Тейк профит для позиции +0.5% движения цены, стоп лосс 5%
import os
import time
import ta
from tradesimulator import TradeSimulator
from concurrent.futures import ProcessPoolExecutor
import numpy as np

deposit = 10000
commission = 0.1

def test(ohlc, ifilterEma, islowEma, takeProfit, stopLoss):
    simulator = TradeSimulator(initial_balance=deposit, commission=commission)
    trendEma = ta.calculate_ema(ohlc, ifilterEma)
    slowEma = ta.calculate_ema(ohlc, islowEma)
    crossover = ta.calculate_crossover(slowEma, trendEma)
    crossunder = ta.calculate_crossunder(slowEma, trendEma)

    for i in range(len(ohlc)):
        if i < 1: continue
        closedBar = ohlc[i-1]
        simulator.on_new_candle(index=closedBar['timestamp'], o=closedBar['open'], h=closedBar['high'], l=closedBar['low'], c=closedBar['close'])
        if(i < max([ifilterEma, islowEma])):
            continue

        newBar = ohlc[i]

        longCondition = crossover[i-1]
        shortCondition = crossunder[i-1]

        if longCondition and simulator.get_current_position()['direction'] != 'long':
            if simulator.get_current_position()['direction'] is not None:
                simulator.close_position(index=newBar['timestamp'], close_price=newBar['open'])
            volume = simulator.balance / newBar['open']
            sl = newBar['open'] * (1 - stopLoss / 100)
            tp = newBar['open'] * (1 + takeProfit / 100)
            simulator.open_position(direction='long', entry_price=newBar['open'], volume=volume, index=newBar['timestamp'])
            simulator.set_stop_loss_and_take_profit(stop_loss=sl, take_profit=tp)


        if shortCondition  and simulator.get_current_position()['direction'] != 'short':
            if simulator.get_current_position()['direction'] is not None:
                simulator.close_position(index=newBar['timestamp'], close_price=newBar['open'])
            volume = simulator.balance / newBar['open']
            sl = newBar['open'] * (1 + stopLoss / 100)
            tp = newBar['open'] * (1 - takeProfit / 100)
            simulator.open_position(direction='short', entry_price=newBar['open'], volume=volume, index=newBar['timestamp'])
            simulator.set_stop_loss_and_take_profit(stop_loss=sl, take_profit=tp)

    #ta.print_trades_history_as_table(simulator.get_trades_history())
    return simulator.get_final_report()

#ohlc = ta.get_ohlc("BTC", "15m")
# Функция для тестирования
def run_test(params):
    ohlc, filter_ema, slow_ema, takeProfit, stopLoss = params
    report = test(ohlc[:-15000], filter_ema, slow_ema, takeProfit, stopLoss)
    #print(f'{filter_ema} {slow_ema} {takeProfit} {stopLoss} {report["Net Profit"]}')
    with open('log.txt', "w") as file:
        file.write(f'{filter_ema} {slow_ema} {takeProfit} {stopLoss} {report["Net Profit"]}\n')
    if report['Net Profit'] < 0:
        return {}
    report30 = test(ohlc[:-30000], filter_ema, slow_ema, takeProfit, stopLoss)
    report45 = test(ohlc, filter_ema, slow_ema, takeProfit, stopLoss)
    report['Net Profit 30k'] = report30['Net Profit']
    report['Net Profit 45k'] = report45['Net Profit']
    report['params'] = f'{filter_ema} {slow_ema} {takeProfit} {stopLoss}'
    return report

if __name__ == "__main__":
    #coins = ['BTC', 'AVAX', 'ETC', 'ETH', 'SOL', 'LINK']
    print(os.cpu_count())
    coins = ['BTC']
    tfs = ['15m']
    for coin in coins:
        for tf in tfs:
            # Параметры для перебора
            ohlc = ta.get_ohlc(coin, tf)
            start_time = time.time()
            filter_ema_range = range(100, 101)
            slow_ema_range = range(50, 52)
            takeProfit_range = np.arange(1.0, 16.0, 0.5)
            stopLoss_range = np.arange(1.0, 16.0, 0.5)

            # Генерация всех комбинаций параметров
            param_combinations = [
                (ohlc, filter_ema, slow_ema, takeProfit, stopLoss)
                for filter_ema in filter_ema_range
                for slow_ema in slow_ema_range
                for takeProfit in takeProfit_range
                for stopLoss in stopLoss_range
            ]

            report_history = []

            # Использование ProcessPoolExecutor для параллельной обработки
            with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
                results = executor.map(run_test, param_combinations)

            # Сбор и вывод результатов
            report_history.extend(results)
            ta.save_sorted_final_report_to_csv(report_history, f'res/v10_{coin}_{tf}.csv')
            print(f'test period: {ohlc[0]["timestamp"]} - {ohlc[-1]["timestamp"]}')
            end_time = time.time()
            execution_time = end_time - start_time
            print(f"Время выполнения: {execution_time} секунд")