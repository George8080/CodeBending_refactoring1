from datetime import datetime, timedelta
import os, shutil
from sqlite3 import IntegrityError
from click import DateTime
from flask import Flask, make_response, render_template, request, url_for, redirect, jsonify, session, flash, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from wtforms import FileField, SubmitField, PasswordField, StringField, DateField, BooleanField, validators, FileField
from werkzeug.utils import secure_filename
from wtforms.validators import InputRequired, Length, ValidationError
from funciones_archivo.manejoArchivosJava import eliminarPackages, agregarPackage
from funciones_archivo.manejoCarpetas import agregarCarpetaSerieEstudiante,crearCarpetaSerie, crearCarpetaEjercicio, crearArchivadorEstudiante, agregarCarpetaEjercicioEstudiante
from funciones_archivo.manejoMaven import ejecutarTestUnitario
from werkzeug.security import check_password_hash, generate_password_hash, check_password_hash
from DBManager import db, init_app
from basedatos.modelos import Supervisor, Grupo, Serie, Estudiante, Ejercicio, Ejercicio_asignado, Curso, serie_asignada, inscripciones, estudiantes_grupos, supervisores_grupos
from pathlib import Path
import markdown
import csv
import logging
from logging.config import dictConfig
from ansi2html import Ansi2HTMLConverter
import json
from routers.dash_docente_router import router

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


#inicializar la aplicacion
app = Flask(__name__)
init_app(app)
app.config['SECRET_KEY'] = 'secret-key-goes-here'

## agregar las rutas
app.register_blueprint(router)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Nombre de la vista para iniciar sesión

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=120)

UPLOAD_FOLDER = 'uploads' #Ruta donde se guardan los archivos subidos para los ejercicios
ALLOWED_EXTENSIONS = {'md','xml','csv','png','jpg', 'jpeg'}

# Encuentra la ruta del directorio del archivo actual
current_directory = os.path.dirname(os.path.abspath(__file__))

# Define la ruta UPLOAD_FOLDER en relación a ese directorio
UPLOAD_FOLDER = os.path.join(current_directory, "uploads")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Se define que tipo de arhivos se pueden recibir
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def procesar_archivo_csv(filename, curso_id):
    # ----->>>Falta borrar los flash de depuracion :)<<<<------
    # Procesa el archivo
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Saltar la primera fila
        for row in reader:
            if len(row) != 5:
                # Manejar el error, por ejemplo, omitiendo esta fila o mostrando un mensaje de advertencia
                current_app.logger.warning(f"La fila no tiene el formato esperado: {row}")
                continue  # Saltar esta fila y continuar con la próxima
            
            # Por cada fila, extraer los datos
            matricula, apellidos, nombres, correo, carrera = row
            password = generate_password_hash(matricula)  # Contraseña por defecto: hash de la matrícula
            # Verificar si el estudiante ya existe en la base de datos:
            estudiante_existente = Estudiante.query.filter_by(matricula=matricula).first()
            
            if estudiante_existente:
                # El estudiante con el mismo correo ya existe
                #flash(f'El estudiante con matrícula {matricula} ya está registrado en la base de datos.', 'warning')
                # Revisar si el estudiante ya está asignado a curso_id
                # Usando tabla de inscripciones
                relacion_existente = db.session.query(inscripciones).filter_by(id_estudiante=estudiante_existente.id, id_curso=curso_id).first()
                if relacion_existente:
                    flash(f'El estudiante con matrícula {matricula} ya está inscrito en el curso {curso_id}.', 'warning')
                    continue

                try:
                    nueva_inscripcion = inscripciones.insert().values(id_estudiante=estudiante_existente.id, id_curso=curso_id)
                    db.session.execute(nueva_inscripcion)
                    db.session.commit()
                    flash(f'El estudiante con matrícula {matricula} ha sido inscrito en el curso.', 'success')
                except IntegrityError as e:
                    db.session.rollback()
                    flash(f'Error al registrar en el curso {curso_id} al estudiante {matricula} .', 'warning')
                    continue
            
            # Si el estudiantes no existe, se crea
            elif not estudiante_existente:

                estudiante = Estudiante(
                matricula=matricula,
                apellidos=apellidos,
                nombres=nombres,
                correo=correo,
                password=password,
                carrera=carrera)
                # Crear el nuevo estudiante en la base de datos
                try:
                    db.session.add(estudiante)
                    db.session.flush()  # Esto genera el id sin confirmar en la base de datos
                    estudiante_id = estudiante.id  # Obtener el id del estudiante recién creado
                    db.session.commit()
                    flash(f'El estudiante con matrícula {matricula} ha sido registrado en la base de datos.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al crear al registrar {nombres} {apellidos} .', 'warning')
                    continue

                # Si el estudiante se creó correctamente en la bd, se inscribe en el curso
                try:
                    nueva_inscripcion = inscripciones.insert().values(id_estudiante=estudiante_id, id_curso=curso_id)
                    db.session.execute(nueva_inscripcion)
                    db.session.commit()
                    flash(f'El estudiante con matrícula {matricula} ha sido inscrito en el curso.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al inscribir a {nombres} {apellidos} en el curso.', 'warning')
                    continue

def calcular_calificacion(total_puntos, puntos_obtenidos):
    if total_puntos == 0:
        return "No hay ejercicios asignados"  # O cualquier mensaje de error adecuado
    else:
        porcentaje = (puntos_obtenidos / total_puntos) * 100

        if porcentaje >= 60:
            # Calcular la calificación para el rango de 4 a 7 redondeado a 2 decimales
            return round(max(1, min(4 + (3 / 40) * (porcentaje - 60), 7)), 2)
        else:
            # Calcular la calificación para el rango de 1 a 4 redondeado a 2 decimales
            return round(max(1, min(1 + (3 / 60) * porcentaje, 7)), 2)


#Refactoring  try-catch 1
@login_manager.user_loader
def load_user(user_id):
    try:
        if user_id.startswith("e"):
            user = db.session.get(Estudiante, int(user_id[1:]))
        elif user_id.startswith("s"):
            user = db.session.get(Supervisor, int(user_id[1:]))
        else:
            return None

        return user
    except Exception as e:
        # Registra el error en el log
        logging.error(f"Error en la función load_user: {e}")
        # Redirige a la página de inicio en caso de error
        return redirect(url_for('home'))


# Verifica que el usuario logueado es un Supervisor
def verify_supervisor(supervisor_id):
    
    if not isinstance(current_user, Supervisor):
        flash('No tienes permiso para acceder a este dashboard. Debes ser un Supervisor.', 'danger')
        return False

    # Asegura que el Supervisor está tratando de acceder a su propio dashboard
    if current_user.id != supervisor_id:
        flash('No tienes permiso para acceder a este dashboard.', 'danger')
        return False

    return True

# Verifica que el usuario logueado es un Estudiante
def verify_estudiante(estudiante_id):
    
    if not isinstance(current_user, Estudiante):
        flash('No tienes permiso para acceder a este dashboard. Debes ser un Estudiante.', 'danger')
        return False
    # Asegura que el Estudiante está tratando de acceder a su propio dashboard
    if current_user.id != estudiante_id:
        flash('No tienes permiso para acceder a este dashboard.', 'danger')
        return False
    return True

def verify_ayudante(supervisor_id):

    if not isinstance(current_user, Supervisor):
        flash('No tienes permiso para acceder a este dashboard. Debes ser un Supervisor.', 'danger')
        return False
    if current_user.id != supervisor_id:
        flash('No tienes permiso para acceder a este dashboard.', 'danger')
        return False

def get_fields(forms):
    fields = {}
    for key in forms:
        fields[key] = request.form.get(key)
    return fields

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
        data = get_fields(['nombres', 'apellidos', 'correo', 'password'])

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


@app.route('/dashEstudiante/<int:estudiante_id>', methods=['GET', 'POST'])
@login_required
def dashEstudiante(estudiante_id):

    if not verify_estudiante(estudiante_id):
        return redirect(url_for('login'))

    estudiante = db.session.get(Estudiante, int(estudiante_id))

    curso = (
        Curso.query
        .join(inscripciones)
        .filter(inscripciones.c.id_estudiante == estudiante_id)
        .filter(Curso.activa == True)
        .first()
    )
    if not curso:
        return render_template('vistaEstudiante.html', estudiante_id=estudiante_id, estudiante=estudiante, curso=None, grupo=None, supervisor=None, seriesAsignadas=None, ejerciciosPorSerie=None)
    # Obtiene el grupo asociado al estudiante
    grupo = (
        Grupo.query
        .join(estudiantes_grupos)  # Join con la tabla estudiantes_grupos
        .filter(estudiantes_grupos.c.id_grupo == Grupo.id)
        .filter(estudiantes_grupos.c.id_estudiante == estudiante_id)
        .first()
    )
    # Si no se encuentra ningún grupo asignado, grupo será None
    if not grupo:
        grupo_nombre = "Ningún grupo asignado"
    else:
        grupo_nombre = grupo.nombre

    supervisor = None

    # Obtiene el supervisor asignado si grupo no es None
    if grupo:
        supervisor = (
            Supervisor.query
            .join(supervisores_grupos)
            .filter(supervisores_grupos.c.id_supervisor == Supervisor.id)
            .filter(supervisores_grupos.c.id_grupo == grupo.id)
            .first()
        )

    seriesAsignadas = []

    # Obtiene las series asignadas solo si grupo no es None
    if grupo:
        seriesAsignadas = (
        Serie.query
        .join(serie_asignada)
        .filter(serie_asignada.c.id_grupo == grupo.id)
        .filter(Serie.activa)  # Filtrar por series activas
        .all()
    )


    # A continuación, puedes obtener los ejercicios para cada serie en series_asignadas
    ejerciciosPorSerie = {}
    for serieAsignada in seriesAsignadas:
        ejercicios = Ejercicio.query.filter_by(id_serie=serieAsignada.id).all()
        ejerciciosPorSerie[serieAsignada] = ejercicios

    return render_template('vistaEstudiante.html', estudiante_id=estudiante_id, estudiante=estudiante,grupo=grupo, curso=curso, supervisor=supervisor,seriesAsignadas=seriesAsignadas,ejerciciosPorSerie=ejerciciosPorSerie)

@app.route('/dashEstudiante/<int:estudiante_id>/serie/<int:serie_id>', methods=['GET', 'POST'])
@login_required
def detallesSeriesEstudiantes(estudiante_id, serie_id):

    if not verify_estudiante(estudiante_id):
        return redirect(url_for('login'))
    serie = db.session.get(Serie, serie_id)
    ejercicios = Ejercicio.query.filter_by(id_serie=serie_id).all()
    ejercicios_asignados = (
        Ejercicio_asignado.query
        .filter(Ejercicio_asignado.id_estudiante == estudiante_id)
        .filter(Ejercicio_asignado.id_ejercicio.in_([ejercicio.id for ejercicio in ejercicios]))
        .all()
    )
    ejercicios_aprobados = sum(1 for ea in ejercicios_asignados if ea.estado)

    total_ejercicios = len(ejercicios)
    if total_ejercicios == 0:
        calificacion = 0
    else:
        calificacion = calcular_calificacion(total_ejercicios, ejercicios_aprobados)

    return render_template('detallesSerieEstudiante.html', serie=serie, ejercicios=ejercicios, estudiante_id=estudiante_id,calificacion=calificacion)

@app.route('/dashEstudiante/<int:estudiante_id>/serie/<int:serie_id>/ejercicio/<int:ejercicio_id>', methods=['GET', 'POST'])
@login_required
def detallesEjerciciosEstudiantes(estudiante_id, serie_id, ejercicio_id):
    if not verify_estudiante(estudiante_id):
        return redirect(url_for('login'))

    serie = Serie.query.get(serie_id)
    ejercicio = Ejercicio.query.get(ejercicio_id)
    matricula= Estudiante.query.get(estudiante_id).matricula
    ejercicios = Ejercicio.query.filter_by(id_serie=serie_id).all()
    ejercicios_asignados = (
        Ejercicio_asignado.query
        .filter(Ejercicio_asignado.id_estudiante == estudiante_id)
        .filter(Ejercicio_asignado.id_ejercicio.in_([ejercicio.id for ejercicio in ejercicios]))
        .all()
    )
    
    colors_info = []

    for ejercicio_disponible in ejercicios:
        ejercicio_info = {'nombre': ejercicio_disponible.nombre, 'id': ejercicio_disponible.id, 'color': 'bg-persian-indigo-opaco'}
            
        for ejercicio_asignado in ejercicios_asignados:
            if ejercicio_disponible.id == ejercicio_asignado.id_ejercicio:
                if ejercicio_asignado.estado:
                    ejercicio_info['color'] = 'bg-success-custom'
                elif not ejercicio_asignado.estado and ejercicio_asignado.contador > 0:
                    ejercicio_info['color'] = 'bg-danger-custom'
                    
        colors_info.append(ejercicio_info)

    ejercicios_aprobados = sum(1 for ea in ejercicios_asignados if ea.estado)

    total_ejercicios = len(ejercicios)
    if total_ejercicios == 0:
        calificacion=0
    else:
        calificacion = calcular_calificacion(total_ejercicios, ejercicios_aprobados)
    
    if ejercicio and ejercicio.enunciado:
        with open(ejercicio.enunciado, 'r') as enunciado_file:
            enunciado_markdown = enunciado_file.read()
            enunciado_html = markdown.markdown(enunciado_markdown)
    else:
        enunciado_html = "<p>El enunciado no está disponible.</p>"

    if request.method == 'POST':
        archivos_java = request.files.getlist('archivo_java')
        rutaArchivador=None
        try:
            rutaArchivador = crearArchivadorEstudiante(matricula)
            flash('Se creo exitosamente el archivador', 'success')
        except Exception as e:
            current_app.logger.error(f'Ocurrió un error al crear el archivador: {str(e)}')
            return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados,colors_info=colors_info, calificacion=calificacion)

        if os.path.exists(rutaArchivador):
            ejercicioAsignado = Ejercicio_asignado.query.filter_by(id_estudiante=estudiante_id, id_ejercicio=ejercicio.id).first()
            if not ejercicioAsignado:
                try:
                    nuevoEjercicioAsignado = Ejercicio_asignado(
                    id_estudiante=estudiante_id,
                    id_ejercicio=ejercicio_id,
                    contador=0,
                    estado=False,
                    ultimo_envio=None,
                    fecha_ultimo_envio=datetime.now(),
                    test_output=None)
                    db.session.add(nuevoEjercicioAsignado)
                    db.session.flush()
                    try:
                        rutaSerieEstudiante = agregarCarpetaSerieEstudiante(rutaArchivador, serie.id)
                        current_app.logger.info(f'Ruta serie estudiante: {rutaSerieEstudiante}')
                        if os.path.exists(rutaSerieEstudiante):
                            try:
                                rutaEjercicioEstudiante = agregarCarpetaEjercicioEstudiante(rutaSerieEstudiante, ejercicio.id,  ejercicio.path_ejercicio)
                                current_app.logger.info(f'Ruta ejercicio estudiante: {rutaEjercicioEstudiante}')
                                if os.path.exists(rutaEjercicioEstudiante):
                                    for archivo_java in archivos_java:
                                        rutaFinal = os.path.join(rutaEjercicioEstudiante, 'src/main/java/org/example')
                                        if archivo_java and archivo_java.filename.endswith('.java'):
                                            archivo_java.save(os.path.join(rutaFinal, archivo_java.filename))
                                            current_app.logger.info(f'Archivo guardado en: {rutaFinal}')
                                    resultadoTest= ejecutarTestUnitario(rutaEjercicioEstudiante)
                                    current_app.logger.info(f'Resultado test: {resultadoTest}')
                                    if resultadoTest == 'BUILD SUCCESS':
                                        current_app.logger.info(f'El test fue exitoso')
                                        nuevoEjercicioAsignado.contador += 1
                                        nuevoEjercicioAsignado.ultimo_envio = rutaFinal
                                        nuevoEjercicioAsignado.fecha_ultimo_envio = datetime.now()
                                        nuevoEjercicioAsignado.test_output = json.dumps(resultadoTest)
                                        nuevoEjercicioAsignado.estado = True
                                        db.session.commit()
                                        errores = {"tipo": "success", "titulo": "Todos los test aprobados", "mensaje": resultadoTest}
                                        return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, errores=errores ,estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados,colors_info=colors_info, calificacion=calificacion)
                                    else:
                                        current_app.logger.info(f'El test no fue exitoso')
                                        nuevoEjercicioAsignado.contador += 1
                                        nuevoEjercicioAsignado.ultimo_envio = rutaFinal
                                        nuevoEjercicioAsignado.fecha_ultimo_envio = datetime.now()
                                        nuevoEjercicioAsignado.test_output = json.dumps(resultadoTest)
                                        nuevoEjercicioAsignado.estado = False
                                        db.session.commit()
                                        errores= {"tipo": "danger", "titulo": "Errores en la ejecución de pruebas unitarias", "mensaje": resultadoTest}
                                        return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, errores=errores ,estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados,colors_info=colors_info, calificacion=calificacion)
                            except Exception as e:
                                current_app.logger.error(f'Ocurrió un error al agregar la carpeta del ejercicio: {str(e)}')
                                db.session.rollback()
                                return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados,colors_info=colors_info, calificacion=calificacion)
                    except Exception as e:
                        current_app.logger.error(f'Ocurrió un error al agregar la carpeta de la serie: {str(e)}')
                        db.session.rollback()
                        # Agregar la eliminación de la carpeta??
                        return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados,colors_info=colors_info, calificacion=calificacion)
                except Exception as e:
                    current_app.logger.error(f'Ocurrió un error al agregar el ejercicio asignado: {str(e)}')
                    db.session.rollback()
                    # Agregar la eliminación de la carpeta??
                    return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados,colors_info=colors_info, calificacion=calificacion)
            else:
                try:
                    rutaSerieEstudiante = agregarCarpetaSerieEstudiante(rutaArchivador, serie.id)
                    if os.path.exists(rutaSerieEstudiante):
                        try:
                            rutaEjercicioEstudiante = agregarCarpetaEjercicioEstudiante(rutaSerieEstudiante, ejercicio.id,  ejercicio.path_ejercicio)
                            if os.path.exists(rutaEjercicioEstudiante):
                                for archivo_java in archivos_java:
                                    rutaFinal = os.path.join(rutaEjercicioEstudiante, 'src/main/java/org/example')
                                    if archivo_java and archivo_java.filename.endswith('.java'):
                                        archivo_java.save(os.path.join(rutaFinal, archivo_java.filename))
                                resultadoTest= ejecutarTestUnitario(rutaEjercicioEstudiante)
                                if resultadoTest == 'BUILD SUCCESS':
                                    ejercicioAsignado.contador += 1
                                    ejercicioAsignado.ultimo_envio = rutaFinal
                                    ejercicioAsignado.fecha_ultimo_envio = datetime.now()
                                    ejercicioAsignado.test_output = json.dumps(resultadoTest)
                                    ejercicioAsignado.estado = True
                                    db.session.commit()
                                    errores = {"tipo": "success", "titulo": "Todos los test aprobados", "mensaje": resultadoTest}
                                    return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, errores=errores ,estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados,colors_info=colors_info, calificacion=calificacion)
                                else:
                                    ejercicioAsignado.contador += 1
                                    ejercicioAsignado.ultimo_envio = rutaFinal
                                    ejercicioAsignado.fecha_ultimo_envio = datetime.now()
                                    ejercicioAsignado.test_output = json.dumps(resultadoTest)
                                    ejercicioAsignado.estado = False
                                    db.session.commit()
                                    errores= {"tipo": "danger", "titulo": "Errores en la ejecución de pruebas unitarias", "mensaje": resultadoTest}
                                    current_app.logger.info(f'resultadoTest: {resultadoTest}')
                                    return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, errores=errores ,estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados,colors_info=colors_info, calificacion=calificacion)
                        except Exception as e:
                            db.session.rollback()
                            current_app.logger.error(f'Ocurrió un error al agregar la carpeta del ejercicio: {str(e)}')
                            return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, errores=resultadoTest, estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados,colors_info=colors_info, calificacion=calificacion)
                except Exception as e:
                    current_app.logger.error(f'Ocurrió un error al agregar la carpeta de la serie: {str(e)}')
                    db.session.rollback()

    return render_template('detallesEjerciciosEstudiante.html', serie=serie, ejercicio=ejercicio, estudiante_id=estudiante_id, enunciado=enunciado_html, ejercicios=ejercicios, ejercicios_asignados=ejercicios_asignados, colors_info=colors_info, calificacion=calificacion)

@app.route('/dashEstudiante/<int:estudiante_id>/cuentaEstudiante', methods=['GET', 'POST'])
@login_required
def cuentaEstudiante(estudiante_id):
    if not verify_estudiante(estudiante_id):
        return redirect(url_for('login'))
    
    estudiante = Estudiante.query.get(estudiante_id)

    if request.method == 'POST':
        contraseña_actual = request.form.get('contraseña_actual')
        nueva_contraseña = request.form.get('nueva_contraseña')
        confirmar_nueva_contraseña = request.form.get('confirmar_nueva_contraseña')

        # Validaciones
        if not check_password_hash(estudiante.password, contraseña_actual):
            flash('Contraseña actual incorrecta', 'danger')
        elif len(nueva_contraseña) < 10:
            flash('La nueva contraseña debe tener al menos 6 caracteres', 'danger')
        elif nueva_contraseña != confirmar_nueva_contraseña:
            flash('Las nuevas contraseñas no coinciden', 'danger')
        else:
            # Cambiar la contraseña
            estudiante.password = generate_password_hash(nueva_contraseña)
            db.session.commit()
            flash('Contraseña actualizada correctamente', 'success')

    return render_template('cuentaEstudiante.html', estudiante=estudiante, estudiante_id=estudiante_id)




#Funcion para ejecutar el script 404
def pagina_no_encontrada(error):
    return render_template('404.html'), 404
    #return redirect(url_for('index')) #te devuelve a esa página

#Ruta para ejecutar el script
if __name__ == '__main__':
    #app.register_error_handler(404, pagina_no_encontrada)
    app.run(host='0.0.0.0',debug=True, port=3000)
    debug=True
