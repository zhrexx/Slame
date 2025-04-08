from Slame.slame import *

server = ZHRXX("127.0.1", 2222)

@server.route("/")
def index(method, merged_params, body):
    return "Hello, World!"


if __name__ == "__main__":
    server.start()




