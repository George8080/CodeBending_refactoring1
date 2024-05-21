from datetime import timedelta
import os
from flask import  render_template, request, url_for, redirect, flash
from flask_login import LoginManager, login_user, logout_user, login_required, logout_user
from werkzeug.security import check_password_hash, generate_password_hash, check_password_hash
from DBManager import db
import logging
from logging.config import dictConfig
from routers.dash_docente_router import router as dashDocenteRouter
from routers.dash_estudiante_router import router as dashEstudianteRouter
from index import app
import services.services as services
from basedatos.modelos import Estudiante, Supervisor


#registrar el blueprint
app.register_blueprint(dashDocenteRouter)
app.register_blueprint(dashEstudianteRouter)

#Refactoring try-catch
import logging

# Configura el logger
logging.basicConfig(filename='error.log', level=logging.ERROR)
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'errores.log',
            'formatter': 'default',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',  # Puedes ajustar este nivel según tus necesidades
            'propagate': True,
        },
    },
})

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Nombre de la vista para iniciar sesión

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=120)


# Encuentra la ruta del directorio del archivo actual
current_directory = os.path.dirname(os.path.abspath(__file__))

# Define la ruta UPLOAD_FOLDER en relación a ese directorio
UPLOAD_FOLDER = os.path.join(current_directory, "uploads")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Se define que tipo de arhivos se pueden recibir

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        
        # Primero verifica si las credenciales son de un estudiante o un supervisor.
        estudiante = Estudiante.query.filter_by(correo=correo).first()
        supervisor = Supervisor.query.filter_by(correo=correo).first()

        # Si es estudiante y las credenciales son correctas.
        if estudiante and check_password_hash(estudiante.password, password):
            login_user(estudiante)
            flash('Has iniciado sesión exitosamente', 'success')
            return redirect(url_for('dashEstudiante', estudiante_id=estudiante.id))
        
        # Si es supervisor y las credenciales son correctas.
        elif supervisor and check_password_hash(supervisor.password, password):
            login_user(supervisor)
            flash('Has iniciado sesión exitosamente', 'success')
            return redirect(url_for('dashDocente', supervisor_id=supervisor.id))
        
        # Si las credenciales no coinciden con ningún usuario.
        flash('Credenciales inválidas', 'danger')
    
    return render_template('inicio.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('inicio.html')

@app.route('/registerSupervisor', methods=['GET'])
def register_page():
    return render_template('register.html')

#Refactoring try-catch 2
@app.route('/registersupervisor', methods=['GET', 'POST'])
def register():
    try:
        # Obtén los datos del formulario
        data = services.get_fields(['nombres', 'apellidos', 'correo', 'password'])

        if not data['nombres'] or not data['apellidos'] or not data['correo'] or not data['password']:
            flash('Todos los campos son requeridos.', 'danger')
            return render_template('registersupervisor.html')
        
        # Verifica si ya existe un supervisor con ese correo
        supervisor = Supervisor.query.filter_by(correo=data['correo']).first()
        if supervisor:
            flash('Ya existe un supervisor con ese correo.', 'warning')
            return render_template('register.html')
        
        # Crea el nuevo supervisor
        new_supervisor = Supervisor(
            nombres=data['nombres'],
            apellidos=data['apellidos'],
            correo=data['correo'],
            password=generate_password_hash(data['password'])  # Almacena la contraseña de forma segura
        )

        # Añade el nuevo supervisor a la base de datos
        db.session.add(new_supervisor)
        db.session.commit()

        flash('Supervisor registrado exitosamente.', 'success')
        return redirect(url_for('login'))

    except Exception as e:
        # Registra el error en el log
        logging.error(f"Error en la función register: {e}")
        # Redirige a la página de inicio en caso de error
        return redirect(url_for('home'))



###########################################################################################################################################
###########################################################################################################################################
###########################################################################################################################################





#Ruta para ejecutar el script
if __name__ == '__main__':
    #app.register_error_handler(404, pagina_no_encontrada)
    app.run(host='0.0.0.0',debug=True, port=3000)
    debug=True
