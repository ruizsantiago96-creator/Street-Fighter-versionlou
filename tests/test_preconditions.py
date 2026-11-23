"""Comprueba cada precondición por separado en ambos lados de la arena."""
from dataclasses import replace
from typing import Any

import pytest

from engine.models import (Accion, Actor, Colision, Distancia, Especial, Estado,
                           Nombre, Postura, crear_estado)
from engine.operators import Operador, OperadorInvalido, TipoOperador as T


def caso(tipo: T, actor: Actor) -> Estado:
    nombres = {T.SPIN_DRIVE: Nombre.JULI, T.LIBERAR: Nombre.JULI,
               T.KILLER_BEE: Nombre.CAMMY, T.FINTA: Nombre.CAMMY,
               T.PSYCHO_CRUSHER: Nombre.BISON, T.DRENAR: Nombre.BISON,
               T.SEICHUSEN: Nombre.MAKOTO, T.LECTURA: Nombre.MAKOTO}
    contacto = (T.AGARRAR, T.SPIN_DRIVE, T.SEICHUSEN, T.LIBERAR)
    media = (T.KILLER_BEE, T.PSYCHO_CRUSHER, T.FINTA)
    distancia = Distancia.CONTACTO if tipo in contacto else Distancia.MEDIA if tipo in media else Distancia.LEJOS if tipo is T.DESPLAZAR else Distancia.CERCA
    s = crear_estado()
    p = replace(s.personaje(actor), nombre=nombres.get(tipo, Nombre.JULI), distancia=distancia)
    r = replace(s.personaje(actor.rival), distancia=distancia)
    if tipo in (T.SPIN_DRIVE, T.KILLER_BEE, T.PSYCHO_CRUSHER, T.SEICHUSEN, T.LIBERAR):
        p = replace(p, medidor_super=3)
    if tipo in (T.BLOQUEAR, T.SALTAR, T.LIBERAR, T.DRENAR, T.LECTURA):
        r = replace(r, acciones=Accion.ATACANDO)
    if tipo is T.AGARRAR:
        p, r = replace(p, acciones=Accion.ATACANDO), replace(r, acciones=Accion.DEFENDIENDO)
    if tipo is T.LIBERAR:
        p = replace(p, puntos_salud=400)
    if tipo is T.FINTA:
        p, r = replace(p, medidor_super=2), replace(r, acciones=Accion.DEFENDIENDO)
    if tipo is T.ATERRIZAR:
        p = replace(p, postura=Postura.AEREO)
    if tipo is T.CARGAR:
        p = replace(p, recarga_energia=1)
    if p.nombre is Nombre.JULI:
        p = replace(p, especial=Especial.ACTIVO)
    return s.con_personajes(actor, p, r)


@pytest.mark.parametrize("actor", Actor)
@pytest.mark.parametrize("tipo", list(T))
def test_trece_operadores_desde_ambos_lados(tipo: T, actor: Actor) -> None:
    s = caso(tipo, actor)
    op = Operador(tipo)
    assert op.puede_aplicarse(s, actor)
    assert all(c.cumple for c in op.condiciones(s, actor))
    nuevo = op.aplicar(s, actor)
    assert nuevo != s
    assert nuevo.personaje(actor).nombre is s.personaje(actor).nombre
    assert nuevo.p1.distancia is nuevo.p2.distancia


@pytest.mark.parametrize("actor", Actor)
@pytest.mark.parametrize("tipo,lado,cambios", [
    (T.DESPLAZAR, "propio", {"postura": Postura.AEREO}),
    (T.GOLPEAR, "propio", {"postura": Postura.AEREO}),
    (T.GOLPEAR, "propio", {"acciones": Accion.ATACANDO}),
    (T.GOLPEAR, "rival", {"colision": Colision.INVULNERABLE}),
    (T.BLOQUEAR, "propio", {"acciones": Accion.ATACANDO}),
    (T.SALTAR, "rival", {"acciones": Accion.REPOSO}),
    (T.SALTAR, "propio", {"postura": Postura.AEREO}),
    (T.AGARRAR, "propio", {"postura": Postura.AEREO}),
    (T.AGARRAR, "rival", {"acciones": Accion.REPOSO}),
    (T.SPIN_DRIVE, "propio", {"especial": Especial.LIBERADA}),
    (T.LIBERAR, "propio", {"especial": Especial.LIBERADA}),
    (T.LIBERAR, "propio", {"medidor_super": 2}),
    (T.LIBERAR, "rival", {"acciones": Accion.REPOSO}),
    (T.FINTA, "propio", {"medidor_super": 1}),
    (T.FINTA, "rival", {"acciones": Accion.REPOSO}),
    (T.DRENAR, "propio", {"medidor_super": 3}),
    (T.DRENAR, "rival", {"acciones": Accion.REPOSO}),
    (T.LECTURA, "rival", {"acciones": Accion.REPOSO}),
    (T.CARGAR, "propio", {"recarga_energia": 0}),
    (T.CARGAR, "propio", {"acciones": Accion.DANO}),
    (T.CARGAR, "propio", {"medidor_super": 3}),
    (T.ATERRIZAR, "propio", {"postura": Postura.NEUTRAL}),
    (T.DESPLAZAR, "rival", {"postura": Postura.AEREO}),
    (T.LIBERAR, "propio", {"puntos_salud": 460}),
])
def test_rechaza_precondicion_rota(tipo: T, lado: str, cambios: dict[str, Any], actor: Actor) -> None:
    s = caso(tipo, actor)
    objetivo = actor if lado == "propio" else actor.rival
    propio = replace(s.personaje(objetivo), **cambios)
    s = s.con_personajes(objetivo, propio, s.personaje(objetivo.rival))
    op = Operador(tipo)
    assert not op.puede_aplicarse(s, actor)
    assert any(not c.cumple for c in op.condiciones(s, actor))
    with pytest.raises(OperadorInvalido):
        op.aplicar(s, actor)
