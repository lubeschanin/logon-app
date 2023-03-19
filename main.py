from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

# Datenbankverbindung einrichten
DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Datenbank-Modelle
class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    logins = relationship("Login", back_populates="client")
    logoffs = relationship("Logoff", back_populates="client")


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    logins = relationship("Login", back_populates="server")
    logoffs = relationship("Logoff", back_populates="server")


class Login(Base):
    __tablename__ = "logins"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    server_id = Column(Integer, ForeignKey("servers.id"))
    timestamp = Column(String, index=True)

    client = relationship("Client", back_populates="logins")
    server = relationship("Server", back_populates="logins")


class Logoff(Base):
    __tablename__ = "logoffs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    server_id = Column(Integer, ForeignKey("servers.id"))
    timestamp = Column(String, index=True)

    client = relationship("Client", back_populates="logoffs")
    server = relationship("Server", back_populates="logoffs")


Base.metadata.create_all(bind=engine)

# FastAPI-Anwendung
app = FastAPI(
    version="0.1.3",
    description="""Diese FastAPI-Anwendung speichert Clientnamen, 
              Servernamen, Login- und Logoff-Zeitstempel in einer SQLite3-Datenbank. 
              Die Anwendung stellt zwei API-Endpunkte bereit.""",
    contact={"Email": "vit@lij.de"},
    title="Logon-API",
    license_info={"name": "GNU General Public License version 2 (GPLv2) "},
)
templates = Jinja2Templates(directory="templates")


class LogData(BaseModel):
    clientname: str
    servername: str
    time: str


@app.post("/api/log")
def log_data(data: LogData):
    session = SessionLocal()
    client = session.query(Client).filter(Client.name == data.clientname).first()

    if not client:
        client = Client(name=data.clientname)
        session.add(client)
        session.commit()
        session.refresh(client)

    server = session.query(Server).filter(Server.name == data.servername).first()

    if not server:
        server = Server(name=data.servername)
        session.add(server)
        session.commit()
        session.refresh(server)

    login = Login(client_id=client.id, server_id=server.id, timestamp=data.time)
    session.add(login)
    session.commit()
    session.refresh(login)

    return {"message": "Data saved successfully"}


@app.post("/api/logoff")
def logoff_data(data: LogData):
    session = SessionLocal()
    client = session.query(Client).filter(Client.name == data.clientname).first()

    if not client:
        client = Client(name=data.clientname)
        session.add(client)
        session.commit()
        session.refresh(client)

    server = session.query(Server).filter(Server.name == data.servername).first()

    if not server:
        server = Server(name=data.servername)
        session.add(server)
        session.commit()
        session.refresh(server)
    logoff = Logoff(client_id=client.id, server_id=server.id, timestamp=data.time)
    session.add(logoff)
    session.commit()
    session.refresh(logoff)

    return {"message": "Logoff data saved successfully"}


@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    session = SessionLocal()

    subquery_login = (
        session.query(
            Login.client_id,
            Login.server_id,
            func.max(Login.timestamp).label("latest_login_time"),
        )
        .group_by(Login.client_id, Login.server_id)
        .subquery()
    )

    subquery_logoff = (
        session.query(
            Logoff.client_id,
            Logoff.server_id,
            func.max(Logoff.timestamp).label("latest_logoff_time"),
        )
        .group_by(Logoff.client_id, Logoff.server_id)
        .subquery()
    )

    data = (
        session.query(
            Client.name.label("client_name"),
            Server.name.label("server_name"),
            subquery_login.c.latest_login_time.label("login_time"),
            subquery_logoff.c.latest_logoff_time.label("logoff_time"),
        )
        .select_from(Client)
        .join(subquery_login, Client.id == subquery_login.c.client_id)
        .join(Server, Server.id == subquery_login.c.server_id)
        .join(
            subquery_logoff,
            (Client.id == subquery_logoff.c.client_id)
            & (Server.id == subquery_logoff.c.server_id),
        )
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "data": data}
    )


# uvicorn main:app --host 0.0.0.0 --port 8001 --reload
