#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы системы потоковой передачи файлов
"""

import asyncio
import httpx
import json

async def test_api():
    """Тестируем API endpoints"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("🧪 Тестирование API endpoints...")
        
        # Тест 1: Получение списка книг для нового пользователя
        print("\n1. Тестируем получение книг для нового пользователя (ID: 999999999)")
        try:
            response = await client.get(f"{base_url}/api/books?user_id=999999999")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Получен список книг: {len(data['books'])} книг")
                print(f"   Данные: {data}")
            else:
                print(f"❌ Ошибка: {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
        
        # Тест 2: Добавление тестового файла
        print("\n2. Тестируем добавление тестового файла")
        try:
            test_file_info = {
                "file_id": "test_file_id_123",
                "file_name": "test_book.pdf",
                "file_size": 1024000,
                "mime_type": "application/pdf"
            }
            
            response = await client.post(
                f"{base_url}/api/add-file",
                json={
                    "user_id": 999999999,
                    "file_info": test_file_info
                }
            )
            
            if response.status_code == 200:
                print("✅ Тестовый файл успешно добавлен")
            else:
                print(f"❌ Ошибка добавления файла: {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        # Тест 3: Проверяем, что файл появился в списке
        print("\n3. Проверяем, что файл появился в списке")
        try:
            response = await client.get(f"{base_url}/api/books?user_id=999999999")
            if response.status_code == 200:
                data = response.json()
                books = data['books']
                print(f"✅ Найдено книг: {len(books)}")
                for book in books:
                    print(f"   - {book['name']} (ID: {book['file_id']})")
            else:
                print(f"❌ Ошибка: {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        # Тест 4: Проверяем простую страницу
        print("\n4. Тестируем простую страницу")
        try:
            response = await client.get(f"{base_url}/simple?user_id=999999999")
            if response.status_code == 200:
                print("✅ Простая страница загружается")
                # Проверяем, что в HTML есть информация о книгах
                html_content = response.text
                if "test_book.pdf" in html_content:
                    print("✅ Тестовая книга найдена на странице")
                else:
                    print("⚠️ Тестовая книга не найдена на странице")
            else:
                print(f"❌ Ошибка: {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестирования системы потоковой передачи файлов")
    print("=" * 60)
    asyncio.run(test_api())
    print("=" * 60)
    print("✅ Тестирование завершено")
