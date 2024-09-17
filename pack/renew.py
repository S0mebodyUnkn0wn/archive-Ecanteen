from pack.DataProcessing.timeUpdater import time_gen_new


def order_list():
    with open('DataFiles/orders.txt', 'w') as file:
        file.write('')


def comment_list():
    with open('DataFiles/comments.txt', 'w') as file:
        file.write('')


def time_list():
    time_gen_new()


def all_lists():
    time_list()
    order_list()
    comment_list()


def menu():
    with open('DataFiles/food_menu_today.txt', 'w') as file:
        file.write('')
