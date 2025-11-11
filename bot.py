# bot.py
import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)

from config import Config
from logger import logger
from handlers import (
    # Основные меню
    start, back_to_main, back_to_main_from_message, cancel,
    
    # Получить продукты
    get_products_menu, get_all_products, 
    search_products_start, search_products_process,
    get_product_by_id_start, handle_product_id_input,
    get_thermocup_by_id_start, advanced_search_start, 
    search_by_category_start, search_by_price_start,
    search_in_stock_only, search_by_price_process,
    search_by_category_process,

    
    # Добавить продукты
    add_products_menu, add_thermocup_start, add_thermocup_process,
    
    # Обновить продукты
    update_products_menu, update_thermocup_start, update_thermocup_process,
    update_thermocup_data_process, update_reserved_start, update_reserved_process,
    update_reserved_quantity_process, update_stock_start, update_stock_process,
    update_stock_warehouse_process, update_stock_quantity_process,
    
    # Вспомогательные
    error_handler, show_more_products,
    
    # Состояния
    MAIN_MENU, GET_PRODUCTS_MENU, ADD_PRODUCT_MENU, UPDATE_PRODUCT_MENU,
    ENTER_PRODUCT_ID, ENTER_SEARCH_QUERY, ENTER_THERMOCUP_DATA, ENTER_CATEGORY, ENTER_PRICE_RANGE,
    ENTER_UPDATE_DATA, ENTER_RESERVED_QUANTITY, ENTER_STOCK_QUANTITY, 
    ENTER_WAREHOUSE_ID
)

def main() -> None:
    """Запуск бота"""
    
    logger.info(f"Токен бота: {Config.BOT_TOKEN[:10]}...")

    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # ConversationHandler с новой структурой
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(get_products_menu, pattern="^get_products$"),
                CallbackQueryHandler(add_products_menu, pattern="^add_products$"),
                CallbackQueryHandler(update_products_menu, pattern="^update_products$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
            ],
            GET_PRODUCTS_MENU: [
                CallbackQueryHandler(get_all_products, pattern="^all_products$"),
                CallbackQueryHandler(search_products_start, pattern="^search_products$"),
                CallbackQueryHandler(advanced_search_start, pattern="^advanced_search$"),
                CallbackQueryHandler(search_by_category_start, pattern="^search_category$"),
                CallbackQueryHandler(search_by_price_start, pattern="^search_price_range$"),
                CallbackQueryHandler(search_in_stock_only, pattern="^search_in_stock$"),
                CallbackQueryHandler(get_product_by_id_start, pattern="^by_id$"),
                CallbackQueryHandler(get_thermocup_by_id_start, pattern="^thermocup_by_id$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(get_products_menu, pattern="^back_to_products_menu$"),
                CallbackQueryHandler(show_more_products, pattern="^show_more_products$"),
            ],
            ADD_PRODUCT_MENU: [
                CallbackQueryHandler(add_thermocup_start, pattern="^add_thermocup$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
            ],
            UPDATE_PRODUCT_MENU: [
                CallbackQueryHandler(update_thermocup_start, pattern="^update_thermocup$"),
                CallbackQueryHandler(update_reserved_start, pattern="^update_reserved$"),
                CallbackQueryHandler(update_stock_start, pattern="^update_stock$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
            ],
            ENTER_PRODUCT_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_id_input),
            ],
            ENTER_SEARCH_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_products_process),
            ],
            ENTER_CATEGORY: [  # ← ДОБАВИТЬ НОВОЕ СОСТОЯНИЕ
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_category_process),
            ],
            ENTER_PRICE_RANGE: [  # ← ДОБАВИТЬ ДЛЯ ПОИСКА ПО ЦЕНЕ
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_price_process),
            ],
            ENTER_THERMOCUP_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_thermocup_process),
            ],
            ENTER_UPDATE_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_thermocup_data_process),
            ],
            ENTER_RESERVED_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_reserved_quantity_process),
            ],
            ENTER_WAREHOUSE_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_stock_warehouse_process),
            ],
            ENTER_STOCK_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_stock_quantity_process),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()