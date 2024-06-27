##import router from flask
from flask import Blueprint
from flask_login import login_required
import controllers.dash_docente_controller as controller


router = Blueprint('dash-docente', __name__, url_prefix='/dash-docente')

@router.route('/<int:supervisor_id>', methods=['GET', 'POST'])
@login_required
def dashDocente(supervisor_id):
    return controller.dashDocente(supervisor_id)


#Refactoring try-catch 3
@router.route('/dashDocente/<int:supervisor_id>/cuentaDocente', methods=['GET', 'POST'])
@login_required
def cuentaDocente(supervisor_id):
    return controller.cuentaDocente(supervisor_id) 

@router.route('/dashDocente/<int:supervisor_id>/agregarSerie', methods=['GET', 'POST'])
@login_required
def agregarSerie(supervisor_id):
    return controller.agregarSerie(supervisor_id)   

@router.route('/dashDocente/<int:supervisor_id>/agregarEjercicio', methods=['GET', 'POST'])
@login_required
def agregarEjercicio(supervisor_id):
    return controller.agregarEjercicio(supervisor_id)

@router.route('/dashDocente/<int:supervisor_id>/serie/<int:serie_id>', methods=['GET', 'POST'])
@login_required
def detallesSerie(supervisor_id, serie_id):
    return controller.detallesSerie(supervisor_id, serie_id)

@router.route('/dashDocente/<int:supervisor_id>/serie/<int:serie_id>/ejercicio/<int:ejercicio_id>', methods=['GET','POST'])
@login_required
def detallesEjercicio(supervisor_id, serie_id, ejercicio_id):
    return controller.detallesEjercicio(supervisor_id, serie_id, ejercicio_id)

@router.route('/dashDocente/<int:supervisor_id>/registrarEstudiante', methods=['GET', 'POST'])
@login_required
def registrarEstudiante(supervisor_id):
    return controller.registrarEstudiante(supervisor_id)

@router.route('/dashDocente/<int:supervisor_id>/detalleCurso/<int:curso_id>', methods=['GET','POST'])
@login_required
def detallesCurso(supervisor_id, curso_id):
    return controller.detallesCurso(supervisor_id, curso_id)

@router.route('/dashDocente/<int:supervisor_id>/asignarGrupos/<int:curso_id>', methods=['GET', 'POST'])
@login_required
def asignarGrupos(supervisor_id, curso_id):
    return controller.asignarGrupos(supervisor_id, curso_id)
@router.route('/dashDocente/<int:supervisor_id>/detalleCurso/<int:curso_id>/detalleGrupo/<int:grupo_id>', methods=['GET', 'POST'])
@login_required
def detallesGrupo(supervisor_id, curso_id, grupo_id):
    return controller.detallesGrupo(supervisor_id, curso_id, grupo_id)
@router.route('/dashDocente/<int:supervisor_id>/detalleCurso/<int:curso_id>/detalleGrupo/<int:grupo_id>/eliminarEstudiante', methods=['GET', 'POST'])
@login_required
def eliminarEstudiante(supervisor_id, curso_id, grupo_id):
    return controller.eliminarEstudiante(supervisor_id, curso_id, grupo_id) 

#Refactoring try-catch 4
@router.route('/dashDocente/<int:supervisor_id>/detalleCurso/<int:curso_id>/detalleEstudiante/<int:estudiante_id>', methods=['GET', 'POST'])
@login_required
def detallesEstudiante(supervisor_id, curso_id, estudiante_id):
    return controller.detallesEstudiante(supervisor_id, curso_id, estudiante_id)
#Refactoring try-catch 5
@router.route('/dashDocente/<int:supervisor_id>/detalleCurso/<int:curso_id>/detalleEstudiante/<int:estudiante_id>/examinarEjercicio/<int:ejercicio_id>', methods=['GET', 'POST'])
@login_required
def examinarEjercicio(supervisor_id, curso_id, estudiante_id, ejercicio_id):
    return controller.examinarEjercicio(supervisor_id, curso_id, estudiante_id, ejercicio_id)
# Ruta para ver el progreso de los estudiantes de un curso
@router.route('/dashDocente/<int:supervisor_id>/progresoCurso/<int:curso_id>', methods=['GET', 'POST'])
@login_required
def progresoCurso(supervisor_id, curso_id):
    return controller.progresoCurso(supervisor_id, curso_id)