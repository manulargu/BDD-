from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('proyecto.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    clientes = conn.execute('''
        SELECT c.*, s.dia_semana, s.hora, v.fecha_inicio, v.fecha_fin
        FROM Clientes c
        LEFT JOIN Sesiones s ON c.nombre_completo = s.cliente_nombre
        LEFT JOIN Vacaciones v ON c.nombre_completo = v.cliente_nombre
        ORDER BY s.dia_semana, s.hora
    ''').fetchall()

    horarios_ocupados = conn.execute('''
        SELECT dia_semana, GROUP_CONCAT(hora, ', ') as horarios_ocupados
        FROM Sesiones
        GROUP BY dia_semana
        ORDER BY dia_semana
    ''').fetchall()

    # Convertir cada fila a un diccionario y ordenar los horarios ocupados de cada día
    horarios_ocupados = [dict(horario) for horario in horarios_ocupados]
    for horario in horarios_ocupados:
        horas = horario['horarios_ocupados'].split(', ')
        horas.sort(key=lambda x: datetime.strptime(x, '%H.%M'))
        horario['horarios_ocupados'] = ', '.join(horas)

    total_cobrado = conn.execute('''
        SELECT SUM(monto) as total
        FROM Clientes
        WHERE pagos = 'Sí' AND monto_sumado = 1
    ''').fetchone()['total']

    total_mensual = conn.execute('''
        SELECT SUM(total_mensual) as total
        FROM Clientes
    ''').fetchone()['total']

    # Convertir cada fila a un diccionario y luego convertir monto a número si es necesario
    clientes = [dict(cliente) for cliente in clientes]
    for cliente in clientes:
        if cliente['monto']:
            try:
                cliente['monto'] = float(cliente['monto'])
            except ValueError:
                cliente['monto'] = 0.0

    conn.close()
    return render_template('index.html', clientes=clientes, horarios_ocupados=horarios_ocupados, total_cobrado=total_cobrado, total_mensual=total_mensual)

@app.route('/create_cliente', methods=('GET', 'POST'))
def create_cliente():
    if request.method == 'POST':
        nombre_completo = request.form['nombre_completo']
        telefono = request.form['telefono']
        monto = request.form['monto']
        dia_semana = request.form['dia_semana']
        hora = request.form['hora']
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']

        conn = get_db_connection()
        conn.execute('INSERT INTO Clientes (nombre_completo, telefono, monto, pagos, asistencia, monto_sumado, total_mensual) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (nombre_completo, telefono, float(monto) if monto else 0, 'No', 'No', 0, 0))
        if dia_semana and hora:
            conn.execute('INSERT INTO Sesiones (cliente_nombre, dia_semana, hora) VALUES (?, ?, ?)',
                         (nombre_completo, dia_semana, hora))
        if fecha_inicio and fecha_fin:
            conn.execute('INSERT INTO Vacaciones (cliente_nombre, fecha_inicio, fecha_fin) VALUES (?, ?, ?)',
                         (nombre_completo, fecha_inicio, fecha_fin))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('create_cliente.html')

@app.route('/edit_cliente', methods=('GET', 'POST'))
def edit_cliente():
    if request.method == 'POST':
        nombre_completo = request.form['nombre_completo']
        return redirect(url_for('edit_cliente_details', nombre=nombre_completo))

    return render_template('edit_cliente.html')

@app.route('/edit_cliente/<string:nombre>', methods=('GET', 'POST'))
def edit_cliente_details(nombre):
    if request.method == 'POST':
        telefono = request.form['telefono']
        monto = request.form['monto']
        dia_semana = request.form['dia_semana']
        hora = request.form['hora']
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']

        conn = get_db_connection()
        if telefono:
            conn.execute('UPDATE Clientes SET telefono = ? WHERE nombre_completo = ?', (telefono, nombre))
        if monto:
            conn.execute('UPDATE Clientes SET monto = ? WHERE nombre_completo = ?', (float(monto) if monto else 0, nombre))
        if dia_semana and hora:
            conn.execute('UPDATE Sesiones SET dia_semana = ?, hora = ? WHERE cliente_nombre = ?', (dia_semana, hora, nombre))
        if fecha_inicio and fecha_fin:
            conn.execute('UPDATE Vacaciones SET fecha_inicio = ?, fecha_fin = ? WHERE cliente_nombre = ?', (fecha_inicio, fecha_fin, nombre))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn = get_db_connection()
    cliente = conn.execute('SELECT * FROM Clientes WHERE nombre_completo = ?', (nombre,)).fetchone()
    sesion = conn.execute('SELECT * FROM Sesiones WHERE cliente_nombre = ?', (nombre,)).fetchone()
    vacacion = conn.execute('SELECT * FROM Vacaciones WHERE cliente_nombre = ?', (nombre,)).fetchone()
    conn.close()
    return render_template('edit_cliente_details.html', cliente=cliente, sesion=sesion, vacacion=vacacion)

@app.route('/delete_cliente', methods=('GET', 'POST'))
def delete_cliente():
    if request.method == 'POST':
        nombre_completo = request.form['nombre_completo']

        conn = get_db_connection()
        conn.execute('DELETE FROM Clientes WHERE nombre_completo = ?', (nombre_completo,))
        conn.execute('DELETE FROM Sesiones WHERE cliente_nombre = ?', (nombre_completo,))
        conn.execute('DELETE FROM Vacaciones WHERE cliente_nombre = ?', (nombre_completo,))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('delete_cliente.html')

@app.route('/toggle_pago/<string:nombre>', methods=['POST'])
def toggle_pago(nombre):
    conn = get_db_connection()
    cliente = conn.execute('SELECT pagos, monto, monto_sumado, total_mensual FROM Clientes WHERE nombre_completo = ?', (nombre,)).fetchone()
    nuevo_estado = 'Sí' if cliente['pagos'] == 'No' else 'No'
    
    if nuevo_estado == 'Sí' and cliente['monto_sumado'] == 0:
        conn.execute('UPDATE Clientes SET pagos = ?, monto_sumado = 1, total_mensual = total_mensual + monto WHERE nombre_completo = ?', (nuevo_estado, nombre))
    else:
        conn.execute('UPDATE Clientes SET pagos = ? WHERE nombre_completo = ?', (nuevo_estado, nombre))
    
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/toggle_asistencia/<string:nombre>', methods=['POST'])
def toggle_asistencia(nombre):
    conn = get_db_connection()
    cliente = conn.execute('SELECT asistencia FROM Clientes WHERE nombre_completo = ?', (nombre,)).fetchone()
    nuevo_estado = 'Sí' if cliente['asistencia'] == 'No' else 'No'
    conn.execute('UPDATE Clientes SET asistencia = ? WHERE nombre_completo = ?', (nuevo_estado, nombre))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cliente/<string:nombre>')
def cliente(nombre):
    conn = get_db_connection()
    cliente = conn.execute('SELECT * FROM Clientes WHERE nombre_completo = ?', (nombre,)).fetchone()
    sesiones = conn.execute('SELECT * FROM Sesiones WHERE cliente_nombre = ?', (nombre,)).fetchall()
    vacaciones = conn.execute('SELECT * FROM Vacaciones WHERE cliente_nombre = ?', (nombre,)).fetchall()
    conn.close()
    return render_template('cliente.html', cliente=cliente, sesiones=sesiones, vacaciones=vacaciones)

@app.route('/reset_week', methods=['POST'])
def reset_week():
    conn = get_db_connection()
    
    # Reiniciar los estados de pagos y asistencia
    conn.execute('UPDATE Clientes SET pagos = "No", asistencia = "No", monto_sumado = 0')
    
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/reset_month', methods=['POST'])
def reset_month():
    conn = get_db_connection()
    conn.execute('UPDATE Clientes SET total_mensual = 0')
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

def reset_pagos_asistencia():
    conn = get_db_connection()
    conn.execute('UPDATE Clientes SET pagos = "No", asistencia = "No"')
    conn.commit()
    conn.close()

scheduler = BackgroundScheduler()
scheduler.add_job(func=reset_pagos_asistencia, trigger='cron', day_of_week='sun', hour=0, minute=0)
scheduler.start()

if __name__ == '__main__':
    try:
        app.run(debug=True)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()