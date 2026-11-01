from .sheets import SheetsTools
from .telegram import TelegramTools


def adapters(channels):
    return {adapter.id: adapter for adapter in (TelegramTools(channels), SheetsTools())}
