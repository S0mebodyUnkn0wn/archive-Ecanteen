import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from pack.DataProcessing.timeUpdater import time_update
from pack.DataProcessing.orderLogger import order_log, check_order
from pack.AdminStuff.menuListIO import import_json_menu
from pack.DataProcessing.ID_IO import check_auth, get_local
from pack.AdminStuff.depositHandler import change_entry, get_balance
from pack.config import load_time_confing
avalible_time = []
avalible_foods = []
avalible_drinks = []
avalible_coffe_syrups = []


def var_gen():
    global avalible_time
    global avalible_foods
    global avalible_drinks
    global avalible_coffe_syrups
    avalible_time = []
    avalible_drinks = []
    avalible_foods = []
    avalible_coffe_syrups = []
    temp = time_update()
    for i in temp.keys():
        avalible_time.append(i[:5])
    temp = import_json_menu('DataFiles/food_menu_today.txt')
    for i in temp:
        avalible_foods.append(i)
    temp = import_json_menu('DataFiles/drinks_menu_today.txt')
    for i in temp:
        avalible_drinks.append(i)
    temp = import_json_menu('DataFiles/coffe_syrups.txt')
    for i in temp:
        avalible_coffe_syrups.append(i)


class OrderFood(StatesGroup):
    waiting_for_time_choice = State()
    waiting_for_food_choice = State()
    waiting_for_drinks_choice = State()
    waiting_for_confirmation = State()
    waiting_for_comment = State()
    waiting_for_syrup_choice = State()
    waiting_for_payment_method = State()


async def order_start(message: types.Message, state: FSMContext):
    await state.finish()
    if not await check_auth(message.from_user, 'usr'):
        await message.answer('Вы не авторизованы, чтобы начать пользоваться ботом введите /login')
        return
    var_gen()
    print(avalible_time)
    if len(avalible_time)==0:
        await message.answer(text='Сегодня кухня больше не принимает заказы, она откроется завтра, примерно в 9:30')
        return
    if len(avalible_foods)==0:
        await message.answer(text='Меню на сегодня пока не сформировано, пожалуйста попробуйте заказть позже')
        return
    keyboard = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton(text=time, callback_data=time) for time in avalible_time]
    keyboard.add(*buttons)
    await message.answer("Выберите время:", reply_markup=keyboard)
    await OrderFood.waiting_for_time_choice.set()


async def prompt_food(call: types.CallbackQuery, state: FSMContext):
    if await check_order(call.data+':00',call.from_user):
        await call.message.answer(text='Вы уже оставляли заказ на это время. Если вы хотите изменить свой заказ, '
                                       'отмените его, с помощью /cancel_order и закажите еще раз')
        await state.finish()
        return 
    await state.update_data(chosen_time=call.data)
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    buttons = [types.InlineKeyboardButton(text=avalible_foods[food]['name'], callback_data=str(food)) for food in
               range(len(avalible_foods))]
    for b in buttons:
        keyboard.row(b)
    keyboard.row(types.InlineKeyboardButton(text='Готово', callback_data='FoodChosen'))
    await call.message.answer(
        text='Выберите позции, затем нажмите "Готово". Для заказа двух и более одинаковых позиций - нажмите на кнопку '
             'столько раз, сколько хотите их заказать .  Если вы хотите только напиток - просто нажмите "Готово". '
             'Позже можно отменить заказ'
             '\n<b>Если вы заказываете комплекс, обязательно укажите какой гарнир вы хотите в комментариях</b>',
        reply_markup=keyboard)
    await OrderFood.waiting_for_food_choice.set()


async def prompt_drinks(call: types.CallbackQuery, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    buttons = [types.InlineKeyboardButton(text=avalible_drinks[drink]['name'], callback_data=str(drink)) for drink in
               range(len(avalible_drinks))]
    keyboard.add(*buttons)
    keyboard.row(types.InlineKeyboardButton(text='Готово', callback_data='DrinkChosen'))
    await call.message.answer(
        text='Выберите напитки, затем нажмите "Готово". Для заказа двух и более одинаковых напитков - нажмите на '
             'кнопку столько раз, сколько хотите их заказать. Если вы не хотите наптков - просто нажмите '
             '"Готово"',
        reply_markup=keyboard)
    await OrderFood.waiting_for_drinks_choice.set()


async def prompt_syrup(call: types.CallbackQuery, state: FSMContext, index):
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    buttons = [types.InlineKeyboardButton(text=avalible_coffe_syrups[syrup]['name'], callback_data=f'{syrup};{index}') for syrup in
               range(len(avalible_coffe_syrups))]
    for b in buttons:
        keyboard.row(b)
    keyboard.row(types.InlineKeyboardButton(text='Без сиропа', callback_data=f'NoSyrup;{index}'))
    await call.message.edit_text(text='Хотите ли вы, чтобы в ваш кофе добавили сироп, если да, то какой?')
    await call.message.edit_reply_markup(reply_markup=keyboard)
    await OrderFood.waiting_for_syrup_choice.set()


async def prompt_confirm(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(comment='')
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.InlineKeyboardButton(text='Да', callback_data='Proceed'),types.InlineKeyboardButton(text='Нет', callback_data='cancel'))
    keyboard.row(types.InlineKeyboardButton(text='Комментарий', callback_data='AddComment'))
    data = await state.get_data()
    time = data['chosen_time']
    forder = ''
    total_cost = 0
    if 'chosen_food' not in data:
        await call.message.answer(text='Похоже вы ничего не заказали, напишите /order, чтобы попробовать еще раз')
        await state.finish()
        return
    order = data['chosen_food']
    order_names = [i['name'] for i in order]
    for unit in order:
        cost = unit['price']
        item = unit['name']
        if 'extras' in unit:
            extras = str(*[t['name'] for t in unit['extras']])
            cost += sum([int(t['price']) for t in unit['extras']])
            item+=f' + {extras}'
        else:
            item+='​'
            extras=False
        item: str
        if item[1:] not in forder:
            if order_names.count(item) > 1:
                forder += item[0].capitalize() + item[1:] + ' x' + str(
                    order_names.count(item)) + f' - {cost * order_names.count(item)}₽\n'
                total_cost += cost * order_names.count(item)
            else:
                forder += item[0].capitalize() + item[1:] + f' - {cost}₽\n'
                total_cost += cost
    await state.update_data(cost=total_cost)
    await call.message.answer(text='Ваш заказ на ' + time + ':\n\n' + forder + f'\nОбщая сумма заказа {total_cost}₽.\n'
                                                                               f'Вы подтверждаете заказ? Если вы '
                                                                               f'хотите добавить комментарий - '
                                                                               f'нажмите на кнопку "Комментарий"',
                              reply_markup=keyboard)
    await OrderFood.waiting_for_comment.set()


async def pay_method(call: types.CallbackQuery, state: FSMContext):
    local_id = await get_local(call.from_user.id)
    balance = await get_balance(local_id)
    await state.update_data(local_id=local_id, from_user = call.from_user)
    data = await state.get_data()
    if balance>=data['cost']:
        #keyboard = types.InlineKeyboardMarkup()
        #keyboard.add(*[types.InlineKeyboardButton(text='Оплатить сейчас',callback_data='Confirmed_deposit'),types.InlineKeyboardButton(text='Оплатить при получении',callback_data='Confirmed_cash')])
        #await call.message.answer(f'На вашем депозите {balance}₽, вы можете оплатить заказ сейчас',reply_markup=keyboard)
        #await OrderFood.waiting_for_payment_method.set()
        await confirmed_dep(call, state)
        return
    await call.message.answer(f'На вашем депозите недостаточно средств ({balance}), чтобы узнать подробнее напишите /deposit')
    await state.finish()
    ''' 
    data['method']='Cash'
    await order_log(data)
    await call.message.answer('Заказ отправлен на кухню!\nвы можете оплачивать заказ с помощью депозита, чтобы узнать подробнее напишите /deposit')
    await state.finish()
    '''

async def confirmed_dep(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(method='Dep')
    data = await state.get_data()
    await order_log(data)
    await call.message.answer(f'Заказ отправлен на кухню!\nС вашего депозита будет списано {data["cost"]}₽. Вы можете отменить заказ с помощью /cancel_order, если до заказа осталось более 10 минут')
    await change_entry(data['local_id'],-data['cost'],'SYSTEM PAYMENT')
    await state.finish()

'''
async def confirmed_cash(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(method='Cash')
    data = await state.get_data()
    await order_log(data)
    await call.message.answer(
        f'Заказ отправлен на кухню!\nОплата заказа при получении')
    await state.finish()
'''

async def cancel(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.answer('Заказ отменен.\nНапишите /order, чтобы попробовать еще раз')


async def prompt_comment(call: types.CallbackQuery, state: FSMContext):
    print('test')
    await call.message.answer('Напишите комментарий')
    await OrderFood.waiting_for_comment.set()


async def add_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.InlineKeyboardButton(text='Да', callback_data='Proceed'),
                 types.InlineKeyboardButton(text='Нет', callback_data='cancel'))
    await OrderFood.waiting_for_comment.set()
    await message.answer('Комментарий добавлен.\nХотите подтвердить заказ?', reply_markup=keyboard)


async def syrup_chosen(call: types.CallbackQuery, state: FSMContext):
    tmp = await state.get_data()
    arr = []
    if 'chosen_food' in tmp.keys():
        arr=tmp['chosen_food'].copy()
    if 'NoSyrup' in call.data:
        data = avalible_drinks[int(call.data.split(';')[1])].copy()
        arr.append(data)
    else:
        data=avalible_drinks[int(call.data.split(';')[1])].copy()
        if 'extras' in data:
            data['extras'].append(avalible_coffe_syrups[int(call.data.split(';')[0])])
        else:
            data['extras']=[avalible_coffe_syrups[int(call.data.split(';')[0])]]
        arr.append(data)
    await state.update_data(chosen_food=arr.copy())
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    buttons = [types.InlineKeyboardButton(text=avalible_drinks[drink]['name'], callback_data=str(drink)) for drink in
               range(len(avalible_drinks))]
    keyboard.add(*buttons)
    keyboard.row(types.InlineKeyboardButton(text='Готово', callback_data='DrinkChosen'))
    if 'extras' in data:
        p=f"{data['name']} + " + str(*[t['name'] for t in data['extras']])
    else:
        p=f"{data['name']}"
    await call.answer(text=f"вы заказали {p}")
    await call.message.edit_reply_markup(keyboard)
    await OrderFood.waiting_for_drinks_choice.set()


async def write_order(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'FoodChosen' or call.data == 'DrinkChosen':
        return
    tmp = await state.get_data()
    data = {}
    mode = None
    if 'food' in await state.get_state():
        data = avalible_foods[int(call.data.split(';')[0])].copy()
        mode='f'
    if 'drinks' in await state.get_state():
        data = avalible_drinks[int(call.data.split(';')[0])].copy()
        mode ='d'
    arr = []
    if 'chosen_food' in tmp.keys():
        arr = tmp['chosen_food'].copy()
    if arr.count(data)<2 and mode == 'f' or arr.count(data)<3 and mode == 'd':
        if data['name'].lower() == 'капучино':
            await prompt_syrup(call, state, int(call.data.split(';')[0]))
        else:
            arr.append(data)
            await state.update_data(chosen_food=arr.copy())
            await call.answer(text=f"вы заказали {data['name']}")
    else:
        await call.answer(text=f'К сожалению, нельзя заказывать больше {arr.count(data)} порций по этой позиции',show_alert=True)


def register_order_handlers(disp: Dispatcher):
    disp.register_message_handler(order_start, commands='order', state='*')
    disp.register_callback_query_handler(prompt_food, state=OrderFood.waiting_for_time_choice)
    disp.register_callback_query_handler(prompt_drinks, state=OrderFood.waiting_for_food_choice, text='FoodChosen')
    disp.register_callback_query_handler(write_order, state=OrderFood.waiting_for_food_choice)
    disp.register_callback_query_handler(prompt_confirm, state=OrderFood.waiting_for_drinks_choice, text='DrinkChosen')
    disp.register_callback_query_handler(write_order, state=OrderFood.waiting_for_drinks_choice)
    disp.register_callback_query_handler(prompt_comment, state=OrderFood.waiting_for_comment, text='AddComment')
    disp.register_callback_query_handler(cancel, state=OrderFood.waiting_for_comment, text='cancel')
    disp.register_callback_query_handler(pay_method, state=OrderFood.waiting_for_comment, text='Proceed')
    #disp.register_callback_query_handler(confirmed_cash, state=OrderFood.waiting_for_payment_method, text='Confirmed_cash')
    disp.register_callback_query_handler(confirmed_dep, state=OrderFood.waiting_for_payment_method, text='Confirmed_deposit')
    disp.register_callback_query_handler(syrup_chosen,state=OrderFood.waiting_for_syrup_choice)
    disp.register_message_handler(add_comment, state=OrderFood.waiting_for_comment)
