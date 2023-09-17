import time
from datetime import datetime
from math import modf
from tinkoff.invest import Client, Quotation, OrderDirection, OrderType, OperationState, OperationType
import json


TOKEN = ''


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
            # print(pos)
            if pos.figi == figi:
                return pos.quantity
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
    price = Quotation(units=(int(price[1])), nano=int(round(price[0], 2) * 1e9))
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


def main():
    print("""
Здравствуйте Алексей, давайте проверим список инструментов и параметры которые вы указали:
    """)
    time.sleep(3)
    with Client(TOKEN) as client:
        instrumentses = read_config_file()
        account_id = client.users.get_accounts().accounts[0].id
        config = instrumentses
        list_dict = list(instrumentses)
        num = 1
        for instrument in list_dict:
            name = config.get(instrument).get('name')
            figi = config.get(instrument).get('figi')
            cv = config.get(instrument).get('Cv')
            cn = config.get(instrument).get('Cn')
            cd = config.get(instrument).get('Cd')
            cv_plus = config.get(instrument).get('Cv_plus')
            cn_plus = config.get(instrument).get('Cn_plus')
            mode = config.get(instrument).get('mode')
            value = check_pos(client, account_id, figi)
            q = cast_money(value)
            if q == 0:
                print(f"""
                {name} | {figi} У вас на счете нет такого актива, его количество = {q}, наверное вы купите его позже.
                """)
                config[figi].update({'late_start': 0})
                continue
            else:
                config[figi].update({'late_start': 1})
            print(f'{num})  Название: {name} | FIGI: {figi} | Cv(%): {cv} | Cn(%): {cn} | Cd(%): {cd} | Cv+(%): {cv_plus} | Cn_+(%):{cn_plus} | Режим: {mode}')
            num += 1
            operations = client.operations.get_operations(account_id=account_id, figi=figi,
                                                          state=OperationState.OPERATION_STATE_EXECUTED).operations
            buy_operate = []
            for operate in operations:
                if operate.operation_type == OperationType.OPERATION_TYPE_BUY:
                    buy_operate.append(operate)
            buy_price = buy_operate[0].price
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
        while True:
            time.sleep(15)
            try:
                for instrument in list_dict:
                    mode = int(instrumentses[instrument].get('mode'))
                    figi = instrumentses[instrument].get('figi')
                    value = check_pos(client, account_id, figi)
                    q = cast_money(value)
                    if q == 0 and config[figi].get('late_start') == 0:
                        continue
                    if q == 0 and config[figi].get('late_start') == 1:
                        print(f'{datetime.now()} | {name} | {figi} | {mode} | Успешно продан')
                        config[figi].update({'late_start': 0})
                        active_orders = client.orders.get_orders(account_id=account_id).orders
                        active_sell_order = ''
                        for order in active_orders:
                            if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                                active_sell_order = order
                                order_id = active_sell_order.order_id
                                delete_order = client.orders.cancel_order(account_id=account_id, order_id=order_id)
                                print(f'{datetime.now()} | {name} | {figi} | {mode} | Ордер {order_id} удален, тк актив был продан.')
                        continue
                    if q != 0 and config[figi].get('late_start') == 0:
                        operations = client.operations.get_operations(account_id=account_id, figi=figi,
                                                                      state=OperationState.OPERATION_STATE_EXECUTED).operations
                        buy_operate = []
                        for operate in operations:
                            if operate.operation_type == OperationType.OPERATION_TYPE_BUY:
                                buy_operate.append(operate)
                        buy_price = buy_operate[0].price
                        config[figi].update({'price': buy_price})
                        Cv = cast_money(buy_price) * (1 + float(instrumentses[instrument].get('Cv')) / 100)
                        config[figi].update({'Cv': Cv})
                        Cn = cast_money(buy_price) * (1 + float(instrumentses[instrument].get('Cn')) / 100)
                        config[figi].update({'Cn': Cn})
                        config[figi].update({'late_start': 1})
                        print(f'{datetime.now()} | {name} | {figi} | {mode} | Была сделана покупка. Покупка по цене {cast_money(buy_price)}, объем {q}')
                    else:
                        operations = client.operations.get_operations(
                            account_id=account_id,
                            figi=figi,
                            state=OperationState.OPERATION_STATE_EXECUTED).operations
                        buy_operate = []
                        for operate in operations:
                            if operate.operation_type == OperationType.OPERATION_TYPE_BUY:
                                buy_operate.append(operate)
                        Cv_plus = (1 + int(instrumentses[instrument].get('Cv_plus'))) / 100
                        Cn_plus = (1 + int(instrumentses[instrument].get('Cn_plus'))) / 100
                        if mode == 1:
                            Cn = config[figi].get('Cn')
                            Cv = config[figi].get('Cv')
                            Cd = config[figi].get('Cd')
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
                                        price=recast_money(config[figi].get('Cn')),
                                        quantity=value,
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    new_sell_order_v = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price=recast_money(config[figi].get('Cv')),
                                        quantity=value,
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Выставлено два ордера. Cn = {Cn} | Cv = {Cv}')
                                actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                                actual_price = cast_money(actual_price)
                                if actual_price >= Cv - Cv * Cd:
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0:
                                        continue
                                    Cn = config[figi].get('Cn') * Cn_plus
                                    config[figi].update({'Cn': Cn})
                                    Cv = config[figi].get('Cv') * Cv_plus
                                    config[figi].update({'Cv': Cv})
                                    active_orders = client.orders.get_orders(account_id=account_id).orders
                                    active_sell_order = ''
                                    for order in active_orders:
                                        if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                                            active_sell_order = order
                                            order_id = active_sell_order.order_id
                                            delete_order = client.orders.cancel_order(account_id=account_id, order_id=order_id)
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0:
                                        continue
                                    new_sell_order_n = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price=recast_money(config[figi].get('Cn')),
                                        quantity=value,
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    new_sell_order_v = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price=recast_money(config[figi].get('Cv')),
                                        quantity=value,
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Повышение корридора на 1% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                            else:
                                continue
                        if mode == 2:
                            value = check_pos(client, account_id, figi)
                            q = cast_money(value)
                            if q == 0:
                                continue
                            count = config[figi].get('count')
                            actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                            actual_price = cast_money(actual_price)
                            if count == 0:
                                actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                                actual_price = cast_money(actual_price)
                                Cn = config[figi].get('Cn')
                                Cv = config[figi].get('Cv')
                                Cd = config[figi].get('Cd')
                                if actual_price >= Cv - Cv * Cd:
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0:
                                        continue
                                    Cv = Cv * Cv_plus
                                    Cn = Cn * Cn_plus
                                    config[figi].update({'Cn': Cn})
                                    config[figi].update({'Cv': Cv})
                                    count = count + 1
                                    config[figi].update({'count': count})
                                    new_sell_order_n = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price=recast_money(config[figi].get('Cn')),
                                        quantity=value,
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    new_sell_order_v = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price=recast_money(config[figi].get('Cv')),
                                        quantity=value,
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Повышение корридора на 1% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
                            if count == 1:
                                actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                                actual_price = cast_money(actual_price)
                                Cn = config[figi].get('Cn')
                                Cv = config[figi].get('Cv')
                                Cd = config[figi].get('Cd')
                                if actual_price > Cv - Cv * Cd:
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0:
                                        continue
                                    Cn = Cn * Cn_plus
                                    config[figi].update({'Cn': Cn})
                                    Cv = Cv * Cv_plus
                                    config[figi].update({'Cv': Cv})
                                    active_orders = client.orders.get_orders(account_id=account_id).orders
                                    active_sell_order = ''
                                    for order in active_orders:
                                        if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                                            active_sell_order = order
                                            order_id = active_sell_order.order_id
                                            delete_order = client.orders.cancel_order(account_id=account_id, order_id=order_id)
                                    value = check_pos(client, account_id, figi)
                                    q = cast_money(value)
                                    if q == 0:
                                        continue
                                    new_sell_order_n = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price=recast_money(config[figi].get('Cn')),
                                        quantity=value,
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    new_sell_order_v = client.orders.post_order(
                                        order_id=str(datetime.utcnow().timestamp()),
                                        figi=figi,
                                        price=recast_money(config[figi].get('Cv')),
                                        quantity=value,
                                        account_id=account_id,
                                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                                        order_type=OrderType.ORDER_TYPE_LIMIT
                                    )
                                    print(
                                        f'{datetime.now()} | {name} | {figi} | {mode} | Повышение корридора на 1% | Актуальная цена = {actual_price} | Cn = {Cn} | Cv = {Cv}')
            except Exception as e:
                print(e)
                time.sleep(30)
                break


if __name__ == '__main__':
    main()