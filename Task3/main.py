import os
import logging
import sys
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import getpass

class LibraryDatabase:
    def __init__(self):
        self.connection = None
        self.setup_logging()
        
    def setup_logging(self):
        """Настройка логирования"""
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_file = os.getenv('LOG_FILE')
        
        self.logger = logging.getLogger('LibraryDB')
        self.logger.setLevel(getattr(logging, log_level))
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def connect(self, dbname: str, user: str, password: str, host: str = 'localhost', port: str = '5432'):
        """Подключение к базе данных"""
        try:
            self.connection = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port
            )
            self.logger.info("Успешное подключение к базе данных")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка подключения к базе данных: {str(e)}")
            return False
    
    def safe_column_name(self, column: str) -> str:
        """Безопасная проверка имени колонки"""
        valid_columns = {
            'authors': ['author_id', 'first_name', 'last_name', 'birth_date', 'created_at'],
            'genres': ['genre_id', 'genre_name', 'description'],
            'books': ['book_id', 'title', 'author_id', 'genre_id', 'isbn', 'publication_year', 'available_copies', 'created_at'],
            'book_loans': ['loan_id', 'book_id', 'borrower_name', 'loan_date', 'due_date', 'return_date', 'status']
        }
        
        return column if column.replace('_', '').isalnum() else None
    
    def safe_table_name(self, table: str) -> str:
        """Безопасная проверка имени таблицы"""
        valid_tables = ['authors', 'genres', 'books', 'book_loans']
        return table if table in valid_tables else None
    
    def select_all(self, table: str) -> List[Dict[str, Any]]:
        """SELECT * FROM table"""
        safe_table = self.safe_table_name(table)
        if not safe_table:
            self.logger.error(f"Недопустимое имя таблицы: {table}")
            return []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(safe_table)))
                result = cursor.fetchall()
                self.logger.info(f"Успешно получено {len(result)} записей из таблицы {table}")
                return result
        except Exception as e:
            self.logger.error(f"Ошибка при чтении таблицы {table}: {str(e)}")
            return []
    
    def select_with_filter(self, table: str, column: str, value: Any) -> List[Dict[str, Any]]:
        """SELECT * FROM table WHERE column = value"""
        safe_table = self.safe_table_name(table)
        safe_column = self.safe_column_name(column)
        
        if not safe_table or not safe_column:
            self.logger.error(f"Недопустимые параметры: таблица={table}, колонка={column}")
            return []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                query = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                    sql.Identifier(safe_table),
                    sql.Identifier(safe_column)
                )
                cursor.execute(query, (value,))
                result = cursor.fetchall()
                self.logger.info(f"Успешно получено {len(result)} записей с фильтром {column}={value}")
                return result
        except Exception as e:
            self.logger.error(f"Ошибка при фильтрации: {str(e)}")
            return []
    
    def select_with_multiple_filters(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """SELECT * FROM table WHERE col1 = val1 AND col2 = val2"""
        safe_table = self.safe_table_name(table)
        if not safe_table:
            self.logger.error(f"Недопустимое имя таблицы: {table}")
            return []
        
        safe_filters = {}
        for col, val in filters.items():
            safe_col = self.safe_column_name(col)
            if safe_col:
                safe_filters[safe_col] = val
            else:
                self.logger.error(f"Недопустимое имя колонки: {col}")
                return []
        
        if not safe_filters:
            self.logger.error("Нет допустимых фильтров")
            return []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                conditions = []
                params = []
                for col, val in safe_filters.items():
                    conditions.append(sql.SQL("{} = %s").format(sql.Identifier(col)))
                    params.append(val)
                
                query = sql.SQL("SELECT * FROM {} WHERE {}").format(
                    sql.Identifier(safe_table),
                    sql.SQL(" AND ").join(conditions)
                )
                cursor.execute(query, params)
                result = cursor.fetchall()
                self.logger.info(f"Успешно получено {len(result)} записей с множественным фильтром")
                return result
        except Exception as e:
            self.logger.error(f"Ошибка при множественной фильтрации: {str(e)}")
            return []
    
    def update_single_record(self, table: str, record_id: int, updates: Dict[str, Any]) -> bool:
        """UPDATE table SET col1 = val1, col2 = val2 WHERE id = record_id"""
        safe_table = self.safe_table_name(table)
        if not safe_table:
            self.logger.error(f"Недопустимое имя таблицы: {table}")
            return False
        
        safe_updates = {}
        for col, val in updates.items():
            safe_col = self.safe_column_name(col)
            if safe_col and safe_col != 'id' and not safe_col.endswith('_id'):
                safe_updates[safe_col] = val
        
        if not safe_updates:
            self.logger.error("Нет допустимых полей для обновления")
            return False
        
        try:
            with self.connection.cursor() as cursor:
                set_clause = sql.SQL(", ").join(
                    sql.SQL("{} = %s").format(sql.Identifier(col))
                    for col in safe_updates.keys()
                )
                
                query = sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
                    sql.Identifier(safe_table),
                    set_clause,
                    sql.Identifier(f"{table.split('_')[0]}_id")
                )
                
                params = list(safe_updates.values()) + [record_id]
                cursor.execute(query, params)
                self.connection.commit()
                self.logger.info(f"Успешно обновлена запись {record_id} в таблице {table}")
                return True
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка при обновлении записи: {str(e)}")
            return False
    
    def update_multiple_records(self, table: str, filter_column: str, filter_values: List[Any], update_column: str, update_value: Any) -> bool:
        """UPDATE table SET update_column = update_value WHERE filter_column IN (values)"""
        safe_table = self.safe_table_name(table)
        safe_filter_col = self.safe_column_name(filter_column)
        safe_update_col = self.safe_column_name(update_column)
        
        if not all([safe_table, safe_filter_col, safe_update_col]):
            self.logger.error("Недопустимые параметры для обновления")
            return False
        
        try:
            with self.connection.cursor() as cursor:
                placeholders = sql.SQL(', ').join([sql.SQL('%s')] * len(filter_values))
                
                query = sql.SQL("UPDATE {} SET {} = %s WHERE {} IN ({})").format(
                    sql.Identifier(safe_table),
                    sql.Identifier(safe_update_col),
                    sql.Identifier(safe_filter_col),
                    placeholders
                )
                
                params = [update_value] + filter_values
                cursor.execute(query, params)
                self.connection.commit()
                self.logger.info(f"Успешно обновлено {cursor.rowcount} записей")
                return True
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка при массовом обновлении: {str(e)}")
            return False
    
    def insert_single_record(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """INSERT INTO table (columns) VALUES (values) RETURNING id"""
        safe_table = self.safe_table_name(table)
        if not safe_table:
            self.logger.error(f"Недопустимое имя таблицы: {table}")
            return None
        
        safe_data = {}
        for col, val in data.items():
            safe_col = self.safe_column_name(col)
            if safe_col:
                safe_data[safe_col] = val
        
        if not safe_data:
            self.logger.error("Нет допустимых данных для вставки")
            return None
        
        try:
            with self.connection.cursor() as cursor:
                columns = sql.SQL(', ').join(map(sql.Identifier, safe_data.keys()))
                values = sql.SQL(', ').join([sql.Placeholder()] * len(safe_data))
                
                id_column = f"{table.split('_')[0]}_id"
                
                query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING {}").format(
                    sql.Identifier(safe_table),
                    columns,
                    values,
                    sql.Identifier(id_column)
                )
                
                cursor.execute(query, list(safe_data.values()))
                result = cursor.fetchone()
                self.connection.commit()
                new_id = result[0] if result else None
                self.logger.info(f"Успешно вставлена запись с ID {new_id} в таблицу {table}")
                return new_id
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка при вставке записи: {str(e)}")
            return None
    
    def insert_related_records(self, main_table: str, main_data: Dict[str, Any], 
                             related_table: str, related_data: Dict[str, Any], 
                             foreign_key: str) -> bool:
        """Вставка в основную таблицу и связанную таблицу"""
        main_id = self.insert_single_record(main_table, main_data)
        if main_id is None:
            return False
        
        related_data[foreign_key] = main_id
        
        related_id = self.insert_single_record(related_table, related_data)
        if related_id is None:
            self.connection.rollback()
            return False
        
        self.logger.info(f"Успешно вставлены связанные записи: {main_table}.id={main_id}, {related_table}.id={related_id}")
        return True
    
    def insert_multiple_records(self, table: str, data_list: List[Dict[str, Any]]) -> bool:
        """Вставка нескольких записей в одну таблицу"""
        safe_table = self.safe_table_name(table)
        if not safe_table or not data_list:
            self.logger.error("Недопустимые параметры для множественной вставки")
            return False
        
        all_keys = set()
        safe_data_list = []
        
        for data in data_list:
            safe_data = {}
            for col, val in data.items():
                safe_col = self.safe_column_name(col)
                if safe_col:
                    safe_data[safe_col] = val
                    all_keys.add(safe_col)
            safe_data_list.append(safe_data)
        
        if not safe_data_list:
            self.logger.error("Нет допустимых данных для вставки")
            return False
        
        try:
            with self.connection.cursor() as cursor:
                columns = sql.SQL(', ').join(map(sql.Identifier, all_keys))
                placeholders = sql.SQL(', ').join([sql.Placeholder()] * len(all_keys))
                
                query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                    sql.Identifier(safe_table),
                    columns,
                    placeholders
                )
                
                for data in safe_data_list:
                    ordered_data = [data.get(col) for col in all_keys]
                    cursor.execute(query, ordered_data)
                
                self.connection.commit()
                self.logger.info(f"Успешно вставлено {len(safe_data_list)} записей в таблицу {table}")
                return True
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка при множественной вставке: {str(e)}")
            return False
        
    def close(self):
        """Закрытие соединения с БД"""
        if self.connection:
            self.connection.close()
            self.logger.info("Соединение с базой данных закрыто")

class LibraryApp:
    def __init__(self):
        self.db = LibraryDatabase()
    
    def get_user_credentials(self):
        """Получение учетных данных от пользователя"""
        print("\n=== Подключение к базе данных библиотеки ===")
        dbname = input("Имя базы данных: ").strip()
        user = input("Пользователь: ").strip()
        password = getpass.getpass("Пароль: ")
        host = input("Хост [postgres]: ").strip() or 'postgres'
        port = input("Порт [5432]: ").strip() or '5432'
        
        return dbname, user, password, host, port
    
    def display_menu(self):
        """Отображение главного меню"""
        print("\n" + "="*50)
        print("СИСТЕМА УПРАВЛЕНИЯ БИБЛИОТЕКОЙ")
        print("="*50)
        print("1. Просмотр таблиц")
        print("2. Фильтрация данных")
        print("3. Обновление записей")
        print("4. Добавление записей")
        print("5. Множественная вставка")
        print("6. Вставка в связанные таблицы")
        print("0. Выход")
        print("-"*50)
    
    def display_table_menu(self):
        """Меню выбора таблицы"""
        print("\nВыберите таблицу:")
        print("1. Авторы (authors)")
        print("2. Жанры (genres)")
        print("3. Книги (books)")
        print("4. Выдача книг (book_loans)")
    
    def get_table_name(self, choice: str) -> str:
        """Получение имени таблицы по выбору"""
        tables = {
            '1': 'authors',
            '2': 'genres', 
            '3': 'books',
            '4': 'book_loans'
        }
        return tables.get(choice)
    
    def display_records(self, records: List[Dict[str, Any]]):
        """Отображение записей в читаемом формате"""
        if not records:
            print("Записи не найдены")
            return
        
        print(f"\nНайдено записей: {len(records)}")
        print("-" * 80)
        
        for i, record in enumerate(records, 1):
            print(f"Запись #{i}:")
            for key, value in record.items():
                print(f"  {key}: {value}")
            print("-" * 40)
    
    def handle_view_tables(self):
        """Обработка просмотра таблиц"""
        self.display_table_menu()
        choice = input("Выберите таблицу (1-4): ").strip()
        table = self.get_table_name(choice)
        
        if not table:
            print("Неверный выбор таблицы")
            return
        
        records = self.db.select_all(table)
        self.display_records(records)
    
    def handle_filter_data(self):
        """Обработка фильтрации данных"""
        self.display_table_menu()
        choice = input("Выберите таблицу (1-4): ").strip()
        table = self.get_table_name(choice)
        
        if not table:
            print("Неверный выбор таблицы")
            return
        
        print("\nТип фильтрации:")
        print("1. По одному значению")
        print("2. По нескольким значениям")
        filter_type = input("Выберите тип (1-2): ").strip()
        
        if filter_type == '1':
            column = input("Введите название колонки для фильтрации: ").strip()
            value = input("Введите значение для фильтрации: ").strip()
            
            records = self.db.select_with_filter(table, column, value)
            self.display_records(records)
            
        elif filter_type == '2':
            filters = {}
            print("Введите фильтры (для завершения введите пустое название колонки):")
            
            while True:
                column = input("Название колонки: ").strip()
                if not column:
                    break
                value = input("Значение: ").strip()
                filters[column] = value
            
            if filters:
                records = self.db.select_with_multiple_filters(table, filters)
                self.display_records(records)
            else:
                print("Не указаны фильтры")
        else:
            print("Неверный выбор типа фильтрации")
    
    def handle_update_records(self):
        """Обработка обновления записей"""
        self.display_table_menu()
        choice = input("Выберите таблицу (1-4): ").strip()
        table = self.get_table_name(choice)
        
        if not table:
            print("Неверный выбор таблицы")
            return
        
        print("\nТип обновления:")
        print("1. Обновление одной записи")
        print("2. Обновление нескольких записей")
        update_type = input("Выберите тип (1-2): ").strip()
        
        if update_type == '1':
            record_id = input("Введите ID записи для обновления: ").strip()
            
            if not record_id.isdigit():
                print("ID должен быть числом")
                return
            
            updates = {}
            print("Введите обновления (для завершения введите пустое название колонки):")
            
            while True:
                column = input("Название колонки: ").strip()
                if not column:
                    break
                value = input("Новое значение: ").strip()
                updates[column] = value
            
            if updates:
                success = self.db.update_single_record(table, int(record_id), updates)
                print("Запись успешно обновлена" if success else "Ошибка при обновлении записи")
            else:
                print("Не указаны обновления")
                
        elif update_type == '2':
            filter_column = input("Введите колонку для фильтрации: ").strip()
            filter_values_input = input("Введите значения для фильтрации (через запятую): ").strip()
            filter_values = [v.strip() for v in filter_values_input.split(',')]
            
            update_column = input("Введите колонку для обновления: ").strip()
            update_value = input("Введите новое значение: ").strip()
            
            success = self.db.update_multiple_records(table, filter_column, filter_values, update_column, update_value)
            print("Записи успешно обновлены" if success else "Ошибка при обновлении записей")
        else:
            print("Неверный выбор типа обновления")
    
    def handle_insert_records(self):
        """Обработка добавления записей"""
        self.display_table_menu()
        choice = input("Выберите таблицу (1-4): ").strip()
        table = self.get_table_name(choice)
        
        if not table:
            print("Неверный выбор таблицы")
            return
        
        data = {}
        print("Введите данные для новой записи (для завершения введите пустое название колонки):")
        
        while True:
            column = input("Название колонки: ").strip()
            if not column:
                break
            value = input("Значение: ").strip()
            data[column] = value
        
        if data:
            new_id = self.db.insert_single_record(table, data)
            if new_id:
                print(f"Запись успешно добавлена с ID: {new_id}")
            else:
                print("Ошибка при добавлении записи")
        else:
            print("Не указаны данные для вставки")
    
    def handle_multiple_insert(self):
        """Обработка множественной вставки"""
        self.display_table_menu()
        choice = input("Выберите таблицу (1-4): ").strip()
        table = self.get_table_name(choice)
        
        if not table:
            print("Неверный выбор таблицы")
            return
        
        data_list = []
        print("Введите данные для множественной вставки:")
        
        while True:
            print(f"\nЗапись #{len(data_list) + 1}:")
            data = {}
            
            while True:
                column = input("Название колонки (пусто для завершения записи): ").strip()
                if not column:
                    break
                value = input("Значение: ").strip()
                data[column] = value
            
            if data:
                data_list.append(data)
            else:
                break
            
            continue_insert = input("Добавить еще одну запись? (y/n): ").strip().lower()
            if continue_insert != 'y':
                break
        
        if data_list:
            success = self.db.insert_multiple_records(table, data_list)
            print(f"Успешно добавлено {len(data_list)} записей" if success else "Ошибка при добавлении записей")
        else:
            print("Не указаны данные для вставки")
    
    def handle_related_insert(self):
        """Обработка вставки в связанные таблицы"""
        print("\nВставка книги и записи о выдаче:")
        
        print("\nДанные для книги:")
        book_data = {}
        book_fields = ['title', 'authors_id', 'genres_id', 'isbn', 'publication_year', 'available_copies']
        
        for field in book_fields:
            value = input(f"{field}: ").strip()
            if value:
                book_data[field] = value
        
        print("\nДанные для выдачи книги:")
        loan_data = {}
        loan_fields = ['borrower_name', 'loan_date', 'due_date']
        
        for field in loan_fields:
            value = input(f"{field}: ").strip()
            if value:
                loan_data[field] = value
        
        if book_data and loan_data:
            success = self.db.insert_related_records(
                'books', book_data, 
                'book_loans', loan_data, 
                'book_id'
            )
            print("Связанные записи успешно добавлены" if success else "Ошибка при добавлении связанных записей")
        else:
            print("Недостаточно данных для вставки")
    
    def run(self):
        """Запуск приложения"""
        dbname, user, password, host, port = self.get_user_credentials()
        
        if not self.db.connect(dbname, user, password, host, port):
            print("Не удалось подключиться к базе данных")
            return
        
        try:
            while True:
                self.display_menu()
                choice = input("Выберите действие (0-6): ").strip()
                
                if choice == '0':
                    print("Выход из программы...")
                    break
                elif choice == '1':
                    self.handle_view_tables()
                elif choice == '2':
                    self.handle_filter_data()
                elif choice == '3':
                    self.handle_update_records()
                elif choice == '4':
                    self.handle_insert_records()
                elif choice == '5':
                    self.handle_multiple_insert()
                elif choice == '6':
                    self.handle_related_insert()
                else:
                    print("Неверный выбор. Попробуйте снова.")
                
                input("\nНажмите Enter для продолжения...")
        
        finally:
            self.db.close()

if __name__ == "__main__":
    app = LibraryApp()
    app.run()