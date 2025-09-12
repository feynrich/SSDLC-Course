import json
import getpass
import psycopg2

def load_db_config(filename):
    with open(filename, "r") as f:
        return json.load(f)

def main():
    config = load_db_config('db_settings.json')

    login = input("Введите логин для подключения к БД: ")
    password = getpass.getpass("Введите пароль: ")

    try:
        with psycopg2.connect(
            host=config["host"],
            port=config["port"],
            dbname=config["dbname"],
            user=login,
            password=password
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION();")
                version = cur.fetchone()
                print("PostgreSQL version:", version[0])
    except Exception as e:
        print("Ошибка подключения к БД:", e)

if __name__ == "__main__":
    main()