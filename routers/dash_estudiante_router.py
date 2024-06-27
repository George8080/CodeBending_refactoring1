from flask import Blueprint
from flask_login import login_required
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
