# README.md

# **Logon Tracking App**

The Logon Tracking App is a simple web application built with FastAPI and SQLite3 that allows you to track login and logoff events for clients on different servers. The app provides an API to record client login and logoff events and a dashboard to view the latest login and logoff events.

## **Features**

- Record client login and logoff events with the API
- View the latest login and logoff events on the dashboard
- Store data in an SQLite3 database

## **Installation**

1. Clone the repository:
    
    ```bash
    
    git clone https://github.com/lubeschanin/logon-app.git
    cd logon-tracking-app
    ```
    
2. Create a virtual environment and install dependencies:
    
    ```bash
    
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
    
3. Run the FastAPI server:
    
    ```bash
    
    uvicorn main:app --host 0.0.0.0 --port 8001
    ```
    
    The server will be available at **[http://localhost:8001](http://localhost:8001/)**.
    

## **Usage**

### **API**

1. Record a client login:
    
    ```json
    POST /api/login
    {
        "client_name": "Client1",
        "server_name": "Server1"
    }
    ```
    
2. Record a client logoff:
    
    ```json
    POST /api/logoff
    {
        "client_name": "Client1",
        "server_name": "Server1"
    }
    
    ```
    

### **Dashboard**

Visit **[http://localhost:8001/dashboard](http://localhost:8001/dashboard)** to view the latest login and logoff events for clients on different servers.

## **Contributing**

We welcome contributions to the Logon Tracking App! Please feel free to submit a pull request or open an issue if you encounter any problems or have suggestions for improvements.

## **License**

This project is licensed under the GNU General Public License version 2 (GPLv2)