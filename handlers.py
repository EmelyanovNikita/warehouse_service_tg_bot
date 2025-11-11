# handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
import logging
from api_client import WarehouseAPIClient
from typing import List, Dict

logger = logging.getLogger(__name__)
api_client = WarehouseAPIClient()

# Состояния для ConversationHandler
(
    MAIN_MENU, GET_PRODUCTS_MENU, ADD_PRODUCT_MENU, UPDATE_PRODUCT_MENU,
    ENTER_PRODUCT_ID, ENTER_SEARCH_QUERY, ENTER_CATEGORY, ENTER_PRICE_RANGE,
    ENTER_THERMOCUP_DATA, ENTER_UPDATE_DATA, ENTER_RESERVED_QUANTITY, 
    ENTER_STOCK_QUANTITY, ENTER_WAREHOUSE_ID
) = range(13)

def truncate_message(text: str, max_length: int = 4096) -> str:
    """Обрезает текст до максимальной длины для Telegram"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 100] + "\n\n... (сообщение обрезано)"

# ===== ГЛАВНОЕ МЕНЮ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с ботом - полный сброс"""
    user = update.message.from_user
    logger.info(f"User {user.first_name} started the conversation")
    
    keyboard = [
        [InlineKeyboardButton("📦 Получить продукты", callback_data="get_products")],
        [InlineKeyboardButton("➕ Добавить продукты", callback_data="add_products")],
        [InlineKeyboardButton("🔄 Обновить продукты", callback_data="update_products")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🏭 Добро пожаловать в систему управления складом, {user.first_name}!\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )
    
    return MAIN_MENU

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вернуться в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📦 Получить продукты", callback_data="get_products")],
        [InlineKeyboardButton("➕ Добавить продукты", callback_data="add_products")],
        [InlineKeyboardButton("🔄 Обновить продукты", callback_data="update_products")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.reply_text(
        "🏭 Главное меню управления складом\nВыберите действие:",
        reply_markup=reply_markup
    )
    
    return MAIN_MENU

# ===== ПОЛУЧИТЬ ПРОДУКТЫ =====
async def get_products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Меню получения продуктов"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📋 Все продукты", callback_data="all_products")],
        [InlineKeyboardButton("🔍 Быстрый поиск", callback_data="search_products")],
        [InlineKeyboardButton("🎯 Расширенный поиск", callback_data="advanced_search")],
        [InlineKeyboardButton("🆔 По ID продукта", callback_data="by_id")],
        [InlineKeyboardButton("☕ Термокружка по ID", callback_data="thermocup_by_id")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.reply_text(
        "📦 **Получить продукты**\nВыберите тип запроса:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return GET_PRODUCTS_MENU

def format_products_message(products: List[Dict], title: str = "Продукты") -> List[str]:
    """
    Форматирует список продуктов в сообщения для Telegram
    Возвращает список сообщений (если не помещается в одно)
    """
    messages = []
    current_message = f"📦 {title}:\n\n"
    
    for product in products:
        # Извлекаем данные в переменные
        product_id = str(product.get('id', 'N/A'))
        product_name = product.get('name', 'Без названия')
        product_sku = product.get('sku', 'Не указан')
        product_category = product.get('category_name', 'Не указана')
        product_quantity = product.get('total_quantity', 0)
        product_price = product.get('base_price', 0)
        
        # Форматируем цену
        formatted_price = f"${product_price:.2f}"
        
        # Создаем разделитель
        separator = "─" * 20
        
        # Формируем текст продукта из переменных
        product_text = (
            f"🆔 ID: {product_id}\n"
            f"📝 Название: {product_name}\n"
            f"🏷️ Артикул: {product_sku}\n"
            f"📂 Категория: {product_category}\n"
            f"📊 Количество: {product_quantity} шт.\n"
            f"💰 Цена: {formatted_price}\n"
            f"{separator}\n"
        )
        
        # Проверяем не превысим ли лимит Telegram
        if len(current_message) + len(product_text) > 3500:
            messages.append(current_message)
            current_message = "📦 Продолжение:\n\n" + product_text
        else:
            current_message += product_text
    
    # Добавляем последнее сообщение
    if current_message and current_message != f"📦 {title}:\n\n":
        messages.append(current_message)
    
    return messages

async def get_all_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получить все продукты - простая версия с пошаговым выводом"""
    query = update.callback_query
    await query.answer()
    
    products = await api_client.get_products(
        limit=100,
        include_inactive=False,
        include_out_of_stock=True
    )
    
    if not products:
        await query.reply_text("❌ Нет продуктов на складе")
        return GET_PRODUCTS_MENU

    # Формируем сообщения
    messages = []
    current_message = "📦 Продукты на складе:\n\n"
    
    for product in products:
        # Сначала присваиваем все значения переменным
        product_id = str(product.get('id', 'N/A'))
        product_name = product.get('name', 'Без названия')
        product_sku = product.get('sku', 'Не указан')
        product_category = product.get('category_name', 'Не указана')
        product_quantity = product.get('total_quantity', 0)
        product_price = product.get('base_price', 0)
        
        # Форматируем цену
        formatted_price = f"${product_price:.2f}"
        
        # Создаем разделитель
        separator = "─" * 20
        
        # Теперь формируем итоговый текст из переменных
        product_text = (
            f"ID: {product_id}\n"
            f"Название: {product_name}\n"
            f"Артикул: {product_sku}\n"
            f"Категория: {product_category}\n"
            f"Количество: {product_quantity}\n"
            f"Цена: {formatted_price}\n"
            f"{separator}\n"
        )
        
        # Если добавляя этот продукт превысим лимит - сохраняем текущее сообщение
        if len(current_message) + len(product_text) > 3500:
            messages.append(current_message)
            current_message = "📦 Продолжение:\n\n" + product_text
        else:
            current_message += product_text
    
    # Добавляем последнее сообщение
    if current_message:
        messages.append(current_message)
    
    # Сохраняем все сообщения в контексте
    context.user_data['product_messages'] = messages
    context.user_data['current_message_index'] = 0
    
    # Показываем первое сообщение
    return await show_next_product_message(update, context)

async def show_next_product_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать следующее сообщение с продуктами"""
    messages = context.user_data.get('product_messages', [])
    current_index = context.user_data.get('current_message_index', 0)
    
    if not messages or current_index >= len(messages):
        # Определяем откуда пришел запрос
        if update.callback_query:
            await update.callback_query.message.reply_text("❌ Нет данных для отображения")
        else:
            await update.message.reply_text("❌ Нет данных для отображения")
        return GET_PRODUCTS_MENU
    
    current_message = messages[current_index]
    
    # Создаем кнопки
    keyboard = []
    
    # Если есть еще сообщения - показываем кнопку "Далее"
    if current_index < len(messages) - 1:
        keyboard.append([InlineKeyboardButton("📄 Показать еще", callback_data="show_more_products")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_products_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Определяем откуда пришел запрос и отправляем сообщение
    if update.callback_query:
        # Если это callback от кнопки
        await update.callback_query.message.reply_text(
            current_message, 
            reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        # Если это текстовое сообщение
        await update.message.reply_text(
            current_message,
            reply_markup=reply_markup
        )
    
    return GET_PRODUCTS_MENU

async def show_more_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать следующую часть продуктов"""
    query = update.callback_query
    await query.answer()
    
    # Увеличиваем индекс и показываем следующее сообщение
    current_index = context.user_data.get('current_message_index', 0)
    context.user_data['current_message_index'] = current_index + 1
    
    return await show_next_product_message(update, context)

async def search_products_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать поиск по названию через API фильтры"""
    query = update.callback_query
    await query.answer()
    
    await query.reply_text(
        "🔍 **Поиск продуктов**\n\n"
        "Введите название продукта или часть названия:\n"
        "• Можно вводить неполное название\n" 
        "• Регистр не имеет значения\n"
        "• Поиск по всем товарам в базе",
        parse_mode='Markdown'
    )
    
    return ENTER_SEARCH_QUERY

async def search_products_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать поисковый запрос через API фильтры"""
    search_query = update.message.text.strip()
    
    if not search_query:
        await update.message.reply_text("❌ Пожалуйста, введите поисковый запрос")
        return ENTER_SEARCH_QUERY
    
    if len(search_query) < 2:
        await update.message.reply_text("❌ Запрос должен содержать минимум 2 символа")
        return ENTER_SEARCH_QUERY
    
    # Показываем индикатор поиска
    search_message = await update.message.reply_text(f"🔍 Ищу \"{search_query}\"...")
    
    try:
        # Используем встроенный поиск API
        products = await api_client.get_products(
            search=search_query,
            limit=50,  # Ограничиваем количество результатов
            include_inactive=False,  # Только активные товары
            include_out_of_stock=True  # Показываем даже отсутствующие
        )
        
        if not products:
            # Пробуем поискать без учета регистра и с частичным совпадением
            products = await api_client.get_products(
                search=search_query.lower(),
                limit=50,
                include_inactive=False,
                include_out_of_stock=True
            )
        
        if not products:
            # Предлагаем альтернативы - ищем похожие товары
            all_products = await api_client.get_products(limit=100)
            similar_products = await find_similar_products(all_products, search_query)
            
            if similar_products:
                message = (
                    f"❌ По запросу \"{search_query}\" ничего не найдено.\n\n"
                    f"💡 Возможно, вы искали:\n"
                )
                
                for i, product in enumerate(similar_products[:3]):
                    message += f"• {product.get('name')} (ID: {product.get('id')})\n"
                
                message += f"\nПопробуйте один из этих вариантов или уточните запрос."
            else:
                message = (
                    f"❌ По запросу \"{search_query}\" ничего не найдено.\n\n"
                    f"💡 Попробуйте:\n"
                    f"• Ввести другое название\n"
                    f"• Использовать часть названия\n"
                    f"• Проверить правильность написания\n"
                    f"• Поискать по ID продукта"
                )
            
            await search_message.reply_text(message)
            return await get_products_menu_from_message(update, context)
        
        # Формируем сообщение с результатами
        if len(products) == 1:
            message = f"✅ Найден 1 продукт по запросу \"{search_query}\":\n\n"
        else:
            message = f"✅ Найдено {len(products)} продуктов по запросу \"{search_query}\":\n\n"
        
        for product in products:
            # Определяем эмодзи статуса
            status_emoji = "✅" if product.get('is_active', True) else "❌"
            stock_emoji = "📦" if product.get('total_quantity', 0) > 0 else "📭"
            
            message += (
                f"{status_emoji}{stock_emoji} ID: {product.get('id', 'N/A')}\n"
                f"📝 Название: {product.get('name', 'Без названия')}\n"
                f"🏷️ Артикул: {product.get('sku', 'Не указан')}\n"
                f"📂 Категория: {product.get('category_name', 'Не указана')}\n"
                f"📊 Количество: {product.get('total_quantity', 0)} шт.\n"
                f"💰 Цена: ${product.get('base_price', 0):.2f}\n"
                "─" * 30 + "\n"
            )
        
        # Если много результатов, предлагаем уточнить запрос
        if len(products) >= 50:
            message += f"\n💡 Найдено много результатов. Уточните запрос для более точного поиска."
        
        # Обрезаем если слишком длинное
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (результаты обрезаны, уточните запрос)"
        
        keyboard = [
            [InlineKeyboardButton("🔍 Новый поиск", callback_data="search_products")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back_to_products_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await search_message.reply_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await search_message.reply_text(
            "❌ Произошла ошибка при поиске. Пожалуйста, попробуйте позже."
        )
    
    return GET_PRODUCTS_MENU

async def find_similar_products(products, search_query):
    """Находит похожие продукты на основе простого сравнения строк"""
    if not products or not search_query:
        return []
    
    search_lower = search_query.lower()
    similar = []
    
    for product in products:
        product_name = product.get('name', '').lower()
        
        # Простой алгоритм схожести - можно улучшить
        if (len(search_lower) >= 3 and 
            (search_lower in product_name or 
             any(word.startswith(search_lower[:3]) for word in product_name.split()))):
            similar.append(product)
    
    return similar[:5]  # Возвращаем до 5 похожих продуктов

async def advanced_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Меню расширенного поиска с фильтрами"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск по названию", callback_data="search_name")],
        [InlineKeyboardButton("📂 Поиск по категории", callback_data="search_category")],
        [InlineKeyboardButton("💰 Поиск по цене", callback_data="search_price_range")],
        [InlineKeyboardButton("📦 Только в наличии", callback_data="search_in_stock")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_products_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.reply_text(
        "🎯 **Расширенный поиск**\n\n"
        "Выберите тип поиска:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return GET_PRODUCTS_MENU

async def search_by_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Поиск по категории"""
    query = update.callback_query
    await query.answer()
    
    await query.reply_text(
        f"📂 **Поиск по категории**\n\n"
        f"Введите название категории:\n\n"
        f"Пример: Thermocups",
        parse_mode='Markdown'
    )
    
    return ENTER_CATEGORY  # ← ИЗМЕНИТЬ НА НОВОЕ СОСТОЯНИЕ

async def search_by_category_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать поиск по категории через API"""
    category_query = update.message.text.strip()
    
    if not category_query:
        await update.message.reply_text("❌ Пожалуйста, введите название категории")
        return ENTER_SEARCH_QUERY
    
    search_message = await update.message.reply_text(f"📂 Ищу категорию \"{category_query}\"...")
    
    try:
        # ПРОСТО API запрос с параметром category
        products = await api_client.get_products(
            category=category_query,
            limit=50,
            include_inactive=False,
            include_out_of_stock=True
        )
        
        if not products:
            await search_message.reply_text(f"❌ В категории \"{category_query}\" товаров не найдено")
            return await get_products_menu_from_message(update, context)
        
        message = f"📂 Продукты в категории \"{category_query}\":\n\n"
        
        for product in products:
            # Заполняем данные через переменные
            product_id = product.get('id', 'N/A')
            product_name = product.get('name', 'Без названия')
            product_quantity = product.get('total_quantity', 0)
            product_price = product.get('base_price', 0)
            
            # Форматируем цену
            formatted_price = f"${product_price:.2f}"
            
            # Создаем разделитель
            separator = "─" * 25
            
            # Формируем сообщение из переменных
            message += (
                f"🆔 ID: {product_id}\n"
                f"📝 Название: {product_name}\n"
                f"📊 Количество: {product_quantity} шт.\n"
                f"💰 Цена: {formatted_price}\n"
                f"{separator}\n"
            )
        
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (результаты обрезаны)"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_products_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await search_message.reply_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Category search error: {e}")
        await search_message.reply_text("❌ Ошибка при поиске по категории")
    
    return GET_PRODUCTS_MENU

async def search_by_price_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Поиск по диапазону цен"""
    query = update.callback_query
    await query.answer()
    
    await query.reply_text(
        "💰 **Поиск по цене**\n\n"
        "Введите диапазон цен в формате:\n"
        "`мин_цена - макс_цена`\n\n"
        "Примеры:\n"
        "`0 - 100` - товары до $100\n"
        "`50 - 200` - товары от $50 до $200\n"
        "`1000 - ` - товары от $1000\n"
        "` - 50` - товары до $50",
        parse_mode='Markdown'
    )
    
    return ENTER_SEARCH_QUERY

async def search_by_price_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать поиск по цене через API"""
    price_query = update.message.text.strip()
    
    search_message = await update.message.reply_text(f"💰 Анализирую диапазон цен...")
    
    try:
        # Парсим диапазон цен
        if ' - ' in price_query:
            min_str, max_str = price_query.split(' - ', 1)
            min_price = float(min_str) if min_str.strip() else None
            max_price = float(max_str) if max_str.strip() else None
        else:
            await search_message.reply_text("❌ Неверный формат. Используйте: мин_цена - макс_цена")
            return ENTER_SEARCH_QUERY
        
        # ПРОСТО API запрос с параметрами min_price и max_price
        products = await api_client.get_products(
            min_price=min_price,
            max_price=max_price,
            limit=50,
            include_inactive=False,
            include_out_of_stock=True
        )
        
        if not products:
            range_text = ""
            if min_price and max_price:
                range_text = f"от ${min_price} до ${max_price}"
            elif min_price:
                range_text = f"от ${min_price}"
            elif max_price:
                range_text = f"до ${max_price}"
            
            await search_message.reply_text(f"❌ В диапазоне {range_text} товаров не найдено")
            return await get_products_menu_from_message(update, context)
        
        range_text = ""
        if min_price and max_price:
            range_text = f"от ${min_price} до ${max_price}"
        elif min_price:
            range_text = f"от ${min_price}"
        elif max_price:
            range_text = f"до ${max_price}"
        
        message = f"💰 Продукты в диапазоне {range_text}:\n\n"
        
        for product in products:
            message += (
                f"🆔 ID: {product.get('id', 'N/A')}\n"
                f"📝 Название: {product.get('name', 'Без названия')}\n"
                f"💰 Цена: ${product.get('base_price', 0):.2f}\n"
                f"📊 Количество: {product.get('total_quantity', 0)} шт.\n"
                "─" * 25 + "\n"
            )
        
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (результаты обрезаны)"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_products_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await search_message.reply_text(message, reply_markup=reply_markup)
        
    except ValueError:
        await search_message.reply_text("❌ Неверный формат цен. Используйте числа")
        return ENTER_SEARCH_QUERY
    except Exception as e:
        logger.error(f"Price search error: {e}")
        await search_message.reply_text("❌ Ошибка при поиске по цене")
    
    return GET_PRODUCTS_MENU

async def search_in_stock_only(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать только товары в наличии через API"""
    query = update.callback_query
    await query.answer()
    
    search_message = await query.reply_text("📦 Ищу товары в наличии...")
    
    try:
        # ПРОСТО API запрос с параметром include_out_of_stock=False
        products = await api_client.get_products(
            include_out_of_stock=False,  # Только товары в наличии
            limit=50,
            include_inactive=False
        )
        
        if not products:
            await search_message.reply_text("❌ Нет товаров в наличии")
            return GET_PRODUCTS_MENU
        
        message = "📦 **Товары в наличии:**\n\n"
        
        for product in products:
            message += (
                f"🆔 ID: {product.get('id', 'N/A')}\n"
                f"📝 Название: {product.get('name', 'Без названия')}\n"
                f"📊 Количество: {product.get('total_quantity', 0)} шт.\n"
                f"💰 Цена: ${product.get('base_price', 0):.2f}\n"
                "─" * 25 + "\n"
            )
        
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (результаты обрезаны)"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_products_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await search_message.reply_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"In-stock search error: {e}")
        await search_message.reply_text("❌ Ошибка при поиске товаров в наличии")
    
    return GET_PRODUCTS_MENU

async def get_thermocup_by_id_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать получение термокружки по ID"""
    query = update.callback_query
    await query.answer()
    
    # ДОБАВЬ ЭТУ СТРОЧКУ ↓
    context.user_data['request_type'] = 'thermocup'
    
    await query.reply_text(
        "☕ **Получить термокружку по ID**\n\n"
        "Введите ID термокружки:"
    )
    
    return ENTER_PRODUCT_ID

async def get_product_by_id_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать получение продукта по ID"""
    query = update.callback_query
    await query.answer()
    
    # ДОБАВЬ ЭТУ СТРОЧКУ ↓
    context.user_data['request_type'] = 'product'
    
    await query.reply_text(
        "🆔 **Получить продукт по ID**\n\n"
        "Введите ID продукта:"
    )
    
    return ENTER_PRODUCT_ID

async def handle_product_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать ввод ID (универсальный обработчик)"""
    try:
        product_id = int(update.message.text)
        request_type = context.user_data.get('request_type', 'product')
        
        if request_type == 'thermocup':
            product = await api_client.get_thermocup_by_id(product_id)
            product_type = "термокружка"
            emoji = "☕"
        else:
            product = await api_client.get_product_by_id(product_id)
            product_type = "продукт"
            emoji = "🆔"
        
        if not product:
            await update.message.reply_text(f"❌ {product_type.capitalize()} с ID {product_id} не найден")
            return await get_products_menu_from_message(update, context)
        
        message = f"{emoji} {product_type.capitalize()} ID {product_id}:\n\n"
        for key, value in product.items():
            message += f"{key}: {value}\n"
        
        message = truncate_message(message)
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_products_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите числовой ID")
        return ENTER_PRODUCT_ID
    
    # Очищаем тип запроса
    context.user_data.pop('request_type', None)
    
    return GET_PRODUCTS_MENU

# ===== ДОБАВИТЬ ПРОДУКТЫ =====
async def add_products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Меню добавления продуктов"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("☕ Добавить термокружку", callback_data="add_thermocup")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.reply_text(
        "➕ **Добавить продукты**\nВыберите тип продукта:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return ADD_PRODUCT_MENU

async def add_thermocup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать добавление термокружки"""
    query = update.callback_query
    await query.answer()
    
    await query.reply_text(
        "☕ **Добавить новую термокружку**\n\n"
        "Введите данные в формате:\n"
        "`Название | Категория ID | Цена | Количество | Склад ID | Объем(мл) | Цвет | Бренд`\n\n"
        "Пример:\n"
        "`Stanley Classic | 1 | 45.99 | 100 | 1 | 500 | Черный | Stanley`\n\n"
        "Обязательные поля: Название, Категория ID, Цена, Количество",
        parse_mode='Markdown'
    )
    
    return ENTER_THERMOCUP_DATA

async def add_thermocup_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать ввод данных термокружки"""
    user_input = update.message.text
    parts = [part.strip() for part in user_input.split('|')]
    
    if len(parts) < 4:
        await update.message.reply_text(
            "❌ Неверный формат. Нужно минимум 4 поля:\n"
            "`Название | Категория ID | Цена | Количество`"
        )
        return ENTER_THERMOCUP_DATA
    
    try:
        thermocup_data = {
            "name": parts[0],
            "category_id": int(parts[1]),
            "base_price": float(parts[2]),
            "initial_quantity": int(parts[3]),
            "warehouse_id": int(parts[4]) if len(parts) > 4 else 1,
            "path_to_photo": parts[5] if len(parts) > 5 else "",
            "attributes": {
                "volume_ml": int(parts[6]) if len(parts) > 6 else 500,
                "color": parts[7] if len(parts) > 7 else "Черный",
                "brand": parts[8] if len(parts) > 8 else "Unknown",
                "model": parts[0],
                "is_hermetic": True,
                "material": "Нержавеющая сталь"
            }
        }
    except (ValueError, IndexError) as e:
        await update.message.reply_text(f"❌ Ошибка в данных: {e}")
        return ENTER_THERMOCUP_DATA
    
    result = await api_client.create_thermocup(thermocup_data)
    
    if result:
        await update.message.reply_text(
            f"✅ Термокружка успешно создана!\n"
            f"ID: {result.get('id', 'N/A')}\n"
            f"Название: {result.get('name', thermocup_data['name'])}"
        )
    else:
        await update.message.reply_text("❌ Ошибка при создании термокружки")
    
    return await add_products_menu_from_message(update, context)

# ===== ОБНОВИТЬ ПРОДУКТЫ =====
async def update_products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Меню обновления продуктов"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✏️ Обновить термокружку", callback_data="update_thermocup")],
        [InlineKeyboardButton("📦 Обновить резерв", callback_data="update_reserved")],
        [InlineKeyboardButton("🏭 Обновить склад", callback_data="update_stock")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.reply_text(
        "🔄 **Обновить продукты**\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return UPDATE_PRODUCT_MENU

async def update_thermocup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать обновление термокружки"""
    query = update.callback_query
    await query.answer()
    
    await query.reply_text(
        "✏️ **Обновить термокружку**\n\n"
        "Введите ID термокружки для обновления:"
    )
    
    return ENTER_PRODUCT_ID

async def update_thermocup_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать обновление термокружки"""
    try:
        product_id = int(update.message.text)
        context.user_data['update_thermocup_id'] = product_id
        
        await update.message.reply_text(
            f"✏️ **Обновление термокружки ID {product_id}**\n\n"
            "Введите новые данные в формате:\n"
            "`Название | Цена | SKU | Активен(true/false)`\n\n"
            "Пример:\n"
            "`Stanley New | 49.99 | STAN-002 | true`\n\n"
            "Все поля опциональны - можно оставить пустыми",
            parse_mode='Markdown'
        )
        
        return ENTER_UPDATE_DATA
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите числовой ID")
        return ENTER_PRODUCT_ID

async def update_thermocup_data_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать ввод данных для обновления"""
    user_input = update.message.text
    parts = [part.strip() for part in user_input.split('|')]
    
    product_id = context.user_data.get('update_thermocup_id')
    
    if not product_id:
        await update.message.reply_text("❌ Ошибка: ID продукта не найден")
        return await update_products_menu_from_message(update, context)
    
    update_data = {}
    
    try:
        if len(parts) > 0 and parts[0]:
            update_data['name'] = parts[0]
        if len(parts) > 1 and parts[1]:
            update_data['base_price'] = float(parts[1])
        if len(parts) > 2 and parts[2]:
            update_data['sku'] = parts[2]
        if len(parts) > 3 and parts[3]:
            update_data['is_active'] = parts[3].lower() == 'true'
    except ValueError as e:
        await update.message.reply_text(f"❌ Ошибка в данных: {e}")
        return ENTER_UPDATE_DATA
    
    result = await api_client.update_thermocup(product_id, update_data)
    
    if result:
        await update.message.reply_text(
            f"✅ Термокружка ID {product_id} успешно обновлена!\n"
            f"Измененные поля: {', '.join(update_data.keys())}"
        )
    else:
        await update.message.reply_text("❌ Ошибка при обновлении термокружки")
    
    return await update_products_menu_from_message(update, context)

async def update_reserved_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать обновление резерва"""
    query = update.callback_query
    await query.answer()
    
    await query.reply_text(
        "📦 **Обновить количество зарезервированного товара**\n\n"
        "Введите ID продукта:"
    )
    
    return ENTER_PRODUCT_ID

async def update_reserved_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать обновление резерва"""
    try:
        product_id = int(update.message.text)
        context.user_data['update_reserved_id'] = product_id
        
        await update.message.reply_text(
            f"📦 **Обновление резерва для ID {product_id}**\n\n"
            "Введите изменение количества:\n"
            "(положительное число - прибавить, отрицательное - отнять)\n\n"
            "Пример: `10` - добавить 10 единиц\n"
            "Пример: `-5` - убрать 5 единиц"
        )
        
        return ENTER_RESERVED_QUANTITY
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите числовой ID")
        return ENTER_PRODUCT_ID

async def update_reserved_quantity_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать ввод количества для резерва"""
    try:
        quantity_change = int(update.message.text)
        product_id = context.user_data.get('update_reserved_id')
        
        if not product_id:
            await update.message.reply_text("❌ Ошибка: ID продукта не найден")
            return await update_products_menu_from_message(update, context)
        
        result = await api_client.update_thermocup_reserved(product_id, quantity_change)
        
        if result:
            await update.message.reply_text(
                f"✅ Резерв для продукта ID {product_id} обновлен!\n"
                f"Изменение: {quantity_change} единиц"
            )
        else:
            await update.message.reply_text("❌ Ошибка при обновлении резерва")
    
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите целое число")
        return ENTER_RESERVED_QUANTITY
    
    return await update_products_menu_from_message(update, context)

async def update_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать обновление склада"""
    query = update.callback_query
    await query.answer()
    
    await query.reply_text(
        "🏭 **Обновить количество товара на складе**\n\n"
        "Введите ID продукта:"
    )
    
    return ENTER_PRODUCT_ID

async def update_stock_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать обновление склада"""
    try:
        product_id = int(update.message.text)
        context.user_data['update_stock_id'] = product_id
        
        await update.message.reply_text(
            f"🏭 **Обновление склада для ID {product_id}**\n\n"
            "Введите ID склада:"
        )
        
        return ENTER_WAREHOUSE_ID
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите числовой ID")
        return ENTER_PRODUCT_ID

async def update_stock_warehouse_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать ввод ID склада"""
    try:
        warehouse_id = int(update.message.text)
        context.user_data['update_stock_warehouse_id'] = warehouse_id
        
        product_id = context.user_data.get('update_stock_id')
        
        await update.message.reply_text(
            f"🏭 **Обновление склада {warehouse_id} для продукта {product_id}**\n\n"
            "Введите изменение количества:\n"
            "(положительное число - прибавить, отрицательное - отнять)"
        )
        
        return ENTER_STOCK_QUANTITY
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите числовой ID склада")
        return ENTER_WAREHOUSE_ID

async def update_stock_quantity_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать ввод количества для склада"""
    try:
        quantity_change = int(update.message.text)
        product_id = context.user_data.get('update_stock_id')
        warehouse_id = context.user_data.get('update_stock_warehouse_id')
        
        if not product_id or not warehouse_id:
            await update.message.reply_text("❌ Ошибка: данные не найдены")
            return await update_products_menu_from_message(update, context)
        
        result = await api_client.update_thermocup_stock(product_id, warehouse_id, quantity_change)
        
        if result:
            await update.message.reply_text(
                f"✅ Склад обновлен!\n"
                f"Продукт ID: {product_id}\n"
                f"Склад ID: {warehouse_id}\n"
                f"Изменение: {quantity_change} единиц"
            )
        else:
            await update.message.reply_text("❌ Ошибка при обновлении склада")
    
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите целое число")
        return ENTER_STOCK_QUANTITY
    
    return await update_products_menu_from_message(update, context)

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
async def get_products_menu_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вернуться в меню продуктов из сообщения"""
    keyboard = [
        [InlineKeyboardButton("📋 Все продукты", callback_data="all_products")],
        [InlineKeyboardButton("🔍 Поиск по названию", callback_data="search_products")],
        [InlineKeyboardButton("🆔 По ID продукта", callback_data="by_id")],
        [InlineKeyboardButton("☕ Термокружка по ID", callback_data="thermocup_by_id")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📦 **Получить продукты**\nВыберите тип запроса:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return GET_PRODUCTS_MENU

async def add_products_menu_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вернуться в меню добавления из сообщения"""
    keyboard = [
        [InlineKeyboardButton("☕ Добавить термокружку", callback_data="add_thermocup")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "➕ **Добавить продукты**\nВыберите тип продукта:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return ADD_PRODUCT_MENU

async def update_products_menu_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вернуться в меню обновления из сообщения"""
    keyboard = [
        [InlineKeyboardButton("✏️ Обновить термокружку", callback_data="update_thermocup")],
        [InlineKeyboardButton("📦 Обновить резерв", callback_data="update_reserved")],
        [InlineKeyboardButton("🏭 Обновить склад", callback_data="update_stock")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔄 **Обновить продукты**\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return UPDATE_PRODUCT_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменить текущую операцию"""
    await update.message.reply_text("Операция отменена.")
    return await back_to_main_from_message(update, context)

async def back_to_main_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вернуться в главное меню из сообщения"""
    keyboard = [
        [InlineKeyboardButton("📦 Получить продукты", callback_data="get_products")],
        [InlineKeyboardButton("➕ Добавить продукты", callback_data="add_products")],
        [InlineKeyboardButton("🔄 Обновить продукты", callback_data="update_products")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏭 Главное меню управления складом\nВыберите действие:",
        reply_markup=reply_markup
    )
    
    return MAIN_MENU

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже."
        )