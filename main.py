from datetime import datetime
from math import modf
from tinkoff.invest import Client, Quotation, OrderDirection, OrderType, OperationState, OperationType
import json


TOKEN = 't.VDO85m1MPqVEtqVm1bZCkOEjeIlJZtPMIW1p6DzR2FLMzrp0Y990eB8hvUtrnISMAmPDEO7yvBbiLBqubitamA'
# FIGI = 'BBG333333333'


def check_pos(client, account_id, figi):
    try:
        positions = client.operations.get_portfolio(account_id=account_id).positions
        for pos in positions:
            print(pos)
            if pos.figi == figi:
                return pos.quantity
    except Exception as e:
        print(e)
        return None


def cast_money(price):
    return price.units + abs(price.nano / 1e9)  # nano - 9 нулей


def recast_money(price):
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


with Client(TOKEN) as client:
    instruments = read_config_file()
    account_id = client.users.get_accounts().accounts[0].id
    positions = client.operations.get_portfolio(account_id=account_id).positions
    config = instruments
    list_dict = list(instruments)
    for instrument in list_dict:
        figi = config.get(instrument).get('figi')
        operations = client.operations.get_operations(account_id=account_id, figi=figi,
                                                      state=OperationState.OPERATION_STATE_EXECUTED).operations
        buy_operate = []
        for operate in operations:
            if operate.operation_type == OperationType.OPERATION_TYPE_BUY:
                buy_operate.append(operate)
        if len(buy_operate) == 0:
            print(f'Вы не покупали такой автив {figi}')
            continue
        buy_value = buy_operate[-1].quantity
        buy_price = buy_operate[-1].price
        config[figi].update({'price': buy_price})
        Cv = cast_money(buy_price) * (1 + float(instruments[instrument].get('Cv')) / 100)
        config[figi].update({'Cv': Cv})
        Cn = cast_money(buy_price) * (1 + float(instruments[instrument].get('Cn')) / 100)
        config[figi].update({'Cn': Cn})
    while True:
        for instrument in list_dict:
            mode = int(instruments[instrument].get('mode'))
            figi = instruments[instrument].get('figi')
            operations = client.operations.get_operations(
                account_id=account_id,
                figi=figi,
                state=OperationState.OPERATION_STATE_EXECUTED).operations
            buy_operate = []
            for operate in operations:
                if operate.operation_type == OperationType.OPERATION_TYPE_BUY:
                    buy_operate.append(operate)
            if len(buy_operate) == 0:
                print(f'Вы не покупали такой автив {figi}')
                continue
            buy_value = buy_operate[-1].quantity
            buy_price = buy_operate[-1].price
            Cd = float(instruments[instrument].get('Cd')) / 100
            Cv_plus = (1 + int(instruments[instrument].get('Cv_plus'))) / 100
            Cn_plus = (1 + int(instruments[instrument].get('Cn_plus'))) / 100
            value = check_pos(client, account_id, figi)
            active_orders = client.orders.get_orders(account_id=account_id).orders
            active_sell_order = ''
            for order in active_orders:
                if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                    active_sell_order = order
            q = cast_money(value)
            if q == 0:
                print(f"""
                У вас нет такого актива {figi} или его количество не достаточно для торговли
                Либоы он был успешно продан по выгодной цене.
                """)
                continue
            if mode == 1:
                Cn = config[figi].get('Cn')
                Cv = config[figi].get('Cv')
                Cd = config[figi].get('Cd')
                if actual_price > Cn:
                    active_orders = client.orders.get_orders(account_id=account_id).orders
                    active_sell_order = ''
                    for order in active_orders:
                        if order.figi == figi and order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                            active_sell_order = order
                    # Если нет существующего ордера,
                    # выставляем новый лимитный ордер на продажу и на покупку по ценам Cn и Cv
                    if active_sell_order == '':
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
                    actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                    actual_price = cast_money(actual_price)
                    if actual_price >= Cv - Cv * Cd:
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
            if mode == 2:
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
                if count == 1:
                    actual_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
                    actual_price = cast_money(actual_price)
                    Cn = config[figi].get('Cn')
                    Cv = config[figi].get('Cv')
                    Cd = config[figi].get('Cd')
                    if actual_price > Cv - Cv * Cd:
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
