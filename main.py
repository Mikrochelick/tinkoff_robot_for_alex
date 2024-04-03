import time
from datetime import datetime
from math import modf, ceil
from tinkoff.invest import (Client, Quotation, StopOrderDirection, OperationState, OperationType, InstrumentIdType,
                            StopOrderExpirationType, StopOrderType, OrderDirection, OrderType)
import json
import logging
import requests
from sqlite3_func import create_base

create_base()


logging.basicConfig(level=logging.WARNING,
    filename="bot_logs.log", format="%(asctime)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s")

with open('token.txt', 'r', encoding='utf-8') as file:
    token = file.read()
TOKEN = token
chat_id = '477647007'


def send_message(text=None):
    url = f'https://api.telegram.org/bot6910807237:AAE5zdaKs8lfAxE_pEM4P6G1xCioWR4BReg/sendMessage'
    data = {'chat_id': chat_id, 'text': text}
    response = requests.post(url, data=data)
    return


def buy_and_check(client=None, account_id=None, figi=None, config=None, instrumentses=None, instrument=None):
    lot = client.instruments.get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, id=figi).instrument.lot
    value = check_pos(client, account_id, figi)
    q = cast_money(value)
    name = config[figi].get('name')
    cmax = config[figi].get("Cmax")
    nmax = config[figi].get("Nmax")
    qmin = config[figi].get("Qmin")
    lmax = config[figi].get("Lmax")
    kmax = config[figi].get("Kmax")
    g = config[figi].get("G")
    count_buy = config[figi].get("count_buy")
    ostatok = client.operations.get_withdraw_limits(account_id=account_id).money[0]
    ostatok = cast_money(ostatok)
    qu = check_pos(client=client, account_id=account_id, figi=figi)
    qu = cast_money(value)
    actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
    actual_price = cast_money(actual_price)
    if actual_price*lot <= cmax and count_buy < nmax:
        if qu == 0 and count_buy == 0:
            if ostatok > qmin:
                r1 = client.orders.post_order(order_id=str(datetime.utcnow().timestamp()),
                                         figi=figi,
                                         price=recast_money(actual_price),
                                         quantity=1,
                                         account_id=account_id,
                                         direction=OrderDirection.ORDER_DIRECTION_BUY,
                                         order_type=OrderType.ORDER_TYPE_LIMIT)
                time.sleep(8)
                config[figi].update({'last_price': actual_price})
                config[figi].update({'late_start': 2})
                name = config[figi].get('name')
                count_buy = config[figi].get("count_buy")
                count_buy = count_buy + 1
                config[figi].update({'count_buy': count_buy})
                positions = client.operations.get_portfolio(account_id=account_id)
                price_in_port = 0.0
                for inst in positions.positions:
                    if figi == inst.figi:
                        price_in_port = inst.average_position_price
                if price_in_port == 0.0:
                    print('1повторный запрос стоимости в портфеле')
                    time.sleep(30)
                    positions = client.operations.get_portfolio(account_id=account_id)
                    for inst in positions.positions:
                        if figi == inst.figi:
                            price_in_port = inst.average_position_price
                config[figi].update({'price': price_in_port})
                Cv = cast_money(price_in_port) * (1 + float(instrumentses[instrument].get('Cv')) / 100)
                config[figi].update({'Cv': Cv})
                Cn = cast_money(price_in_port) * (1 + float(instrumentses[instrument].get('Cn')) / 100)
                config[figi].update({'Cn': Cn})
                print(
                    f'{datetime.now()} | {name} |  Покупка № {count_buy} | Цене = {actual_price} | Cтоимость в портфеле = {cast_money(price_in_port)} | объем = {1}')
                logging.warning(
                    f' | {name} |  Покупка № {count_buy} | Цене = {actual_price} | Cтоимость в портфеле = {cast_money(price_in_port)} | объем = {1}')
                send_message(
                    text=f'{name} |  Покупка № {count_buy} | Цене = {actual_price} | Cтоимость в портфеле = {cast_money(price_in_port)} | объем = {1}')
                return config
            else:
                return config
        if qu != 0:
            quantity = g * (config[figi].get("count_buy")+1)
            last_price = config[figi].get('last_price')
            delta = last_price * ((100 - kmax) / 100)
            actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
            actual_price = cast_money(actual_price)
            if count_buy < nmax and actual_price <= delta and ostatok > qmin and quantity <= lmax:
                r2 = client.orders.post_order(order_id=str(datetime.utcnow().timestamp()),
                                         figi=figi,
                                         price=recast_money(actual_price),
                                         quantity=quantity,
                                         account_id=account_id,
                                         direction=OrderDirection.ORDER_DIRECTION_BUY,
                                         order_type=OrderType.ORDER_TYPE_LIMIT)
                time.sleep(8)
                config[figi].update({'last_price': actual_price})
                config[figi].update({'late_start': 2})
                name = config[figi].get('name')
                count_buy = config[figi].get("count_buy")
                count_buy = count_buy + 1
                config[figi].update({'count_buy': count_buy})
                positions = client.operations.get_portfolio(account_id=account_id)
                price_in_port = 0
                for inst in positions.positions:
                    if figi == inst.figi:
                        price_in_port = inst.average_position_price
                if price_in_port == 0:
                    print('2повторный запрос стоимости в портфеле')
                    time.sleep(8)
                    positions = client.operations.get_portfolio(account_id=account_id)
                    for inst in positions.positions:
                        if figi == inst.figi:
                            price_in_port = inst.average_position_price
                config[figi].update({'price': price_in_port})
                Cv = cast_money(price_in_port) * (1 + float(instrumentses[instrument].get('Cv')) / 100)
                config[figi].update({'Cv': Cv})
                Cn = cast_money(price_in_port) * (1 + float(instrumentses[instrument].get('Cn')) / 100)
                config[figi].update({'Cn': Cn})
                print(f'{datetime.now()} | {name} |  Покупка № {count_buy} | Цене = {actual_price} | Cтоимость в портфеле = {cast_money(price_in_port)} | объем = {quantity}')
                logging.warning(f' | {name} |  Покупка № {count_buy} | Цене = {actual_price} | Cтоимость в портфеле = {cast_money(price_in_port)} | объем = {quantity}')
                send_message(text=f'{name} |  Покупка № {count_buy} | Цене = {actual_price} | Cтоимость в портфеле = {cast_money(price_in_port)} | объем = {quantity}')
                return config
            else:
                return config
    else:
        return config


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
    """
    Чтение конфигурационного файла
    :return: возвращает список с параметрами
    """
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
    """
    Функция округления числа до n количества знаков после запятой
    :param number:
    :return:
    """
    str_f = str(number)
    if '.' not in str_f:
        listik = list(str(number))
        k = int(listik[-1])
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
        config = instrumentses.copy()
        num = 1
        for instrument in list_dict:
            try:
                time.sleep(4.5)
                name = config.get(instrument).get('name')
                figi = config.get(instrument).get('figi')
                cv = config.get(instrument).get('Cv')
                cn = config.get(instrument).get('Cn')
                cd = config.get(instrument).get('Cd')
                cv_plus = config.get(instrument).get('Cv_plus')
                cn_plus = config.get(instrument).get('Cn_plus')
                mode = config.get(instrument).get('mode')
                min_price_increment = cast_money(
                    client.instruments.get_instrument_by(
                        id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, id=figi).instrument.min_price_increment)
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
                positions = client.operations.get_portfolio(account_id=account_id)
                for inst in positions.positions:
                    if figi == inst.figi:
                        price_in_port = inst.average_position_price
                if cast_money(price_in_port) == 0:
                    continue
                config[figi].update({'price': price_in_port})
                Cv = cast_money(price_in_port) * (1 + float(instrumentses[instrument].get('Cv')) / 100)
                config[figi].update({'Cv': Cv})
                Cn = cast_money(price_in_port) * (1 + float(instrumentses[instrument].get('Cn')) / 100)
                config[figi].update({'Cn': Cn})
                operations = client.operations.get_operations(account_id=account_id, figi=figi,
                                                              state=OperationState.OPERATION_STATE_EXECUTED).operations
                buy_operate = []
                for operate in operations:
                    if operate.operation_type == OperationType.OPERATION_TYPE_BUY:
                        buy_operate.append(operate)
                buy_price = cast_money(buy_operate[0].price)
                config[figi].update({'last_price': buy_price})
                continue
            except Exception as e:
                print(e)
                logging.warning(f' | {name} | {figi} | {mode} | {e} ')
                time.sleep(7)
                continue
        check = input('\nПодтвердите корректность параметров и выбранных вами инструментов\nЕсли все верно, введите (Да\Нет):')
        if check in ['Нет', 'нет']:
            print('Сделайте исправления в config файле. Программа закроется через 4 секунды.')
            time.sleep(4)
            return
        check_mode = input(f"""Выберите режим работы бота
        1) Покупка + Продажа
        2) Продажа
""")
        timing = input('Введите количество секунд задержки (5, 10...) увеличивайте в случае превышения лимитов на запросы.\nЧем больше инструментов вы торгуете, тем больше должна быть задержка:')
        instrumentses = read_config_file()
        while True:
            for instrument in list_dict:
                now = datetime.now()
                hours = now.hour
                minut = now.minute
                weekday = datetime.isoweekday(now)
                if weekday in [6, 7]:
                    time.sleep(43200)
                # if hours < 10 or hours >= 19:
                #     print(f'pause {now}')
                #     time.sleep(300)
                #     continue
                time.sleep(int(timing))
                try:
                    time.sleep(1.5)
                    mode = int(instrumentses[instrument].get('mode'))
                    figi = instrumentses[instrument].get('figi')
                    if int(check_mode) == 1:
                        buy_and_check(client=client, account_id=account_id, figi=figi, config=config, instrument=instrument, instrumentses=instrumentses)
                    value = check_pos(client, account_id, figi)
                    name = config[figi].get('name')
                    q = cast_money(value)
                    if q == 0 and config[figi].get('late_start') == 0:
                        continue
                    if q == 0 and (config[figi].get('late_start') in [1, 2]):
                        time.sleep(8)
                        operations = client.operations.get_operations(account_id=account_id, figi=figi,
                                                                      state=OperationState.OPERATION_STATE_EXECUTED).operations
                        sell_operate = []
                        for operate in operations:
                            if operate.operation_type == OperationType.OPERATION_TYPE_SELL:
                                sell_operate.append(operate)
                        sell_price = cast_money(sell_operate[0].price)
                        print(f'{datetime.now()} | {name} | {figi} | {mode} | Продажа по цене={sell_price}')
                        logging.warning(f' | {name} | {figi} | {mode} | Продажа по цене={sell_price}')
                        send_message(text=f'{name} | Продажа по цене={sell_price}')
                        config[figi].update({'late_start': 0})
                        config[figi].update({'count_buy': 0})
                        config[figi].update({'last_price': 0})
                        continue
                    if q != 0 and config[figi].get('late_start') == 1:
                        config[figi].update({'late_start': 2})
                        continue
                    else:
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
                            actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                            actual_price = cast_money(actual_price)
                            if actual_price > Cn:
                                active_orders = client.stop_orders.get_stop_orders(account_id=account_id).stop_orders
                                active_sell_order = ''
                                for order in active_orders:
                                    if order.figi == figi and order.direction == StopOrderDirection.STOP_ORDER_DIRECTION_SELL:
                                        active_sell_order = order
                                # Если нет существующего ордера,
                                # выставляем новый стоп-лос ордер на продажу Cn
                                if active_sell_order == '':
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0:
                                        continue
                                    new_sell_stop_order_n = client.stop_orders.post_stop_order(
                                        figi=figi,
                                        quantity=int(q),
                                        price=recast_money(Cn),
                                        stop_price=recast_money(Cn),
                                        direction=StopOrderDirection.STOP_ORDER_DIRECTION_SELL,
                                        account_id=account_id,
                                        expiration_type=StopOrderExpirationType.STOP_ORDER_EXPIRATION_TYPE_GOOD_TILL_CANCEL,
                                        stop_order_type=StopOrderType.STOP_ORDER_TYPE_STOP_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Выставлен первый ордер по нижней границе. Cn = {Cn} | Cv = {Cv}')
                                    logging.warning(
                                        f' | {name} | {figi} | {mode} | Выставлен первый ордер по нижней границе. Cn = {Cn} | Cv = {Cv}')
                                    send_message(
                                        text=f'{name} | Выставлен первый ордер по нижней границе. Cn = {Cn} | Cv = {Cv}')
                                    continue
                                actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                                actual_price = cast_money(actual_price)
                                u = Cv - Cv * Cd
                                if actual_price >= u:
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
                                    active_orders = client.stop_orders.get_stop_orders(
                                        account_id=account_id).stop_orders
                                    active_sell_order = ''
                                    for order in active_orders:
                                        if order.figi == figi and order.direction == StopOrderDirection.STOP_ORDER_DIRECTION_SELL:
                                            active_sell_order = order
                                            order_id = active_sell_order.stop_order_id
                                            delete_order = client.stop_orders.cancel_stop_order(account_id=account_id,
                                                                                                order_id=order_id)
                                            time.sleep(10)
                                    new_sell_stop_order_n = client.stop_orders.post_stop_order(
                                        figi=figi,
                                        quantity=int(q),
                                        price=recast_money(Cn),
                                        stop_price=recast_money(Cn),
                                        direction=StopOrderDirection.STOP_ORDER_DIRECTION_SELL,
                                        account_id=account_id,
                                        expiration_type=StopOrderExpirationType.STOP_ORDER_EXPIRATION_TYPE_GOOD_TILL_CANCEL,
                                        stop_order_type=StopOrderType.STOP_ORDER_TYPE_STOP_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn}  | Cv = {Cv}')
                                    logging.warning(
                                        f' | {name} | {figi} | {mode} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    send_message(
                                        text=f'{name} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
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
                                actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                                actual_price = cast_money(actual_price)
                                u = Cv - Cv * Cd
                                if actual_price >= u:
                                    # print(f'303 count={count} actual_price={actual_price}, u={u}, Cv={Cv}, Cv*Cd={Cv*Cd}')
                                    Cv = Cv * Cv_plus
                                    Cn = Cn * Cn_plus
                                    Cv = ceil(Cv / config[figi].get('min_price_increment')) * config[figi].get(
                                        'min_price_increment')
                                    Cn = ceil(Cn / config[figi].get('min_price_increment')) * config[figi].get(
                                        'min_price_increment')
                                    # print(f'308 actual_price={actual_price}, Cv={Cv}, Cn={Cn}, recastCn={recast_money(Cn)}')
                                    config[figi].update({'Cn': Cn})
                                    config[figi].update({'Cv': Cv})
                                    count = count + 1
                                    config[figi].update({'count': count})
                                    active_orders = client.stop_orders.get_stop_orders(
                                        account_id=account_id).stop_orders
                                    active_sell_order = ''
                                    for order in active_orders:
                                        if order.figi == figi and order.direction == StopOrderDirection.STOP_ORDER_DIRECTION_SELL:
                                            active_sell_order = order
                                            order_id = active_sell_order.stop_order_id
                                            delete_order = client.stop_orders.cancel_stop_order(account_id=account_id,
                                                                                                stop_order_id=order_id)
                                    new_sell_stop_order_n = client.stop_orders.post_stop_order(
                                        figi=figi,
                                        quantity=int(q),
                                        price=recast_money(Cn),
                                        stop_price=recast_money(Cn),
                                        direction=StopOrderDirection.STOP_ORDER_DIRECTION_SELL,
                                        account_id=account_id,
                                        expiration_type=StopOrderExpirationType.STOP_ORDER_EXPIRATION_TYPE_GOOD_TILL_CANCEL,
                                        stop_order_type=StopOrderType.STOP_ORDER_TYPE_STOP_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Выставлен первый ордер | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    logging.warning(
                                        f' | {name} | {figi} | {mode} | Выставлен первый ордер | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    send_message(
                                        text=f'{name} | Выставлен первый ордер | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
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
                                if actual_price >= u:
                                    # print(f' 343 count={count} actual_price={actual_price}, u={u}, Cv={Cv}, Cv*Cd={Cv * Cd}')
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0:
                                        continue
                                    Cn = Cn * Cn_plus
                                    Cn = ceil(Cn / config[figi].get('min_price_increment')) * config[figi].get(
                                        'min_price_increment')
                                    config[figi].update({'Cn': Cn})
                                    Cv = Cv * Cv_plus
                                    Cv = ceil(Cv / config[figi].get('min_price_increment')) * config[figi].get(
                                        'min_price_increment')
                                    config[figi].update({'Cv': Cv})
                                    # print(f'354 count={count} actual_price={actual_price}, Cv={Cv}, Cn={Cn}, recastCn={recast_money(Cn)}')
                                    active_orders = client.stop_orders.get_stop_orders(
                                        account_id=account_id).stop_orders
                                    active_sell_order = ''
                                    for order in active_orders:
                                        if order.figi == figi and order.direction == StopOrderDirection.STOP_ORDER_DIRECTION_SELL:
                                            active_sell_order = order
                                            order_id = active_sell_order.stop_order_id
                                            delete_order = client.stop_orders.cancel_stop_order(account_id=account_id,
                                                                                                stop_order_id=order_id)
                                    new_sell_stop_order_n = client.stop_orders.post_stop_order(
                                        figi=figi,
                                        quantity=int(q),
                                        price=recast_money(Cn),
                                        stop_price=recast_money(Cn),
                                        direction=StopOrderDirection.STOP_ORDER_DIRECTION_SELL,
                                        account_id=account_id,
                                        expiration_type=StopOrderExpirationType.STOP_ORDER_EXPIRATION_TYPE_GOOD_TILL_CANCEL,
                                        stop_order_type=StopOrderType.STOP_ORDER_TYPE_STOP_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} |  Cv = {Cv}')
                                    logging.warning(
                                        f' | {name} | {figi} | {mode} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    send_message(
                                        text=f'{name} | Повышение корридора на {config[figi].get("Cn_plus")}% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                                    continue
                                else:
                                    continue
                        else:
                            continue
                except Exception as e:
                    print(f'{datetime.now()} | {name} | {figi} | {mode} | {e} ')
                    logging.warning(f' | {name} | {figi} | {mode} | {e} ')
                    time.sleep(7)
                    continue
                except ConnectionError:
                    pass





if __name__ == '__main__':
    main()