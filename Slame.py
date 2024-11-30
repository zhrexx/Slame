import socket
import os
import secrets
import time
import sqlite3
import hashlib
from urllib.parse import parse_qs


class ZHRXX:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.routes = {}
        self.middlewares = []

    def route(self, path, methods=['GET']):
        def decorator(func):
            self.routes[path] = {'methods': methods, 'handler': func}
            return func
        return decorator

    def use(self, middleware):
        self.middlewares.append(middleware)

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        while True:
            client_socket, _ = server_socket.accept()
            request_data = client_socket.recv(1024).decode('utf-8')
            if request_data:
                request_lines = request_data.split('\r\n')
                request_line = request_lines[0]
                method, path, *_ = request_line.split()
                body = request_lines[-1] if method == "POST" else None
                response = self.handle_request(method, path, body)
                client_socket.send(response.encode('utf-8'))
                client_socket.close()

    def handle_request(self, method, path, body=None):
        for middleware in self.middlewares:
            result = middleware(method, path, body)
            if result is not None:
                return result

        for route_path, route in self.routes.items():
            route_params = self.match_route(route_path, path)
            if route_params is not None and method in route['methods']:
                if method == 'POST' and body:
                    body_data = parse_qs(body)
                    return route['handler'](**route_params, body=body_data)
                return route['handler'](**route_params)
        
        if path.startswith('/static/'):
            return self.serve_static_file(path)
        
        return "HTTP/1.1 404 Not Found\r\n\r\n404 Not Found"

    def serve_static_file(self, path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        abs_file_path = os.path.join(script_dir, path.lstrip('/'))
        try:
            with open(abs_file_path, 'rb') as file:
                content = file.read()
            return f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n{content.decode('utf-8')}"
        except FileNotFoundError:
            return "HTTP/1.1 404 Not Found\r\n\r\n404 Not Found"

    def match_route(self, route_path, request_path):
        route_parts = route_path.split('/')
        request_parts = request_path.split('/')
        if len(route_parts) != len(request_parts):
            return None
        params = {}
        for route_part, request_part in zip(route_parts, request_parts):
            if route_part.startswith(':'):
                params[route_part[1:]] = request_part
            elif route_part != request_part:
                return None
        return params


class Work_with_Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             username TEXT UNIQUE NOT NULL,
                             password TEXT NOT NULL)''')
        self.conn.commit()

    def close(self):
        self.conn.close()

    def add_user(self, username, password):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def verify_user(self, username, password):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        self.cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, hashed_password))
        user_data = self.cursor.fetchone()
        return user_data[0] if user_data else None


class Sessions:
    session_data = {}
    session_timeout = 3600

    @staticmethod
    def create_session():
        session_id = secrets.token_hex(16)
        Sessions.session_data[session_id] = {'timestamp': time.time(), 'data': {}}
        return session_id

    @staticmethod
    def get_session(session_id):
        session = Sessions.session_data.get(session_id)
        if session and time.time() - session['timestamp'] <= Sessions.session_timeout:
            return session
        if session_id in Sessions.session_data:
            del Sessions.session_data[session_id]
        return None

    @staticmethod
    def update_session(session_id, data):
        session = Sessions.get_session(session_id)
        if session:
            session['data'].update(data)

    @staticmethod
    def end_session(session_id):
        if session_id in Sessions.session_data:
            del Sessions.session_data[session_id]

    @staticmethod
    def set_session_data(session_id, key, value):
        session = Sessions.get_session(session_id)
        if session:
            session['data'][key] = value

    @staticmethod
    def get_session_data(session_id, key):
        session = Sessions.get_session(session_id)
        return session['data'].get(key) if session else None
