"""Regresión contra las 36 transiciones publicadas en la especificación v7."""
from dataclasses import replace
from pathlib import Path

import pytest

from engine.models import (Accion, Actor, Colision, Distancia, Especial, Estado,
                           Nombre, Postura, crear_estado, iniciar_turno)
from engine.operators import ESPECIALES, OPERADORES, Operador, OperadorInvalido, TipoOperador as T


DOCUMENTO = Path(__file__).resolve().parents[1] / "docs/3_1_an_lisis_eeo_2_operadores_y_reglas_v7_definitivo.md"
POSTURAS = {"Neutral": Postura.NEUTRAL, "Desplaz.": Postura.DESPLAZAMIENTO, "Desp. Aéreo": Postura.AEREO}
ACCIONES = {"Reposo": Accion.REPOSO, "Atacando": Accion.ATACANDO, "Cargando": Accion.CARGANDO,
            "Recib.": Accion.DANO, "Defend.": Accion.DEFENDIENDO, "Recup.": Accion.RECUPERACION,
            "Agarre": Accion.AGARRE}
COLISIONES = {"Vuln.": Colision.VULNERABLE, "Atac.": Colision.ATACANDO,
              "Invenc.": Colision.INVENCIBLE, "Invuln.": Colision.INVULNERABLE}


def filas_documento(ronda: int) -> list[list[str]]:
    contenido = DOCUMENTO.read_text(encoding="utf-8")
    seccion = contenido.split("## 4. Tabla de Estados", 1)[1] if ronda == 1 else contenido.split("## 5. Tabla de Estados", 1)[1]
    if ronda == 1:
        seccion = seccion.split("## 5. Tabla de Estados", 1)[0]
    filas = []
    for linea in seccion.splitlines():
        if linea.startswith("|"):
            celdas = [c.replace("**", "").strip() for c in linea.split("|")[1:-1]]
            if celdas[0] in ("Inicio", "J1", "J2"):
                filas.append(celdas)
    return filas


def estado_fila(celdas: list[str], ronda: int) -> Estado:
    nombres = (Nombre.JULI, Nombre.CAMMY) if ronda == 1 else (Nombre.MAKOTO, Nombre.BISON)
    estado = crear_estado(*nombres)
    distancia = Distancia(celdas[2])
    for actor, indice in ((Actor.P1, 3), (Actor.P2, 11 if ronda == 1 else 10)):
        p = estado.personaje(actor)
        especial = Especial(celdas[10]) if ronda == 1 and actor is Actor.P1 else p.especial
        p = replace(p, distancia=distancia, puntos_salud=int(celdas[indice]),
                    postura=POSTURAS[celdas[indice + 1]], acciones=ACCIONES[celdas[indice + 2]],
                    medidor_super=int(celdas[indice + 3]), recarga_energia=int(celdas[indice + 4]),
                    colision=COLISIONES[celdas[indice + 5]], dano_recibido=int(celdas[indice + 6]),
                    especial=especial)
        # Construye los dos personajes antes de validar la distancia simétrica.
        if actor is Actor.P1:
            primero = p
        else:
            estado = replace(estado, p1=primero, p2=p)
    return estado


@pytest.mark.parametrize("ronda,turnos,salud", [(1, 21, 240), (2, 15, 540)])
@pytest.mark.parametrize("invertir", [False, True])
def test_corridas_v7_completas_y_reflejadas(ronda: int, turnos: int, salud: int, invertir: bool) -> None:
    filas = filas_documento(ronda)
    assert len(filas) == turnos + 1
    actual = estado_fila(filas[0], ronda)
    if invertir:
        actual = replace(actual, p1=actual.p2, p2=actual.p1)
    for numero, fila in enumerate(filas[1:], 1):
        actor = Actor.P1 if fila[0] == "J1" else Actor.P2
        assert actor is (Actor.P1 if numero % 2 else Actor.P2)
        if invertir:
            actor = actor.rival
        nombre = fila[1].split(". ", 1)[1].split(" [", 1)[0]
        op = Operador(T.CARGAR if nombre == "Cargar_Energia" else T(nombre))
        assert op.puede_aplicarse(actual, actor), (ronda, numero, nombre)
        assert all(c.cumple for c in op.condiciones(actual, actor))
        anterior = actual
        actual = op.aplicar(actual, actor)
        esperado = estado_fila(fila, ronda)
        if invertir:
            esperado = replace(esperado, p1=esperado.p2, p2=esperado.p1)
        assert actual == esperado, (ronda, numero, nombre, actual, esperado)
        assert anterior != actual
    assert actual.terminado
    ganador = Actor.P2 if invertir else Actor.P1
    assert actual.ganador is ganador and actual.personaje(ganador).puntos_salud == salud
    assert all(not op.puede_aplicarse(actual, a) for op in OPERADORES for a in Actor)


@pytest.mark.parametrize("actor", Actor)
def test_aire_exige_aterrizar_y_no_se_normaliza_solo(actor: Actor) -> None:
    s = crear_estado(Nombre.CAMMY, Nombre.CAMMY)
    s = s.con_personajes(actor, replace(s.personaje(actor), postura=Postura.AEREO,
                                       medidor_super=3, recarga_energia=1), s.personaje(actor.rival))
    assert iniciar_turno(s, actor).personaje(actor).postura is Postura.AEREO
    validos = [o.tipo for o in OPERADORES if o.puede_aplicarse(s, actor)]
    assert validos == [T.ATERRIZAR]
    s = Operador(T.ATERRIZAR).aplicar(s, actor)
    assert s.personaje(actor).postura is Postura.NEUTRAL
    assert s.personaje(actor).recarga_energia == 1


@pytest.mark.parametrize("actor", Actor)
@pytest.mark.parametrize("tipo", list(ESPECIALES))
@pytest.mark.parametrize("distancia", list(Distancia))
def test_alcances_de_poderes_y_derribo_aereo(tipo: T, distancia: Distancia, actor: Actor) -> None:
    nombre, alcances, dano = ESPECIALES[tipo]
    s = crear_estado(nombre, nombre)
    s = replace(s, p1=replace(s.p1, distancia=distancia), p2=replace(s.p2, distancia=distancia))
    s = s.con_personajes(actor, replace(s.personaje(actor), medidor_super=3, recarga_energia=1),
                        replace(s.personaje(actor.rival), postura=Postura.AEREO, colision=Colision.INVULNERABLE))
    op = Operador(tipo)
    assert op.puede_aplicarse(s, actor) is (distancia in alcances)
    if distancia not in alcances:
        with pytest.raises(OperadorInvalido):
            op.aplicar(s, actor)
        return
    nuevo = op.aplicar(s, actor)
    p, r = nuevo.personaje(actor), nuevo.personaje(actor.rival)
    assert p.medidor_super == p.recarga_energia == 0
    assert r.puntos_salud == 1000 - dano and r.postura is Postura.NEUTRAL
    assert r.colision is Colision.VULNERABLE


@pytest.mark.parametrize("actor", Actor)
@pytest.mark.parametrize("distancia", [Distancia.MEDIA, Distancia.CERCA, Distancia.CONTACTO])
def test_guardia_sin_ofensiva_no_cobra_chip_y_persiste(actor: Actor, distancia: Distancia) -> None:
    s = crear_estado()
    s = replace(s, p1=replace(s.p1, distancia=distancia), p2=replace(s.p2, distancia=distancia))
    s = Operador(T.BLOQUEAR).aplicar(s, actor)
    assert s.personaje(actor).puntos_salud == 1000
    s = iniciar_turno(s, actor.rival)
    assert s.personaje(actor).colision is Colision.INVULNERABLE
    assert not Operador(T.GOLPEAR).puede_aplicarse(s, actor.rival)


def test_salto_reposo_distancia_y_bandera_recarga_se_conserva() -> None:
    s = crear_estado()
    s = replace(s, p1=replace(s.p1, distancia=Distancia.CERCA, recarga_energia=1),
                p2=replace(s.p2, distancia=Distancia.CERCA, acciones=Accion.ATACANDO))
    s = Operador(T.SALTAR).aplicar(s, Actor.P1)
    assert s.p1.acciones is Accion.REPOSO and s.p1.distancia is Distancia.MEDIA
    assert not Operador(T.CARGAR).puede_aplicarse(s, Actor.P1)
    s = Operador(T.ATERRIZAR).aplicar(s, Actor.P1)
    assert Operador(T.CARGAR).puede_aplicarse(s, Actor.P1)
