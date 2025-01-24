class TradeSimulator:
    def __init__(self, initial_balance: float = 10000.0, commission: float = 0.035):
        """
        Инициализация симулятора.
        :param initial_balance: начальный депозит.
        :param commission: комиссия за сделку (в процентах от объёма сделки).
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.commission = commission

        # Текущая открытая позиция
        self.current_position = {
            'direction': None,  # 'long' или 'short'
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None,
            'volume': 0.0,
            'entry_index': None  # Индекс свечи (или время), когда открыли позицию
        }

        # История сделок
        self.trades_history = []

        # Для расчёта максимальной просадки
        self.equity_curve = [self.balance]  # Будем хранить баланс/эквити после прихода каждой новой свечи

    def set_basic_settings(self, initial_balance: float, commission: float):
        """
        Установка базовых настроек.
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.commission = commission
        self.current_position = {
            'direction': None,
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None,
            'volume': 0.0,
            'entry_index': None
        }
        self.trades_history.clear()
        self.equity_curve = [self.balance]

    def open_position(self, direction: str, entry_price: float, volume: float, index=None):
        """
        Открытие позиции:
        :param direction: 'long' или 'short'
        :param entry_price: цена входа
        :param volume: условный объём позиции (кол-во лотов, контрактов, и т.п.)
        :param index: индекс свечи или метка времени
        """
        if self.current_position['direction'] is not None:
            print("У вас уже есть открытая позиция. Сначала закройте предыдущую.")
            return

        if direction not in ['long', 'short']:
            print("Неверное направление позиции. Используйте 'long' или 'short'.")
            return

        # Комиссия за открытие (условно, без учёта плеча)
        open_commission = (entry_price * volume * self.commission) / 100

        # Проверка, хватает ли средств на открытие с учётом комиссии (упрощённо).
        if self.balance < open_commission:
            print("Недостаточно средств для уплаты комиссии.")
            return

        # Списываем комиссию
        self.balance -= open_commission

        self.current_position = {
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': None,
            'take_profit': None,
            'volume': volume,
            'entry_index': index
        }

    def set_stop_loss_and_take_profit(self, stop_loss: float, take_profit: float):
        """
        Установка стоп-лосса и тейк-профита для уже открытой позиции.
        """
        if self.current_position['direction'] is None:
            print("Нет открытой позиции, чтобы установить SL/TP.")
            return

        self.current_position['stop_loss'] = stop_loss
        self.current_position['take_profit'] = take_profit

    def close_position(self, close_price: float, index=None, reason: str = "manual"):
        """
        Принудительное закрытие позиции по цене close_price (или закрытие SL/TP).
        :param close_price: цена выхода
        :param index: индекс свечи или время
        :param reason: причина закрытия, например 'manual', 'stop_loss', 'take_profit'
        """
        if self.current_position['direction'] is None:
            print("Нет открытой позиции для закрытия.")
            return

        direction = self.current_position['direction']
        entry_price = self.current_position['entry_price']
        volume = self.current_position['volume']
        entry_index = self.current_position['entry_index']

        # Комиссия за закрытие
        close_commission = (close_price * volume * self.commission) / 100

        # Расчёт профита (упрощённо, без плеча)
        if direction == 'long':
            trade_profit = (close_price - entry_price) * volume
        else:  # short
            trade_profit = (entry_price - close_price) * volume

        # Учёт комиссии за закрытие
        trade_profit -= close_commission

        # Изменяем баланс
        self.balance += trade_profit

        # Сохраняем сделку в историю
        self.trades_history.append({
            'entry_index': entry_index,
            'entry_price': entry_price,
            'close_index': index,
            'close_price': close_price,
            'direction': direction,
            'volume': volume,
            'profit': trade_profit,
            'reason': reason
        })

        # Сброс текущей позиции
        self.current_position = {
            'direction': None,
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None,
            'volume': 0.0,
            'entry_index': None
        }

    def on_new_candle(self, index, o: float, h: float, l: float, c: float):
        """
        Вызывается при приходе новой свечи.
        Здесь проверяем, не сработал ли стоп-лосс или тейк-профит.

        :param index: индекс или время текущей свечи
        :param o, h, l, c: open, high, low, close цены свечи
        """
        # Если нет открытой позиции, просто обновляем эквити (баланс) и выходим
        if self.current_position['direction'] is None:
            self.equity_curve.append(self.balance)
            return

        direction = self.current_position['direction']
        stop_loss = self.current_position['stop_loss']
        take_profit = self.current_position['take_profit']

        triggered_reason = None
        triggered_price = None

        # Проверка стоп-лосса и тейк-профита для лонга
        if direction == 'long':
            # Сначала проверяем, дошла ли цена до стоп-лосса
            if stop_loss is not None and l <= stop_loss:
                triggered_reason = "stop_loss"
                triggered_price = stop_loss
            # Если стоп не сработал, проверяем тейк
            elif take_profit is not None and h >= take_profit:
                triggered_reason = "take_profit"
                triggered_price = take_profit

        # Проверка стоп-лосса и тейк-профита для шорта
        if direction == 'short':
            # Для шорта стоп-лосс: если high >= stop_loss
            if stop_loss is not None and h >= stop_loss:
                triggered_reason = "stop_loss"
                triggered_price = stop_loss
            # Тейк-профит: если low <= take_profit
            elif take_profit is not None and l <= take_profit:
                triggered_reason = "take_profit"
                triggered_price = take_profit

        # Если был триггер стопа или тейка, закрываем позицию
        if triggered_reason and triggered_price:
            self.close_position(close_price=triggered_price, index=index, reason=triggered_reason)
        else:
            # Если стоп/тейк не сработал, то просто фиксируем текущий баланс (эквити).
            # Баланс не меняется, позиция ещё открыта.
            self.equity_curve.append(self.balance)

    def get_current_position(self):
        """
        Возвращает информацию о текущей позиции.
        """
        return self.current_position

    def get_trades_history(self):
        """
        Возвращает историю сделок.
        """
        return self.trades_history

    def get_final_report(self):
        """
        Формирует итоговый отчёт о торговых результатах:
         - Net Profit
         - Total Trades
         - Percent Profitable
         - Profit Factor (отношение суммарной прибыли к суммарному убытку)
         - Max Drawdown
         - Average Trade (в процентах от начального депозита)
        """
        total_trades = len(self.trades_history)
        if total_trades == 0:
            return {
                'Net Profit': 0.0,
                'Total Trades': 0,
                'Percent Profitable': 0.0,
                'Profit Factor': 0.0,
                'Max Drawdown': 0.0,
                'Avg Trade (%)': 0.0
            }

        net_profit = self.balance - self.initial_balance

        # Подсчёт прибыли и убытков
        wins = [t['profit'] for t in self.trades_history if t['profit'] > 0]
        losses = [t['profit'] for t in self.trades_history if t['profit'] < 0]

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))

        # Процент прибыльных сделок
        percent_profitable = (len(wins) / total_trades) * 100.0 if total_trades else 0.0

        # Profit factor
        profit_factor = (gross_profit / gross_loss) if gross_loss != 0 else float('inf')

        # Максимальная просадка
        # Для расчёта используем equity_curve:
        #   max_dd = максимальное (предыдущее max_equity - текущее equity)
        max_equity = self.equity_curve[0]
        max_drawdown_abs = 0.0

        for eq in self.equity_curve:
            if eq > max_equity:
                max_equity = eq
            drawdown = max_equity - eq
            if drawdown > max_drawdown_abs:
                max_drawdown_abs = drawdown

        max_drawdown_percent = (max_drawdown_abs / self.initial_balance) * 100.0

        # Средняя прибыль/убыток на сделку в процентах от начального депозита
        avg_trade_percent = (net_profit / self.initial_balance) * 100.0 / total_trades

        return {
            'Net Profit': net_profit,
            'Total Trades': total_trades,
            'Percent Profitable': percent_profitable,
            'Profit Factor': profit_factor,
            'Max Drawdown': max_drawdown_percent,
            'Avg Trade (%)': avg_trade_percent
        }
