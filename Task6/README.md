# Task 4: HashiCorp Vault Integration

Это задание демонстрирует интеграцию сервиса PostgreSQL Pinger с HashiCorp Vault для безопасного хранения учетных данных базы данных.

## Структура проекта

```
Task4_Kubernetes/
├── docker-compose.yml       # Docker Compose конфигурация с Vault
├── Dockerfile              # Dockerfile для pinger сервиса
├── main.py                 # Python код с hvac клиентом Vault
├── requirements.txt        # Python зависимости
├── db_settings.json        # Настройки подключения к БД
├── .env                    # Переменные окружения
├── vault_data/             # Volume для данных Vault (создается автоматически)
├── vault_init/             # Результаты инициализации Vault (role_id, secret_id)
└── postgres_ru/            # Директория с PostgreSQL Dockerfile
```

## Архитектура

1. **Vault** - Запускается в режиме dev server
2. **vault-init** - Сервис инициализации Vault, который:
   - Включает AppRole аутентификацию
   - Создает секрет `database/creds` с логином и паролем БД
   - Создает политику `pinger-policy` для чтения секрета
   - Создает AppRole `pinger`
   - Сохраняет role_id и secret_id в файлы
3. **postgres-pinger** - Мониторинговый сервис, который:
   - Аутентифицируется в Vault через AppRole
   - Получает учетные данные БД из Vault перед каждым запросом
4. **postgres** - База данных PostgreSQL

## Запуск

1. Запустите Docker Compose:
```bash
docker-compose up -d
```

2. Проверьте статус сервисов:
```bash
docker-compose ps
```

3. Посмотрите логи сервисов:
```bash
# Все логи
docker-compose logs -f

# Только pinger
docker-compose logs -f postgres-pinger

# Только vault
docker-compose logs -f vault
```

## Настройка Vault

После запуска сервис `vault-init` автоматически:

1. Включает AppRole аутентификацию:
```bash
vault auth enable approle
```

2. Создает секрет для БД:
```bash
vault kv put database/creds username=test_user password='REDACTED__1__'
```

3. Создает политику для чтения секрета:
```hcl
path "database/data/creds" {
  capabilities = ["read"]
}
```

4. Создает AppRole:
```bash
vault write auth/approle/role/pinger policies=pinger-role token_ttl=1h token_max_ttl=4h
```

5. Сохраняет role_id и secret_id в файлы:
- `vault_init/role_id.txt`
- `vault_init/secret_id.txt`

## Получение role_id

role_id доступен в файле `vault_init/role_id.txt`:

```bash
cat vault_init/role_id.txt
```

## Тестирование

### Тест 1: Правильные учетные данные

Запустите сервисы и убедитесь, что pinger успешно подключается к БД:

```bash
docker-compose logs postgres-pinger
```

Вы должны увидеть:
```
Успешная аутентификация в Vault
Успешно получены учетные данные из Vault для пользователя: test_user
PostgreSQL version: PostgreSQL 17.x.x on x86_64-pc-linux-gnu...
```

### Тест 2: Неправильные учетные данные

Для тестирования с неправильными учетными данными:

1. Остановите сервисы:
```bash
docker-compose down
```

2. Измените секрет в Vault (или role_id/secret_id):
```bash
echo "invalid_role_id" > vault_init/role_id.txt
```

3. Запустите сервисы снова:
```bash
docker-compose up -d
```

4. Проверьте логи - должны быть ошибки аутентификации.

## Использование hvac клиента в коде

Основные функции в `main.py`:

### `get_vault_client()`
Создает клиент Vault с аутентификацией через AppRole:
- Читает `VAULT_ADDR` из переменных окружения
- Читает `role_id` и `secret_id` из файлов
- Возвращает аутентифицированный клиент Vault

### `get_db_credentials(vault_client)`
Получает учетные данные БД из Vault:
- Читает `VAULT_SECRET_PATH` из переменных окружения
- Получает секрет из KV v2 хранилища
- Возвращает username и password

### `check_postgres_version(vault_client)`
Проверяет версию PostgreSQL:
- Получает учетные данные из Vault
- Подключается к БД
- Выполняет `SELECT VERSION()`

## Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `DB_USER` | Имя пользователя PostgreSQL | postgres |
| `DB_PASSWORD` | Пароль PostgreSQL | REDACTED__1__ |
| `DB_NAME` | Имя базы данных | postgres |
| `CHECK_INTERVAL` | Интервал проверки (сек) | 30 |
| `LOG_FILE` | Путь к файлу логов | /app/logs/pinger.log |
| `VAULT_ADDR` | Адрес Vault | http://vault:8200 |
| `VAULT_ROLE_ID_FILE` | Путь к файлу с role_id | /run/secrets/vault_role_id |
| `VAULT_SECRET_ID_FILE` | Путь к файлу с secret_id | /run/secrets/vault_secret_id |
| `VAULT_SECRET_PATH` | Путь к секрету в Vault | database/creds |

## Полезные команды

### Проверить статус Vault
```bash
docker exec vault vault status
```

### Прочитать секрет из Vault
```bash
docker exec vault vault kv get database/creds
```

### Проверить AppRole
```bash
docker exec vault vault read auth/approle/role/pinger
```

### Пересоздать AppRole credentials
```bash
docker exec vault vault write -f -field=secret_id auth/approle/role/pinger/secret-id
```

## Доступ к Vault UI

Vault UI доступен по адресу: http://0.0.0.0:8200/ui

Логин для dev режима:
- Token: `dev-only-token`

## Очистка

Для остановки и удаления всех сервисов:
```bash
docker-compose down -v
```

Это также удалит volume с данными Vault и PostgreSQL.
