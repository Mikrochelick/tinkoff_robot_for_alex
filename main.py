import time
from datetime import datetime
from math import modf, ceil
from tinkoff.invest import Client, Quotation, OrderDirection, OrderType, OperationState, OperationType, InstrumentIdType
import json
import logging


logging.basicConfig(level=logging.WARNING, filename = "bot_logs.log", format = "%(asctime)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s")

with open('token.txt', 'r', encoding='utf-8') as file:
    token = file.read()
TOKEN = token
print(f'Ваш TOKEN: {TOKEN}')


def check_pos(client, account_id, figi):
    """
    Проверяет количество активов на счете. При наличии актива возвращает его количество. При остутствии возвращает None.
    :param client: клиент
    :param account_id: id аккаунта
    :param figi: номер актива
    :return: количество актива, либо указание на его отсутствие
    """
    try:
        positions = client.operations.get_portfolio(account_id=account_id).positions
        for pos in positions:
            if pos.figi == figi:
                return pos.quantity_lots
    except Exception as e:
        print(e)
        return None


def cast_money(price):
    """
    Преобразует цену (любое значение) из типа Quotation в тип float.
    Quotation
    Котировка - денежная сумма без указания валюты
    Field	Type	Description
    units	int64	Целая часть суммы, может быть отрицательным числом
    nano	int32	Дробная часть суммы, может быть отрицательным числом
    :param price:
    :return: число типа float
    """
    if price == None:
        return 0
    return price.units + abs(price.nano / 1e9)  # nano - 9 нулей


def recast_money(price):
    """
    Преобразует цену (любое значение) из типа float в тип Quotation
    Quotation
    Котировка - денежная сумма без указания валюты
    Field	Type	Description
    units	int64	Целая часть суммы, может быть отрицательным числом
    nano	int32	Дробная часть суммы, может быть отрицательным числом
    :param price:
    :return: число типа Quotation
        """
    price = modf(price)
    price = Quotation(units=(int(price[1])), nano=int(round(price[0], 9) * 1e9))
    return price


def read_config_file():
    listik = {}
    with open('config.json', 'r', encoding='utf-8') as file:
        lines = file.readlines()
    for line in lines:
        if line == '\n' or '':
            continue
        line = line.replace('\n', '')
        line = json.loads(line)
        figi = line.get('figi')
        listik[figi] = line
    return listik


def get_precision(number):
    str_f = str(number)
    if '.' not in str_f:
        listik = list(str(number))
        k = int(listik[-1])
        number1 = f"{number:.{k}f}"
        print(number)
        return k
    # Получение строки после точки и возвращение ее длины
    return len(str_f[str_f.index('.') + 1:])


def main():
    print("""
Здравствуйте Алексей, давайте проверим список инструментов и параметры которые вы указали:
    """)
    with Client(TOKEN) as client:
        instrumentses = read_config_file()
        account_id = client.users.get_accounts().accounts[0].id
        config = instrumentses
        list_dict = list(instrumentses)
        num = 1
        for instrument in list_dict:
            time.sleep(0.5)
            name = config.get(instrument).get('name')
            figi = config.get(instrument).get('figi')
            cv = config.get(instrument).get('Cv')
            cn = config.get(instrument).get('Cn')
            cd = config.get(instrument).get('Cd')
            cv_plus = config.get(instrument).get('Cv_plus')
            cn_plus = config.get(instrument).get('Cn_plus')
            mode = config.get(instrument).get('mode')
            min_price_increment = cast_money(client.instruments.get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, id=figi).instrument.min_price_increment)
            config[figi].update({'min_price_increment': min_price_increment})
            Cd = cd / 100
            config[figi].update({'Cd': Cd})
            value = check_pos(client, account_id, figi)
            q = cast_money(value)
            if q == 0:
                logging.warning(f'Название: {name} | FIGI: {figi} | Cv(%): {cv} | Cn(%): {cn} | Cd(%): {cd} | Cv+(%): {cv_plus} | Cn_+(%):{cn_plus} | Режим: {mode} | Объем на счете = {q}')
                print(
                    f'{num})  Название: {name} | FIGI: {figi} | Cv(%): {cv} | Cn(%): {cn} | Cd(%): {cd} | Cv+(%): {cv_plus} | Cn_+(%):{cn_plus} | Режим: {mode} | Объем на счете = {q}')
                config[figi].update({'late_start': 0})
                num += 1
                continue
            else:
                config[figi].update({'late_start': 1})
            logging.warning(f'{num})  Название: {name} | FIGI: {figi} | Cv(%): {cv} | Cn(%): {cn} | Cd(%): {cd} | Cv+(%): {cv_plus} | Cn_+(%):{cn_plus} | Режим: {mode} | Объем на счете = {q}')
            print(f'{num})  Название: {name} | FIGI: {figi} | Cv(%): {cv} | Cn(%): {cn} | Cd(%): {cd} | Cv+(%): {cv_plus} | Cn_+(%):{cn_plus} | Режим: {mode} | Объем на счете = {q}')
            num += 1
            operations = client.operations.get_operations(account_id=account_id, figi=figi,
                                                          state=OperationState.OPERATION_STATE_EXECUTED).operations
            buy_operate = []
            for operate in operations:
                if operate.operation_type == OperationType.OPERATION_TYPE_BUY:
                    buy_operate.append(operate)
            if len(buy_operate) == 0:
                continue
            positions = client.operations.get_portfolio(account_id=account_id)
            for inst in positions.positions:
                if figi == inst.figi:
                    buy_price = inst.average_position_price
            if cast_money(buy_price) == 0:
                continue
            config[figi].update({'price': buy_price})
            Cv = cast_money(buy_price) * (1 + float(instrumentses[instrument].get('Cv')) / 100)
            config[figi].update({'Cv': Cv})
            Cn = cast_money(buy_price) * (1 + float(instrumentses[instrument].get('Cn')) / 100)
            config[figi].update({'Cn': Cn})
        check = input('\nПодтвердите корректность параметров и выбранных вами инструментов\nЕсли все верно, введите (Да\Нет):')
        if check in ['Нет', 'нет']:
            print('Сделайте исправления в config файле. Программа закроется через 4 секунды.')
            time.sleep(4)
            return
        timing = input('Введите количество секунд задержки (5, 10...) увеличивайте в случае превышения лимитов на запросы.\nЧем больше инструментов вы торгуете, тем больше должна быть задержка:')
        while True:
            time.sleep(int(timing))
            try:
                for instrument in list_dict:
                    time.sleep(0.5)
                    mode = int(instrumentses[instrument].get('mode'))
                    figi = instrumentses[instrument].get('figi')
                    value = check_pos(client, account_id, figi)
                    name = config[figi].get('name')
                    q = cast_money(value)
                    if q == 0 and config[figi].get('late_start') == 0:
                        continue
                    if q == 0 and config[figi].get('late_start') == 1:
                        print(f'{datetime.now()} | {name} | {figi} | {mode} | Успешно продан')
                        logging.warning(f' | {name} | {figi} | {mode} | Успешно продан')
                        config[figi].update({'late_start': 0})
                        active_orders = client.orders.get_orders(account_id=account_id).orders
                        active_sell_order = ''
                        for order in active_orders:
                            if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                                active_sell_order = order
                                order_id = active_sell_order.order_id
                                delete_order = client.orders.cancel_order(account_id=account_id, order_id=order_id)
                                print(f'{datetime.now()} | {name} | {figi} | {mode} | Ордер {order_id} удален, тк актив был продан.')
                                logging.warning(f' | {name} | {figi} | {mode} | Ордер {order_id} удален, тк актив был продан.')
                        continue
                    if q != 0 and config[figi].get('late_start') == 0:
                        positions = client.operations.get_portfolio(account_id=account_id)
                        for inst in positions.positions:
                            if figi == inst.figi:
                                buy_price = inst.average_position_price
                        if cast_money(buy_price) == 0:
                            continue
                        config[figi].update({'price': buy_price})
                        Cv = cast_money(buy_price) * (1 + float(instrumentses[instrument].get('Cv')) / 100)
                        config[figi].update({'Cv': Cv})
                        Cn = cast_money(buy_price) * (1 + float(instrumentses[instrument].get('Cn')) / 100)
                        config[figi].update({'Cn': Cn})
                        config[figi].update({'late_start': 1})
                        name = config[figi].get('name')
                        print(f'{datetime.now()} | {name} | {figi} | {mode} | Была сделана покупка. Покупка по цене = {cast_money(buy_price)}, объем = {q}')
                        logging.warning(f' | {name} | {figi} | {mode} | Была сделана покупка. Покупка по цене = {cast_money(buy_price)}, объем = {q}')
                    else:
                        operations = client.operations.get_operations(
                            account_id=account_id,
                            figi=figi,
                            state=OperationState.OPERATION_STATE_EXECUTED).operations
                        buy_operate = []
                        for operate in operations:
                            if operate.operation_type == OperationType.OPERATION_TYPE_BUY:
                                buy_operate.append(operate)
                        if len(buy_operate) == 0:
                            print('нет ордера на покупку, ваша покупка не прошла полностью')
                            logging.warning('нет ордера на покупку, ваша покупка не прошла полностью')
                            continue
                        Cv_plus = (1 + float(instrumentses[instrument].get('Cv_plus')) / 100)
                        Cn_plus = (1 + float(instrumentses[instrument].get('Cn_plus')) / 100)
                        if mode == 1:
                            Cn = config[figi].get('Cn')
                            Cn = ceil(Cn / config[figi].get('min_price_increment')) * config[figi].get(
                                'min_price_increment')
                            Cv = config[figi].get('Cv')
                            Cv = ceil(Cv / config[figi].get('min_price_increment')) * config[figi].get(
                                'min_price_increment')
                            Cd = config[figi].get('Cd')
                            print(Cd)
                            actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                            actual_price = cast_money(actual_price)
                            if actual_price > Cn:
                                active_orders = client.orders.get_orders(account_id=account_id).orders
                                active_sell_order = ''
                                for order in active_orders:
                                    if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                                        active_sell_order = order
                                # Если нет существующего ордера,
                                # выставляем новый лимитный ордер на продажу и на покупку по ценам Cn и Cv
                                if active_sell_order == '':
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0 and config[figi].get('late_start') == 0:
                                        continue
                                    new_sell_order_n = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price=recast_money(Cn),
                                        quantity=int(q),
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Выставлен ордер по нижней границе. Cn = {Cn} | Cv = {Cv}')
                                    logging.warning(f' | {name} | {figi} | {mode} | Выставлен ордер по нижней границе. Cn = {Cn} | Cv = {Cv}')
                                actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                                actual_price = cast_money(actual_price)
                                if actual_price >= Cv - Cv * Cd:
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0:
                                        continue
                                    Cn = config[figi].get('Cn') * Cn_plus
                                    Cn = ceil(Cn / config[figi].get('min_price_increment')) * config[figi].get(
                                            'min_price_increment')
                                    config[figi].update({'Cn': Cn})
                                    Cv = config[figi].get('Cv') * Cv_plus
                                    Cv = ceil(Cv / config[figi].get('min_price_increment')) * config[figi].get(
                                            'min_price_increment')
                                    config[figi].update({'Cv': Cv})
                                    active_orders = client.orders.get_orders(account_id=account_id).orders
                                    active_sell_order = ''
                                    for order in active_orders:
                                        if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                                            active_sell_order = order
                                            order_id = active_sell_order.order_id
                                            delete_order = client.orders.cancel_order(account_id=account_id, order_id=order_id)
                                            time.sleep(10)
                                    new_sell_order_n = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price=recast_money(Cn),
                                        quantity=int(q),
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    logging.warning(f' | {name} | {figi} | {mode} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    continue

                            else:
                                continue
                        if mode == 2:
                            value = check_pos(client, account_id, figi)
                            q = cast_money(value)
                            if q == 0:
                                continue
                            count = config[figi].get('count')
                            if count == 0:
                                Cn = config[figi].get('Cn')
                                Cv = config[figi].get('Cv')
                                Cd = config[figi].get('Cd')
                                print(Cd)
                                actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                                actual_price = cast_money(actual_price)
                                u = Cv - Cv * Cd
                                if actual_price >= Cv - Cv * Cd:
                                    print(f'303 count={count} actual_price={actual_price}, u={u}, Cv={Cv}, Cv*Cd={Cv*Cd}')
                                    Cv = Cv * Cv_plus
                                    Cn = Cn * Cn_plus
                                    Cv = ceil(Cv / config[figi].get('min_price_increment')) * config[figi].get('min_price_increment')
                                    Cn = ceil(Cn / config[figi].get('min_price_increment')) * config[figi].get('min_price_increment')
                                    print(f'308 actual_price={actual_price}, Cv={Cv}, Cn={Cn}, recastCn={recast_money(Cn)}')
                                    config[figi].update({'Cn': Cn})
                                    config[figi].update({'Cv': Cv})
                                    count = count + 1
                                    config[figi].update({'count': count})
                                    active_orders = client.orders.get_orders(account_id=account_id).orders
                                    active_sell_order = ''
                                    for order in active_orders:
                                        if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                                            active_sell_order = order
                                            order_id = active_sell_order.order_id
                                            delete_order = client.orders.cancel_order(account_id=account_id,
                                                                                      order_id=order_id)
                                    new_sell_order_n = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price= recast_money(Cn),
                                        quantity=int(q),
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Выставлен первый ордер | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    logging.warning(f' | {name} | {figi} | {mode} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    continue
                                else:
                                    continue
                            if count == 1:
                                Cn = config[figi].get('Cn')
                                Cv = config[figi].get('Cv')
                                Cd = config[figi].get('Cd')
                                actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                                actual_price = cast_money(actual_price)
                                u = Cv - Cv * Cd
                                if actual_price >= Cv - Cv * Cd:
                                    print(f' 343 count={count} actual_price={actual_price}, u={u}, Cv={Cv}, Cv*Cd={Cv * Cd}')
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0:
                                        continue
                                    Cn = Cn * Cn_plus
                                    Cn = ceil(Cn / config[figi].get('min_price_increment')) * config[figi].get('min_price_increment')
                                    config[figi].update({'Cn': Cn})
                                    Cv = Cv * Cv_plus
                                    Cv = ceil(Cv / config[figi].get('min_price_increment')) * config[figi].get('min_price_increment')
                                    config[figi].update({'Cv': Cv})
                                    print(f'354 count={count} actual_price={actual_price}, Cv={Cv}, Cn={Cn}, recastCn={recast_money(Cn)}')
                                    active_orders = client.orders.get_orders(account_id=account_id).orders
                                    active_sell_order = ''
                                    for order in active_orders:
                                        if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                                            active_sell_order = order
                                            order_id = active_sell_order.order_id
                                            delete_order = client.orders.cancel_order(account_id=account_id, order_id=order_id)
                                    new_sell_order_n = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price= recast_money(Cn),
                                        quantity=int(q),
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    logging.warning(f' | {name} | {figi} | {mode} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    continue
                                else:
                                    continue
                        else:
                            continue
            except Exception as e:
                print(e)
                logging.warning(f' | {name} | {figi} | {mode} | {e} ')
                continue


if __name__ == '__main__':
    main()