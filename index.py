
#inicializar la aplicacion
from flask import Flask

from DBManager import init_app


app = Flask(__name__)
init_app(app)
app.config['SECRET_KEY'] = 'secret-key-goes-here'

