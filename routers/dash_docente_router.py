##import router from flask
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from basedatos.modelos import Serie, Curso, Ejercicio, Grupo, serie_asignada
from main import verify_supervisor, db



router = Blueprint('dash-docente', __name__, url_prefix='/dash-docente')

@router.route('/<int:supervisor_id>', methods=['GET', 'POST'])
@login_required
def dashDocente(supervisor_id):
    # Usa la función de verificación
    if not verify_supervisor(supervisor_id):
        return redirect(url_for('login'))
    
    series = Serie.query.all()
    cursos = Curso.query.all()
    ejercicios = Ejercicio.query.all()
    ejercicios_por_serie = {}

    # Verificar si hay cursos, series y ejercicios
    curso_seleccionado_id=None
    grupos = []
    if not cursos:
        flash('No existen cursos, por favor crear un curso', 'danger')
        id_curso_seleccionado=None

    if not series:
        flash('No existen series, por favor crear una serie', 'danger')

    if not ejercicios:
        flash('No existen ejercicios, por favor crear un ejercicio', 'danger')

    # Si no se selecciona un curso o se selecciona el primer curso, busca los grupos del primer curso en tu base de datos.
    if curso_seleccionado_id is None or curso_seleccionado_id == 1:  # Ajusta el 1 al ID del primer curso en tu base de datos
        # primer_curso = Curso.query.get(1)  # Obtén el primer curso por ID
        primer_curso = session.get(1)
        if primer_curso:
            grupos = Grupo.query.filter_by(id_curso=curso_seleccionado_id)

    if request.method == 'POST':
        if request.form['accion']=='seleccionarCurso':
            curso_seleccionado_id = int(request.form['curso'])
            # Con el ID del curso seleccionado, se obtienen los grupos asociados
            grupos = Grupo.query.filter_by(id_curso=curso_seleccionado_id).all()
            series = Serie.query.all()
            return render_template('vistaDocente.html', supervisor_id=supervisor_id, cursos=cursos, grupos=grupos, id_curso_seleccionado=curso_seleccionado_id,series=series)
        if request.form['accion']=='asignarSeri189410.pts-0.pa3p2es':
            serie_seleccionada= request.form.get('series')
            grupo_seleccionado= request.form.get('grupos')
            try:
                if serie_seleccionada and grupo_seleccionado: 
                    db.session.execute(serie_asignada.insert().values(id_serie=serie_seleccionada, id_grupo=grupo_seleccionado))
                    db.session.commit()
                    flash('Serie asignada con éxito', 'success')
                    grupos = Grupo.query.filter_by(id_curso=curso_seleccionado_id).all()
                    series = Serie.query.all()
                    return redirect(url_for('dashDocente', supervisor_id=supervisor_id))
            except Exception as e:
                db.session.rollback()
                flash('Error al asignar la serie', 'danger')
                return redirect(url_for('dashDocente', supervisor_id=supervisor_id))

    # Luego, busca los grupos asociados al curso seleccionado, si hay uno.
    grupos = []
    if curso_seleccionado_id is not None:
        grupos = Grupo.query.filter_by(curso_id=curso_seleccionado_id).all()

    return render_template('vistaDocente.html', supervisor_id=supervisor_id, cursos=cursos, grupos=grupos, curso_seleccionado_id=curso_seleccionado_id,series=series)

