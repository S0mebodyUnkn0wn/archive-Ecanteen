import asyncio
import json
from datetime import datetime

from aiogram import Bot

from pack import renew
from pack.config import load_time_confing
from pack.senderHandlers.senderHandler import form_delayed_order

KillAll = False


async def next_order_updater(bot: Bot):  # call form_delayed_order(1) and send it to all ids in list every 10 minutes
    global KillAll  # MAYBE BROKEN
    while not KillAll:
        print('order_updater_update')
        times = load_time_confing('config/OrderBot.ini').timing
        closing_hour = times.closing_time
        opening_minute = 0
        opening_hour = times.opening_time
        if datetime.now() >= datetime.now().replace(hour=closing_hour, minute=0, second=0,
                                                    microsecond=0) or datetime.now() <= datetime.now().replace(
            hour=opening_hour - 1, minute=0, second=0):
            delay = opening_hour - datetime.now().hour - 1
            if delay < 0:
                delay += 24
            delay *= 3600
            delay -= datetime.now().minute * 60
            delay -= datetime.now().second
        else:
            delay = ((10 - datetime.now().time().minute % 10) * 60 - datetime.now().time().second + 59)
        if opening_hour>datetime.now().hour and datetime.now().minute<50:
            #wakeup_call
            delay = (60 - datetime.now().minute)*60 - 600
        print('delay', delay)
        await asyncio.sleep(delay)
        forder = await form_delayed_order(modif=0)
        with open('DataFiles/autosendStates.txt') as file:
            autosend_users = json.load(file)
        if type(forder) is not str:
            forder = f'заказов на {forder} нет'
        for user in autosend_users:
            print(user)
            await bot.send_message(chat_id=user, text=forder)


async def full_reset():  # reset everything at the end of every day BROKEN?
    global KillAll
    while not KillAll:
        print('reset')
        times = load_time_confing('config/OrderBot.ini').timing
        now = datetime.now()
        if now > now.replace(hour=times.closing_time, minute=0, second=0):
            renew.all_lists()
            renew.menu()
            sleep_time = times.closing_time - now.hour
            if sleep_time <= 0:
                sleep_time += 24
            sleep_time *= 3600
            sleep_time -= datetime.now().minute * 60
            sleep_time -= datetime.now().second
            print('everything was reset, next reset in', sleep_time, 'seconds')
            await asyncio.sleep(sleep_time)
        else:
            await asyncio.sleep(999999)
