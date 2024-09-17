import json


def import_json_menu(path):
    with open(path) as file:
        try:
            menu = json.load(file)
        except json.JSONDecodeError:
            menu = []
    menu: list
    return menu


def export_json_menu(path, menu_items: list):
    with open(path, 'w') as file:
        json.dump(menu_items, file)
    return True


def add_json_menu_item(path, item: dict):
    menu = import_json_menu(path)
    menu: list
    menu.append(item)
    export_json_menu(path, menu)


def del_json_menu_item(path, item: dict):
    menu = import_json_menu(path)
    menu: list
    menu.remove(item)
    export_json_menu(path, menu)


def add_interactive_item_console():
    path = input('choose into which file you want to add an item')
    repeat = True
    while repeat:
        name = input('type the name of new item')
        price = input('type a price of a new item in rubles')
        item = {'name': name, 'price': price}
        add_json_menu_item(path, item)
        if input('add one more item in the same file? Y/n').lower() == 'n':
            repeat = False