# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Конфигурация приложения"""
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    WAREHOUSE_API_URL = os.getenv('WAREHOUSE_API_URL', 'http://localhost:8000/api')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env файле")
        if not cls.WAREHOUSE_API_URL:
            raise ValueError("WAREHOUSE_API_URL не установлен в .env файле")

Config.validate()