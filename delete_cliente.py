import sqlite3

def get_db_connection():
    conn = sqlite3.connect('proyecto.db')
    return conn

def delete_cliente(nombre):
    conn = get_db_connection()
    conn.execute('DELETE FROM Clientes WHERE nombre_completo = ?', (nombre,))
    conn.execute('DELETE FROM Sesiones WHERE cliente_nombre = ?', (nombre,))
    conn.execute('DELETE FROM Vacaciones WHERE cliente_nombre = ?', (nombre,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    delete_cliente('lucas')
    print("Cliente 'Augusto' eliminado de la base de datos.")