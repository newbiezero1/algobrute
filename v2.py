#V1. RSI ниже 30 тогда мы покупаем, если выше 70 тогда продаем.
#Тейк профит для позиции +0.5% движения цены, стоп лосс 5%
import ta
from tradesimulator import TradeSimulator
from concurrent.futures import ProcessPoolExecutor
import numpy as np

deposit = 10000
commission = 0.1

def test(ohlc, rsi_length, rsi_overbought, rsi_oversold, name='15'):
    ohlc_history = []
    simulator = TradeSimulator(initial_balance=deposit, commission=commission)
    rsi = ta.calculate_rsi(ohlc, rsi_length, name)

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
    ohlc, rsi, overbought, oversold = params
    report = test(ohlc[-15000:], rsi, overbought, oversold, '15')
    with open('log_v2.txt', "w") as file:
        file.write(f'{rsi} {overbought} {oversold} {report["Net Profit"]}\n')
    if report['Net Profit'] < 0:
        return {}
    report30 = test(ohlc[-30000:], rsi, overbought, oversold, '30')
    report45 = test(ohlc, rsi, overbought, oversold, '45')
    report['Net Profit 30k'] = report30['Net Profit']
    report['Net Profit 45k'] = report45['Net Profit']
    report['params'] = f'{rsi} {overbought} {oversold}'
    return report

if __name__ == "__main__":
    coins = ['BTC', 'AVAX', 'ETC', 'ETH', 'SOL', 'LINK']
    #coins = ['ADA']
    tfs = ['5m', '15m']
    for coin in coins:
        for tf in tfs:
            ta.flush_indicator_cache()
            # Параметры для перебора
            ohlc = ta.get_ohlc(coin, tf)
            rsi_range = range(14, 28)
            overbought_range = range(70, 91)
            oversold_range = range(10, 31)

            # Генерация всех комбинаций параметров
            param_combinations = [
                (ohlc, rsi, overbought, oversold)
                for rsi in rsi_range
                for overbought in overbought_range
                for oversold in oversold_range
            ]

            report_history = []

            # Использование ProcessPoolExecutor для параллельной обработки
            with ProcessPoolExecutor() as executor:
                results = executor.map(run_test, param_combinations)

            # Сбор и вывод результатов
            report_history.extend(results)
            ta.save_sorted_final_report_to_csv(report_history, f'res/v2_{coin}_{tf}.csv')
            print(f'test period: {ohlc[0]["timestamp"]} - {ohlc[-1]["timestamp"]}')