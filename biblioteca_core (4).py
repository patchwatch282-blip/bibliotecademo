import json
import os
import secrets
import string
import hashlib
import sqlite3
from datetime import date, timedelta


# ============================================================
# CONFIGURACION GENERAL
# ============================================================

ARCHIVO_DATOS = "biblioteca.db"
DIAS_PRESTAMO = 1
MAX_LIBROS = 5


# ============================================================
# DATOS INICIALES
# ============================================================

LIBROS_INICIALES = [
    {
        "id": 1,
        "titulo": "Batman: Year One",
        "autor": "Frank Miller",
        "genero": "Novela grafica",
        "stock": 2,
        "origen": "Compra",
        "fecha_alta": "2026-01-01",
    },
    {
        "id": 2,
        "titulo": "Resident Evil Archives",
        "autor": "Capcom",
        "genero": "Terror",
        "stock": 2,
        "origen": "Compra",
        "fecha_alta": "2026-01-01",
    },
    {
        "id": 3,
        "titulo": "El arte de crear",
        "autor": "Autor desconocido",
        "genero": "Creatividad",
        "stock": 2,
        "origen": "Donacion",
        "fecha_alta": "2026-01-01",
    },
    {
        "id": 4,
        "titulo": "El Principito",
        "autor": "Antoine de Saint-Exupery",
        "genero": "Literatura",
        "stock": 2,
        "origen": "Donacion",
        "fecha_alta": "2026-01-01",
    },
    {
        "id": 5,
        "titulo": "El Arte de la Guerra",
        "autor": "Sun Tzu",
        "genero": "Estrategia",
        "stock": 2,
        "origen": "Compra",
        "fecha_alta": "2026-01-01",
    },
    {
        "id": 6,
        "titulo": "Cien Años de Soledad",
        "autor": "Gabriel Garcia Marquez",
        "genero": "Realismo magico",
        "stock": 2,
        "origen": "Compra",
        "fecha_alta": "2026-01-01",
    },
    {
        "id": 7,
        "titulo": "Don Quijote",
        "autor": "Miguel de Cervantes",
        "genero": "Clasico",
        "stock": 2,
        "origen": "Donacion",
        "fecha_alta": "2026-01-01",
    },
    {
        "id": 8,
        "titulo": "1984",
        "autor": "George Orwell",
        "genero": "Distopia",
        "stock": 2,
        "origen": "Compra",
        "fecha_alta": "2026-01-01",
    },
    {
        "id": 9,
        "titulo": "Fahrenheit 451",
        "autor": "Ray Bradbury",
        "genero": "Ciencia ficcion",
        "stock": 2,
        "origen": "Intercambio",
        "fecha_alta": "2026-01-01",
    },
    {
        "id": 10,
        "titulo": "Dracula",
        "autor": "Bram Stoker",
        "genero": "Terror",
        "stock": 2,
        "origen": "Compra",
        "fecha_alta": "2026-01-01",
    },
]


GENEROS_PREDETERMINADOS = [
    "Literatura",
    "Romance",
    "Misterio",
    "Terror",
    "Fantasia",
    "Ciencia ficcion",
    "Aventura",
    "Drama",
    "Comedia",
    "Historia",
    "Suspenso",
    "Infantil",
]

PREGUNTAS_SEGURIDAD = [
    "¿Cual es el nombre de tu primera mascota?",
    "¿Cual es el nombre de tu mejor amigo de la infancia?",
    "¿En que ciudad naciste?",
    "¿Cual es tu comida favorita?",
    "¿Cual es el nombre de tu escuela primaria?",
    "¿Cual es el segundo nombre de tu mama?",
    "¿Cual fue tu primer trabajo?",
    "¿Cual es tu pelicula favorita?",
]

MAPA_GENEROS_ANTIGUOS = {
    "novela grafica": "Literatura",
    "creatividad": "Literatura",
    "estrategia": "Aventura",
    "realismo magico": "Literatura",
    "clasico": "Literatura",
    "distopia": "Ciencia ficcion",
}

USUARIOS_INICIALES = [
    {
        "nombre": "Neithan Durant",
        "codigo": "1234",
        "telefono": "99999999",
        "rol": "CLIENTE",
        "password": "1234",
        "deuda": 0,
        "pagado": 0,
    },
    {
        "nombre": "Jose Carranza",
        "codigo": "1010",
        "telefono": "88888888",
        "rol": "CLIENTE",
        "password": "1010",
        "deuda": 0,
        "pagado": 0,
    },
    {
        "nombre": "Administrador",
        "codigo": "admin",
        "telefono": "00000000",
        "rol": "ADMIN",
        "password": "Admin123!",
        "deuda": 0,
        "pagado": 0,
    },
]


# ============================================================
# FUNCIONES DE SEGURIDAD Y UTILIDAD
# ============================================================

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def generar_password(conexion=None):
    # Contraseña sencilla: palabra + 3 numeros, por ejemplo "libro123".
    palabras = ["libro", "lectura", "pagina", "cuento", "novela", "biblioteca", "estudio", "libreta"]

    while True:
        password = secrets.choice(palabras) + "".join(
            secrets.choice(string.digits) for _ in range(3)
        )

        if conexion is None:
            return password

        existe = conexion.execute(
            "SELECT 1 FROM usuarios WHERE password = ? LIMIT 1",
            (hash_password(password),)
        ).fetchone()

        if existe is None:
            return password




def hoy_texto():
    return date.today().isoformat()


def fecha_legible(valor):
    try:
        return date.fromisoformat(valor).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return valor


# ============================================================
# CLASE PRINCIPAL: LOGICA Y PERSISTENCIA
# ============================================================

class Biblioteca:
    """Capa de datos de la biblioteca usando SQLite."""

    def __init__(self):
        self.con = sqlite3.connect(ARCHIVO_DATOS, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.crear_tablas()
        if self.base_vacia():
            self.datos_iniciales()
        self.normalizar_generos()
        self.asegurar_administrador()
        self.refrescar_cache()

    # --------------------------------------------------------
    # BASE DE DATOS
    # --------------------------------------------------------

    def crear_tablas(self):
        self.con.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS usuarios (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL UNIQUE,
            rol TEXT NOT NULL CHECK (rol IN ('CLIENTE', 'ADMIN')),
            password TEXT NOT NULL,
            deuda REAL NOT NULL DEFAULT 0 CHECK (deuda >= 0),
            pagado REAL NOT NULL DEFAULT 0 CHECK (pagado >= 0),
            pregunta_seguridad TEXT DEFAULT '',
            respuesta_seguridad TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS libros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            autor TEXT NOT NULL,
            genero TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
            origen TEXT NOT NULL,
            fecha_alta TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_usuario TEXT NOT NULL,
            id_libro INTEGER NOT NULL,
            fecha_prestamo TEXT NOT NULL,
            fecha_vencimiento TEXT NOT NULL,
            fecha_devolucion TEXT DEFAULT '',
            estado TEXT NOT NULL DEFAULT 'PRESTADO' CHECK (estado IN ('PRESTADO', 'DEVUELTO')),
            multa REAL NOT NULL DEFAULT 0,
            multa_pagada INTEGER NOT NULL DEFAULT 0 CHECK (multa_pagada IN (0, 1)),
            FOREIGN KEY (codigo_usuario) REFERENCES usuarios(codigo) ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (id_libro) REFERENCES libros(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_usuario TEXT NOT NULL,
            id_libro INTEGER DEFAULT NULL,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            autor TEXT DEFAULT '',
            genero TEXT DEFAULT '',
            comentario TEXT DEFAULT '',
            estado TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'APROBADA', 'RECHAZADA')),
            fecha TEXT NOT NULL,
            FOREIGN KEY (codigo_usuario) REFERENCES usuarios(codigo) ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            detalle TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_usuario TEXT NOT NULL,
            id_libro INTEGER NOT NULL,
            calificacion INTEGER NOT NULL CHECK (calificacion BETWEEN 1 AND 5),
            comentario TEXT DEFAULT '',
            fecha TEXT NOT NULL,
            UNIQUE(codigo_usuario, id_libro),
            FOREIGN KEY (codigo_usuario) REFERENCES usuarios(codigo) ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (id_libro) REFERENCES libros(id) ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_calificaciones_libro ON calificaciones(id_libro);
        CREATE INDEX IF NOT EXISTS idx_calificaciones_usuario ON calificaciones(codigo_usuario);

        CREATE INDEX IF NOT EXISTS idx_libros_titulo ON libros(titulo);
        CREATE INDEX IF NOT EXISTS idx_libros_autor ON libros(autor);
        CREATE INDEX IF NOT EXISTS idx_libros_genero ON libros(genero);
        CREATE INDEX IF NOT EXISTS idx_prestamos_usuario ON prestamos(codigo_usuario);
        CREATE INDEX IF NOT EXISTS idx_prestamos_libro ON prestamos(id_libro);
        CREATE INDEX IF NOT EXISTS idx_solicitudes_usuario ON solicitudes(codigo_usuario);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_prestamo_activo_unico
            ON prestamos(codigo_usuario, id_libro)
            WHERE estado = 'PRESTADO';
        """)
        # Migracion para bases de datos creadas con versiones anteriores.
        columnas = {fila["name"] for fila in self.con.execute("PRAGMA table_info(usuarios)")}
        if "pregunta_seguridad" not in columnas:
            self.con.execute("ALTER TABLE usuarios ADD COLUMN pregunta_seguridad TEXT DEFAULT ''")
        if "respuesta_seguridad" not in columnas:
            self.con.execute("ALTER TABLE usuarios ADD COLUMN respuesta_seguridad TEXT DEFAULT ''")

        columnas = {fila["name"] for fila in self.con.execute("PRAGMA table_info(solicitudes)")}
        if "id_libro" not in columnas:
            self.con.execute("ALTER TABLE solicitudes ADD COLUMN id_libro INTEGER DEFAULT NULL")
        if "comentario" not in columnas:
            self.con.execute("ALTER TABLE solicitudes ADD COLUMN comentario TEXT DEFAULT ''")

        # Normalizamos los generos antiguos para que el sistema trabaje
        # solamente con las categorias permitidas.
        for antiguo, nuevo in MAPA_GENEROS_ANTIGUOS.items():
            self.con.execute(
                "UPDATE libros SET genero = ? WHERE lower(genero) = ?",
                (nuevo, antiguo)
            )
        placeholders = ",".join("?" for _ in GENEROS_PREDETERMINADOS)
        self.con.execute(
            f"UPDATE libros SET genero = 'Literatura' WHERE genero NOT IN ({placeholders})",
            GENEROS_PREDETERMINADOS
        )
        self.con.commit()

    def normalizar_generos(self):
        """Convierte categorias antiguas a las categorias oficiales del sistema."""
        for antiguo, nuevo in MAPA_GENEROS_ANTIGUOS.items():
            self.con.execute(
                "UPDATE libros SET genero = ? WHERE lower(genero) = ?",
                (nuevo, antiguo)
            )
        placeholders = ",".join("?" for _ in GENEROS_PREDETERMINADOS)
        self.con.execute(
            f"UPDATE libros SET genero = 'Literatura' WHERE genero NOT IN ({placeholders})",
            GENEROS_PREDETERMINADOS
        )
        self.con.commit()

    def asegurar_administrador(self):
        fila = self.con.execute(
            "SELECT codigo, rol FROM usuarios WHERE lower(codigo) = 'admin' LIMIT 1"
        ).fetchone()

        if fila is None:
            self.con.execute(
                """INSERT INTO usuarios
                   (codigo, nombre, telefono, rol, password, deuda, pagado,
                    pregunta_seguridad, respuesta_seguridad)
                   VALUES ('admin', 'Administrador', '00000000', 'ADMIN', ?, 0, 0, ?, ?)""",
                (
                    hash_password("Admin123!"),
                    "¿Cual es tu codigo de biblioteca?",
                    hash_password("admin")
                )
            )
            self.con.commit()

    def base_vacia(self):
        fila = self.con.execute("SELECT COUNT(*) AS total FROM usuarios").fetchone()
        return fila["total"] == 0

    def refrescar_cache(self):
        self.libros = [dict(f) for f in self.con.execute("SELECT id, titulo, autor, genero, stock, origen, fecha_alta FROM libros ORDER BY id")]
        self.usuarios = [dict(f) for f in self.con.execute("SELECT codigo, nombre, telefono, rol, password, deuda, pagado, pregunta_seguridad, respuesta_seguridad FROM usuarios ORDER BY codigo")]
        self.prestamos = [dict(f) for f in self.con.execute("SELECT id, codigo_usuario, id_libro, fecha_prestamo, fecha_vencimiento, fecha_devolucion, estado, multa, multa_pagada FROM prestamos ORDER BY id")]
        for p in self.prestamos:
            p["multa_pagada"] = bool(p["multa_pagada"])
        self.solicitudes = [dict(f) for f in self.con.execute("SELECT id, codigo_usuario, id_libro, tipo, titulo, autor, genero, comentario, estado, fecha FROM solicitudes ORDER BY id")]
        self.movimientos = [dict(f) for f in self.con.execute("SELECT fecha, tipo, detalle FROM movimientos ORDER BY id")]
        self.calificaciones = [dict(f) for f in self.con.execute(
            "SELECT id, codigo_usuario, id_libro, calificacion, comentario, fecha "
            "FROM calificaciones ORDER BY id"
        )]

    def puede_calificar(self, codigo_usuario, libro_id):
        # Solo puede calificar quien haya tenido el libro y ya lo haya devuelto.
        fila = self.con.execute(
            """SELECT 1 FROM prestamos
               WHERE codigo_usuario = ? AND id_libro = ? AND estado = 'DEVUELTO'
               LIMIT 1""",
            (codigo_usuario, libro_id)
        ).fetchone()
        return fila is not None

    def obtener_calificacion_usuario(self, codigo_usuario, libro_id):
        fila = self.con.execute(
            """SELECT id, codigo_usuario, id_libro, calificacion, comentario, fecha
               FROM calificaciones
               WHERE codigo_usuario = ? AND id_libro = ?
               LIMIT 1""",
            (codigo_usuario, libro_id)
        ).fetchone()
        return dict(fila) if fila else None

    def guardar_calificacion(self, codigo_usuario, libro_id, calificacion, comentario):
        if not self.puede_calificar(codigo_usuario, libro_id):
            return False, "Solo puede calificar un libro que haya tomado en prestamo y devuelto."

        if not 1 <= int(calificacion) <= 5:
            return False, "La calificacion debe estar entre 1 y 5."

        comentario = comentario.strip()

        try:
            self.con.execute(
                """INSERT INTO calificaciones
                   (codigo_usuario, id_libro, calificacion, comentario, fecha)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(codigo_usuario, id_libro)
                   DO UPDATE SET calificacion=excluded.calificacion,
                                 comentario=excluded.comentario,
                                 fecha=excluded.fecha""",
                (codigo_usuario, libro_id, int(calificacion), comentario, hoy_texto())
            )
            libro = self.buscar_libro(libro_id)
            titulo = libro["titulo"] if libro else "Desconocido"
            self.registrar_movimiento(
                "CALIFICACION",
                f"{codigo_usuario} califico '{titulo}' con {int(calificacion)}/5."
            )
            self.con.commit()
            self.refrescar_cache()
            return True, "Calificacion guardada correctamente."
        except sqlite3.Error:
            self.con.rollback()
            return False, "No se pudo guardar la calificacion."

    def opiniones_libro(self, libro_id):
        filas = self.con.execute(
            """SELECT c.calificacion, c.comentario, c.fecha,
                      u.nombre, u.codigo
               FROM calificaciones c
               JOIN usuarios u ON u.codigo = c.codigo_usuario
               WHERE c.id_libro = ?
               ORDER BY c.id DESC""",
            (libro_id,)
        ).fetchall()
        return [dict(f) for f in filas]

    def resumen_libro(self, libro_id):
        fila = self.con.execute(
            """SELECT COUNT(*) AS cantidad,
                      COALESCE(AVG(calificacion), 0) AS promedio
               FROM calificaciones
               WHERE id_libro = ?""",
            (libro_id,)
        ).fetchone()
        return {"cantidad": fila["cantidad"], "promedio": float(fila["promedio"] or 0)}

    def libros_mejor_calificados(self, limite=10):
        filas = self.con.execute(
            """SELECT l.id, l.titulo, l.autor,
                      COUNT(c.id) AS cantidad,
                      COALESCE(AVG(c.calificacion), 0) AS promedio
               FROM libros l
               LEFT JOIN calificaciones c ON c.id_libro = l.id
               GROUP BY l.id
               HAVING COUNT(c.id) > 0
               ORDER BY promedio DESC, cantidad DESC, l.titulo
               LIMIT ?""",
            (limite,)
        ).fetchall()
        return [dict(f) for f in filas]

    def libros_mas_leidos(self, limite=10):
        filas = self.con.execute(
            """SELECT l.id, l.titulo, l.autor,
                      COUNT(p.id) AS prestamos
               FROM libros l
               LEFT JOIN prestamos p ON p.id_libro = l.id
               GROUP BY l.id
               HAVING COUNT(p.id) > 0
               ORDER BY prestamos DESC, l.titulo
               LIMIT ?""",
            (limite,)
        ).fetchall()
        return [dict(f) for f in filas]

    def cerrar(self):
        try:
            self.con.close()
        except sqlite3.Error:
            pass

    def datos_iniciales(self):
        self.con.execute("DELETE FROM prestamos")
        self.con.execute("DELETE FROM solicitudes")
        self.con.execute("DELETE FROM movimientos")
        self.con.execute("DELETE FROM libros")
        self.con.execute("DELETE FROM usuarios")

        for libro in LIBROS_INICIALES:
            self.con.execute(
                "INSERT INTO libros (id, titulo, autor, genero, stock, origen, fecha_alta) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (libro["id"], libro["titulo"], libro["autor"], libro["genero"], libro["stock"], libro["origen"], libro["fecha_alta"])
            )

        for usuario in USUARIOS_INICIALES:
            pregunta = "¿Cual es tu codigo de biblioteca?"
            respuesta = usuario["codigo"]
            self.con.execute(
                "INSERT INTO usuarios (codigo, nombre, telefono, rol, password, deuda, pagado, pregunta_seguridad, respuesta_seguridad) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    usuario["codigo"], usuario["nombre"], usuario["telefono"], usuario["rol"],
                    hash_password(usuario["password"]), usuario["deuda"], usuario["pagado"],
                    pregunta, hash_password(respuesta.lower())
                )
            )

        self.con.execute(
            "INSERT INTO movimientos (fecha, tipo, detalle) VALUES (?, ?, ?)",
            (hoy_texto(), "SISTEMA", "Sistema iniciado con datos iniciales.")
        )
        self.con.commit()
        self.refrescar_cache()

    def guardar_datos(self):
        """La informacion se guarda inmediatamente con cada INSERT/UPDATE/DELETE.
        Se mantiene este metodo para compatibilidad con la interfaz existente."""
        try:
            self.con.commit()
            self.refrescar_cache()
        except sqlite3.Error:
            self.con.rollback()

    def obtener_multa_por_dia(self):
        """Devuelve la multa configurada por cada día de atraso."""
        fila = self.con.execute(
            "SELECT valor FROM configuracion WHERE clave = 'multa_por_dia' LIMIT 1"
        ).fetchone()

        if fila is None:
            # Valor inicial: L.100 por día.
            self.con.execute(
                "INSERT INTO configuracion (clave, valor) VALUES ('multa_por_dia', '100')"
            )
            self.con.commit()
            return 100.0

        try:
            return float(fila["valor"])
        except (ValueError, TypeError):
            return 100.0

    def cambiar_multa_por_dia(self, nuevo_monto):
        """Guarda la nueva multa y la deja disponible para futuros cálculos."""
        try:
            nuevo_monto = float(nuevo_monto)
        except (ValueError, TypeError):
            return False, "Ingrese un monto numerico."

        if nuevo_monto < 0:
            return False, "La multa no puede ser negativa."

        try:
            self.con.execute(
                """INSERT INTO configuracion (clave, valor)
                   VALUES ('multa_por_dia', ?)
                   ON CONFLICT(clave)
                   DO UPDATE SET valor = excluded.valor""",
                (str(nuevo_monto),)
            )
            self.registrar_movimiento(
                "CONFIGURACION",
                f"Se cambio la multa diaria a L.{nuevo_monto:.2f}."
            )
            self.con.commit()
            self.refrescar_cache()
            return True, f"La multa por dia ahora es de L.{nuevo_monto:.2f}."
        except sqlite3.Error:
            self.con.rollback()
            return False, "No se pudo guardar la nueva multa."

    def registrar_movimiento(self, tipo, detalle):
        self.con.execute(
            "INSERT INTO movimientos (fecha, tipo, detalle) VALUES (?, ?, ?)",
            (hoy_texto(), tipo, detalle)
        )

    # --------------------------------------------------------
    # BUSQUEDAS
    # --------------------------------------------------------

    def buscar_usuario(self, codigo):
        fila = self.con.execute(
            "SELECT codigo, nombre, telefono, rol, password, deuda, pagado, pregunta_seguridad, respuesta_seguridad FROM usuarios WHERE lower(codigo) = lower(?)",
            (codigo,)
        ).fetchone()
        return dict(fila) if fila else None
       
    def buscar_usuarios_por_nombre(self, nombre):
        nombre = (nombre or "").strip()
        filas = self.con.execute(
            "SELECT codigo, nombre, telefono, rol, password, deuda, pagado FROM usuarios WHERE lower(nombre) = lower(?)",
            (nombre,)
        ).fetchall()
        return [dict(f) for f in filas]
    
    def obtener_pregunta_seguridad(self, codigo):
        """Devuelve la pregunta de seguridad asignada a un usuario, o None si no existe."""
        fila = self.con.execute(
            "SELECT pregunta_seguridad FROM usuarios WHERE lower(codigo) = lower(?)",
            (codigo,)
        ).fetchone()
        return fila["pregunta_seguridad"] if fila else None
    
    def buscar_libro(self, libro_id):
        fila = self.con.execute(
            "SELECT id, titulo, autor, genero, stock, origen, fecha_alta FROM libros WHERE id = ?",
            (libro_id,)
        ).fetchone()
        return dict(fila) if fila else None

    def buscar_libro_por_titulo(self, titulo):
        fila = self.con.execute(
            "SELECT id, titulo, autor, genero, stock, origen, fecha_alta FROM libros WHERE lower(titulo) = lower(?)",
            (titulo,)
        ).fetchone()
        return dict(fila) if fila else None

    def siguiente_id_libro(self):
        fila = self.con.execute("SELECT COALESCE(MAX(id), 0) + 1 AS siguiente FROM libros").fetchone()
        return fila["siguiente"]

    def siguiente_id_prestamo(self):
        fila = self.con.execute("SELECT COALESCE(MAX(id), 0) + 1 AS siguiente FROM prestamos").fetchone()
        return fila["siguiente"]

    def siguiente_id_solicitud(self):
        fila = self.con.execute("SELECT COALESCE(MAX(id), 0) + 1 AS siguiente FROM solicitudes").fetchone()
        return fila["siguiente"]

    # --------------------------------------------------------
    # USUARIOS
    # --------------------------------------------------------

    def autenticar(self, codigo, password):
        codigo = codigo.strip()

        # Primero buscamos por codigo, sin importar mayusculas/minusculas.
        fila = self.con.execute(
            """SELECT codigo, nombre, telefono, rol, password, deuda, pagado
               FROM usuarios
               WHERE lower(codigo) = lower(?)""",
            (codigo,)
        ).fetchone()

        if fila is None:
            return None

        usuario = dict(fila)
        clave_guardada = usuario["password"]
        clave_ingresada = hash_password(password)

        # Funcion normal: contraseña almacenada como hash.
        if clave_guardada == clave_ingresada:
            return usuario

        # Compatibilidad con versiones anteriores que pudieron guardar
        # la contraseña sin hash.
        if clave_guardada == password:
            self.con.execute(
                "UPDATE usuarios SET password = ? WHERE codigo = ?",
                (clave_ingresada, usuario["codigo"])
            )
            self.con.commit()
            usuario["password"] = clave_ingresada
            return usuario

        # Recuperacion del administrador inicial de la version del proyecto.
        # Solo se usa si se escribe exactamente la clave inicial.
        if usuario["rol"] == "ADMIN" and password == "Admin123!":
            self.con.execute(
                "UPDATE usuarios SET password = ? WHERE codigo = ?",
                (hash_password("Admin123!"), usuario["codigo"])
            )
            self.con.commit()
            usuario["password"] = hash_password("Admin123!")
            return usuario

        return None


    def generar_codigo_usuario(self, telefono):
        base = telefono[-4:]

        # Preferimos los ultimos 4 digitos del telefono.
        if self.buscar_usuario(base) is None:
            return base

        # Si ya existe, agregamos un identificador consecutivo.
        numero = 1
        while True:
            codigo = f"{base}{numero:02d}"
            if self.buscar_usuario(codigo) is None:
                return codigo
            numero += 1

    def restablecer_password_admin(self, codigo_usuario, password_admin):
        """El administrador restablece la contraseña de un usuario."""
        admin = self.con.execute(
            "SELECT codigo, password, rol, nombre FROM usuarios WHERE lower(codigo) = 'admin' LIMIT 1"
        ).fetchone()

        if admin is None:
            return None, "No existe la cuenta de administrador."

        # Aceptar hash normal o contraseña antigua en texto para compatibilidad.
        correcto = (
            admin["password"] == hash_password(password_admin)
            or admin["password"] == password_admin
        )

        if not correcto:
            return None, "La contraseña del administrador no es correcta."

        usuario = self.buscar_usuario(codigo_usuario)
        if usuario is None:
            return None, "No se encontró el usuario seleccionado."

        if usuario["rol"] == "ADMIN" and usuario["codigo"].lower() == "admin":
            return None, "Para cambiar la contraseña del administrador use 'Cambiar contraseña'."

        nueva = generar_password(self.con)
        nuevo_hash = hash_password(nueva)

        try:
            self.con.execute(
                "UPDATE usuarios SET password = ? WHERE codigo = ?",
                (nuevo_hash, codigo_usuario)
            )
            self.registrar_movimiento(
                "SEGURIDAD",
                f"El administrador restablecio la contraseña de {usuario['nombre']}."
            )
            self.con.commit()
            self.refrescar_cache()
            return nueva, ""
        except sqlite3.Error:
            self.con.rollback()
            return None, "No se pudo restablecer la contraseña."

    def crear_usuario(self, nombre, telefono, password=None, pregunta_seguridad="", respuesta_seguridad=""):
        nombre = nombre.strip()
        telefono = telefono.strip()
        respuesta_seguridad = respuesta_seguridad.strip()

        if not nombre:
            return None, "El nombre es obligatorio."
        if not telefono.isdigit():
            return None, "El telefono debe contener solo numeros."
        if len(telefono) < 4:
            return None, "El telefono debe tener al menos 4 digitos."
        if pregunta_seguridad not in PREGUNTAS_SEGURIDAD:
            return None, "Selecciona una pregunta de seguridad valida."
        if not respuesta_seguridad:
            return None, "La respuesta de seguridad es obligatoria."

        codigo = self.generar_codigo_usuario(telefono)
        
        if self.con.execute("SELECT 1 FROM usuarios WHERE telefono = ?", (telefono,)).fetchone():
            return None, "Ya existe un usuario con ese telefono."

        if password is None:
            password = generar_password(self.con)
        else:
            if self.con.execute(
                "SELECT 1 FROM usuarios WHERE password = ? LIMIT 1",
                (hash_password(password),)
            ).fetchone():
                return None, "Esa contraseña ya esta utilizada. Elija otra."

        try:
            self.con.execute(
                """INSERT INTO usuarios
                (codigo, nombre, telefono, rol, password, deuda, pagado, pregunta_seguridad, respuesta_seguridad)
                VALUES (?, ?, ?, 'CLIENTE', ?, 0, 0, ?, ?)""",
                (codigo, nombre, telefono, hash_password(password),
                 pregunta_seguridad, hash_password(respuesta_seguridad.lower()))
            )
            self.registrar_movimiento("USUARIO", f"Se registro el usuario {nombre}.")
            self.con.commit()
            self.refrescar_cache()
            return {
                "usuario": self.buscar_usuario(codigo),
                "password_inicial": password,
                "pregunta_seguridad": pregunta_seguridad,
            }, ""
        except sqlite3.IntegrityError:
            self.con.rollback()
            return None, "No se pudo registrar el usuario."

    def cambiar_password(self, usuario, nueva_password):
        nuevo_hash = hash_password(nueva_password)
        self.con.execute("UPDATE usuarios SET password = ? WHERE codigo = ?", (nuevo_hash, usuario["codigo"]))
        usuario["password"] = nuevo_hash
        self.registrar_movimiento("SEGURIDAD", f"Se cambio la contrasena de {usuario['nombre']}.")
        self.con.commit()
        self.refrescar_cache()

    def recuperar_password(self, codigo, telefono, respuesta):
        usuario = self.buscar_usuario(codigo)
        if usuario is None:
            return None, "No se encontro el usuario."

        if usuario["telefono"] != telefono.strip():
            return None, "El telefono no coincide con el registrado."

        if not usuario.get("respuesta_seguridad"):
            return None, "Esta cuenta no tiene configurada la recuperacion segura."

        if usuario["respuesta_seguridad"] != hash_password(respuesta.strip().lower()):
            return None, "La respuesta de seguridad no coincide."

        nueva = generar_password(self.con)
        self.con.execute(
            "UPDATE usuarios SET password = ? WHERE codigo = ?",
            (hash_password(nueva), codigo)
        )
        self.registrar_movimiento("SEGURIDAD", f"Se recupero la contrasena de {usuario['nombre']}.")
        self.con.commit()
        self.refrescar_cache()
        return nueva, ""

    def registrar_pago(self, codigo_usuario, monto):
        usuario = self.buscar_usuario(codigo_usuario)
        if usuario is None:
            return False, "Usuario no encontrado."

        if monto <= 0:
            return False, "El monto debe ser mayor que 0."

        if monto > usuario["deuda"]:
            return False, "El pago supera la deuda pendiente."

        nueva_deuda = usuario["deuda"] - monto
        nuevo_pagado = usuario["pagado"] + monto
        self.con.execute(
            "UPDATE usuarios SET deuda = ?, pagado = ? WHERE codigo = ?",
            (nueva_deuda, nuevo_pagado, codigo_usuario)
        )
        self.con.execute(
            "UPDATE prestamos SET multa_pagada = 1 WHERE codigo_usuario = ? AND multa > 0 AND multa_pagada = 0 AND ABS(multa - ?) < 0.000001",
            (codigo_usuario, monto)
        )
        self.registrar_movimiento("PAGO", f"{usuario['nombre']} pago L.{monto:.2f}.")
        self.con.commit()
        self.refrescar_cache()
        return True, "Pago registrado."

    # --------------------------------------------------------
    # LIBROS
    # --------------------------------------------------------

    def agregar_libro(self, titulo, autor, genero, stock, origen):
        genero = genero.strip()
        if genero not in GENEROS_PREDETERMINADOS:
            raise ValueError("Genero no permitido.")
        cursor = self.con.execute(
            "INSERT INTO libros (titulo, autor, genero, stock, origen, fecha_alta) VALUES (?, ?, ?, ?, ?, ?)",
            (titulo, autor, genero, stock, origen, hoy_texto())
        )
        self.registrar_movimiento("LIBRO", f"Se agrego el libro '{titulo}'.")
        self.con.commit()
        self.refrescar_cache()
        return self.buscar_libro(cursor.lastrowid)

    def editar_libro(self, libro_id, titulo, autor, genero, stock, origen):
        genero = genero.strip()
        if genero not in GENEROS_PREDETERMINADOS:
            return False
        libro = self.buscar_libro(libro_id)
        if libro is None:
            return False

        self.con.execute(
            "UPDATE libros SET titulo = ?, autor = ?, genero = ?, stock = ?, origen = ? WHERE id = ?",
            (titulo, autor, genero, stock, origen, libro_id)
        )
        self.registrar_movimiento("LIBRO", f"Se modifico el libro '{titulo}'.")
        self.con.commit()
        self.refrescar_cache()
        return True

    def eliminar_libro(self, libro_id):
        libro = self.buscar_libro(libro_id)
        if libro is None:
            return False, "Libro no encontrado."

        activo = self.con.execute(
            "SELECT 1 FROM prestamos WHERE id_libro = ? AND estado = 'PRESTADO' LIMIT 1",
            (libro_id,)
        ).fetchone()
        if activo:
            return False, "No puede eliminar un libro con un prestamo activo."

        historico = self.con.execute("SELECT 1 FROM prestamos WHERE id_libro = ? LIMIT 1", (libro_id,)).fetchone()
        if historico:
            return False, "No puede eliminar un libro que tiene historial de prestamos."

        self.con.execute("DELETE FROM libros WHERE id = ?", (libro_id,))
        self.registrar_movimiento("LIBRO", f"Se elimino el libro '{libro['titulo']}'.")
        self.con.commit()
        self.refrescar_cache()
        return True, "Libro eliminado."

    def buscar_libros(self, texto="", autor="", genero=""):
        sql = """
            SELECT id, titulo, autor, genero, stock, origen, fecha_alta
            FROM libros
            WHERE 1 = 1
        """
        parametros = []

        texto = texto.strip()
        autor = autor.strip()
        genero = genero.strip()

        if texto:
            sql += " AND (lower(titulo) LIKE ? OR lower(autor) LIKE ?)"
            patron = f"%{texto.lower()}%"
            parametros.extend([patron, patron])

        if autor:
            sql += " AND lower(autor) LIKE ?"
            parametros.append(f"%{autor.lower()}%")

        if genero:
            sql += " AND lower(genero) = ?"
            parametros.append(genero.lower())

        sql += " ORDER BY id"
        return [dict(f) for f in self.con.execute(sql, parametros)]

    # --------------------------------------------------------
    # PRESTAMOS
    # --------------------------------------------------------

    def prestamos_usuario(self, codigo):
        return [dict(f) for f in self.con.execute(
            "SELECT id, codigo_usuario, id_libro, fecha_prestamo, fecha_vencimiento, fecha_devolucion, estado, multa, multa_pagada FROM prestamos WHERE codigo_usuario = ? ORDER BY id",
            (codigo,)
        )]

    def activos_usuario(self, codigo):
        return [dict(f) for f in self.con.execute(
            "SELECT id, codigo_usuario, id_libro, fecha_prestamo, fecha_vencimiento, fecha_devolucion, estado, multa, multa_pagada FROM prestamos WHERE codigo_usuario = ? AND estado = 'PRESTADO' ORDER BY id",
            (codigo,)
        )]

    def crear_prestamo(self, codigo_usuario, libro_id):
        usuario = self.buscar_usuario(codigo_usuario)
        libro = self.buscar_libro(libro_id)

        if usuario is None:
            return False, "Usuario no encontrado."
        if libro is None:
            return False, "El libro no existe."

        if usuario["rol"] == "CLIENTE":
            vencidos = [p for p in self.activos_usuario(codigo_usuario) if self.estado_prestamo(p) == "VENCIDO"]
            if vencidos:
                return False, (
                    "Tienes un prestamo vencido. Debes devolver el libro y pagar la multa "
                    "correspondiente antes de solicitar otro."
                )

        activos = self.activos_usuario(codigo_usuario)
       
        if len(activos) >= MAX_LIBROS:
            return False, "El usuario ya tiene el maximo de prestamos."

        repetido = self.con.execute(
            "SELECT 1 FROM prestamos WHERE codigo_usuario = ? AND id_libro = ? AND estado = 'PRESTADO'",
            (codigo_usuario, libro_id)
        ).fetchone()
        if repetido:
            return False, "El usuario ya tiene este libro prestado."

        libro_actual = self.buscar_libro(libro_id)
        if libro_actual is None or libro_actual["stock"] <= 0:
            return False, "NO DISPONIBLE"

        fecha_prestamo = date.today()
        fecha_vencimiento = fecha_prestamo + timedelta(days=DIAS_PRESTAMO)

        try:
            self.con.execute("UPDATE libros SET stock = stock - 1 WHERE id = ? AND stock > 0", (libro_id,))
            if self.con.execute("SELECT changes() AS c").fetchone()["c"] != 1:
                self.con.rollback()
                return False, "NO DISPONIBLE"

            cursor = self.con.execute(
                """INSERT INTO prestamos
                (codigo_usuario, id_libro, fecha_prestamo, fecha_vencimiento, fecha_devolucion, estado, multa, multa_pagada)
                VALUES (?, ?, ?, ?, ?, 'PRESTADO', 0, 1)""",
                (codigo_usuario, libro_id, fecha_prestamo.isoformat(), fecha_vencimiento.isoformat(), "")
            )
            self.registrar_movimiento("PRESTAMO", f"{usuario['nombre']} saco '{libro['titulo']}'.")
            self.con.commit()
            self.refrescar_cache()
            return True, fecha_vencimiento
        except sqlite3.Error:
            self.con.rollback()
            return False, "No se pudo registrar el prestamo."

    def devolver_prestamo_por_id(self, prestamo_id):
        fila = self.con.execute(
            """SELECT id, codigo_usuario, id_libro, fecha_prestamo,
                      fecha_vencimiento, fecha_devolucion, estado, multa, multa_pagada
               FROM prestamos
               WHERE id = ? AND estado = 'PRESTADO'
               LIMIT 1""",
            (prestamo_id,)
        ).fetchone()

        if not fila:
            return False, 0

        prestamo = dict(fila)
        hoy = date.today()
        vencimiento = date.fromisoformat(prestamo["fecha_vencimiento"])
        dias_atraso = max((hoy - vencimiento).days, 0)
        multa = dias_atraso * self.obtener_multa_por_dia()

        libro = self.buscar_libro(prestamo["id_libro"])
        usuario = self.buscar_usuario(prestamo["codigo_usuario"])

        try:
            if libro:
                self.con.execute(
                    "UPDATE libros SET stock = stock + 1 WHERE id = ?",
                    (prestamo["id_libro"],)
                )

            self.con.execute(
                """UPDATE prestamos
                   SET estado='DEVUELTO',
                       fecha_devolucion=?,
                       multa=?,
                       multa_pagada=?
                   WHERE id=?""",
                (
                    hoy.isoformat(),
                    multa,
                    1 if multa == 0 else 0,
                    prestamo_id
                )
            )

            if usuario and multa > 0:
                self.con.execute(
                    "UPDATE usuarios SET deuda = deuda + ? WHERE codigo = ?",
                    (multa, prestamo["codigo_usuario"])
                )

            titulo = libro["titulo"] if libro else "Desconocido"
            nombre = usuario["nombre"] if usuario else prestamo["codigo_usuario"]

            self.registrar_movimiento(
                "DEVOLUCION",
                f"{nombre} devolvio '{titulo}'."
            )

            self.con.commit()
            self.refrescar_cache()
            return True, multa

        except sqlite3.Error:
            self.con.rollback()
            return False, 0

    def devolver_libro(self, codigo_usuario, libro_id):
        prestamo = self.con.execute(
            """SELECT id, codigo_usuario, id_libro, fecha_prestamo, fecha_vencimiento,
                      fecha_devolucion, estado, multa, multa_pagada
               FROM prestamos
               WHERE codigo_usuario = ? AND id_libro = ? AND estado = 'PRESTADO'
               LIMIT 1""",
            (codigo_usuario, libro_id)
        ).fetchone()

        if not prestamo:
            return False, 0

        prestamo = dict(prestamo)
        hoy = date.today()
        vencimiento = date.fromisoformat(prestamo["fecha_vencimiento"])
        dias_atraso = max((hoy - vencimiento).days, 0)
        multa = dias_atraso * self.obtener_multa_por_dia()

        libro = self.buscar_libro(libro_id)
        usuario = self.buscar_usuario(codigo_usuario)

        try:
            if libro:
                self.con.execute("UPDATE libros SET stock = stock + 1 WHERE id = ?", (libro_id,))

            self.con.execute(
                "UPDATE prestamos SET estado = 'DEVUELTO', fecha_devolucion = ?, multa = ?, multa_pagada = ? WHERE id = ?",
                (hoy.isoformat(), multa, 1 if multa == 0 else 0, prestamo["id"])
            )

            if usuario:
                self.con.execute("UPDATE usuarios SET deuda = deuda + ? WHERE codigo = ?", (multa, codigo_usuario))

            titulo = libro["titulo"] if libro else "Desconocido"
            nombre = usuario["nombre"] if usuario else codigo_usuario
            self.registrar_movimiento("DEVOLUCION", f"{nombre} devolvio '{titulo}'.")
            self.con.commit()
            self.refrescar_cache()
            return True, multa
        except sqlite3.Error:
            self.con.rollback()
            return False, 0

    def estado_prestamo(self, prestamo):
        if prestamo["estado"] == "DEVUELTO":
            return "DEVUELTO"

        vencimiento = date.fromisoformat(prestamo["fecha_vencimiento"])
        diferencia = (vencimiento - date.today()).days

        if diferencia < 0:
            return "VENCIDO"
        if diferencia == 0:
            return "VENCE HOY"
        if diferencia == 1:
            return "FALTA 1 DIA"
        if diferencia == 2:
            return "FALTAN 2 DIAS"

        return "VIGENTE"

    # --------------------------------------------------------
    # SOLICITUDES
    # --------------------------------------------------------

    def crear_solicitud(self, codigo_usuario, tipo, titulo, autor="", genero="", comentario="", id_libro=None):
        if genero and genero not in GENEROS_PREDETERMINADOS:
            return None
        cursor = self.con.execute(
            """INSERT INTO solicitudes
               (codigo_usuario, id_libro, tipo, titulo, autor, genero, comentario, estado, fecha)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', ?)""",
            (codigo_usuario, id_libro, tipo, titulo, autor, genero, comentario, hoy_texto())
        )
        self.registrar_movimiento("SOLICITUD", f"Nueva solicitud de tipo {tipo}: '{titulo}'.")
        self.con.commit()
        self.refrescar_cache()
        fila = self.con.execute(
            "SELECT id, codigo_usuario, id_libro, tipo, titulo, autor, genero, comentario, estado, fecha FROM solicitudes WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()
        return dict(fila)

    def cambiar_estado_solicitud(self, solicitud_id, estado):
        fila = self.con.execute("SELECT 1 FROM solicitudes WHERE id = ?", (solicitud_id,)).fetchone()
        if not fila:
            return False

        self.con.execute("UPDATE solicitudes SET estado = ? WHERE id = ?", (estado, solicitud_id))
        self.registrar_movimiento("SOLICITUD", f"Solicitud #{solicitud_id}: {estado}.")
        self.con.commit()
        self.refrescar_cache()
        return True


