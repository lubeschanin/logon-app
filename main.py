import sqlite3
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_400_BAD_REQUEST
from pydantic import BaseModel
import secrets

# Datenbankverbindung einrichten
DATABASE_URL = "data.db"


def create_tables():
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS logins (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS logoffs (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            token TEXT UNIQUE NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


create_tables()

# FastAPI-Anwendung
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


class TokenRequest(BaseModel):
    email: str


class LogData(BaseModel):
    username: str
    clientname: str
    servername: str
    time: str


def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def authenticate_token(token: str, conn: sqlite3.Connection = Depends(get_db)):
    c = conn.cursor()
    c.execute("SELECT * FROM tokens WHERE token=?", (token,))
    token_data = c.fetchone()

    if not token_data:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return token_data


def get_or_create_user(conn, username):
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()

    if not user:
        c.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()

    return user


def get_or_create_client(conn, clientname):
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE name=?", (clientname,))
    client = c.fetchone()

    if not client:
        c.execute("INSERT INTO clients (name) VALUES (?)", (clientname,))
        conn.commit()
        c.execute("SELECT * FROM clients WHERE name=?", (clientname,))
        client = c.fetchone()

    return client


def get_or_create_server(conn, servername):
    c = conn.cursor()
    c.execute("SELECT * FROM servers WHERE name=?", (servername,))
    server = c.fetchone()

    if not server:
        c.execute("INSERT INTO servers (name) VALUES (?)", (servername,))
        conn.commit()
        c.execute("SELECT * FROM servers WHERE name=?", (servername,))
        server = c.fetchone()

    return server


# Routen
@app.post("/api/log")
def log_data(data: LogData, conn: sqlite3.Connection = Depends(get_db)):
    user = get_or_create_user(conn, data.username)
    client = get_or_create_client(conn, data.clientname)
    server = get_or_create_server(conn, data.servername)

    c = conn.cursor()
    c.execute(
        "INSERT INTO logins (user_id, client_id, server_id, timestamp) VALUES (?, ?, ?, ?)",
        (user[0], client[0], server[0], data.time),
    )
    conn.commit()

    return {"message": "Data saved successfully"}


@app.post("/api/logoff")
def logoff_data(data: LogData, conn: sqlite3.Connection = Depends(get_db)):
    user = get_or_create_user(conn, data.username)
    client = get_or_create_client(conn, data.clientname)
    server = get_or_create_server(conn, data.servername)

    c = conn.cursor()
    c.execute(
        "INSERT INTO logoffs (user_id, client_id, server_id, timestamp) VALUES (?, ?, ?, ?)",
        (user[0], client[0], server[0], data.time),
    )
    conn.commit()

    return {"message": "Logoff data saved successfully"}


@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(
    request: Request,
    token_data: str = Depends(authenticate_token),
    conn: sqlite3.Connection = Depends(get_db),
):
    c = conn.cursor()
    c.execute(
        """
        SELECT users.username as username, clients.name as client_name, servers.name as server_name, logins.timestamp as login_time, MAX(logoffs.timestamp) as logoff_time
        FROM logins
        INNER JOIN users ON logins.user_id = users.id
        INNER JOIN clients ON logins.client_id = clients.id
        INNER JOIN servers ON logins.server_id = servers.id
        INNER JOIN logoffs ON logoffs.user_id = users.id AND logoffs.client_id = clients.id AND logoffs.server_id = servers.id
        WHERE logoffs.timestamp > logins.timestamp
        GROUP BY logins.id
        """
    )
    data = c.fetchall()
    columns = ["username", "client_name", "server_name", "login_time", "logoff_time"]
    data = [dict(zip(columns, row)) for row in data]

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "data": data}
    )


@app.get("/stats", response_class=HTMLResponse)
def get_stats(
    request: Request,
    token_data: str = Depends(authenticate_token),
    conn: sqlite3.Connection = Depends(get_db),
):
    c = conn.cursor()
    c.execute(
        "SELECT clients.name, COUNT(logins.id) AS usage FROM clients JOIN logins ON clients.id = logins.client_id GROUP BY clients.name ORDER BY COUNT(logins.id) DESC"
    )
    client_usage = c.fetchall()

    c.execute(
        "SELECT servers.name, COUNT(logins.id) AS usage FROM servers JOIN logins ON servers.id = logins.server_id GROUP BY servers.name ORDER BY COUNT(logins.id) DESC"
    )
    server_usage = c.fetchall()

    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "client_usage": client_usage,
            "server_usage": server_usage,
        },
    )


@app.post("/api/generate_token")
def generate_token(
    token_request: TokenRequest, conn: sqlite3.Connection = Depends(get_db)
):
    token = secrets.token_hex(32)

    c = conn.cursor()
    c.execute("SELECT * FROM tokens WHERE email=?", (token_request.email,))
    existing_email = c.fetchone()

    if existing_email:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    c.execute(
        "INSERT INTO tokens (email, token) VALUES (?, ?)",
        (
            token_request.email,
            token,
        ),
    )
    conn.commit()

    return {
        "message": "Token generated and saved in the database with the provided email"
    }
