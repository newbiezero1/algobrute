from tradesimulator import TradeSimulator
import os
print(os.cpu_count())
# Инициализируем симулятор
simulator = TradeSimulator(initial_balance=10000.0, commission=0.0005)

# Открываем лонг по цене 100, объём 1 лот
simulator.open_position(direction='long', entry_price=100, volume=1, index=0)
# Устанавливаем стоп-лосс и тейк-профит
simulator.set_stop_loss_and_take_profit(stop_loss=95, take_profit=110)

# Новая свеча: цены O=101, H=105, L=99, C=104
simulator.on_new_candle(index=1, o=101, h=105, l=99, c=104)
# Позиция не должна была закрыться, т.к. L=99 не пробил стоп-лосс 95, а H=105 не достиг тейка 110

# Следующая свеча: O=104, H=112, L=103, C=111
# Здесь должна сработать тейк-профит (т.к. High=112 >= 110)
simulator.on_new_candle(index=2, o=104, h=112, l=103, c=111)

# Проверяем результат сделки
print("Текущий баланс:", simulator.balance)
print("История сделок:", simulator.get_trades_history())

# Открываем шорт по цене 120, объём 1
simulator.open_position(direction='short', entry_price=120, volume=1, index=3)
# Ставим стоп-лосс и тейк-профит
simulator.set_stop_loss_and_take_profit(stop_loss=125, take_profit=110)

# Имитация свечей
simulator.on_new_candle(index=4, o=119, h=123, l=118, c=122)  # стоп не сработал (high=123 < 125)
simulator.on_new_candle(index=5, o=122, h=126, l=121, c=125)  # теперь high=126 -> стоп-лосс 125 сработает

# Итоговый отчёт
# Проверяем результат сделки
print("Текущий баланс:", simulator.balance)
print("История сделок:", simulator.get_trades_history())
final_report = simulator.get_final_report()
print("Итоговый отчёт:", final_report)
