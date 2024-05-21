import logging
from sqlite3 import IntegrityError
from flask import current_app as app
import os
import csv
from flask import flash, current_app, redirect, render_template, url_for, request
from werkzeug.security import generate_password_hash
from basedatos.modelos import Estudiante, Supervisor, inscripciones
from DBManager import db
from flask_login import login_manager, current_user

UPLOAD_FOLDER = 'uploads' #Ruta donde se guardan los archivos subidos para los ejercicios
ALLOWED_EXTENSIONS = {'md','xml','csv','png','jpg', 'jpeg'}


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

#Funcion para ejecutar el script 404
def pagina_no_encontrada(error):
    return render_template('404.html'), 404
    #return redirect(url_for('index')) #te devuelve a esa página

