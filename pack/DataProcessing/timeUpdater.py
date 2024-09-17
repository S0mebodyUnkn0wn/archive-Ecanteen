import datetime
import pandas as pd
from pack.config import load_time_confing
from pack.config import update_config

config = load_time_confing('config/OrderBot.ini')
closing_hour = config.timing.closing_time
free_space = config.timing.free_space
opening_hour = config.timing.opening_time
delay = config.timing.delay
opening_minute = 30

def time_update():
    check_time = datetime.datetime.now()
    check_time = check_time.replace(hour=11, minute=0, second=0, microsecond=0)
    if check_time < datetime.datetime.now():
        check_time += datetime.timedelta(days=1)
    return time_avalible()


def time_gen_new():
    global config
    global closing_hour
    global free_space
    global opening_hour
    global opening_minute
    newtime = datetime.time(hour=opening_hour,minute=opening_minute)
    time_dict = {}
    while newtime.hour < closing_hour:
        time_dict[f'{newtime}'] = [[]]
        if newtime.minute < 50:
            newtime = newtime.replace(minute=newtime.minute + 10)
        else:
            newtime = newtime.replace(hour=newtime.hour + 1, minute=0)
    time_dict[f'{newtime}'] = [[]]
    dat = pd.DataFrame(time_dict, index=['occupancy'])
    dat.to_json('DataFiles/times.txt')
    update_config('config/OrderBot.ini', 'time', 'times_regened', 'True')


def time_avalible():
    dat = pd.read_json('DataFiles/times.txt', convert_axes=False)
    time_dict = dat.to_dict()
    outp = {}
    global opening_hour
    global closing_hour
    global delay
    global free_space
    factor = 0.9
    newtime = datetime.time(hour=opening_hour, minute=opening_minute)
    current_time = datetime.datetime.today()
    current_time = datetime.time(hour=current_time.hour, minute=current_time.minute, second=current_time.second)
    if current_time.minute + 10 < 60:
        current_time = current_time.replace(minute=current_time.minute + 10)
    else:
        current_time = current_time.replace(hour=current_time.hour + 1, minute=(current_time.minute + 10) % 60)
    while newtime.hour < closing_hour:
        time_dict[f'{newtime}']['occupancy'] = list(time_dict[f'{newtime}']['occupancy'])
        if (current_time < newtime or (
                current_time.hour == newtime.hour and current_time.minute + delay < newtime.minute)) and len(
            time_dict[f'{newtime}']['occupancy']) < free_space * factor:
            outp[f'{newtime}'] = time_dict[f'{newtime}']
        if newtime.minute < 50:
            newtime = newtime.replace(minute=newtime.minute + 10)
        else:
            newtime = newtime.replace(hour=newtime.hour + 1, minute=0)
    return outp
