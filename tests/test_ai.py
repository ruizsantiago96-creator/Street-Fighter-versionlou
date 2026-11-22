from dataclasses import replace
from math import inf

import pytest

from engine.ai import elegir_operador, evaluar
from engine.models import Accion, Actor, Colision, Distancia, Estado, Nombre, crear_estado
from engine.operators import TipoOperador as T, ejecutar_turno, operadores_prioritarios


def escenario() -> Estado:
    s = crear_estado(Nombre.JULI, Nombre.CAMMY)
    return replace(s, p1=replace(s.p1, distancia=Distancia.CERCA), p2=replace(s.p2, distancia=Distancia.CERCA))


@pytest.mark.parametrize("actor", Actor)
@pytest.mark.parametrize("profundidad", [2, 3])
def test_elige_ko_y_explica(actor: Actor, profundidad: int) -> None:
    s = escenario()
    s = s.con_personajes(actor, s.personaje(actor), replace(s.personaje(actor.rival), puntos_salud=90))
    decision = elegir_operador(s, actor, profundidad)
    assert decision.operador is not None and decision.operador.tipo is T.GOLPEAR
    assert decision.evaluaciones[0].puntuacion == 100_000
    assert 1 <= len(decision.evaluaciones) <= 5
    assert decision.nodos_visitados > 0
    assert s.personaje(actor.rival).puntos_salud == 90
    assert decision == elegir_operador(s, actor, profundidad)


def test_ia_respeta_prioridad_inteligente() -> None:
    s = escenario()
    s = replace(s, p1=replace(s.p1, nombre=Nombre.MAKOTO), p2=replace(s.p2, acciones=Accion.ATACANDO))
    decision = elegir_operador(s, Actor.P1)
    assert decision.operador is not None and decision.operador.tipo is T.LECTURA


def test_terminal_no_tiene_decision() -> None:
    s = escenario()
    s = replace(s, p1=replace(s.p1, puntos_salud=0))
    decision = elegir_operador(s, Actor.P1)
    assert decision.operador is None and decision.evaluaciones == ()
    assert evaluar(s, Actor.P1) == -100_000
    assert evaluar(s, Actor.P2) == 100_000


def test_heuristica_salud_super_y_recuperacion() -> None:
    s = escenario()
    assert evaluar(s, Actor.P1) == 0
    fuerte = replace(s, p1=replace(s.p1, medidor_super=3))
    assert evaluar(fuerte, Actor.P1) > evaluar(s, Actor.P1)
    debil = replace(s, p1=replace(s.p1, puntos_salud=500, acciones=Accion.RECUPERACION))
    assert evaluar(debil, Actor.P1) < 0
    protegido = replace(s, p1=replace(s.p1, colision=Colision.INVENCIBLE))
    assert evaluar(protegido, Actor.P1) > 0
    assert evaluar(debil, Actor.P1) == -evaluar(debil, Actor.P2)


@pytest.mark.parametrize("profundidad", [2, 3])
def test_alfa_beta_coincide_con_minimax_exhaustivo(profundidad: int) -> None:
    s = escenario()

    def referencia(estado: Estado, turno: Actor, restante: int) -> float:
        if restante == 0 or estado.terminado:
            return evaluar(estado, Actor.P1)
        valores = [referencia(ejecutar_turno(estado, turno, op), turno.rival, restante - 1) for op in operadores_prioritarios(estado, turno)]
        return (max(valores, default=-inf) if turno is Actor.P1 else min(valores, default=inf))

    decision = elegir_operador(s, Actor.P1, profundidad, limite_evaluaciones=30)
    for jugada in decision.evaluaciones:
        assert jugada.puntuacion == referencia(ejecutar_turno(s, Actor.P1, jugada.operador), Actor.P2, profundidad - 1)
    assert decision.evaluaciones[0].puntuacion == max(j.puntuacion for j in decision.evaluaciones)


@pytest.mark.parametrize("profundidad,limite", [(1, 5), (4, 5), (2, 0)])
def test_argumentos_invalidos(profundidad: int, limite: int) -> None:
    with pytest.raises(ValueError):
        elegir_operador(escenario(), Actor.P1, profundidad, limite)


@pytest.mark.parametrize("p1", Nombre)
@pytest.mark.parametrize("p2", Nombre)
@pytest.mark.parametrize("profundidad", [2, 3])
def test_partidas_completas_llegan_a_ko(p1: Nombre, p2: Nombre, profundidad: int) -> None:
    estado = crear_estado(p1, p2)
    actor = Actor.P1
    sin_dano = 0
    primer_golpe: int | None = None
    for turno in range(160):
        decision = elegir_operador(estado, actor, profundidad, turnos_sin_dano=sin_dano)
        assert decision.operador is not None and decision.operador.puede_aplicarse(estado, actor)
        salud_anterior = estado.p1.puntos_salud + estado.p2.puntos_salud
        estado = ejecutar_turno(estado, actor, decision.operador)
        dano = salud_anterior - estado.p1.puntos_salud - estado.p2.puntos_salud
        if dano and primer_golpe is None:
            primer_golpe = turno + 1
        sin_dano = 0 if dano else sin_dano + 1
        assert sin_dano <= 10, (p1, p2, profundidad, turno, estado)
        if estado.terminado:
            break
        actor = actor.rival
    assert primer_golpe is not None and primer_golpe <= 8
    assert estado.terminado and turno + 1 <= 100, (p1, p2, profundidad)
    print(f"{p1.value} vs {p2.value}, nivel {profundidad}: primer daño turno {primer_golpe}, KO turno {turno + 1}")


@pytest.mark.parametrize("distancia,tipo", [(Distancia.LEJOS, T.DESPLAZAR), (Distancia.MEDIA, T.ACERCAR), (Distancia.CERCA, T.GOLPEAR), (Distancia.CONTACTO, T.ALEJAR)])
def test_iniciativa_prepara_un_ataque_legal(distancia: Distancia, tipo: T) -> None:
    s = crear_estado()
    s = replace(s, p1=replace(s.p1, distancia=distancia), p2=replace(s.p2, distancia=distancia))
    decision = elegir_operador(s, Actor.P1, turnos_sin_dano=3)
    assert decision.operador is not None and decision.operador.tipo is tipo
    assert decision.motivo


def test_iniciativa_conserva_prioridad_inteligente() -> None:
    s = escenario()
    s = replace(s, p1=replace(s.p1, nombre=Nombre.BISON), p2=replace(s.p2, acciones=Accion.ATACANDO))
    decision = elegir_operador(s, Actor.P1, turnos_sin_dano=3)
    assert decision.operador is not None and decision.operador.tipo is T.DRENAR


def test_inactividad_invalida() -> None:
    with pytest.raises(ValueError):
        elegir_operador(escenario(), Actor.P1, turnos_sin_dano=-1)


