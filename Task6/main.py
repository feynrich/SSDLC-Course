import json
import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import psycopg2
import hvac
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

def get_vault_client():
    """Создать клиент Vault с аутентификацией через AppRole"""
    logger = logging.getLogger('postgres_pinger')

    vault_addr = os.getenv('VAULT_ADDR')
    if not vault_addr:
        logger.error("Не указан VAULT_ADDR")
        return None

    role_id_file = os.getenv('VAULT_ROLE_ID_FILE')
    secret_id_file = os.getenv('VAULT_SECRET_ID_FILE')

    if not role_id_file or not secret_id_file:
        logger.error("Не указаны VAULT_ROLE_ID_FILE или VAULT_SECRET_ID_FILE")
        return None

    try:
        # Читаем role_id и secret_id из файлов
        with open(role_id_file, 'r') as f:
            role_id = f.read().strip()
        with open(secret_id_file, 'r') as f:
            secret_id = f.read().strip()

        # Создаем клиент Vault
        client = hvac.Client(url=vault_addr)

        # Аутентифицируемся через AppRole
        auth_response = client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id
        )

        if client.is_authenticated():
            logger.info("Успешная аутентификация в Vault")
            return client
        else:
            logger.error("Не удалось аутентифицироваться в Vault")
            return None

    except FileNotFoundError as e:
        logger.error(f"Файл с учетными данными Vault не найден: {e}")
        return None
    except hvac.exceptions.InvalidRequest as e:
        logger.error(f"Ошибка запроса к Vault: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при подключении к Vault: {e}")
        return None

def get_db_credentials(vault_client):
    """Получить учетные данные БД из Vault"""
    logger = logging.getLogger('postgres_pinger')

    secret_path = os.getenv('VAULT_SECRET_PATH')
    if not secret_path:
        logger.error("Не указан VAULT_SECRET_PATH")
        return None, None

    try:
        # Получаем секрет из KV v2 хранилища
        response = vault_client.secrets.kv.v2.read_secret_version(path=secret_path, mount_point='database')

        if response and 'data' in response and 'data' in response['data']:
            data = response['data']['data']
            username = data.get('username')
            password = data.get('password')

            if username and password:
                logger.info(f"Успешно получены учетные данные из Vault для пользователя: {username}")
                return username, password
            else:
                logger.error("В секрете Vault отсутствуют username или password")
                return None, None
        else:
            logger.error("Не удалось получить секрет из Vault")
            return None, None

    except hvac.exceptions.InvalidPath:
        logger.error(f"Секрет не найден по пути: {secret_path}")
        return None, None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении секрета: {e}")
        return None, None

def check_postgres_version(vault_client):
    """Проверка версии PostgreSQL с получением учетных данных из Vault"""
    logger = logging.getLogger('postgres_pinger')

    config = load_db_config('db_settings.json')

    host = config.get('DB_HOST', 'localhost')
    port = config.get('DB_PORT', '5432')
    dbname = config.get('DB_NAME', 'postgres')
    connection_timeout = config.get('CONNECTION_TIMEOUT', 30)

    # Получаем учетные данные из Vault перед каждым запросом
    user, password = get_db_credentials(vault_client)

    if not user or not password:
        logger.error("Не удалось получить учетные данные из Vault")
        return

    try:
        logger.info(f"Подключение к БД: host={host}, port={port}, db={dbname}, user={user}, pass={password}")
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

    # Инициализируем клиент Vault
    vault_client = get_vault_client()

    if not vault_client:
        logger.error("Не удалось инициализировать клиент Vault. Выход.")
        sys.exit(1)

    logger.info(f"Запуск мониторинга PostgreSQL с интервалом {interval_seconds} секунд")

    while True:
        try:
            check_postgres_version(vault_client)
        except Exception as e:
            logger.error(f"Критическая ошибка в основном цикле: {e}")

        time.sleep(interval_seconds)

if __name__ == "__main__":
    main()
