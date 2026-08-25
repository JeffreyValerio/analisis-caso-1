from flask import Flask
import socket
import os

app = Flask(__name__)


@app.route("/")
def hola_mundo():
    return (
        f"<h1>Hola Mundo</h1>"
        f"<p>Servido desde el contenedor: <b>{socket.gethostname()}</b></p>"
        f"<p>PID del proceso: <b>{os.getpid()}</b></p>"
    )


@app.route("/health")
def health():
    return {"status": "ok", "hostname": socket.gethostname()}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
