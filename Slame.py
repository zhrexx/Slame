'''
(c) ZHRXXgroup
https://zhrxxgroup.com/

Version: 1.0
'''
# VERSION 1.0
import socket
import os
import secrets
import time
import sqlite3
import hashlib

#VERSION 1.1
from urllib.parse import parse_qs

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
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Server is listening on {self.host}:{self.port}")

        while True:
            client_socket, client_address = server_socket.accept()
            request_data = client_socket.recv(1024).decode('utf-8')

            if request_data:
                request_lines = request_data.split('\n')
                request_line = request_lines[0]
                method, path, _ = request_line.split()
                response = self.handle_request(method, path)
                client_socket.send(response.encode('utf-8'))
                client_socket.close()

    def handle_request(self, method, path, data=None):
        # Execute middleware functions
        for middleware in self.middlewares:
        middleware()

        # Check if the requested path matches any defined route
        if path in self.routes:
        route = self.routes[path]
        # Check if the requested HTTP method is allowed for the route
            if method in route['methods']:
                if method == 'POST':
                # Execute the handler function for the matched route with provided data
                    response = route['handler'](data)
                else:
                # Execute the handler function for the matched route
                    response = route['handler'](method)
            # Return a successful HTTP response with the response content
                    return f"HTTP/1.1 200 OK\n\n{response}"
            else:
            # Return a "Method Not Allowed" response if the method is not allowed for the route
                return "HTTP/1.1 405 Method Not Allowed\n\n405 Method Not Allowed"
    # Check if the requested path starts with '/static/', indicating a static file request
            elif path.startswith('/static/'):
            # Serve the requested static file
            return self.serve_static_file(path)
            else:
                # Return a "Not Found" response for paths that don't match any route or static file
                return "HTTP/1.1 404 Not Found\n\n404 Not Found"


    @staticmethod
    def read_file(file_path):
        # Get the absolute path to the file based on the script's directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        abs_file_path = os.path.join(script_dir, file_path)

        try:
            with open(abs_file_path, 'rb') as file:
                content = file.read()
            return content.decode('utf-8')
        except FileNotFoundError:
            return "HTTP/1.1 404 Not Found\n\n404 Not Found"








class Work_with_Database:
    '''for user login'''
    
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

        # Create the 'users' table if it doesn't exist
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT UNIQUE NOT NULL,
                                password TEXT NOT NULL)''')
        self.conn.commit()

    def close(self):
        self.conn.close()

    def add_user(self, username, password):
        # Hash the password before storing it in the database
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Username is already taken

    def verify_user(self, username, password):
        # Verify user credentials and return user ID if successful
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        self.cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, hashed_password))
        user_data = self.cursor.fetchone()
        if user_data:
            return user_data[0]
        return None






'''
(c) ZHRXXgroup
https://zhrxxgroup.com

Version: 1.1
'''
class Sessions:
    session_data = {}  # Dictionary to store session data
    session_timeout = 3600  # Session timeout in seconds (1 hour)

    @staticmethod
    def create_session():
        session_id = secrets.token_hex(16)  # Generate a random session ID
        Sessions.session_data[session_id] = {'timestamp': time.time(), 'data': {}}  # Store creation timestamp and session data
        return session_id

    @staticmethod
    def get_session(session_id):
        session = Sessions.session_data.get(session_id)
        if session:
            # Check if the session has expired
            if time.time() - session['timestamp'] > Sessions.session_timeout:
                del Sessions.session_data[session_id]
                return None
            return session
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
            Sessions.update_session(session_id, session['data'])

    @staticmethod
    def get_session_data(session_id, key):
        session = Sessions.get_session(session_id)
        if session:
            return session['data'].get(key)
        return None
    
