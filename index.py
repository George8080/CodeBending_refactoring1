
#inicializar la aplicacion
from flask import Flask
from flask_login import LoginManager

from DBManager import init_app


app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
init_app(app)
app.config['SECRET_KEY'] = 'secret-key-goes-here'

