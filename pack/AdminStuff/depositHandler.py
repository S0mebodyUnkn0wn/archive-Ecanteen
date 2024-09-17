import json

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from pack.DataProcessing.ID_IO import check_auth
import hashlib
import datetime
import pandas as pd

CheckSumFail = False


class DepositStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_amount = State()
    waiting_for_confirmation = State()


class CheckSumError(Exception):
    pass


try:
    def get_deposit():
        with open('DataFiles/ForBackup/deposits') as depfile:
            try:
                deposits = json.load(depfile)
            except json.JSONDecodeError:
                return {}
        with open('DataFiles/ForBackup/hash') as hfile:
            entrychecksum = json.load(hfile)
        if hashlib.md5(str(deposits).encode()).hexdigest() != entrychecksum:
            raise CheckSumError
        return deposits


    async def update_users_tel(message: types.Message):
        if check_auth(message.from_user,lvl='perm'):
            update_users(message.from_user.id)
            await message.answer('Новые пользователи добавлены')
        else:
            await message.answer('У вас нет прав на использование этой команды')

    def update_users(source):
        user_list = pd.read_csv('DataFiles/user_list.txt', index_col=1, header=0)
        deposits = get_deposit()
        if len(deposits) > 0:
            entryhash = hashlib.md5(str(deposits).encode()).hexdigest()
            with open(
                    f'DataFiles/ForBackup/deposits_at_' + datetime.datetime.now().isoformat(timespec="seconds").replace(
                        ':', '-'), 'x') as backfile:
                json.dump(deposits, backfile)
        else:
            entryhash = None
        deposits = {}
        for user in user_list.index:
            if user not in deposits:
                deposits[f'{user}'] = 0
        exithash = hashlib.md5(str(deposits).encode()).hexdigest()
        with open('DataFiles/ForBackup/deposits', 'w') as depfile:
            json.dump(deposits, depfile)
        with open('DataFiles/ForBackup/hash', 'w') as hfile:
            json.dump(exithash, hfile)
        with open('DataFiles/ForBackup/transactionlog.txt', 'a') as log:
            log.write(f'[{datetime.datetime.now()}] | UPDATE | BY: {source} | ENTRY: {entryhash} EXIT: {exithash} \n')


    async def change_entry(local_id, change, source):
        depositinfo = get_deposit()
        with open('DataFiles/ForBackup/hash') as hfile:
            entrychecksum = json.load(hfile)
        if local_id not in depositinfo:
            return 'NoNameFail'
        before = depositinfo[local_id]
        depositinfo[local_id] += change
        exitchecksum = hashlib.md5(str(depositinfo).encode()).hexdigest()
        changelog = {'date': datetime.datetime.now(), 'by': source, 'account': local_id, 'from': before,
                     'to': depositinfo[local_id], 'entry': entrychecksum, 'exit': exitchecksum}
        with open('DataFiles/ForBackup/transactionlog.txt', 'a') as log:
            log.write(f"[{changelog['date']}] | EDIT | BY: {changelog['by']} | CHANGE: {changelog['account']} FROM "
                      f"{changelog['from']} TO {changelog['to']} | "
                      f"ENTRY: {changelog['entry']} EXIT: {changelog['exit']}\n")
            with open('DataFiles/ForBackup/deposits', 'w') as iofile:
                json.dump(depositinfo, iofile)
            with open('DataFiles/ForBackup/hash', 'w') as hfile:
                json.dump(exitchecksum, hfile)
        # transaction complete
        return changelog


    async def get_balance(local_id: str):
        try:
            balance = get_deposit()[local_id]
        except KeyError:
            return False
        return balance


    async def cancel(call: types.CallbackQuery, state: FSMContext):
        await call.message.answer('Изменение депозита отменено')
        await state.finish()


    async def start(message: types.Message, state: FSMContext):
        global CheckSumFail
        if not await check_auth(message.from_user, lvl='perm'):
            await message.answer('у вас не прав на использование этой команды, инцидент будет записан')
            with open('DataFiles/ForBackup/transactionlog.txt', 'a') as log:
                log.write(f'[{datetime.datetime.now()}] | FAILED LOGIN | BY: {message.from_user} | No rights for login')
            await state.finish()
        if CheckSumFail:
            await message.answer('Произошла ошибка Чексуммы, пожалуйста, незамедлительно сообщите об этом разработчику')
        await message.answer('Чей депозит вы хотите изменить?')
        await DepositStates.waiting_for_username.set()


    async def get_change(message: types.Message, state: FSMContext):
        name = message.text
        users = pd.read_csv('DataFiles/usr_ID_list.txt', header=0, usecols=['true_name', 'local_id', 'id', 'username'])
        local_id = False
        local_id: bool
        for user in users.iterrows():  # Will get painfully slow if there are a lot of users, optimisation possible
            if user[1].str.contains(name).any():
                local_id = user[1]['local_id']
                name = user[1]['true_name']
                await state.update_data(true_name=name, local_id=local_id)
        if not local_id:
            await message.answer('Такого пользователя не существует, попробуйте еще раз.'
                                 '\nЧтобы выйти из режима редактирования депозита используйте /escape')
            await DepositStates.waiting_for_username.set()
            return
        local_id: str
        balance = await get_balance(local_id)
        account_repo = f'Аккаунт найден:\n\nИмя: {name}({local_id})\n\nСейчас на балансе: {balance}\n'
        await message.answer(text=account_repo + 'На сколько вы хотите изменить баланс пользователя?')
        await DepositStates.waiting_for_amount.set()


    async def get_confirmation(message: types.Message, state: FSMContext):
        change = message.text
        try:
            change = int(change)
        except ValueError:
            await message.answer('Ваше сообщение не является числом, пожалуйста поробуйте еще раз.'
                                 '\nЧтобы выйти из режима редактирования депозита используйте /escape')
            return
        data = await state.get_data()
        current_balance = await get_balance(data['local_id'])
        conf_message = f"{data['true_name']}\n" \
                       f"\nСейчас на балансе: {current_balance}" \
                       f"\nБаланс будет изменен на: {change}" \
                       f"\nИтоговый баланс пользователя составит: {current_balance + change}\n" \
                       f"\nВы уверены, что вы хотите изменить баланс пользователя?"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text='Да', callback_data='Confirm'),
                       types.InlineKeyboardButton(text='Нет', callback_data='Cancel')])
        await state.update_data(change=change, source=f'TG_USER {message.from_user.id}')
        await message.answer(text=conf_message, reply_markup=keyboard)
        await DepositStates.waiting_for_confirmation.set()


    async def confirmed(call: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        changelog = await change_entry(local_id=data['local_id'], change=data['change'], source=data['source'])
        if changelog == 'NoNameFail':
            await call.answer('Такого пользователя нет в системе депозитов, скорее всего что-то пошло не так, '
                              'пожалуйста уведомите разработчика об ошибке', show_alert=True)
            await state.finish()
            return
        changelog: dict
        # noinspection PyBroadException
        try:
            await call.message.answer(text=f"Депозит успешно изменен\n"
                                           f"\nПользователь: {changelog['account']}\n"
                                           f"\nБаланс изменен с {changelog['from']}  до {changelog['to']}"
                                           f"\nИзменение: {changelog['to'] - changelog['from']}\n"
                                           f"\nЧексумма входа = {changelog['entry']}"
                                           f"\nЧексумма выхода = {changelog['exit']}")
        except:
            await call.answer(text='Депозит был успешно изменен, но, при отправке лога, что-то пошло не так',
                              show_alert=True)
        await state.finish()
except CheckSumError:
    CheckSumFail = True
    with open('DataFiles/ForBackup/deposits') as Errdepfile:
        Errdeposits = json.load(Errdepfile)
    with open('DataFiles/ForBackup/hash') as Errhfile:
        Errentrychecksum = json.load(Errhfile)
    with open('DataFiles/ForBackup/transactionlog.txt', 'a') as Errlog:
        Errlog.write(f'[{datetime.datetime.now()}] | CHECKSUM FAILURE | ENTRY: '
                     f'{hashlib.md5(str(Errdeposits).encode()).hexdigest()} != RECORDED: {Errentrychecksum}')


def register_deposit_handlers(disp: Dispatcher):
    disp.register_message_handler(start, commands='change_dep', state='*')
    disp.register_message_handler(update_users_tel, commands='Update_deps', state='*')
    disp.register_message_handler(get_change, state=DepositStates.waiting_for_username)
    disp.register_message_handler(get_confirmation, state=DepositStates.waiting_for_amount)
    disp.register_callback_query_handler(confirmed, state=DepositStates.waiting_for_confirmation, text='Confirm')
    disp.register_callback_query_handler(cancel, state=DepositStates.waiting_for_confirmation, text='Cancel')
