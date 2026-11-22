from dataclasses import FrozenInstanceError, replace

import pytest

from engine.models import (Accion, Actor, Colision, Distancia, Especial, Hora,
                           Lugar, Nombre, Postura, Vista, crear_estado,
                           crear_personaje, iniciar_turno)


@pytest.mark.parametrize("nombre", Nombre)
def test_personajes_iniciales(nombre: Nombre) -> None:
    p = crear_personaje(nombre)
    assert p.nombre is nombre
    assert p.puntos_salud == 1000
    assert p.medidor_super == p.recarga_energia == p.dano_recibido == 0
    assert p.especial is Especial.ACTIVO
    assert p.postura is Postura.NEUTRAL
    assert p.acciones is Accion.REPOSO
    assert p.colision is Colision.VULNERABLE
    assert len(p.color) == 3 and p.diseno


def test_estado_inicial_e_inmutabilidad() -> None:
    estado = crear_estado(hora=Hora.NOCHE, lugar=Lugar.DOJO)
    assert estado.escenario.hora is Hora.NOCHE
    assert estado.escenario.lugar is Lugar.DOJO
    assert estado.p1.vista is Vista.DERECHA
    assert estado.p2.vista is Vista.IZQUIERDA
    assert not estado.terminado and estado.ganador is None
    with pytest.raises(FrozenInstanceError):
        setattr(estado.p1, "puntos_salud", 5)
    assert hash(estado)


@pytest.mark.parametrize("campo,valor", [("puntos_salud", -1), ("puntos_salud", 1001), ("medidor_super", 4), ("medidor_super", -1), ("recarga_energia", 2), ("dano_recibido", -1), ("puntos_salud", True)])
def test_dominios_invalidos(campo: str, valor: int) -> None:
    with pytest.raises(ValueError):
        replace(crear_personaje(Nombre.JULI), **{campo: valor})


def test_distancia_simetrica() -> None:
    s = crear_estado()
    with pytest.raises(ValueError):
        replace(s, p1=replace(s.p1, distancia=Distancia.CERCA))


def test_rechaza_categorias_y_paletas_mutables() -> None:
    p = crear_personaje(Nombre.JULI)
    with pytest.raises(ValueError):
        replace(p, postura="Neutral")
    with pytest.raises(ValueError):
        replace(p, color=list(p.color))
    with pytest.raises(ValueError):
        replace(p, color=((256, 0, 0), (0, 0, 0), (0, 0, 0)))
    with pytest.raises(ValueError):
        replace(crear_estado().escenario, hora="Día")


@pytest.mark.parametrize("actor", Actor)
def test_normalizacion_conserva_amenaza_rival(actor: Actor) -> None:
    s = crear_estado()
    propio = replace(s.personaje(actor), acciones=Accion.DANO, postura=Postura.DESPLAZAMIENTO, colision=Colision.INVENCIBLE, dano_recibido=1)
    rival = replace(s.personaje(actor.rival), acciones=Accion.ATACANDO, colision=Colision.ATACANDO)
    s = s.con_personajes(actor, propio, rival)
    nuevo = iniciar_turno(s, actor)
    assert nuevo.personaje(actor).acciones is Accion.REPOSO
    assert nuevo.personaje(actor).postura is Postura.NEUTRAL
    assert nuevo.personaje(actor).colision is Colision.VULNERABLE
    assert nuevo.personaje(actor).dano_recibido == 0
    assert nuevo.personaje(actor.rival) == rival


def test_ko_y_empate() -> None:
    s = crear_estado()
    s = replace(s, p1=replace(s.p1, puntos_salud=0))
    assert s.terminado and s.ganador is Actor.P2
    assert iniciar_turno(s, Actor.P1).p1.postura is Postura.FINAL
    s = replace(s, p2=replace(s.p2, puntos_salud=0))
    assert s.ganador is None
