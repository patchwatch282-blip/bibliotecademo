

import streamlit as st
from datetime import date

from biblioteca_core import (
    Biblioteca,
    GENEROS_PREDETERMINADOS,
    PREGUNTAS_SEGURIDAD,
    fecha_legible,
    hoy_texto,
)

st.set_page_config(page_title="Biblioteca", page_icon="", layout="wide")


# ============================================================
# CONEXION A LA BASE DE DATOS (una sola instancia compartida)
# ============================================================

@st.cache_resource
def obtener_biblioteca():
    return Biblioteca()


db = obtener_biblioteca()

# ============================================================
# ESTADO DE SESION
# ============================================================

if "usuario" not in st.session_state:
    st.session_state.usuario = None


def usuario_actual():
    """Siempre relee el usuario desde la base para tener datos frescos (deuda, etc.)."""
    if st.session_state.usuario is None:
        return None
    return db.buscar_usuario(st.session_state.usuario["codigo"])


def cerrar_sesion():
    st.session_state.usuario = None
    st.rerun()


# ============================================================
# PANTALLAS: LOGIN / REGISTRO / RECUPERAR
# ============================================================

def pantalla_login():
    st.title("Sistema de Biblioteca")
    tab_login, tab_registro, tab_recuperar = st.tabs(
        ["Iniciar sesion", "Registrarme", "Recuperar contraseña"]
    )

    with tab_login:
        with st.form("form_login"):
            nombre = st.text_input("Nombre de usuario")
            password = st.text_input("Contraseña", type="password")
            enviado = st.form_submit_button("Entrar", type="primary")
        if enviado:
            coincidencias = db.buscar_usuarios_por_nombre(nombre)
            if not coincidencias:
                st.error("No existe ningun usuario con ese nombre.")
            elif len(coincidencias) > 1:
                st.error(
                    "Hay mas de un usuario registrado con ese nombre exacto. "
                    "Pide a un administrador tu codigo de usuario para poder entrar."
                )
            else:
                usuario = db.autenticar(coincidencias[0]["codigo"], password)
                if usuario:
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
     
    with tab_registro:
        with st.form("form_registro"):
            nombre = st.text_input("Nombre completo")
            telefono = st.text_input("Telefono")
            pregunta = st.selectbox("Pregunta de seguridad", PREGUNTAS_SEGURIDAD)
            respuesta = st.text_input("Respuesta de seguridad")
            enviado = st.form_submit_button("Registrarme", type="primary")
        if enviado:
            resultado, error = db.crear_usuario(nombre, telefono, None, pregunta, respuesta)
            if error:
                st.error(error)
            else:
                st.success(
                    f"Registro exitoso. Tu codigo es **{resultado['usuario']['codigo']}** "
                    f"y tu contraseña inicial es **{resultado['password_inicial']}**. "
                    "Guardala, no se volvera a mostrar."
                )

    with tab_recuperar:
        if "recuperar_pregunta" not in st.session_state:
            st.session_state.recuperar_pregunta = None
            st.session_state.recuperar_codigo = ""

        codigo_buscar = st.text_input("Codigo de usuario", key="rec_codigo_buscar")
        if st.button("Buscar mi pregunta de seguridad"):
            pregunta = db.obtener_pregunta_seguridad(codigo_buscar)
            if pregunta:
                st.session_state.recuperar_pregunta = pregunta
                st.session_state.recuperar_codigo = codigo_buscar
            else:
                st.session_state.recuperar_pregunta = None
                st.error("No existe ningun usuario con ese codigo.")

        if st.session_state.recuperar_pregunta:
            st.write(f"**Tu pregunta:** {st.session_state.recuperar_pregunta}")
            with st.form("form_recuperar"):
                telefono = st.text_input("Telefono registrado", key="rec_tel")
                respuesta = st.text_input("Respuesta de seguridad", key="rec_resp")
                enviado = st.form_submit_button("Recuperar", type="primary")
            if enviado:
                nueva, error = db.recuperar_password(st.session_state.recuperar_codigo, telefono, respuesta)
                if error:
                    st.error(error)
                else:
                    st.success(f"Tu nueva contrasena es: **{nueva}**")
                    st.session_state.recuperar_pregunta = None


# ============================================================
# PANTALLAS COMUNES (cliente y admin)
# ============================================================

def pantalla_catalogo(usuario):
    st.header("Catalogo de libros")
    col1, col2, col3 = st.columns(3)
    texto = col1.text_input("Buscar por titulo o autor")
    autor = col2.text_input("Filtrar por autor")
    genero = col3.selectbox("Genero", [""] + GENEROS_PREDETERMINADOS)

    libros = db.buscar_libros(texto=texto, autor=autor, genero=genero)
    if not libros:
        st.info("No se encontraron libros con esos filtros.")
        return

    for libro in libros:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.subheader(libro["titulo"])
                st.caption(f"{libro['autor']} · {libro['genero']} · Origen: {libro['origen']}")
                resumen = db.resumen_libro(libro["id"])
                if resumen["cantidad"] > 0:
                    st.write(f" {resumen['promedio']:.1f}/5 ({resumen['cantidad']} opiniones)")
                else:
                    st.caption("Aun sin calificaciones.")
                st.write(f"Disponibles: **{libro['stock']}**")
            with c2:
                if usuario["rol"] == "CLIENTE" and libro["stock"] > 0:
                    if st.button("Pedir prestado", key=f"prestar_{libro['id']}"):
                        ok, resultado = db.crear_prestamo(usuario["codigo"], libro["id"])
                        if ok:
                            st.success(f"Prestamo registrado. Vence el {fecha_legible(resultado.isoformat())}.")
                            st.rerun()
                        else:
                            st.error(resultado)
                elif usuario["rol"] == "CLIENTE":
                    st.button("No disponible", key=f"nodisp_{libro['id']}", disabled=True)

            if resumen["cantidad"] > 0:
                with st.popover("Ver opiniones"):
                    pantalla_opiniones_libro(libro)


def pantalla_opiniones_libro(libro):
    """Equivalente a mostrar_opiniones_libro() del original: detalle de comentarios de un libro."""
    resumen = db.resumen_libro(libro["id"])
    st.markdown(f"** {libro['titulo']}**")
    st.caption(f" {resumen['promedio']:.1f}/5 · {resumen['cantidad']} calificacion(es)")
    for opinion in db.opiniones_libro(libro["id"]):
        estrellas = "★" * opinion["calificacion"] + "☆" * (5 - opinion["calificacion"])
        st.write(f"**{opinion['nombre']}** — {estrellas}")
        st.caption(opinion["comentario"] or "(Sin comentario)")
        st.caption(fecha_legible(opinion["fecha"]))
        st.divider()


def pantalla_mis_prestamos(usuario):
    st.header(" Mis prestamos")
    prestamos = db.prestamos_usuario(usuario["codigo"])
    if not prestamos:
        st.info("Aun no tienes prestamos registrados.")
        return

    for prestamo in prestamos:
        libro = db.buscar_libro(prestamo["id_libro"])
        titulo = libro["titulo"] if libro else "Desconocido"
        estado = db.estado_prestamo(prestamo)
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"**{titulo}**")
                st.caption(
                    f"Prestado: {fecha_legible(prestamo['fecha_prestamo'])}  ·  "
                    f"Vence: {fecha_legible(prestamo['fecha_vencimiento'])}  ·  Estado: {estado}"
                )
                if prestamo["multa"] > 0:
                    st.caption(f"Multa: L.{prestamo['multa']:.2f} ({'pagada' if prestamo['multa_pagada'] else 'pendiente'})")
            with c2:
                if prestamo["estado"] == "PRESTADO":
                    if st.button("Devolver", key=f"devolver_{prestamo['id']}"):
                        ok, multa = db.devolver_prestamo_por_id(prestamo["id"])
                        if ok:
                            mensaje = "Libro devuelto."
                            if multa > 0:
                                mensaje += f" Se genero una multa de L.{multa:.2f}."
                            st.success(mensaje)
                            st.rerun()
                        else:
                            st.error("No se pudo registrar la devolucion.")
                elif db.puede_calificar(usuario["codigo"], prestamo["id_libro"]):
                    st.caption("Puedes calificarlo abajo")

    st.divider()
    st.subheader("Calificar un libro devuelto")
    libros_calificables = [
        db.buscar_libro(p["id_libro"])
        for p in prestamos
        if p["estado"] == "DEVUELTO" and db.puede_calificar(usuario["codigo"], p["id_libro"])
    ]
    libros_calificables = [l for l in libros_calificables if l]
    if not libros_calificables:
        st.caption("No tienes libros pendientes de calificar.")
        return

    opciones = {l["titulo"]: l["id"] for l in libros_calificables}
    seleccion = st.selectbox("Libro", list(opciones.keys()))
    libro_id = opciones[seleccion]
    anterior = db.obtener_calificacion_usuario(usuario["codigo"], libro_id)
    with st.form("form_calificar"):
        calificacion = st.slider("Calificacion", 1, 5, anterior["calificacion"] if anterior else 5)
        comentario = st.text_area("Comentario", value=anterior["comentario"] if anterior else "")
        enviado = st.form_submit_button("Guardar calificacion", type="primary")
    if enviado:
        ok, mensaje = db.guardar_calificacion(usuario["codigo"], libro_id, calificacion, comentario)
        (st.success if ok else st.error)(mensaje)


def pantalla_solicitudes(usuario):
    st.header(" Solicitudes")
    st.subheader("Nueva solicitud")
    with st.form("form_solicitud"):
        tipo = st.selectbox("Tipo", ["LIBRO_NUEVO", "NO_DISPONIBLE"])
        titulo = st.text_input("Titulo")
        autor = st.text_input("Autor (opcional)")
        genero = st.selectbox("Genero (opcional)", [""] + GENEROS_PREDETERMINADOS)
        comentario = st.text_area("Comentario (opcional)")
        enviado = st.form_submit_button("Enviar solicitud", type="primary")
    if enviado:
        if not titulo.strip():
            st.error("El titulo es obligatorio.")
        else:
            db.crear_solicitud(usuario["codigo"], tipo, titulo, autor, genero, comentario)
            st.success("Solicitud enviada.")
            st.rerun()

    st.divider()
    st.subheader("Mis solicitudes")
    propias = [s for s in db.solicitudes if s["codigo_usuario"] == usuario["codigo"]]
    if not propias:
        st.caption("No has enviado solicitudes.")
    else:
        st.dataframe(
            [{"Titulo": s["titulo"], "Tipo": s["tipo"], "Estado": s["estado"], "Fecha": fecha_legible(s["fecha"])}
             for s in reversed(propias)],
            use_container_width=True, hide_index=True,
        )


def pantalla_perfil(usuario):
    st.header(" Mi perfil")
    st.write(f"**Nombre:** {usuario['nombre']}")
    st.write(f"**Codigo:** {usuario['codigo']}")
    st.write(f"**Telefono:** {usuario['telefono']}")
    if usuario["rol"] != "ADMIN":
            st.write(f"**Deuda pendiente:** L.{usuario['deuda']:.2f}")
            st.write(f"**Total pagado:** L.{usuario['pagado']:.2f}")

    with st.expander("Cambiar mi contrasena"):
        with st.form("form_cambiar_password"):
            nueva = st.text_input("Nueva contraseña", type="password")
            confirmar = st.text_input("Confirmar contraseña", type="password")
            enviado = st.form_submit_button("Cambiar")
        if enviado:
            if not nueva or nueva != confirmar:
                st.error("Las contraseñas no coinciden.")
            else:
                db.cambiar_password(usuario, nueva)
                st.success("Contraseña actualizada.")

    if usuario["deuda"] > 0:
        with st.expander("Pagar deuda"):
            with st.form("form_pagar"):
                monto = st.number_input("Monto a pagar", min_value=0.0, max_value=float(usuario["deuda"]), step=1.0)
                enviado = st.form_submit_button("Pagar")
            if enviado:
                ok, mensaje = db.registrar_pago(usuario["codigo"], monto)
                (st.success if ok else st.error)(mensaje)
                if ok:
                    st.rerun()


# ============================================================
# PANTALLAS SOLO ADMIN
# ============================================================

def pantalla_administrar_libros():
    st.header(" Administrar libros")

    with st.expander(" Agregar libro nuevo"):
        with st.form("form_agregar_libro"):
            titulo = st.text_input("Titulo")
            autor = st.text_input("Autor")
            genero = st.selectbox("Genero", GENEROS_PREDETERMINADOS)
            stock = st.number_input("Stock", min_value=0, step=1, value=1)
            origen = st.selectbox("Origen", ["Compra", "Donacion", "Intercambio"])
            enviado = st.form_submit_button("Agregar", type="primary")
        if enviado:
            if not titulo.strip() or not autor.strip():
                st.error("Titulo y autor son obligatorios.")
            else:
                db.agregar_libro(titulo, autor, genero, int(stock), origen)
                st.success("Libro agregado.")
                st.rerun()

    st.subheader("Libros existentes")
    for libro in db.libros:
        with st.container(border=True):
            with st.expander(f"{libro['titulo']} — {libro['autor']} (stock: {libro['stock']})"):
                with st.form(f"form_editar_{libro['id']}"):
                    titulo = st.text_input("Titulo", value=libro["titulo"], key=f"t_{libro['id']}")
                    autor = st.text_input("Autor", value=libro["autor"], key=f"a_{libro['id']}")
                    genero = st.selectbox(
                        "Genero", GENEROS_PREDETERMINADOS,
                        index=GENEROS_PREDETERMINADOS.index(libro["genero"]) if libro["genero"] in GENEROS_PREDETERMINADOS else 0,
                        key=f"g_{libro['id']}",
                    )
                    stock = st.number_input("Stock", min_value=0, step=1, value=libro["stock"], key=f"s_{libro['id']}")
                    origen = st.text_input("Origen", value=libro["origen"], key=f"o_{libro['id']}")
                    c1, c2 = st.columns(2)
                    guardar = c1.form_submit_button("Guardar cambios")
                    eliminar = c2.form_submit_button("Eliminar libro")
                if guardar:
                    db.editar_libro(libro["id"], titulo, autor, genero, int(stock), origen)
                    st.success("Libro actualizado.")
                    st.rerun()
                if eliminar:
                    ok, mensaje = db.eliminar_libro(libro["id"])
                    (st.success if ok else st.error)(mensaje)
                    if ok:
                        st.rerun()

def pantalla_usuarios_admin():
    st.header("Usuarios")
    st.dataframe(
        [{"Codigo": u["codigo"], "Nombre": u["nombre"], "Telefono": u["telefono"],
          "Rol": u["rol"], "Deuda": f"L.{u['deuda']:.2f}", "Pagado": f"L.{u['pagado']:.2f}"}
         for u in db.usuarios],
        use_container_width=True, hide_index=True,
    )

def pantalla_solicitudes_admin():
    st.header("Solicitudes de usuarios")
    pendientes = [s for s in db.solicitudes if s["estado"] == "PENDIENTE"]
    if not pendientes:
        st.info("No hay solicitudes pendientes.")
    for solicitud in pendientes:
        usuario = db.buscar_usuario(solicitud["codigo_usuario"])
        with st.container(border=True):
            st.write(f"**{solicitud['titulo']}** ({solicitud['tipo']}) — {usuario['nombre'] if usuario else solicitud['codigo_usuario']}")
            if solicitud["comentario"]:
                st.caption(solicitud["comentario"])
            c1, c2 = st.columns(2)
            if c1.button("Aprobar", key=f"aprobar_{solicitud['id']}"):
                db.cambiar_estado_solicitud(solicitud["id"], "APROBADA")
                st.rerun()
            if c2.button("Rechazar", key=f"rechazar_{solicitud['id']}"):
                db.cambiar_estado_solicitud(solicitud["id"], "RECHAZADA")
                st.rerun()

    st.divider()
    st.subheader("Historial de solicitudes")
    st.dataframe(
        [{"Titulo": s["titulo"], "Tipo": s["tipo"], "Estado": s["estado"], "Fecha": fecha_legible(s["fecha"])}
         for s in reversed(db.solicitudes)],
        use_container_width=True, hide_index=True,
    )


def pantalla_alertas(usuario):
    """Equivalente a mostrar_alertas(): admin ve todos los prestamos activos, cliente solo los suyos."""
    st.header("Alertas de prestamos!")
    activos = [p for p in db.prestamos if p["estado"] == "PRESTADO"]
    if usuario["rol"] != "ADMIN":
        activos = [p for p in activos if p["codigo_usuario"] == usuario["codigo"]]

    if not activos:
        st.info("No hay prestamos activos.")
        return
    filas = []
    for p in activos:
        u = db.buscar_usuario(p["codigo_usuario"])
        libro = db.buscar_libro(p["id_libro"])
        filas.append({
            "Usuario": u["nombre"] if u else "Desconocido",
            "Libro": libro["titulo"] if libro else "Desconocido",
            "Vencimiento": fecha_legible(p["fecha_vencimiento"]),
            "Estado": db.estado_prestamo(p),
            "Multa": f"L.{p.get('multa', 0):.2f}",
        })
    st.dataframe(filas, use_container_width=True, hide_index=True)


def pantalla_historial_admin():
    """Equivalente a mostrar_historial(): el admin busca prestamos de cualquier usuario y puede devolverlos."""
    st.header("Prestamos e historial")
    busqueda = st.text_input("Buscar usuario (codigo o nombre)")

    filtro = busqueda.strip().lower()
    filas_mostradas = []
    for prestamo in db.prestamos:
        usuario = db.buscar_usuario(prestamo["codigo_usuario"])
        libro = db.buscar_libro(prestamo["id_libro"])
        nombre = usuario["nombre"] if usuario else "Desconocido"

        if filtro and filtro not in nombre.lower() and filtro not in prestamo["codigo_usuario"].lower():
            continue

        filas_mostradas.append((prestamo, nombre, libro))

    if not filas_mostradas:
        st.info("No se encontraron prestamos con ese filtro.")
        return

    st.dataframe(
        [{
            "ID": p["id"], "Usuario": nombre, "Codigo": p["codigo_usuario"],
            "Libro": libro["titulo"] if libro else "Desconocido",
            "Prestamo": fecha_legible(p["fecha_prestamo"]),
            "Vencimiento": fecha_legible(p["fecha_vencimiento"]),
            "Devolucion": fecha_legible(p["fecha_devolucion"]) if p["fecha_devolucion"] else "-",
            "Estado": db.estado_prestamo(p),
            "Multa": f"L.{p['multa']:.2f}",
        } for p, nombre, libro in filas_mostradas],
        use_container_width=True, hide_index=True,
    )

    pendientes = [(p, nombre, libro) for p, nombre, libro in filas_mostradas if p["estado"] == "PRESTADO"]
    if pendientes:
        st.subheader("Registrar devolucion")
        opciones = {
            f"#{p['id']} — {nombre} — {libro['titulo'] if libro else 'Desconocido'}": p["id"]
            for p, nombre, libro in pendientes
        }
        seleccion = st.selectbox("Prestamo", list(opciones.keys()))
        if st.button("Registrar devolucion", type="primary"):
            ok, multa = db.devolver_prestamo_por_id(opciones[seleccion])
            if ok:
                mensaje = "Devolucion registrada."
                if multa > 0:
                    mensaje += f" Multa: L.{multa:.2f}"
                st.success(mensaje)
                st.rerun()
            else:
                st.error("No se pudo registrar la devolucion.")


def pantalla_calificaciones_admin():
    """Equivalente a mostrar_calificaciones_admin(): todas las opiniones de todos los libros."""
    st.header("Calificaciones y comentarios")
    filas = db.con.execute(
        """SELECT l.titulo, u.nombre, c.calificacion, c.comentario, c.fecha
           FROM calificaciones c
           JOIN libros l ON l.id = c.id_libro
           JOIN usuarios u ON u.codigo = c.codigo_usuario
           ORDER BY c.id DESC"""
    ).fetchall()

    if not filas:
        st.info("Aun no hay calificaciones registradas.")
        return

    st.dataframe(
        [{
            "Libro": f["titulo"], "Usuario": f["nombre"],
            "Calificacion": "★" * f["calificacion"] + "☆" * (5 - f["calificacion"]),
            "Comentario": f["comentario"] or "(Sin comentario)",
            "Fecha": fecha_legible(f["fecha"]),
        } for f in filas],
        use_container_width=True, hide_index=True,
    )


def pantalla_estadisticas():
    st.header("Estadisticas")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(" Mas leidos")
        st.dataframe(
            [{"Libro": l["titulo"], "Autor": l["autor"], "Prestamos": l["prestamos"]}
             for l in db.libros_mas_leidos()],
            use_container_width=True, hide_index=True,
        )
    with col2:
        st.subheader("Mejor calificados")
        st.dataframe(
            [{"Libro": l["titulo"], "Autor": l["autor"], "Promedio": f"{l['promedio']:.1f}", "Votos": l["cantidad"]}
             for l in db.libros_mejor_calificados()],
            use_container_width=True, hide_index=True,
        )

    st.divider()
    st.subheader("Configurar multa por dia")
    with st.form("form_multa"):
        monto = st.number_input("Multa diaria (L.)", min_value=0.0, value=db.obtener_multa_por_dia(), step=1.0)
        enviado = st.form_submit_button("Guardar")
    if enviado:
        ok, mensaje = db.cambiar_multa_por_dia(monto)
        (st.success if ok else st.error)(mensaje)

    st.divider()
    st.subheader("Movimientos recientes")
    st.dataframe(
        [{"Fecha": fecha_legible(m["fecha"]), "Tipo": m["tipo"], "Detalle": m["detalle"]}
         for m in reversed(db.movimientos[-100:])],
        use_container_width=True, hide_index=True,
    )


# ============================================================
# NAVEGACION PRINCIPAL
# ============================================================

def pantalla_principal():
    usuario = usuario_actual()
    if usuario is None:
        cerrar_sesion()
        return
    st.session_state.usuario = usuario

    st.sidebar.title("Biblioteca")
    st.sidebar.write(f"Sesion: **{usuario['nombre']}** ({usuario['rol']})")

    if usuario["rol"] == "ADMIN":
        opciones = [
            "Catalogo", "Administrar libros", "Usuarios",
            "Solicitudes", "Historial", "Alertas",
            "Calificaciones", "Estadisticas", "Mi perfil",
        ]
    else:
        opciones = [
            "Catalogo", "Mis prestamos", "Solicitudes", "Alertas", "Mi perfil",
        ]

    seccion = st.sidebar.radio("Menu", opciones)

    if st.sidebar.button("Cerrar sesion"):
        cerrar_sesion()

    if seccion == "Catalogo":
        pantalla_catalogo(usuario)
    elif seccion == "Mis prestamos":
        pantalla_mis_prestamos(usuario)
    elif seccion == "Solicitudes" and usuario["rol"] == "CLIENTE":
        pantalla_solicitudes(usuario)
    elif seccion == "Solicitudes" and usuario["rol"] == "ADMIN":
        pantalla_solicitudes_admin()
    elif seccion == "Mi perfil":
        pantalla_perfil(usuario)
    elif seccion == "Administrar libros":
        pantalla_administrar_libros()
    elif seccion == "Usuarios":
        pantalla_usuarios_admin()
    elif seccion == "Historial":
        pantalla_historial_admin()
    elif seccion == "Alertas":
        pantalla_alertas(usuario)
    elif seccion == "Calificaciones":
        pantalla_calificaciones_admin()
    elif seccion == "Estadisticas":
        pantalla_estadisticas()


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if st.session_state.usuario is None:
    pantalla_login()
else:
    pantalla_principal()
