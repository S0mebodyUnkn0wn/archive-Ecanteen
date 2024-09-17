import json

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup

from pack.DataProcessing.ID_IO import get_csv_frame, write_to_usr_id_file, get_local
from pack.DataProcessing.orderLogger import free_order, free_time, free_comment
from pack.senderHandlers.common import print_orders, time_update, orders_update
from pack.AdminStuff.depositHandler import get_balance

from pack.DataProcessing.orderLogger import refund_money
class Deposit(StatesGroup):
    deposit_main = State()

class LoginStates(StatesGroup):
    waiting_for_login_info = State()


class CancelStates(StatesGroup):
    waiting_for_tming = State()


async def start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer('Чтобы начать пользоваться E-Canteen, вам нужно зарегестрироваться. Пожалуйста, введите /login', reply_markup=types.ReplyKeyboardRemove())


async def login_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer('Пожалуйста, отправьте индентификационный код, который вам предоставила администрация')
    await LoginStates.waiting_for_login_info.set()


async def login_entered(message: types.Message, state: FSMContext):
    id_frame = await get_csv_frame('DataFiles/user_list.txt')
    id_series = id_frame['ID']
    if message.text in map(str, id_series.values):
        user_id = message.from_user
        if await write_to_usr_id_file(user_id, message.text):
            await message.answer('Регистрация прошла успешно')
            await about(message,state)
        else:
            await message.answer('Вы уже зарегестрированы в системе, напишите /order, чтобы оставить заказ')
        await state.finish()
    else:
        await message.answer('Такого кода нет в базе данных, проверьте правильность написания и попробуйте еще раз, '
                             'если вы уверены, что ввели все правильно - свяжитесь с администрацией')


async def deposit_main(message: types.Message, state: FSMContext):
    await state.finish()
    local_id = await get_local(message.from_user.id)
    balance = await get_balance(local_id)
    await state.update_data(local_id=local_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text='Подробнее о системе', callback_data='About_deposit'))
    await message.answer(f'На вашем депозите {balance}₽',reply_markup=keyboard)
    await Deposit.deposit_main.set()
async def deposit_show(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    local_id = data['local_id']
    balance = await get_balance(local_id)
    await state.update_data(local_id=local_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text='Подробнее о системе', callback_data='About_deposit'))
    await call.message.edit_text(f'На вашем депозите {balance}₽')
    await call.message.edit_reply_markup(reply_markup=keyboard)
    await Deposit.deposit_main.set()

async def about_deposit(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text='Назад',callback_data='Show_deposit'))
    await call.message.edit_text('Пополни свой счет у Ромы в любое время, назвав Фамилию и Имя или свой логин '
                                 '(тот код из 5 символов по которому ты регестрировался). При заказе, деньги автоматически '
                                 'списываются со счета. Ты всегда можешь проверить состояние своего счета написав '
                                 '/deposit',reply_markup=keyboard)


async def menu(message: types.Message):
    menuout = 'Меню на сегодня:\n\n'
    with open('DataFiles/food_menu_today.txt') as file:
        try: foods = json.load(file)
        except json.JSONDecodeError: foods=[]
    with open('DataFiles/drinks_menu_today.txt') as file:
        try: drinks = json.load(file)
        except json.JSONDecodeError: drinks=[]
    if len(foods) == 0:
        await message.answer('Меню еще не составлено, пожалуйста попробуйте позже')
        return
    for item in foods:
        menuout += f"{item['name']} - {item['price']}₽\n"
    menuout += '\n'
    for item in drinks:
        menuout += f"{item['name']} - {item['price']}₽\n"
    await message.answer(menuout)


async def escape(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("текущее действие отменено", reply_markup=types.ReplyKeyboardRemove())


async def cancel_order(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer('заказ на какое время вы хотите отменить?')
    await CancelStates.waiting_for_tming.set()


async def about(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer('Привет!'
                         '\nТы успешно зарегистрировался в E-Canteen, сервисе по дистанционному заказу еды в столовой!'
                         '\nЧто-то плохо работает? Не хватает функционала? (или просто не с кем поболтать)- обязательно пиши @pdv_jr или @S0meb0dyUnkn0wn.'
                         '\n\nКак пользоваться:'
                         '\n1) Можно заказывать с 9:30 на время с 11:30 до 17:00, но при этом <b>минимум за 10 мин до времени выдачи.</b>'
                         '\n2) Для заказа двух и более одинаковых блюд - нажми на кнопку столько раз, сколько хочешь блюд.'
                         '\n3) <b>Оплата только через депозит</b>.\nВ любой удобный для тебя момент оставь депозит Роме '
                         '(хоть на 1 день, хоть на неделю вперёд) и забери свой заказ без очереди, просто обозначив своё '
                         'присутсие Роме (помаши ему или назови своё имя).'
                         '\n\nМногих функций на данном этапе нет, но мы постоянно доработаем нашего бота!'
                         '\n\nПриятного аппетита,'
                         '\nКоманда E-Canteen.')


async def cancel_order_final(message: types.Message, state: FSMContext):
    timing = message.text
    if len(timing) == 5 and timing[2] == ':':
        timing += ':00'
    else:
        await message.answer('пожалуйста введите время в формате час:минута')
        return
    result = await free_order(timing, message.from_user.id)
    local_id = await get_local(message.from_user.id)
    refund=False
    if result[0]:
        if result[1]:
            refund = await refund_money(local_id,result[0])
        await free_time(timing, message.from_user.id)
        await free_comment(timing, message.from_user.id)
    else:
        await message.answer(f'вы не оставляли заказа на {timing[:5]}')
        await state.finish()
        return
    output = f'ваш заказ на {timing[:5]} отменен, в заказе было:\n'
    for item in result[0]:
        output += f'{item}\n'
    await message.answer(output)
    await state.finish()


def register_common_order_handlers(disp: Dispatcher):
    disp.register_message_handler(deposit_main, commands='deposit', state='*')
    disp.register_message_handler(menu, commands='menu', state='*')
    disp.register_message_handler(print_orders, commands="print_all_orders", state="*")
    disp.register_message_handler(start, commands="start", state="*")
    disp.register_message_handler(escape, commands="escape", state="*")
    disp.register_message_handler(time_update, commands="times_update", state="*")
    disp.register_message_handler(orders_update, commands="flush_order_list", state="*")
    disp.register_message_handler(escape, Text(equals="отмена", ignore_case=True), state="*")
    disp.register_message_handler(login_start, commands='login', state='*')
    disp.register_message_handler(cancel_order, commands='cancel_order')
    disp.register_message_handler(about, commands='about', state='*')
    disp.register_callback_query_handler(deposit_show, text='Show_deposit', state='*')
    disp.register_callback_query_handler(about_deposit, text='About_deposit', state=Deposit.deposit_main)
    disp.register_message_handler(cancel_order_final, state=CancelStates.waiting_for_tming)
    disp.register_message_handler(login_entered, state=LoginStates.waiting_for_login_info)
