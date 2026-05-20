from pprint import pprint
from db import run_query_select, run_update_query

def create_tables ():

    run_update_query("""CREATE TABLE IF NOT EXISTS authors (
        id        INTEGER PRIMARY KEY,
        name TEXT    NOT NULL,
        country    TEXT   )""")

    run_update_query("""CREATE TABLE IF NOT EXISTS books (
        id        INTEGER PRIMARY KEY,
        title       TEXT    NOT NULL,
        author_id    INTEGER,
        year     INTEGER    NOT NULL,
        FOREIGN KEY (author_id) REFERENCES authors(id))""")

def insert_data ():
    run_update_query("INSERT INTO authors (name, country) VALUES (?, ?)", ("George Orwell", "UK"))
    run_update_query("INSERT INTO authors (name, country) VALUES (?, ?)", ("Gabriel García Márquez", "Colombia"))
    run_update_query("INSERT INTO authors (name, country) VALUES (?, ?)", ("Haruki Murakami", "Japan"))

    run_update_query("INSERT INTO books (title, author_id, year) VALUES (?, ?, ?)", ("1984", 1, 1949))
    run_update_query("INSERT INTO books (title, author_id, year) VALUES (?, ?, ?)", ("Animal Farm", 1, 1945))
    run_update_query("INSERT INTO books (title, author_id, year) VALUES (?, ?, ?)", ("One Hundred Years of Solitude", 2, 1967))

def select_query ():
    books_result = run_query_select("""SELECT title FROM books WHERE year > 1960""")
    pprint(books_result)

def join_query ():
    join_result = run_query_select("""SELECT b.title, a.name FROM books b INNER JOIN authors a ON b.author_id = a.id""")
    for row in join_result:
        pprint(f"{row['title']} - {row['name']}")

def add_book ():
    try:
        title = input('What is the book title?')
        '''
        to add the author by name per a real-life example, the below can be used. 
        Per task, I am asking here for the author_id, and it will work then ask for the author name if not exist and add it
        author_name = input('What is the authors name ?')
        result = run_query_select("SELECT id FROM authors WHERE name = ?", (author_name,))
        if not result:
            author_name = input('What is the authors name ?')
            country = input("Enter author country: ")
            run_update_query("INSERT INTO authors (id, name, country) VALUES (?, ?, ?)", (author_id, author_name, country))
            print(f"New author '{author_name}' added.")
        else:
            author_id = result[0]["id"]
        '''
        author_id = int(input('What is the author id?' ))
        result = run_query_select("SELECT id FROM authors WHERE id = ?", (author_id,))
        if not result:
            author_name = input('Author not found. What is the authors name? ')
            country = input("Enter author country: ")
            run_update_query("INSERT INTO authors (id, name, country) VALUES (?, ?, ?)", (author_id, author_name, country))
            pprint(f"New author '{author_name}' added.")
        else:
            pprint(f"Author found")
        while True:
            try:
                year = int(input('What is the book year?'))
                break
            except ValueError:
                pprint("Invalid input. Please try again.")

        run_update_query("INSERT INTO books (title, author_id, year) VALUES (?, ?, ?)", (title, author_id, year))
        pprint(f"'{title}' added successfully.")

    except Exception as e:
        pprint(f"Something went wrong: {e}")

create_tables()
try:
    insert_data()
except Exception as e:
    print(f"Initial data insertion skipped or already exists: {e}")
join_query()
add_book()