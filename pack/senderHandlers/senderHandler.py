import json
from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from pack.DataProcessing.ID_IO import get_csv_frame, write_to_perm_id_file, get_true_name
from pack.DataProcessing.orderLogger import get_order, get_comments
from pack.config import load_autosend_config
from pack.AdminStuff.menuListIO import import_json_menu, add_json_menu_item, del_json_menu_item


# file for command handlers for the bot that sends orders to kitchen
class MenuStates(StatesGroup):
    item_creation_name = State()
    item_creation_price = State()
    item_creation_type = State()


class LoginStates(StatesGroup):
    waiting_for_login_info = State()


async def escape(message: types.Message, state: FSMContext):
    await message.answer('Действие прервано')
    await state.finish()


async def login_start(message: types.Message):
    await message.answer('Пожалуйста отправте индентификационный код, который вам предоставила администрация')
    await LoginStates.waiting_for_login_info.set()


async def login_entered(message: types.Message, state: FSMContext):
    id_frame = await get_csv_frame('DataFiles/perm_list.txt')
    id_series = id_frame['ID']
    if message.text in map(str, id_series.values):
        user_id = message.from_user
        await write_to_perm_id_file(user_id, message.text)
        await message.answer('Регистрация прошла успешно')
    else:
        await message.answer('Такого кода нет в базе данных, проверьте правильность написания и попробуйте еще раз, '
                             'если вы уверены, что ввели все правильно - свяжитесь с администрацией')
    await state.finish()


async def send_next_order(message: types.Message):
    forder = await form_delayed_order(modif=1)
    if type(forder) is str:
        await message.answer(forder)
    else:
        await message.answer(f'заказов на {forder} нет!')


async def send_current_order(message: types.Message):
    forder = await form_delayed_order(modif=0)
    if type(forder) is str:
        await message.answer(forder)
    else:
        await message.answer(f'заказов на {forder} нет!')


async def form_delayed_order(modif):
    config = load_autosend_config('config/OrderBot.ini')
    send_delay = config.autosend.delay
    timing = datetime.now().time()
    corm = timing.minute + (send_delay - timing.minute % 10) + send_delay * modif
    if corm >= 60:
        corh = corm // 60 + timing.hour
        corm = corm % 60
    else:
        corh = timing.hour
    timing = timing.replace(minute=corm, hour=corh, second=0, microsecond=0)
    return await form_order(timing)


async def form_order(timing):
    order = await get_order(timing)
    if not order:
        return timing
    order: dict
    forder = f'<b>Список заказов на {timing}:</b>\n{"-" * 40}\n'
    forder += 'Все заказы:\n\n'
    names = []
    for item in order.keys():
        forder += f'<i>{item} x{len(order[item])}</i>\n'
        for user in order[item]:
            if user not in names:
                names.append(user)
    commnets = await get_comments(timing)
    if commnets:
        commnets: dict
        forder += f'\n<b>Из них {len(commnets.keys())} с комментариями:</b>\n'
        for user in commnets:
            forder += f'{"-" * 40}\n'
            tmp = {}
            for item in commnets[user]['order']:
                if item not in tmp:
                    tmp[item] = 1
                else:
                    tmp[item] += 1
            for item in tmp:
                forder += '<i>' + str(item) + f' x{tmp[item]}' + '</i>\n'
            forder += '\nкомментарий: ' + str(commnets[user]['comment']) + '\n'
    forder += f'{"-" * 40}\nИмена: '
    for ident in names:
        true_name = await get_true_name(telegram_id=ident)
        forder += f'{true_name} '
    forder += '\n'
    return forder


async def orders_autosend_toggle(message: types.Message, state: FSMContext):  # write/remove ids from a list
    with open('DataFiles/autosendStates.txt') as file:
        try:
            autosend_users = json.load(file)
        except json.JSONDecodeError:
            autosend_users = []
    if message.from_user.id in autosend_users:
        autosend_users.remove(message.from_user.id)
        await message.answer('автоотправка заказов отключена')
    else:
        autosend_users.append(message.from_user.id)
        await message.answer('автоотправка заказов включена')
    with open('DataFiles/autosendStates.txt', 'w') as file:
        json.dump(autosend_users, file)


async def menu_form(food_today: dict, drinks_today: dict):
    menuout = 'Меню на сегодня:\n'
    for item in food_today:
        menuout += f"{item['name']} - {item['price']}₽\n"
    menuout += '\n'
    for item in drinks_today:
        menuout += f"{item['name']} - {item['price']}₽\n"
    return menuout


async def menu_main(message: types.Message, state: FSMContext):
    await state.finish()
    food_today = import_json_menu('DataFiles/food_menu_today.txt')
    drinks_today = import_json_menu('DataFiles/drinks_menu_today.txt')
    menuout = 'Меню на сегодня:\n'
    for item in food_today:
        menuout += f"{item['name']} - {item['price']}₽\n"
    menuout += '\n'
    for item in drinks_today:
        menuout += f"{item['name']} - {item['price']}₽\n"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Редактировать меню', callback_data='Edit_menu'))
    keyboard.add(types.InlineKeyboardButton(text='Выйти', callback_data='Close_menu'))
    await message.answer(text=menuout, reply_markup=keyboard)


async def menu_edit(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    food_today = import_json_menu('DataFiles/food_menu_today.txt')
    drinks_today = import_json_menu('DataFiles/drinks_menu_today.txt')
    food_all = [item['name'] for item in import_json_menu('DataFiles/food_menu_all.txt')]
    drikns_all = [item['name'] for item in import_json_menu('DataFiles/drinks_menu_all.txt')]
    menu_possible = food_all + drikns_all
    menuout = 'Меню на сегодня:\n'
    menu_items = []
    for item in food_today:
        menuout += f"{item['name']} - {item['price']}₽\n"
        menu_items.append(item['name'])
    menuout += '\n'
    for item in drinks_today:
        menuout += f"{item['name']} - {item['price']}₽\n"
        menu_items.append(item['name'])
    keyboard = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton(text='Добавить', callback_data='Add_items'),
               types.InlineKeyboardButton(text='Удалить', callback_data='Del_items')]
    keyboard.add(*buttons)
    keyboard.row(types.InlineKeyboardButton(text='Закончить редактирование', callback_data='Finish_edit'))
    await call.message.edit_text(text=menuout)
    await call.message.edit_reply_markup(keyboard)


async def menu_add(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    food_today = import_json_menu('DataFiles/food_menu_today.txt')
    drinks_today = import_json_menu('DataFiles/drinks_menu_today.txt')
    food_all = import_json_menu('DataFiles/food_menu_all.txt')
    drikns_all = import_json_menu('DataFiles/drinks_menu_all.txt')
    name = call.data.split('_')[1]
    if name != 'items':
        for item in food_all:
            if item['name'] == name:
                add_json_menu_item('DataFiles/food_menu_today.txt', item)
                food_today.append(item)
                break
        for item in drikns_all:
            if item['name'] == name:
                add_json_menu_item('DataFiles/drinks_menu_today.txt', item)
                drinks_today.append(item)
                break
    food_all_names = {item['name'] for item in food_all}
    drikns_all_names = {item['name'] for item in drikns_all}
    food_today_names = {item['name'] for item in food_today}
    drinks_today_names = {item['name'] for item in drinks_today}
    menu_possible = food_all_names | drikns_all_names
    menu_not_in = menu_possible - (food_today_names | drinks_today_names)
    menutext = await menu_form(food_today, drinks_today)
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.row(types.InlineKeyboardButton(text='Добавить новую позицию', callback_data='New_item'))
    for button in [types.InlineKeyboardButton(text=f'{item}', callback_data=f'Add_{item}') for item in menu_not_in]:
        keyboard.add(button)
    keyboard.row(types.InlineKeyboardButton(text='Назад', callback_data='Edit_menu'))
    await call.message.edit_text(menutext)
    await call.message.edit_reply_markup(keyboard)


async def menu_remove(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    food_today = import_json_menu('DataFiles/food_menu_today.txt')
    drinks_today = import_json_menu('DataFiles/drinks_menu_today.txt')
    food_all = import_json_menu('DataFiles/food_menu_all.txt')
    drikns_all = import_json_menu('DataFiles/drinks_menu_all.txt')
    name = call.data.split('_')[1]
    if name != 'items':
        for item in food_all:
            if item['name'] == name:
                del_json_menu_item('DataFiles/food_menu_today.txt', item)
                food_today.remove(item)
                break
        for item in drikns_all:
            if item['name'] == name:
                del_json_menu_item('DataFiles/drinks_menu_today.txt', item)
                drinks_today.remove(item)
                break
    food_today_names = {item['name'] for item in food_today}
    drinks_today_names = {item['name'] for item in drinks_today}
    menu_in = food_today_names | drinks_today_names
    menutext = await menu_form(food_today, drinks_today)
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for button in [types.InlineKeyboardButton(text=f'{item}', callback_data=f'Del_{item}') for item in menu_in]:
        keyboard.add(button)
    keyboard.row(types.InlineKeyboardButton(text='Назад', callback_data='Edit_menu'))
    await call.message.edit_text(menutext)
    await call.message.edit_reply_markup(keyboard)


async def menu_new_start(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    dat = await state.get_data()
    if 'prim' in dat:
        await dat['prim'].delete()
    if 'prom' in dat:
        await dat['prom'].delete()
    else:
        await call.message.edit_text('Напишите название позиции меню')
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='Add_item'))
        await call.message.edit_reply_markup(keyboard)
    await MenuStates.item_creation_name.set()


async def menu_new_price(message: types.Message, state: FSMContext):
    name = message.text
    if len(name)>31:
        await message.answer('Название позиции должно быть короче 32 символов, попробуйте еще раз')
        return
    await state.update_data(prim=message)  # PRice Incoming Message
    text = f'Название позиции: {name}\n\nНапишите цену позиции'
    await state.update_data(name=name)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='New_item'))
    mes = await message.answer(text=text, reply_markup=keyboard)
    await state.update_data(prom=mes)  # PRice Outgoing Message
    await MenuStates.item_creation_price.set()


async def menu_new_type(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
    except ValueError:
        return
    await state.update_data(price=price)
    dat = await state.get_data()
    text = f'Название позиции: {dat["name"]}\nцена позиции: {price}\n\nВыберите тип позиции'
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text='Еда', callback_data='FIN_food'))
    keyboard.row(types.InlineKeyboardButton(text='Напиток', callback_data='FIN_drink'))
    await message.answer(text=text, reply_markup=keyboard)
    await MenuStates.item_creation_type.set()


async def menu_new_final(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    dat = await state.get_data()
    ftype = call.data.split('_')[1]
    ptype = ''
    if ftype == 'food':
        ptype = 'еда'
    if ftype == 'drink':
        ptype = 'напиток'
    await state.update_data(type=ftype)
    text = f'Название позиции: {dat["name"]}\nцена позиции: {dat["price"]}\nтип позиции: {ptype}\n\nВы хотите создать новую позицию?'
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(*[types.InlineKeyboardButton(text='Да', callback_data='Menu_confirm'),
                   types.InlineKeyboardButton(text='Нет', callback_data='Menu_end')])
    await call.message.edit_text(text)
    await call.message.edit_reply_markup(keyboard)


async def menu_new_confirmed(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    dat = await state.get_data()
    item = {'name': dat['name'], 'price': dat['price']}
    if dat['type'] == 'food':
        add_json_menu_item('DataFiles/food_menu_all.txt', item)
    if dat['type'] == 'drink':
        add_json_menu_item('DataFiles/drinks_menu_all.txt', item)
    await state.finish()
    await menu_add(call, state)


async def menu_new_cancelled(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.finish()
    await menu_edit(call, state)


async def menu_show(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.finish()
    food_today = import_json_menu('DataFiles/food_menu_today.txt')
    drinks_today = import_json_menu('DataFiles/drinks_menu_today.txt')
    menuout = await menu_form(food_today, drinks_today)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Редактировать меню', callback_data='Edit_menu'))
    keyboard.add(types.InlineKeyboardButton(text='Выйти', callback_data='Close_menu'))
    await call.message.edit_text(text=menuout)
    await call.message.edit_reply_markup(reply_markup=keyboard)


async def menu_close(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.finish()
    await call.message.delete()


def register_sender_handlers(disp: Dispatcher):
    disp.register_message_handler(login_start, commands='login', state='*')
    disp.register_message_handler(login_entered, state=LoginStates.waiting_for_login_info)
    disp.register_message_handler(orders_autosend_toggle, commands='autosend', state='*')
    disp.register_message_handler(send_next_order, commands='send_next_order', state='*')
    disp.register_message_handler(send_current_order, commands='send_current_order', state='*')
    disp.register_message_handler(escape, commands='escape', state='*')
    disp.register_message_handler(menu_main, commands='menu', state='*')
    disp.register_message_handler(menu_new_price, state=MenuStates.item_creation_name)
    disp.register_message_handler(menu_new_type, state=MenuStates.item_creation_price)
    disp.register_callback_query_handler(menu_edit, text='Edit_menu', state='*')
    disp.register_callback_query_handler(menu_add, Text(contains='Add'), state='*')
    disp.register_callback_query_handler(menu_remove, Text(contains='Del'), state='*')
    disp.register_callback_query_handler(menu_new_start, text='New_item', state='*')
    disp.register_callback_query_handler(menu_new_final, Text(contains='FIN'), state=MenuStates.item_creation_type)
    disp.register_callback_query_handler(menu_new_confirmed, text='Menu_confirm', state='*')
    disp.register_callback_query_handler(menu_new_cancelled, text='Menu_end', state='*')
    disp.register_callback_query_handler(menu_show, text='Finish_edit')
    disp.register_callback_query_handler(menu_close, text='Close_menu')
