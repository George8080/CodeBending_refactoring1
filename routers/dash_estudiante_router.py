import markdown
from flask import current_app as app 
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from basedatos.modelos import db, Estudiante, Supervisor, Curso, Grupo, Serie, Ejercicio, Ejercicio_asignado, inscripciones, estudiantes_grupos, supervisores_grupos, serie_asignada
from services.services import services
from datetime import datetime
import os
import json
from funciones_archivo.manejoCarpetas import agregarCarpetaSerieEstudiante, agregarCarpetaEjercicioEstudiante, crearArchivadorEstudiante
from funciones_archivo.manejoMaven import ejecutarTestUnitario
from werkzeug.security import generate_password_hash, check_password_hash
from controllers import dash_estudiante_controller as controller



router = Blueprint('dash_estudiante_router', __name__)

@router.route('/dashEstudiante/<int:estudiante_id>', methods=['GET', 'POST'])
@login_required
def dashEstudiante(estudiante_id):
    return controller.dashEstudiante(estudiante_id)


@router.route('/dashEstudiante/<int:estudiante_id>/serie/<int:serie_id>', methods=['GET', 'POST'])
@login_required
def detallesSeriesEstudiantes(estudiante_id, serie_id):
    return controller.detallesSeriesEstudiantes(estudiante_id, serie_id)
        
        
@router.route('/dashEstudiante/<int:estudiante_id>/serie/<int:serie_id>/ejercicio/<int:ejercicio_id>', methods=['GET', 'POST'])
@login_required
def detallesEjerciciosEstudiantes(estudiante_id, serie_id, ejercicio_id):
    return controller.detallesEjerciciosEstudiantes(estudiante_id, serie_id, ejercicio_id)


@router.route('/dashEstudiante/<int:estudiante_id>/cuentaEstudiante', methods=['GET', 'POST'])
@login_required
def cuentaEstudiante(estudiante_id):
    return controller.cuentaEstudiante(estudiante_id)
