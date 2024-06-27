from datetime import datetime
import json
import os
import markdown
from funciones_archivo.manejoCarpetas import agregarCarpetaEjercicioEstudiante, agregarCarpetaSerieEstudiante, crearArchivadorEstudiante
from funciones_archivo.manejoMaven import ejecutarTestUnitario
from services import services
from flask import current_app, flash, render_template, redirect, request, url_for
from DBManager import db
from basedatos.modelos import Ejercicio_asignado, Estudiante, Curso, inscripciones, Grupo, estudiantes_grupos, Supervisor, supervisores_grupos, Serie, serie_asignada, Ejercicio
from werkzeug.security import check_password_hash, generate_password_hash


def dashEstudiante(estudiante_id):

    if not services.verify_estudiante(estudiante_id):
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
        pass
    else:
        grupo.nombre

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


def detallesSeriesEstudiantes(estudiante_id, serie_id):

    if not services.verify_estudiante(estudiante_id):
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
        calificacion = services.calcular_calificacion(total_ejercicios, ejercicios_aprobados)

    return render_template('detallesSerieEstudiante.html', serie=serie, ejercicios=ejercicios, estudiante_id=estudiante_id,calificacion=calificacion)


def detallesEjerciciosEstudiantes(estudiante_id, serie_id, ejercicio_id):
    if not services.verify_estudiante(estudiante_id):
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
        calificacion = services.calcular_calificacion(total_ejercicios, ejercicios_aprobados)
    
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


def cuentaEstudiante(estudiante_id):
    if not services.verify_estudiante(estudiante_id):
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
