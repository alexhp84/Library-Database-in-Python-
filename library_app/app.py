from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import date

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().with_name("my_sql.db")

st.set_page_config(page_title="Library Database | Live Demo", page_icon="📚", layout="wide")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialise_database() -> None:
    """Create tables and seed examples only when both tables are empty."""
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            country TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            year INTEGER NOT NULL CHECK (year BETWEEN 1 AND 9999),
            FOREIGN KEY (author_id) REFERENCES authors(id)
        )""")
        author_count = conn.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
        book_count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        if author_count == 0 and book_count == 0:
            conn.executemany(
                "INSERT INTO authors (name, country) VALUES (?, ?)",
                [("George Orwell", "UK"), ("Gabriel García Márquez", "Colombia"), ("Haruki Murakami", "Japan")],
            )
            ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM authors")}
            conn.executemany(
                "INSERT INTO books (title, author_id, year) VALUES (?, ?, ?)",
                [("1984", ids["George Orwell"], 1949), ("Animal Farm", ids["George Orwell"], 1945),
                 ("One Hundred Years of Solitude", ids["Gabriel García Márquez"], 1967)],
            )


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def add_author(name: str, country: str) -> tuple[bool, str]:
    name, country = name.strip(), country.strip()
    if not name:
        return False, "Please enter an author name."
    try:
        with connect() as conn:
            conn.execute("INSERT INTO authors (name, country) VALUES (?, ?)", (name, country or None))
        return True, f"Added author: {name}"
    except sqlite3.IntegrityError:
        return False, "An author with that name already exists."


def add_book(title: str, author_id: int, year: int) -> tuple[bool, str]:
    title = title.strip()
    if not title:
        return False, "Please enter a book title."
    if not 1 <= year <= date.today().year:
        return False, f"Enter a publication year between 1 and {date.today().year}."
    try:
        with connect() as conn:
            conn.execute("INSERT INTO books (title, author_id, year) VALUES (?, ?, ?)", (title, author_id, year))
        return True, f"Added “{title}” to the library."
    except sqlite3.IntegrityError as exc:
        return False, f"Could not add the book: {exc}"


initialise_database()
st.title("📚 Library Database")
st.caption("An interactive Python and SQLite demonstration — browse books, explore SQL joins, and add records.")

with st.sidebar:
    st.header("Library demo")
    page = st.radio("Navigate", ["Library catalogue", "Add a book", "Manage authors", "SQL examples", "About"])
    st.divider()
    st.caption("Built with Python · Streamlit · SQLite")

metrics = query_df("SELECT (SELECT COUNT(*) FROM books) books, (SELECT COUNT(*) FROM authors) authors, (SELECT COUNT(DISTINCT author_id) FROM books) represented_authors").iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Books in catalogue", int(metrics["books"]))
c2.metric("Authors", int(metrics["authors"]))
c3.metric("Authors with books", int(metrics["represented_authors"]))
st.divider()

if page == "Library catalogue":
    st.subheader("Browse the catalogue")
    st.write("Search the collection or narrow it by author and publication year.")
    authors = query_df("SELECT id, name FROM authors ORDER BY name")
    options = {"All authors": None}
    options.update({r["name"]: int(r["id"]) for _, r in authors.iterrows()})
    a, b, c = st.columns([2, 1, 1])
    search = a.text_input("Search title or author", placeholder="e.g. Orwell")
    selected = b.selectbox("Author", list(options))
    year_filter = c.selectbox("Publication year", ["Any year", "Before 1900", "1900–1949", "1950–1999", "2000 onwards"])
    sql = """SELECT b.id, b.title AS Title, a.name AS Author,
        COALESCE(a.country, 'Not specified') AS Country, b.year AS Year
        FROM books b JOIN authors a ON a.id = b.author_id WHERE 1=1"""
    params: list = []
    if search.strip():
        sql += " AND (b.title LIKE ? OR a.name LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term])
    if options[selected] is not None:
        sql += " AND a.id = ?"
        params.append(options[selected])
    year_conditions = {"Before 1900": "b.year < 1900", "1900–1949": "b.year BETWEEN 1900 AND 1949", "1950–1999": "b.year BETWEEN 1950 AND 1999", "2000 onwards": "b.year >= 2000"}
    if year_filter != "Any year":
        sql += " AND " + year_conditions[year_filter]
    sql += " ORDER BY b.year DESC, b.title COLLATE NOCASE"
    data = query_df(sql, tuple(params))
    st.dataframe(data.drop(columns=["id"]), use_container_width=True, hide_index=True)
    st.caption(f"{len(data)} book(s) match your filters.")
    with st.expander("View the SQL behind this catalogue"):
        st.code(sql.strip(), language="sql")
        st.caption("Search values are passed as parameters rather than inserted into SQL text.")

elif page == "Add a book":
    st.subheader("Add a book")
    authors = query_df("SELECT id, name, country FROM authors ORDER BY name")
    if authors.empty:
        st.warning("Add an author first using Manage authors.")
    else:
        labels = {f'{r["name"]} ({r["country"] or "country unknown"})': int(r["id"]) for _, r in authors.iterrows()}
        with st.form("add_book_form", clear_on_submit=True):
            title = st.text_input("Book title", placeholder="Enter the title")
            author_label = st.selectbox("Author", list(labels))
            year = st.number_input("Publication year", min_value=1, max_value=date.today().year, value=2000, step=1)
            submitted = st.form_submit_button("Add book", type="primary")
        if submitted:
            ok, msg = add_book(title, labels[author_label], int(year))
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()

elif page == "Manage authors":
    st.subheader("Manage authors")
    with st.form("add_author_form", clear_on_submit=True):
        name = st.text_input("Author name", placeholder="e.g. Ursula K. Le Guin")
        country = st.text_input("Country", placeholder="Optional")
        submitted = st.form_submit_button("Add author", type="primary")
    if submitted:
        ok, msg = add_author(name, country)
        (st.success if ok else st.error)(msg)
        if ok:
            st.rerun()
    st.subheader("Current authors")
    authors = query_df("""SELECT a.id, a.name AS Author, COALESCE(a.country, 'Not specified') AS Country,
        COUNT(b.id) AS Books FROM authors a LEFT JOIN books b ON b.author_id=a.id
        GROUP BY a.id, a.name, a.country ORDER BY a.name COLLATE NOCASE""")
    st.dataframe(authors.drop(columns=["id"]), use_container_width=True, hide_index=True)

elif page == "SQL examples":
    st.subheader("Explore SQL")
    example = st.selectbox("Choose a query", ["Books published after a year", "Books with author details (INNER JOIN)", "Book count by author (LEFT JOIN)"])
    examples = {
        "Books published after a year": "SELECT title, year FROM books WHERE year > ? ORDER BY year, title",
        "Books with author details (INNER JOIN)": "SELECT b.title, a.name AS author, a.country, b.year FROM books AS b INNER JOIN authors AS a ON b.author_id=a.id ORDER BY b.title",
        "Book count by author (LEFT JOIN)": "SELECT a.name AS author, COUNT(b.id) AS book_count FROM authors AS a LEFT JOIN books AS b ON b.author_id=a.id GROUP BY a.id, a.name ORDER BY book_count DESC, a.name",
    }
    sql = examples[example]
    st.code(sql, language="sql")
    if example == "Books published after a year":
        threshold = st.slider("Publication year must be after", 1800, date.today().year, 1960)
        result = query_df(sql, (threshold,))
    else:
        result = query_df(sql)
    st.dataframe(result, use_container_width=True, hide_index=True)
    st.caption(f"{len(result)} row(s) returned.")

else:
    st.subheader("About this project")
    st.markdown("""This demo presents a small relational library database built with **Python** and **SQLite**.

**Concepts demonstrated**
- Relational tables and primary/foreign keys
- Parameterised SQL statements
- `SELECT`, filtering and `JOIN` queries
- Basic input validation and database error handling
- A browser interface built with Streamlit

The application seeds sample records only when both tables are empty. A hosted deployment needs persistent storage if changes must survive restarts.""")
    st.info("This is a portfolio demonstration, not a production library system.")

st.divider()
st.caption("Library Database demo · Python + SQLite")
