// estado.js — Estado de sesion en memoria, compartido por todas las vistas.

export const estado = {                              // objeto unico de estado global
  sesion: { usuario: null, rol: null },              // usuario autenticado (null = invitado)
  entrar(usuario, rol) {                             // registra una sesion iniciada
    this.sesion.usuario = usuario                     // guarda el nombre de usuario
    this.sesion.rol = rol                             // guarda el rol (User/Admin)
  },
  salir() {                                           // cierra la sesion
    this.sesion.usuario = null                        // limpia el usuario
    this.sesion.rol = null                            // limpia el rol
  },
}
