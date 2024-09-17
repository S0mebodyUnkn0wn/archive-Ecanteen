from dataclasses import dataclass


@dataclass
class Food(object):

    def __init__(self, name: str):
        self.name = name


@dataclass
class Drink(object):

    def __init__(self, name: str):
        self.name = name

