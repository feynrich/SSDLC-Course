CREATE USER test_user WITH PASSWORD 'супер-секретный-пароль-юзера';
GRANT CONNECT ON DATABASE postgres TO test_user;
GRANT USAGE ON SCHEMA public TO test_user;