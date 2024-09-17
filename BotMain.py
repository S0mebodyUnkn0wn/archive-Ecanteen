import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from pack.config import load_config
from pack.orderHandlers.orderHandler import register_order_handlers
from pack.orderHandlers.common import register_common_order_handlers

from pack.senderHandlers.senderHandler import register_sender_handlers
from pack.senderHandlers.common import register_common_sender_handlers
from pack.AdminStuff.depositHandler import register_deposit_handlers
from pack.updaters import next_order_updater, full_reset

logger = logging.getLogger(__name__)
order_bot: Bot
sender_bot: Bot
order_disp: Dispatcher
sender_disp: Dispatcher


async def set_order_commands(bot: Bot):
    commands = [
        BotCommand(command='/menu', description='Показать меню на день'),
        BotCommand(command='/order', description='Начать Заказ'),
        BotCommand(command='/deposit', description='Показать информацию о вашем депозите'),
        BotCommand(command='/escape', description='Прервать текущее действее'),
        BotCommand(command='/cancel_order', description='Отменить сделанный заказ')

    ]
    await bot.set_my_commands(commands)


async def set_sender_commands(bot: Bot):
    commands = [
        BotCommand(command='/menu', description='Открыть интерактивное меню'),
        BotCommand(command='/autosend', description='Автоматическая отправка заказа на след. окно'),
        BotCommand(command='/change_dep', description='Изменить баланс на депозите пользователя'),
        BotCommand(command='/escape', description='Прервать текущее действее'),
        BotCommand(command='/send_next_order', description='Прислать список заказов на след. окно'),
        BotCommand(command='/send_current_order', description='Прислать список заказов на текущее окно'),
        BotCommand(command='/print_all_orders', description='Прислать все сделанные на сегодня заказы'),
    ]
    await bot.set_my_commands(commands)


async def order_bot_run():
    await set_order_commands(order_bot)
    await order_disp.start_polling()


async def sender_bot_run():
    await set_sender_commands(sender_bot)
    await sender_disp.start_polling()


async def autosend_run():
    await next_order_updater(sender_bot)


async def reset_run():
    await full_reset()


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    logger.error('Starting bot')
    global order_bot
    global order_disp
    global sender_bot
    global sender_disp
    config = load_config('config/OrderBot.ini')

    order_bot = Bot(token=config.order_bot.token, parse_mode=types.ParseMode.HTML)
    order_disp = Dispatcher(order_bot, storage=MemoryStorage())
    sender_bot = Bot(token=config.sender_bot.token, parse_mode=types.ParseMode.HTML)
    sender_disp = Dispatcher(sender_bot, storage=MemoryStorage())

    register_common_order_handlers(order_disp)
    register_order_handlers(order_disp)

    register_sender_handlers(sender_disp)
    register_common_sender_handlers(sender_disp)

    register_deposit_handlers(sender_disp)

    order_func = loop.create_task(order_bot_run())
    sender_func = loop.create_task(sender_bot_run())
    autosend_func = loop.create_task(autosend_run())
    reset_func = loop.create_task(reset_run())

    await asyncio.wait([order_func, sender_func, autosend_func, reset_func])


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
