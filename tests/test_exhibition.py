"""Garantía de exhibición en los 16 cruces, dos profundidades, sin atajos EEO."""
from engine.exhibition import cargar_planes, elegir_exposicion, pasos_exposicion
from engine.models import Actor, Nombre, crear_estado
from engine.operators import ejecutar_turno
import pytest


@pytest.mark.parametrize("p1", list(Nombre))
@pytest.mark.parametrize("p2", list(Nombre))
@pytest.mark.parametrize("profundidad", [2, 3])
def test_ambos_inteligentes_antes_de_ko_en_todos_los_cruces(p1: Nombre, p2: Nombre, profundidad: int) -> None:
    estado, actor = crear_estado(p1, p2), Actor.P1
    assert estado.p1.medidor_super == estado.p2.medidor_super == 0
    mostrados: set[Actor] = set()
    turnos_sin_dano = 0
    planes = pasos_exposicion(p1, p2)
    assert len(planes) <= 26
    for turno in range(90):
        decision = elegir_exposicion(estado, actor, profundidad, turno, turnos_sin_dano=turnos_sin_dano)
        op = decision.operador
        assert op is not None and op.puede_aplicarse(estado, actor)
        assert all(c.cumple for c in op.condiciones(estado, actor))
        if turno < len(planes):
            assert decision.estrategia == "Plan EEO"
        else:
            assert decision.estrategia == "Minimax / cierre"
            assert not op.prioridad  # Evita repetir inteligentes ya expuestos.
        if op.prioridad:
            mostrados.add(actor)
        total_antes = estado.p1.puntos_salud + estado.p2.puntos_salud
        nuevo = ejecutar_turno(estado, actor, op)
        assert nuevo.p1.puntos_salud <= estado.p1.puntos_salud
        assert nuevo.p2.puntos_salud <= estado.p2.puntos_salud
        assert nuevo.p1.distancia is nuevo.p2.distancia
        hubo_dano = nuevo.p1.puntos_salud + nuevo.p2.puntos_salud < total_antes
        turnos_sin_dano = 0 if hubo_dano else turnos_sin_dano + 1
        estado = nuevo
        if estado.terminado:
            assert mostrados == set(Actor)
            break
        actor = actor.rival
    assert estado.terminado, (p1, p2, profundidad)
    assert mostrados == set(Actor)


def test_planes_cubren_exactamente_los_16_cruces() -> None:
    assert set(cargar_planes()) == {f"{a.value}|{b.value}" for a in Nombre for b in Nombre}
