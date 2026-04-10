\c library_db;

CREATE TABLE authors (
    authors_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birth_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE genres (
    genres_id SERIAL PRIMARY KEY,
    genre_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE books (
    books_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    authors_id INTEGER REFERENCES authors(authors_id) ON DELETE CASCADE,
    genres_id INTEGER REFERENCES genres(genres_id) ON DELETE SET NULL,
    isbn VARCHAR(20) UNIQUE,
    publication_year INTEGER,
    available_copies INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE book_loans (
    loans_id SERIAL PRIMARY KEY,
    books_id INTEGER REFERENCES books(books_id) ON DELETE CASCADE,
    borrower_name VARCHAR(200) NOT NULL,
    loan_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    status VARCHAR(20) DEFAULT 'borrowed' CHECK (status IN ('borrowed', 'returned', 'overdue'))
);

CREATE INDEX idx_books_author ON books(authors_id);
CREATE INDEX idx_books_genre ON books(genres_id);
CREATE INDEX idx_loans_book ON book_loans(books_id);
CREATE INDEX idx_loans_status ON book_loans(status);