from slame import *
import jwt

app = ZHRXX('127.0.0.1', 8080)
app.use(logger_middleware)
app.use(jwt_auth_middleware)

@app.route('/')
def home(query):
    return "Welcome to ZHRXX server!"

@app.route('/protected')
def protected(query):
    return "You have access to a protected route."

app.start()
