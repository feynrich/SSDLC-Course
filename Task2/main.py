import json
import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import psycopg2
from datetime import datetime

def load_db_config(filename):
    with open(filename, "r") as f:
        return json.load(f)

def setup_logging(log_file=None):
    """Настройка системы логирования"""
    logger = logging.getLogger('postgres_pinger')
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)
    
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
    
    if log_file:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10485760, backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def check_postgres_version():
    """Проверка версии PostgreSQL"""
    logger = logging.getLogger('postgres_pinger')
    
    config = load_db_config('db_settings.json')

    host = config.get('DB_HOST', 'localhost')
    port = config.get('DB_PORT', '5432')
    dbname = config.get('DB_NAME', 'postgres')
    connection_timeout = config.get('CONNECTION_TIMEOUT', 30)

    user = os.getenv('DB_TEST_USER')
    password = os.getenv('DB_TEST_PASSWORD')
    
    if not user or not password:
        logger.error("Не указаны логин или пароль для подключения к БД")
        return
    
    try:
        with psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=connection_timeout
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION();")
                version = cur.fetchone()
                
                if version and len(version) > 0:
                    version_str = str(version[0])
       
                    if 'PostgreSQL' in version_str:
                        logger.info(f"PostgreSQL version: {version_str}")
                    else:
                        logger.info(f"Нестандартный ответ версии: {version_str}")
                else:
                    logger.info("Пустой ответ на запрос версии")
                    
    except psycopg2.OperationalError as e:
        logger.error(f"Ошибка подключения к БД: {e}")
    except psycopg2.Error as e:
        logger.error(f"Ошибка PostgreSQL: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")

def main():
    """Основная функция приложения"""

    log_file = os.getenv('LOG_FILE')
    logger = setup_logging(log_file)

    try:
        interval_seconds = int(os.getenv('CHECK_INTERVAL', 300))
    except ValueError:
        logger.error("Некорректное значение интервала, используется значение по умолчанию: 5 минут")
        interval_seconds = 300
    
    logger.info(f"Запуск мониторинга PostgreSQL с интервалом {interval_seconds} секунд")
    
    while True:
        try:
            check_postgres_version()
        except Exception as e:
            logger.error(f"Критическая ошибка в основном цикле: {e}")
        
        time.sleep(interval_seconds)

if __name__ == "__main__":
    main()