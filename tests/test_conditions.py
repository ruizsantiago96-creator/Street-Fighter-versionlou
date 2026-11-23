from dataclasses import replace
from random import Random

from engine.models import (Accion, Actor, Colision, Distancia, Especial, Nombre,
                           Postura, crear_estado)
from engine.operators import OPERADORES


def test_explicacion_coincide_con_precondiciones_del_motor() -> None:
    rng = Random(73)
    for _ in range(250):
        s = crear_estado(rng.choice(list(Nombre)), rng.choice(list(Nombre)))
        distancia = rng.choice(list(Distancia))
        for actor in Actor:
            p = replace(s.personaje(actor), distancia=distancia,
                        puntos_salud=rng.choice((0, 10, 400, 450, 460, 1000)),
                        postura=rng.choice(list(Postura)), acciones=rng.choice(list(Accion)),
                        colision=rng.choice(list(Colision)), medidor_super=rng.randrange(4),
                        especial=rng.choice(list(Especial)), recarga_energia=rng.randrange(2))
            r = replace(s.personaje(actor.rival), distancia=distancia)
            s = s.con_personajes(actor, p, r)
        for actor in Actor:
            for op in OPERADORES:
                condiciones = op.condiciones(s, actor)
                assert condiciones and all(c.regla and c.observado for c in condiciones)
                assert all(c.cumple for c in condiciones) is op.puede_aplicarse(s, actor), (op, actor, s)
