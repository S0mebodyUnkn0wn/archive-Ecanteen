import json
from pack.AdminStuff.menuListIO import import_json_menu
from pack.AdminStuff.depositHandler import change_entry

async def order_log(data: dict):
    order = []
    for item in data['chosen_food']:
        if 'extras' in item:
            order.append(f"{item['name']} + " + str(*[t['name'] for t in item['extras']]))
        else:
            order.append(item['name'])
    timing = data['chosen_time'] + ':00'
    comment = data['comment']
    usr = data['from_user']
    method = data['method']
    await write_time(timing, usr.id)
    await write_order(timing, order, usr.id,method)
    await write_comments(timing, order, comment, usr)


async def write_comments(timing, order, comment, usr):
    if comment == '':
        return
    with open('DataFiles/comments.txt', 'r') as file:
        try:
            comments_dict = json.load(file)
        except json.JSONDecodeError:
            comments_dict = {}
        try:  # Вот эта штука перезаписывает коммент, если один и тот же юзер делает два заказа на 1 время.
            comments_dict[f'{timing}'][f'{usr.id}'] = {'order': order, 'comment': comment}
        except KeyError:
            comments_dict[f'{timing}'] = {f'{usr.id}': {'order': order, 'comment': comment}}
    with open('DataFiles/comments.txt', 'w') as file:
        json.dump(comments_dict, file)


async def write_order(timing, order, usr,method):
    with open('DataFiles/orders.txt') as file:
        try:
            orders = json.load(file)
        except json.JSONDecodeError:
            orders = {}
    orders: dict
    if str(timing) in orders.keys() and type(orders[f'{timing}']) is dict:
        timing_order = orders[f'{timing}'].copy()
    else:
        timing_order = {}
    orders[f'{timing}'] = timing_order
    for item in order:
        if str(item) in timing_order.keys():
            timing_order[f'{item}'] = timing_order[f'{item}'] + {usr:method}
        else:
            timing_order[f'{item}'] = {usr:method}
    with open('DataFiles/orders.txt', 'w') as file:
        json.dump(orders, file)


async def write_time(timing, usr):
    with open('DataFiles/times.txt') as file:
        dat = json.load(file)
    dat[f'{timing}']['occupancy'].append(usr)
    with open('DataFiles/times.txt', 'w') as file:
        json.dump(dat, file)


async def free_time(timing, usr):
    with open('DataFiles/times.txt') as file:
        dat = json.load(file)
    dat[f'{timing}']['occupancy'].remove(usr)
    with open('DataFiles/times.txt', 'w') as file:
        json.dump(dat, file)


async def check_order(timing, usr):  # checks is user has order for a specific time
    with open('DataFiles/times.txt') as file:
        try:
            times = json.load(file)
        except json.JSONDecodeError:
            return False
    times: dict
    if str(timing) in times.keys():
        if usr.id in times[timing]['occupancy']:
            return True
    else:
        return False


async def free_order(timing, usr):
    with open('DataFiles/orders.txt') as file:
        try:
            orders = json.load(file)
        except json.JSONDecodeError:
            return False
    orders: dict
    if str(timing) in orders.keys() and type(orders[f'{timing}']) is dict:
        timing_order = orders[f'{timing}'].copy()
    else:
        return False
    orders[f'{timing}'] = timing_order
    outp = False
    ref=False
    empty_iems = []
    for item in timing_order.keys():  # goes through all items in timing, if user is spotted, user is removed
        if str(usr) in timing_order[item]:
            if timing_order[item][str(usr)]=='Dep':
                ref=True
            timing_order[item].pop(str(usr))
            if len(timing_order[item]) == 0:
                empty_iems.append(item)
            if type(outp) is list:
                outp.append(item)
            else:
                outp = [item]
    for item in empty_iems:
        timing_order.pop(item)
    with open('DataFiles/orders.txt', 'w') as file:
        json.dump(orders, file)
    return (outp,ref)


async def free_comment(timing, usr):
    with open('DataFiles/comments.txt', 'r') as file:
        try:
            comments_dict = json.load(file)
        except json.JSONDecodeError:
            return False
    comments_dict: dict
    try:
        comments_dict[f'{timing}'].pop(f'{usr}')
    except KeyError:
        return False
    with open('DataFiles/comments.txt', 'w') as file:
        json.dump(comments_dict, file)
    return True


async def get_comments(timing):
    with open('DataFiles/comments.txt') as file:
        try:
            commnets = json.load(file)
        except json.JSONDecodeError:
            return False
    commnets: dict
    if f'{timing}' in commnets:
        return commnets[f'{timing}']
    else:
        return False


async def get_order(timing):
    with open('DataFiles/orders.txt') as file:
        try:
            orders = json.load(file)
        except json.JSONDecodeError:
            orders = {}
    orders: dict
    if str(timing) in orders.keys():
        return orders[f'{timing}']
    else:
        return False


async def refund_money(local_id,order: list):
    print(order)
    drinks = import_json_menu('DataFiles/drinks_menu_all.txt')
    food = import_json_menu('DataFiles/food_menu_all.txt')
    refund_amount=0
    for item in food:
        if item['name'] in order:
            refund_amount += order.count(item['name'])*item['price']
    for item in drinks:
        if item['name'] in order:
            refund_amount += order.count(item['name'])*item['price']
    await change_entry(local_id,refund_amount,'SYSTEM REFUND')
    return refund_amount
