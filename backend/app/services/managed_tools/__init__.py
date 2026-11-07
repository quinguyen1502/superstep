from .sheets import SheetsTools
from .telegram import TelegramTools
from .http_api import HttpApiTools
from .channel_actions import SlackTools, WhatsAppTools, EmailTools, TeamsTools
from .drive import DriveTools
from .browser import BrowserTools
from .web import WebTools


def adapters(channels, quota=None):
    return {adapter.id: adapter for adapter in (TelegramTools(channels), SheetsTools(), HttpApiTools(),
        SlackTools(channels), WhatsAppTools(channels), EmailTools(channels, quota), TeamsTools(channels), DriveTools(), BrowserTools(), WebTools())}
