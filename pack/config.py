import configparser
from dataclasses import dataclass


@dataclass
class Order_Bot:
    token: str


@dataclass
class Sender_Bot:
    token: str


@dataclass
class Autosend:
    delay: int


@dataclass
class Timing:
    times_regened: bool
    opening_time: int
    closing_time: int
    free_space: int
    delay: int


@dataclass
class TimeConfig:
    timing: Timing


@dataclass
class AutosendConfig:
    autosend: Autosend


@dataclass
class Config:
    order_bot: Order_Bot
    sender_bot: Sender_Bot


def update_config(path: str, group: str, field: str, value: str):
    config = configparser.ConfigParser()
    file = config.read(path)


def parse(string):
    d = {'True': True, 'False': False}
    return d.get(string, string)


def load_autosend_config(path: str):
    config = configparser.ConfigParser()
    config.read(path)
    autosend = config['autosend']
    return AutosendConfig(
        autosend=Autosend(
            delay=int(autosend['delay'])
        )
    )


def load_time_confing(path: str):
    config = configparser.ConfigParser()
    config.read(path)
    timing = config["time"]
    return TimeConfig(
        timing=Timing(
            times_regened=parse(timing['times_regened']),
            opening_time=int(timing['opening_time']),
            closing_time=int(timing['closing_time']),
            free_space=int(timing['free_space']),
            delay=int(timing['delay'])
        )
    )


def load_config(path: str):
    config = configparser.ConfigParser()
    config.read(path)

    order_bot = config["order_bot"]
    sender_bot = config["sender_bot"]
    return Config(
        sender_bot=Sender_Bot(
            token=sender_bot["token"]
        ),
        order_bot=Order_Bot(
            token=order_bot["token"]
        )
    )
