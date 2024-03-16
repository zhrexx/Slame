import socket
import os
import sqlite3
import hashlib



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

    def handle_request(self, method, path):
        for middleware in self.middlewares:
            middleware()

        if path in self.routes:
            route = self.routes[path]
            if method in route['methods']:
                response = route['handler'](method)
                return f"HTTP/1.1 200 OK\n\n{response}"
            else:
                return "HTTP/1.1 405 Method Not Allowed\n\n405 Method Not Allowed"
        elif path.startswith('/static/'):
            return self.serve_static_file(path)
        else:
            return "HTTP/1.1 404 Not Found\n\n404 Not Found"

    def serve_static_file(self, path):
        try:
            with open(path[1:], 'rb') as file:
                content = file.read()
            return f"HTTP/1.1 200 OK\nContent-Length: {len(content)}\n\n{content.decode('utf-8')}"
        except FileNotFoundError:
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
