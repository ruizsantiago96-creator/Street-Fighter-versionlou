from dataclasses import replace

import pytest

from engine.models import (Accion, Actor, Colision, Distancia, Especial, Estado,
                           Nombre, Postura, crear_estado, iniciar_turno)
from engine.operators import (OPERADORES, Operador, OperadorInvalido,
                              TipoOperador as T, ejecutar_turno,
                              operadores_prioritarios, operadores_validos)


def preparar(nombre: Nombre = Nombre.JULI, distancia: Distancia = Distancia.CERCA, actor: Actor = Actor.P1) -> Estado:
    s = crear_estado(nombre, Nombre.CAMMY) if actor is Actor.P1 else crear_estado(Nombre.CAMMY, nombre)
    return replace(s, p1=replace(s.p1, distancia=distancia), p2=replace(s.p2, distancia=distancia))


@pytest.mark.parametrize("actor", Actor)
def test_desplazar_y_movimiento_simetrico(actor: Actor) -> None:
    s = preparar(distancia=Distancia.LEJOS, actor=actor)
    s = Operador(T.DESPLAZAR).aplicar(s, actor)
    assert s.p1.distancia is s.p2.distancia is Distancia.MEDIA
    assert s.p1.postura is s.p2.postura is Postura.DESPLAZAMIENTO
    for distancia in (Distancia.CERCA, Distancia.CONTACTO):
        s = Operador(T.ACERCAR).aplicar(s, actor)
        assert s.p1.distancia is s.p2.distancia is distancia
    assert not Operador(T.ACERCAR).puede_aplicarse(s, actor)
    for distancia in (Distancia.CERCA, Distancia.MEDIA, Distancia.LEJOS):
        s = Operador(T.ALEJAR).aplicar(s, actor)
        assert s.p1.distancia is s.p2.distancia is distancia


@pytest.mark.parametrize("actor", Actor)
def test_golpe_inmutable_y_bloqueo_literal(actor: Actor) -> None:
    s = preparar(actor=actor)
    nuevo = Operador(T.GOLPEAR).aplicar(s, actor)
    p, r = nuevo.personaje(actor), nuevo.personaje(actor.rival)
    assert s.personaje(actor.rival).puntos_salud == 1000
    assert (p.acciones, p.colision, p.recarga_energia) == (Accion.ATACANDO, Colision.ATACANDO, 1)
    assert (r.puntos_salud, r.dano_recibido, r.acciones) == (900, 1, Accion.DANO)
    nuevo = iniciar_turno(nuevo, actor.rival)
    assert Operador(T.BLOQUEAR).puede_aplicarse(nuevo, actor.rival)
    bloqueado = Operador(T.BLOQUEAR).aplicar(nuevo, actor.rival).personaje(actor.rival)
    assert (bloqueado.puntos_salud, bloqueado.acciones, bloqueado.colision, bloqueado.dano_recibido) == (890, Accion.DEFENDIENDO, Colision.INVULNERABLE, 0)


@pytest.mark.parametrize("distancia,resultado", [(Distancia.CERCA, Distancia.MEDIA), (Distancia.MEDIA, Distancia.LEJOS)])
def test_saltar(distancia: Distancia, resultado: Distancia) -> None:
    s = preparar(distancia=distancia)
    s = replace(s, p2=replace(s.p2, acciones=Accion.ATACANDO))
    s = Operador(T.SALTAR).aplicar(s, Actor.P1)
    assert s.p1.distancia is s.p2.distancia is resultado
    assert s.p1.postura is Postura.AEREO
    assert s.p1.colision is Colision.INVULNERABLE


def test_agarre() -> None:
    s = preparar(distancia=Distancia.CONTACTO)
    s = replace(s, p1=replace(s.p1, acciones=Accion.ATACANDO), p2=replace(s.p2, acciones=Accion.DEFENDIENDO))
    s = Operador(T.AGARRAR).aplicar(s, Actor.P1)
    assert s.p1.acciones is Accion.AGARRE
    assert s.p1.colision is Colision.VULNERABLE
    assert s.p1.distancia is s.p2.distancia is Distancia.CONTACTO
    assert s.p1.recarga_energia == 1 and s.p2.acciones is Accion.DANO
    assert s.p2.puntos_salud == 850 and s.p2.dano_recibido == 1


@pytest.mark.parametrize("actor", Actor)
@pytest.mark.parametrize("tipo,nombre,distancia,dano", [(T.SPIN_DRIVE, Nombre.JULI, Distancia.CONTACTO, 300), (T.KILLER_BEE, Nombre.CAMMY, Distancia.MEDIA, 300), (T.PSYCHO_CRUSHER, Nombre.BISON, Distancia.MEDIA, 350), (T.SEICHUSEN, Nombre.MAKOTO, Distancia.CONTACTO, 350)])
def test_especiales(tipo: T, nombre: Nombre, distancia: Distancia, dano: int, actor: Actor) -> None:
    s = preparar(nombre, distancia, actor)
    p, r = s.personaje(actor), s.personaje(actor.rival)
    s = s.con_personajes(actor, replace(p, medidor_super=3, recarga_energia=1), r)
    op = Operador(tipo)
    assert op.puede_aplicarse(s, actor)
    nuevo = op.aplicar(s, actor)
    p, r = nuevo.personaje(actor), nuevo.personaje(actor.rival)
    assert p.medidor_super == 0 and p.colision is Colision.INVENCIBLE
    assert p.acciones is Accion.ATACANDO
    assert r.puntos_salud == 1000 - dano and r.dano_recibido == 1
    assert r.acciones is Accion.DANO
    assert p.distancia is r.distancia is Distancia.CONTACTO
    if tipo in (T.SPIN_DRIVE, T.SEICHUSEN):
        assert p.recarga_energia == 0
    assert not op.puede_aplicarse(nuevo, actor)


@pytest.mark.parametrize("tipo,nombre,distancia", [(T.SPIN_DRIVE, Nombre.JULI, Distancia.CONTACTO), (T.KILLER_BEE, Nombre.CAMMY, Distancia.MEDIA), (T.PSYCHO_CRUSHER, Nombre.BISON, Distancia.MEDIA), (T.SEICHUSEN, Nombre.MAKOTO, Distancia.CONTACTO)])
def test_especial_exige_nombre_distancia_y_medidor(tipo: T, nombre: Nombre, distancia: Distancia) -> None:
    op = Operador(tipo)
    s = preparar(nombre, distancia)
    assert not op.puede_aplicarse(s, Actor.P1)
    s = replace(s, p1=replace(s.p1, medidor_super=3))
    incorrecto = Nombre.CAMMY if nombre is not Nombre.CAMMY else Nombre.JULI
    assert not op.puede_aplicarse(replace(s, p1=replace(s.p1, nombre=incorrecto)), Actor.P1)
    otra = Distancia.LEJOS
    assert not op.puede_aplicarse(replace(s, p1=replace(s.p1, distancia=otra), p2=replace(s.p2, distancia=otra)), Actor.P1)


@pytest.mark.parametrize("salud,permitido", [(0, False), (10, True), (400, True), (450, True), (460, False)])
def test_liberar_umbral(salud: int, permitido: bool) -> None:
    s = preparar(distancia=Distancia.CONTACTO)
    s = replace(s, p1=replace(s.p1, puntos_salud=salud, medidor_super=3, dano_recibido=1), p2=replace(s.p2, acciones=Accion.ATACANDO))
    op = Operador(T.LIBERAR)
    assert op.puede_aplicarse(s, Actor.P1) is permitido
    if permitido:
        s = op.aplicar(s, Actor.P1)
        assert s.p1.especial is Especial.LIBERADA and s.p1.medidor_super == 0
        assert s.p1.dano_recibido == 0 and s.p1.colision is Colision.INVENCIBLE
        assert s.p2.puntos_salud == 650
        s = replace(s, p1=replace(s.p1, medidor_super=3))
        assert not op.puede_aplicarse(s, Actor.P1)
        assert not Operador(T.SPIN_DRIVE).puede_aplicarse(s, Actor.P1)


@pytest.mark.parametrize("defensa", [False, True])
def test_finta_conserva_medidor_segun_tabla(defensa: bool) -> None:
    s = preparar(Nombre.CAMMY, Distancia.MEDIA)
    s = replace(s, p1=replace(s.p1, medidor_super=2), p2=replace(s.p2, postura=Postura.NEUTRAL, acciones=Accion.DEFENDIENDO if defensa else Accion.REPOSO))
    if not defensa:
        assert not Operador(T.FINTA).puede_aplicarse(s, Actor.P1)
        return
    s = Operador(T.FINTA).aplicar(s, Actor.P1)
    assert s.p1.medidor_super == 2
    assert s.p1.postura is Postura.AEREO and s.p1.colision is Colision.INVENCIBLE
    assert s.p1.distancia is s.p2.distancia is Distancia.CONTACTO
    assert s.p2.puntos_salud == 750


@pytest.mark.parametrize("medidor_rival", [0, 1, 3])
def test_drenar_limites(medidor_rival: int) -> None:
    s = preparar(Nombre.BISON)
    s = replace(s, p1=replace(s.p1, medidor_super=2, dano_recibido=1), p2=replace(s.p2, acciones=Accion.ATACANDO, medidor_super=medidor_rival))
    s = Operador(T.DRENAR).aplicar(s, Actor.P1)
    assert s.p1.medidor_super == 3 and s.p1.dano_recibido == 0
    assert s.p1.colision is Colision.INVENCIBLE
    assert s.p2.medidor_super == max(0, medidor_rival - 1)
    assert s.p2.acciones is Accion.RECUPERACION and s.p2.colision is Colision.VULNERABLE
    assert s.p2.puntos_salud == 1000
    assert not Operador(T.DRENAR).puede_aplicarse(s, Actor.P1)


@pytest.mark.parametrize("distancia", [Distancia.CERCA, Distancia.CONTACTO])
def test_lectura(distancia: Distancia) -> None:
    s = preparar(Nombre.MAKOTO, distancia)
    s = replace(s, p1=replace(s.p1, dano_recibido=1), p2=replace(s.p2, acciones=Accion.ATACANDO))
    s = Operador(T.LECTURA).aplicar(s, Actor.P1)
    assert s.p1.medidor_super == 3 and s.p1.dano_recibido == 0
    assert s.p1.colision is Colision.INVENCIBLE
    assert s.p1.distancia is s.p2.distancia is Distancia.CONTACTO
    assert s.p2.puntos_salud == 850 and s.p2.acciones is Accion.RECUPERACION
    assert s.p2.colision is Colision.VULNERABLE


def test_carga_consume_permiso_y_necesita_accion_de_preparacion() -> None:
    s = preparar()
    assert not Operador(T.CARGAR).puede_aplicarse(s, Actor.P1)
    s = Operador(T.GOLPEAR).aplicar(s, Actor.P1)
    assert not Operador(T.CARGAR).puede_aplicarse(s, Actor.P1)  # Sigue Atacando.
    s = Operador(T.ALEJAR).aplicar(s, Actor.P1)
    s = Operador(T.CARGAR).aplicar(s, Actor.P1)
    assert s.p1.medidor_super == 1 and s.p1.recarga_energia == 0
    assert s.p1.acciones is Accion.CARGANDO
    assert not Operador(T.CARGAR).puede_aplicarse(s, Actor.P1)


@pytest.mark.parametrize("op", OPERADORES)
def test_ningun_operador_tras_ko(op: Operador) -> None:
    s = crear_estado()
    s = replace(s, p2=replace(s.p2, puntos_salud=0))
    for actor in Actor:
        assert not op.puede_aplicarse(s, actor)
        with pytest.raises(OperadorInvalido):
            op.aplicar(s, actor)


def test_dano_saturado_y_final_inmediato() -> None:
    s = preparar()
    s = replace(s, p2=replace(s.p2, puntos_salud=30))
    s = ejecutar_turno(s, Actor.P1, Operador(T.GOLPEAR))
    assert s.p2.puntos_salud == 0 and s.p2.postura is Postura.NEUTRAL
    assert s.ganador is Actor.P1
    assert operadores_validos(s, Actor.P1) == ()


@pytest.mark.parametrize("distancia", Distancia)
@pytest.mark.parametrize("nombre", Nombre)
def test_siempre_existe_transicion(distancia: Distancia, nombre: Nombre) -> None:
    s = preparar(nombre, distancia)
    assert operadores_validos(s, Actor.P1)
    for op in operadores_validos(s, Actor.P1):
        nuevo = op.aplicar(s, Actor.P1)
        assert nuevo.p1.distancia is nuevo.p2.distancia
        assert nuevo.escenario == s.escenario


def test_prioridad_inteligente() -> None:
    s = preparar(Nombre.MAKOTO)
    s = replace(s, p2=replace(s.p2, acciones=Accion.ATACANDO))
    assert operadores_validos(s, Actor.P1)[0].tipo is T.LECTURA
    assert tuple(op.tipo for op in operadores_prioritarios(s, Actor.P1)) == (T.LECTURA,)


@pytest.mark.parametrize("distancia", Distancia)
def test_golpear_conserva_distancia_original(distancia: Distancia) -> None:
    s = preparar(distancia=distancia)
    assert Operador(T.GOLPEAR).puede_aplicarse(s, Actor.P1) is (distancia in (Distancia.CERCA, Distancia.CONTACTO))


