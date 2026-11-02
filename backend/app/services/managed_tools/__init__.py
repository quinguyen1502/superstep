from .sheets import SheetsTools
from .telegram import TelegramTools
from .http_api import HttpApiTools


def adapters(channels):
    return {adapter.id: adapter for adapter in (TelegramTools(channels), SheetsTools(), HttpApiTools())}
