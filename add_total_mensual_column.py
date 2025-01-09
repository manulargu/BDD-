import sqlite3

def add_total_mensual_column():
    # Conectar a la base de datos
    conn = sqlite3.connect('proyecto.db')
    
    # Ejecutar la sentencia SQL para agregar la columna 'total_mensual'
    conn.execute('ALTER TABLE Clientes ADD COLUMN total_mensual REAL DEFAULT 0')
    
    # Confirmar los cambios
    conn.commit()
    
    # Cerrar la conexión
    conn.close()

if __name__ == '__main__':
    add_total_mensual_column()
    print("Columna 'total_mensual' agregada a la tabla 'Clientes'.")