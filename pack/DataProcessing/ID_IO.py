import pandas
from aiogram import types


async def get_csv_frame(path):
    data = pandas.read_csv(path)
    data: pandas.DataFrame
    return data


async def write_to_perm_id_file(userid, localid):
    perm_reference = pandas.read_csv("DataFiles/perm_list.txt", index_col=1)
    try:
        data = pandas.read_csv("DataFiles/perm_ID_list.txt", index_col=0)
    except pandas.errors.EmptyDataError:
        data = pandas.DataFrame()
    userid_list = [userid['id'], userid['is_bot'], userid['first_name'], userid['last_name'], userid['username'],
                   userid['language_code']]
    useid_series = pandas.Series([perm_reference.loc[localid]['Name'], localid] + userid_list,
                                 index=['true_name', 'local_id', 'id', 'is_bot', 'first_name', 'last_name',
                                        'username', 'language_code'])
    if useid_series.to_list() in [tmp[1].to_list() for tmp in data.iterrows()]:
        return False
    outp_data = pandas.concat([data, useid_series.to_frame().T], ignore_index=True)
    outp_data.to_csv("DataFiles/perm_ID_list.txt")
    return True


async def write_to_usr_id_file(userid, localid):
    user_reference = pandas.read_csv("DataFiles/user_list.txt", index_col=1)
    try:
        data = pandas.read_csv("DataFiles/usr_ID_list.txt", index_col=0)
    except pandas.errors.EmptyDataError:
        data = pandas.DataFrame()
    userid_list = [userid['id'], userid['is_bot'], userid['first_name'], userid['last_name'], userid['username'],
                   userid['language_code']]
    useid_series = pandas.Series([user_reference.loc[localid]['Name'], localid] + userid_list,
                                 index=['true_name', 'local_id', 'id', 'is_bot', 'first_name', 'last_name',
                                        'username', 'language_code'])

    if useid_series.to_list() in [tmp[1].to_list() for tmp in data.iterrows()]:
        return False
    outp_data = pandas.concat([data, useid_series.to_frame().T], ignore_index=True)
    outp_data.to_csv("DataFiles/usr_ID_list.txt")
    return True


async def get_local(telegramid):
    user_ref=pandas.read_csv('DataFiles/usr_ID_list.txt', usecols=['local_id','id'],header=0)
    local_id=False
    for user in user_ref.iterrows():
        if str(user[1]['id'])==str(telegramid):
            local_id = user[1]['local_id']
    return local_id


async def get_true_name(telegram_id=False, local_id=False):
    user_ref=pandas.read_csv('DataFiles/usr_ID_list.txt', usecols=['true_name','local_id','id'],header=0)
    true_name=False
    for user in user_ref.iterrows():
        if str(user[1]['id'])==str(telegram_id):
            true_name = user[1]['true_name']
        if str(user[1]['local_id'])==str(local_id):
            true_name = user[1]['true_name']
    return true_name


async def check_auth(user: types.User, lvl='usr'):
    if lvl == 'perm':
        data = await get_csv_frame('DataFiles/perm_ID_list.txt')
        data: pandas.DataFrame
        if user.id in data['id'].values:
            return True
        else:
            return False
    if lvl == 'usr':
        data = await get_csv_frame('DataFiles/usr_ID_list.txt')
        data: pandas.DataFrame
        if user.id in data['id'].values:
            return True
        else:
            return False
    raise RuntimeError
