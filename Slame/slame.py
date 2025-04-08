import socket
import os
import secrets
import time
import sqlite3
import hashlib
from urllib.parse import parse_qs, urlparse
from .utils import default_middleware

class ZHRXX:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.routes = {}
        self.middlewares = []

    def route(self, path, methods=['GET']):
        def decorator(func):
            self.routes[path] = {
                'methods': methods,
                'handler': func
            }
            return func
        return decorator

    def use(self, middleware):
        self.middlewares.append(middleware)

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Server is listening on {self.host}:{self.port}")

        try:
            while True:
                client_socket, client_address = server_socket.accept()
                try:
                    self.handle_connection(client_socket, client_address)
                except Exception as e:
                    print(f"Error handling connection: {e}")
                finally:
                    client_socket.close()
        finally:
            server_socket.close()

    def handle_connection(self, client_socket, client_address):
        request_data = client_socket.recv(1024).decode('utf-8')
        if not request_data:
            return
        try:
            headers, body = self.parse_request(request_data)
            method = headers['method']
            path = headers['path']
            query = headers['query']

            response = self.handle_request(client_address, method, path, body, query)
        except Exception as e:
            print(f"Request parsing error: {e}")
            response = "HTTP/1.1 400 Bad Request\n\n400 Bad Request"
        client_socket.send(response.encode('utf-8'))

    def parse_request(self, request_data):
        lines = request_data.split('\r\n')
        request_line = lines[0]
        method, raw_path, _ = request_line.split()
        parsed_url = urlparse(raw_path)
        headers = {
            'method': method,
            'path': parsed_url.path,
            'query': {k: v[0] for k, v in parse_qs(parsed_url.query).items()}
        }
        body = "\n".join(lines[lines.index('') + 1:]) if '' in lines else None
        return headers, body

    def handle_request(self, client_address, method, path, body, query):
        if len(self.middlewares) == 0:
            self.middlewares.append(default_middleware)

        for middleware in self.middlewares:
            middleware(client_address, method, path, body, query)

        route_params = {}
        for route_path, route_info in self.routes.items():
            match, params = self.match_route(route_path, path)
            if match:
                route_params = params
                path = route_path
                break

        if path in self.routes:
            route = self.routes[path]
            if method in route['methods']:
                merged_params = {**route_params, **query}
                response = route['handler'](method, merged_params, body)
                return f"HTTP/1.1 200 OK\n\n{response}"
            return "HTTP/1.1 405 Method Not Allowed\n\n405 Method Not Allowed"
        elif path.startswith('/static/'):
            return self.serve_static_file(path)
        return "HTTP/1.1 404 Not Found\n\n404 Not Found"

    def match_route(self, route_path, actual_path):
        route_parts = route_path.strip('/').split('/')
        actual_parts = actual_path.strip('/').split('/')

        if len(route_parts) != len(actual_parts):
            return False, {}

        params = {}
        for route_part, actual_part in zip(route_parts, actual_parts):
            if route_part.startswith(':'):
                params[route_part[1:]] = actual_part
            elif route_part != actual_part:
                return False, {}
        return True, params

    def serve_static_file(self, path):
        file_path = path.lstrip('/static/')
        try:
            with open(file_path, 'rb') as file:
                content = file.read()
            return f"HTTP/1.1 200 OK\n\n{content.decode('utf-8')}"
        except FileNotFoundError:
            return "HTTP/1.1 404 Not Found\n\n404 Not Found"


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
        if session:
            if time.time() - session['timestamp'] > Sessions.session_timeout:
                del Sessions.session_data[session_id]
                return None
            session['timestamp'] = time.time()
            return session
        return None

    @staticmethod
    def update_session(session_id, data):
        session = Sessions.get_session(session_id)
        if session:
            session['data'].update(data)

    @staticmethod
    def end_session(session_id):
        Sessions.session_data.pop(session_id, None)

    @staticmethod
    def set_session_data(session_id, key, value):
        session = Sessions.get_session(session_id)
        if session:
            session['data'][key] = value

    @staticmethod
    def get_session_data(session_id, key):
        session = Sessions.get_session(session_id)
        return session['data'].get(key) if session else None