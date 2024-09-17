import json

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from pack import renew
from pack.DataProcessing.ID_IO import check_auth
from pack.DataProcessing.orderLogger import get_comments
from pack.DataProcessing.timeUpdater import time_gen_new
from pack.config import update_config


# file for commmon command handlers (e.g /help, /start)


async def start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer('Добро пожаловать в ECanteen, этот бот предназначен для работников кухни, '
                         'чтобы авторизоваться введите /login')


async def orders_update(message: types.Message, state: FSMContext):
    if not await check_auth(message.from_user, 'perm'):
        await message.answer('у вас нет прав для использования этой команды')
        return
    await state.finish()
    renew.order_list()
    renew.comment_list()
    await message.answer('список заказов и комментариев опустошен')


async def time_update(message: types.Message, state: FSMContext):
    if not await check_auth(message.from_user, 'perm'):
        await message.answer('у вас нет прав для использования этой команды')
        return
    await state.finish()
    update_config('config/OrderBot.ini', 'time', 'times_regened', 'False')
    time_gen_new()
    await message.answer('время обновлено')


async def print_orders(message: types.Message, state: FSMContext):
    if not await check_auth(message.from_user, 'perm'):
        await message.answer('у вас нет прав для использования этой команды')
        return
    with open('DataFiles/orders.txt') as file:
        try:
            order = json.load(file)
        except json.JSONDecodeError:
            await message.answer('заказов пока нет')
            return
    order: dict
    forder = ''
    for timing in order.keys():
        forder += f'заказы на {timing}\n'
        for item in order[timing]:
            forder += f'{item} x{len(order[timing][item])}\n'
        commnets = await get_comments(timing)
        if commnets:
            commnets: dict
            forder += f'\nИз них {len(commnets.keys())} с комментариями:\n'
            for user in commnets:
                forder += '\n'
                tmp = {}
                for item in commnets[user]['order']:
                    if item not in tmp:
                        tmp[item] = 1
                    else:
                        tmp[item] += 1
                for item in tmp:
                    forder += str(item) + f' x{tmp[item]}' + '\n'
                forder += 'комментарий: ' + str(commnets[user]['comment']) + '\n'
        forder += '-----------------------------------------------\n'
    await message.answer(forder)


def register_common_sender_handlers(disp: Dispatcher):
    disp.register_message_handler(start, commands='start', state='*')
    disp.register_message_handler(print_orders, commands='print_all_orders', state='*')
