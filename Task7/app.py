import os
import logging
import sys
import datetime
from functools import wraps
from typing import List, Dict, Any, Optional

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-me-in-production')

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', '/app/logs/app.log')
DB_NAME = os.getenv('DB_NAME', 'library_db')
DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')

os.makedirs(os.path.dirname(LOG_FILE) if LOG_FILE else '/app/logs', exist_ok=True)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('LibraryWeb')
logger.setLevel(getattr(logging, LOG_LEVEL))

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

if LOG_FILE:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

VALID_TABLES = ['authors', 'genres', 'books', 'book_loans']

VALID_COLUMNS = {
    'authors': ['authors_id', 'first_name', 'last_name', 'birth_date', 'created_at'],
    'genres': ['genres_id', 'genre_name', 'description'],
    'books': ['books_id', 'title', 'authors_id', 'genres_id', 'isbn', 'publication_year', 'available_copies', 'created_at'],
    'book_loans': ['loans_id', 'books_id', 'borrower_name', 'loan_date', 'due_date', 'return_date', 'status']
}

TABLE_LABELS = {
    'authors': 'Авторы',
    'genres': 'Жанры',
    'books': 'Книги',
    'book_loans': 'Выдача книг'
}

TABLE_ID_COLUMNS = {
    'authors': 'authors_id',
    'genres': 'genres_id',
    'books': 'books_id',
    'book_loans': 'loans_id'
}

TABLE_FIELDS = {
    'authors': [
        {'name': 'first_name', 'label': 'Имя', 'type': 'text', 'required': True},
        {'name': 'last_name', 'label': 'Фамилия', 'type': 'text', 'required': True},
        {'name': 'birth_date', 'label': 'Дата рождения', 'type': 'date', 'required': False},
    ],
    'genres': [
        {'name': 'genre_name', 'label': 'Название жанра', 'type': 'text', 'required': True},
        {'name': 'description', 'label': 'Описание', 'type': 'textarea', 'required': False},
    ],
    'books': [
        {'name': 'title', 'label': 'Название', 'type': 'text', 'required': True},
        {'name': 'authors_id', 'label': 'ID автора', 'type': 'number', 'required': True},
        {'name': 'genres_id', 'label': 'ID жанра', 'type': 'number', 'required': False},
        {'name': 'isbn', 'label': 'ISBN', 'type': 'text', 'required': False},
        {'name': 'publication_year', 'label': 'Год публикации', 'type': 'number', 'required': False},
        {'name': 'available_copies', 'label': 'Доступные экземпляры', 'type': 'number', 'required': False},
    ],
    'book_loans': [
        {'name': 'books_id', 'label': 'ID книги', 'type': 'number', 'required': True},
        {'name': 'borrower_name', 'label': 'Имя заёмщика', 'type': 'text', 'required': True},
        {'name': 'loan_date', 'label': 'Дата выдачи', 'type': 'date', 'required': True},
        {'name': 'due_date', 'label': 'Дата возврата', 'type': 'date', 'required': True},
        {'name': 'return_date', 'label': 'Фактическая дата возврата', 'type': 'date', 'required': False},
        {'name': 'status', 'label': 'Статус', 'type': 'select', 'options': ['borrowed', 'returned', 'overdue'], 'required': False},
    ]
}

UPDATABLE_COLUMNS = {
    'authors': ['first_name', 'last_name', 'birth_date'],
    'genres': ['genre_name', 'description'],
    'books': ['title', 'authors_id', 'genres_id', 'isbn', 'publication_year', 'available_copies'],
    'book_loans': ['borrower_name', 'loan_date', 'due_date', 'return_date', 'status']
}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Необходимо войти в систему', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_db_connection():
    return psycopg2.connect(
        dbname=session.get('dbname', DB_NAME),
        user=session.get('user'),
        password=session.get('password'),
        host=session.get('host', DB_HOST),
        port=session.get('port', DB_PORT)
    )


def safe_table_name(table: str) -> Optional[str]:
    return table if table in VALID_TABLES else None


def safe_column_name(column: str, table: str = None) -> Optional[str]:
    if not column.replace('_', '').isalnum():
        return None
    if table and table in VALID_COLUMNS:
        if column not in VALID_COLUMNS[table]:
            return None
    return column


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        dbname = request.form.get('dbname', '').strip() or DB_NAME
        host = request.form.get('host', '').strip() or DB_HOST
        port = request.form.get('port', '').strip() or DB_PORT

        if not user or not password:
            flash('Введите логин и пароль', 'error')
            return render_template('login.html',
                                   db_name=dbname, db_host=host, db_port=port)

        try:
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port
            )
            conn.close()

            session['user'] = user
            session['password'] = password
            session['dbname'] = dbname
            session['host'] = host
            session['port'] = port

            logger.info(f"Успешный вход пользователя: {user}")
            return redirect(url_for('index'))

        except Exception as e:
            log_details = f"host={host}, port={port}, db={dbname}, user={user}"
            logger.warning(f"Неудачная попытка входа: {log_details} - ошибка: {e}")
            flash(f'Ошибка входа: неверные учетные данные', 'error')
            return render_template('login.html',
                                   db_name=dbname, db_host=host, db_port=port)

    return render_template('login.html',
                           db_name=DB_NAME, db_host=DB_HOST, db_port=DB_PORT)


@app.route('/logout')
def logout():
    user = session.get('user', 'unknown')
    session.clear()
    logger.info(f"Пользователь вышел: {user}")
    return redirect(url_for('login'))


@app.route('/index')
@login_required
def index():
    return render_template('index.html', tables=TABLE_LABELS)


@app.route('/view')
@app.route('/view/<table_name>')
@login_required
def view_table(table_name=None):
    if table_name and not safe_table_name(table_name):
        flash('Недопустимое имя таблицы', 'error')
        return redirect(url_for('view_table'))

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if table_name:
                cursor.execute(
                    sql.SQL("SELECT * FROM {} ORDER BY {}").format(
                        sql.Identifier(table_name),
                        sql.Identifier(TABLE_ID_COLUMNS[table_name])
                    )
                )
                records = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return render_template('view_table.html',
                                       table_name=table_name,
                                       table_label=TABLE_LABELS[table_name],
                                       columns=columns,
                                       records=records,
                                       id_column=TABLE_ID_COLUMNS[table_name])

            all_data = {}
            for tbl in VALID_TABLES:
                cursor.execute(
                    sql.SQL("SELECT * FROM {} ORDER BY {} LIMIT 50").format(
                        sql.Identifier(tbl),
                        sql.Identifier(TABLE_ID_COLUMNS[tbl])
                    )
                )
                all_data[tbl] = {
                    'records': cursor.fetchall(),
                    'columns': [desc[0] for desc in cursor.description]
                }
            conn.close()
            return render_template('view_all.html',
                                   tables=TABLE_LABELS,
                                   all_data=all_data,
                                   id_columns=TABLE_ID_COLUMNS)
    except Exception as e:
        logger.error(f"Ошибка при просмотре таблиц: {e}")
        flash(f'Ошибка при чтении данных: {e}', 'error')
        return redirect(url_for('index'))


@app.route('/view/<table_name>/<int:record_id>')
@login_required
def view_record(table_name, record_id):
    table = safe_table_name(table_name)
    if not table:
        flash('Недопустимое имя таблицы', 'error')
        return redirect(url_for('view_table'))

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            id_col = TABLE_ID_COLUMNS[table]
            cursor.execute(
                sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                    sql.Identifier(table),
                    sql.Identifier(id_col)
                ),
                (record_id,)
            )
            record = cursor.fetchone()
            conn.close()

            if not record:
                flash('Запись не найдена', 'error')
                return redirect(url_for('view_table', table_name=table))

            return render_template('view_record.html',
                                   table_name=table,
                                   table_label=TABLE_LABELS[table],
                                   record=record,
                                   id_column=id_col)
    except Exception as e:
        logger.error(f"Ошибка при просмотре записи: {e}")
        flash(f'Ошибка: {e}', 'error')
        return redirect(url_for('view_table', table_name=table))


@app.route('/add', methods=['GET', 'POST'])
@app.route('/add/<table_name>', methods=['GET', 'POST'])
@login_required
def add_record(table_name=None):
    if request.method == 'POST':
        table = request.form.get('table_name') or table_name
        if not table or not safe_table_name(table):
            flash('Недопустимое имя таблицы', 'error')
            return redirect(url_for('add_record'))

        data = {}
        for field in TABLE_FIELDS[table]:
            val = request.form.get(field['name'], '').strip()
            if val:
                if field['type'] == 'number':
                    data[field['name']] = int(val)
                else:
                    data[field['name']] = val
            elif field['required']:
                flash(f'Поле "{field["label"]}" обязательно для заполнения', 'error')
                return render_template('add_record.html',
                                       table_name=table,
                                       table_label=TABLE_LABELS[table],
                                       fields=TABLE_FIELDS[table])

        if not data:
            flash('Нет данных для добавления', 'error')
            return render_template('add_record.html',
                                   table_name=table,
                                   table_label=TABLE_LABELS[table],
                                   fields=TABLE_FIELDS[table])

        safe_data = {}
        for col, val in data.items():
            sc = safe_column_name(col, table)
            if sc:
                safe_data[sc] = val

        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                columns_sql = sql.SQL(', ').join(map(sql.Identifier, safe_data.keys()))
                placeholders = sql.SQL(', ').join([sql.Placeholder()] * len(safe_data))
                id_col = TABLE_ID_COLUMNS[table]

                query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING {}").format(
                    sql.Identifier(table),
                    columns_sql,
                    placeholders,
                    sql.Identifier(id_col)
                )
                cursor.execute(query, list(safe_data.values()))
                new_id = cursor.fetchone()[0]
                conn.commit()
                conn.close()

                logger.info(f"Вставлена запись в {table}: id={new_id}")
                flash(f'Запись успешно добавлена (ID: {new_id})', 'success')
                return redirect(url_for('view_table', table_name=table))

        except Exception as e:
            logger.error(f"Ошибка при вставке в {table}: {e}")
            flash(f'Ошибка при добавлении: {e}', 'error')
            return render_template('add_record.html',
                                   table_name=table,
                                   table_label=TABLE_LABELS[table],
                                   fields=TABLE_FIELDS[table])

    if table_name:
        if not safe_table_name(table_name):
            flash('Недопустимое имя таблицы', 'error')
            return redirect(url_for('add_record'))
        return render_template('add_record.html',
                               table_name=table_name,
                               table_label=TABLE_LABELS[table_name],
                               fields=TABLE_FIELDS[table_name])

    return render_template('add_record.html', tables=TABLE_LABELS, fields_map=TABLE_FIELDS)


@app.route('/update', methods=['GET', 'POST'])
@app.route('/update/<table_name>', methods=['GET', 'POST'])
@login_required
def update_record(table_name=None):
    if request.method == 'POST':
        action = request.form.get('action', 'load')

        if action == 'load':
            table = request.form.get('table_name', '').strip()
            record_id = request.form.get('record_id', '').strip()

            if not table or not safe_table_name(table):
                flash('Выберите таблицу', 'error')
                return redirect(url_for('update_record'))
            if not record_id or not record_id.isdigit():
                flash('Введите корректный ID', 'error')
                return redirect(url_for('update_record', table_name=table))

            try:
                conn = get_db_connection()
                id_col = TABLE_ID_COLUMNS[table]
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                            sql.Identifier(table),
                            sql.Identifier(id_col)
                        ),
                        (int(record_id),)
                    )
                    record = cursor.fetchone()
                conn.close()

                if not record:
                    flash(f'Запись с ID {record_id} не найдена', 'error')
                    return redirect(url_for('update_record', table_name=table))

                updatable = UPDATABLE_COLUMNS[table]
                field_defs = [f for f in TABLE_FIELDS[table] if f['name'] in updatable]

                return render_template('update_form.html',
                                       table_name=table,
                                       table_label=TABLE_LABELS[table],
                                       record=record,
                                       record_id=record_id,
                                       id_column=id_col,
                                       fields=field_defs)

            except Exception as e:
                logger.error(f"Ошибка загрузки записи: {e}")
                flash(f'Ошибка: {e}', 'error')
                return redirect(url_for('update_record', table_name=table))

        elif action == 'update':
            table = request.form.get('table_name', '').strip()
            record_id = request.form.get('record_id', '').strip()

            if not table or not safe_table_name(table):
                flash('Ошибка: неверная таблица', 'error')
                return redirect(url_for('update_record'))

            updates = {}
            updatable = UPDATABLE_COLUMNS.get(table, [])
            for field in TABLE_FIELDS[table]:
                if field['name'] not in updatable:
                    continue
                val = request.form.get(field['name'], '').strip()
                if val:
                    if field['type'] == 'number':
                        updates[field['name']] = int(val)
                    else:
                        updates[field['name']] = val

            if not updates:
                flash('Нет данных для обновления', 'error')
                return redirect(url_for('update_record', table_name=table))

            safe_updates = {}
            for col, val in updates.items():
                sc = safe_column_name(col, table)
                if sc:
                    safe_updates[sc] = val

            try:
                conn = get_db_connection()
                with conn.cursor() as cursor:
                    set_clause = sql.SQL(", ").join(
                        sql.SQL("{} = %s").format(sql.Identifier(col))
                        for col in safe_updates.keys()
                    )
                    id_col = TABLE_ID_COLUMNS[table]
                    query = sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
                        sql.Identifier(table),
                        set_clause,
                        sql.Identifier(id_col)
                    )
                    params = list(safe_updates.values()) + [int(record_id)]
                    cursor.execute(query, params)
                    conn.commit()
                    conn.close()

                    logger.info(f"Обновлена запись {record_id} в {table}")
                    flash(f'Запись ID {record_id} успешно обновлена', 'success')
                    return redirect(url_for('view_table', table_name=table))

            except Exception as e:
                logger.error(f"Ошибка обновления: {e}")
                flash(f'Ошибка при обновлении: {e}', 'error')
                return redirect(url_for('update_record', table_name=table))

    if table_name:
        if not safe_table_name(table_name):
            flash('Недопустимое имя таблицы', 'error')
            return redirect(url_for('update_record'))
        return render_template('update_record.html',
                               table_name=table_name,
                               table_label=TABLE_LABELS[table_name])

    return render_template('update_record.html', tables=TABLE_LABELS)


@app.route('/api/tables/<table_name>')
@login_required
def api_table_data(table_name):
    table = safe_table_name(table_name)
    if not table:
        return jsonify({'error': 'Invalid table'}), 400

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                sql.SQL("SELECT * FROM {} ORDER BY {}").format(
                    sql.Identifier(table),
                    sql.Identifier(TABLE_ID_COLUMNS[table])
                )
            )
            records = cursor.fetchall()
        conn.close()
        return jsonify({'records': records})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
