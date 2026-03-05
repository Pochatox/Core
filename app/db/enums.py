# flake8-in-file-ignores: noqa: WPS115

from enum import IntEnum, StrEnum


class TaskPriority(IntEnum):
    LOW = 10
    MEDIUM = 20
    HIGH = 30
    VERY_HIGH = 40
    CRITICAL = 50


class UserRole(IntEnum):
    OWNER = 100
    MAINTAINER = 50
    MEMBER = 10


class Avatar(StrEnum):
    ARTICHOKE = "artichoke.png"
    ASPARAGUS = "asparagus.png"
    BEAN = "bean.png"
    BEETROOT = "beetroot.png"
    BELL_PEPPER = "bell_pepper.png"
    BLACK_RADISH = "black_radish.png"
    BROCCOLI = "broccoli.png"
    CARROT = "carrot.png"
    CAULIFLOWER = "cauliflower.png"
    CELERY = "celery.png"
    CORN = "corn.png"
    CUCUMBER = "cucumber.png"
    DILL = "dill.png"
    EGGPLANT = "eggplant.png"
    GARLIC = "garlic.png"
    GREAN_PEES = "grean_pees.png"
    HORSERADISH = "horseradish.png"
    JERUSALEM = "jerusalem.png"
    KOHLABI = "Kohlabi.png"
    LEAF_LETTUCE = "leaf_lettuce.png"
    LEEK = "leek.png"
    NAPA_CABBAGE = "napa_cabbage.png"
    ONION = "onion.png"
    PARSLEY = "parsley.png"
    PARSNIP = "parsnip.png"
    PATTYPAN_SQUASH = "pattypan_squash.png"
    POD_OF_PEAS = "pod_of_peas.png"
    PUMPKIN = "pumpkin.png"
    RADISH = "radish.png"
    RUTABAGA = "rutabaga.png"
    SHALLOT = "shallot.png"
    SORREL = "sorrel.png"
    SPINACH = "spinach.png"
    SWEET_POTATO = "sweet_potato.png"
    TOMATO = "tomato.png"
    TURNIP = "turnip.png"
    WHITE_CABBAGE = "white_cabbage.png"
    ZUCCHINI = "zucchini.png"
