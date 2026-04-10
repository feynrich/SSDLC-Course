\c library_db;

CREATE USER library_user WITH PASSWORD 'user_password123';

GRANT CONNECT ON DATABASE library_db TO library_user;
GRANT USAGE ON SCHEMA public TO library_user;

GRANT SELECT, INSERT, UPDATE ON authors TO library_user;
GRANT SELECT, INSERT, UPDATE ON genres TO library_user;
GRANT SELECT, INSERT, UPDATE ON books TO library_user;
GRANT SELECT, INSERT, UPDATE ON book_loans TO library_user;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO library_user;