# api_client.py
import aiohttp
import asyncio
from typing import Optional, Dict, List
import logging
from config import Config

logger = logging.getLogger(__name__)

class WarehouseAPIClient:
    """Асинхронный клиент для работы с Warehouse API"""
    
    def __init__(self):
        self.base_url = Config.WAREHOUSE_API_URL.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Универсальный метод для выполнения запросов к API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Логируем параметры для отладки
        if 'params' in kwargs:
            logger.info(f"Request params: {kwargs['params']}")
        if 'json' in kwargs:
            logger.info(f"Request JSON: {kwargs['json']}")
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(method, url, **kwargs) as response:
                    
                    if response.status == 204:
                        return {"success": True}
                    
                    if response.status >= 400:
                        logger.error(f"API error {response.status}: {await response.text()}")
                        return None
                    
                    return await response.json()
                        
        except Exception as e:
            logger.error(f"API request error: {e}")
            return None

    # GET методы
    def _prepare_api_params(self, filters: Dict) -> Dict[str, str]:
        """Преобразует параметры фильтров в строки для API"""
        params = {}
        for key, value in filters.items():
            if value is not None:
                if isinstance(value, bool):
                    params[key] = str(value).lower()
                elif isinstance(value, (int, float)):
                    params[key] = str(value)
                else:
                    params[key] = str(value)
        return params

    async def get_products(self, **filters) -> Optional[List[Dict]]:
        """Получить список товаров с фильтрами"""
        params = self._prepare_api_params(filters)
        
        logger.info(f"Making API request to /products with params: {params}")
        result = await self._make_request("GET", "products", params=params)
        logger.info(f"API response type: {type(result)}, length: {len(result) if result else 0}")
        
        return result

    async def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Получить товар по ID"""
        return await self._make_request("GET", f"products/{product_id}")
    
    async def get_thermocup_by_id(self, product_id: int) -> Optional[Dict]:
        """Получить термокружку по ID"""
        return await self._make_request("GET", f"products/thermocups/{product_id}")
    
    # POST методы
    async def create_thermocup(self, thermocup_data: Dict) -> Optional[Dict]:
        """Создать новую термокружку"""
        return await self._make_request("POST", "products/thermocups/create", json=thermocup_data)
    
    # PUT методы
    async def update_thermocup(self, product_id: int, update_data: Dict) -> Optional[Dict]:
        """Обновить термокружку по ID"""
        return await self._make_request("PUT", f"products/thermocups/update/{product_id}", json=update_data)
    
    # PATCH методы
    async def update_thermocup_reserved(self, product_id: int, quantity_change: int) -> Optional[Dict]:
        """Обновить количество зарезервированного товара"""
        data = {"quantity_change": quantity_change}
        return await self._make_request("PATCH", f"products/thermocups/update/{product_id}/reserved", json=data)
    
    async def update_thermocup_stock(self, product_id: int, warehouse_id: int, quantity_change: int) -> Optional[Dict]:
        """Обновить количество товара на складе"""
        data = {
            "warehouse_id": warehouse_id,
            "quantity_change": quantity_change
        }
        return await self._make_request("PATCH", f"products/thermocups/update/{product_id}/stock", json=data)