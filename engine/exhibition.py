"""Planificación cooperativa EEO para exponer ambos inteligentes, sin cambiar reglas.

Los planes reproducibles se compilan fuera del bucle gráfico. Cada transición
se revalida con los operadores del motor; no se conceden salud ni cargas.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
import json
from math import ceil
from pathlib import Path

from engine.ai import DecisionIA, EvaluacionJugada, elegir_operador, evaluar
from engine.models import Accion, Actor, Distancia, Estado, Nombre, Postura, crear_estado
from engine.operators import Operador, TipoOperador as T, ejecutar_turno, operadores_validos


INTELIGENTE = {Nombre.JULI: T.LIBERAR, Nombre.CAMMY: T.FINTA,
               Nombre.BISON: T.DRENAR, Nombre.MAKOTO: T.LECTURA}
RUTA_PLANES = Path(__file__).with_name("exhibition_plans.json")


def firma(estado: Estado, actor: Actor) -> tuple[object, ...]:
    """Variables dinámicas necesarias para verificar una etapa del plan."""
    datos: list[object] = [actor, estado.p1.distancia]
    for p in (estado.p1, estado.p2):
        datos.extend((p.nombre, p.puntos_salud, p.postura, p.acciones,
                      p.medidor_super, p.recarga_energia, p.colision, p.especial))
    return tuple(datos)


def distancia_objetivo(estado: Estado, usados: int) -> float:
    """Estimación de preparación: cargas reales, posición, presión y guardia."""
    valor = 0.0
    indices = {Distancia.LEJOS: 0, Distancia.MEDIA: 1, Distancia.CERCA: 2, Distancia.CONTACTO: 3}
    for i, actor in enumerate(Actor):
        if usados & (1 << i):
            continue
        p, r = estado.personaje(actor), estado.personaje(actor.rival)
        if p.nombre is Nombre.JULI:
            valor += max(0, ceil((p.puntos_salud - 450) / 100)) * 1.5
            valor += max(0, 3 - p.medidor_super) * 3
            valor -= 1.2 if p.recarga_energia and p.medidor_super < 3 else 0
            valor += abs(3 - indices[p.distancia]) * 0.6
            valor += 0 if r.acciones is Accion.ATACANDO else 0.8
        elif p.nombre is Nombre.CAMMY:
            valor += max(0, 2 - p.medidor_super) * 3
            valor -= 1.2 if p.recarga_energia and p.medidor_super < 2 else 0
            valor += abs(1 - indices[p.distancia]) * 0.8
            valor += 0 if r.acciones is Accion.DEFENDIENDO else 1
        elif p.nombre is Nombre.BISON:
            valor += 3 if p.medidor_super == 3 else 0
            valor += abs(2 - indices[p.distancia]) * 0.8
            valor += 0 if r.acciones is Accion.ATACANDO else 1
        else:
            valor += max(0, 2 - indices[p.distancia]) * 0.8
            valor += 0 if r.acciones is Accion.ATACANDO else 1
        if p.recarga_energia and p.acciones not in (Accion.REPOSO, Accion.CARGANDO):
            valor += 0.7
        if p.postura is Postura.AEREO:
            valor += 1
    return valor + (2000 - estado.p1.puntos_salud - estado.p2.puntos_salud) / 500


@dataclass(frozen=True, slots=True)
class Nodo:
    estado: Estado
    actor: Actor
    usados: int
    camino: tuple[T, ...]


def buscar_plan(estado: Estado, ancho: int = 220, limite: int = 70) -> tuple[T, ...]:
    """Búsqueda en haz por objetivos; no es Minimax competitivo.

    Solo admite transiciones legales y descarta K.O. prematuro. Los operadores
    inteligentes se ejecutan cuando ayudan a cubrir un objetivo pendiente;
    se permite preparar su condición en vez de forzar su repetición.
    """
    frontera = [Nodo(estado, Actor.P1, 0, ())]
    vistos = {(*firma(estado, Actor.P1), 0)}
    for _ in range(limite):
        siguientes: list[Nodo] = []
        for n in frontera:
            for op in operadores_validos(n.estado, n.actor):
                usados = n.usados | ((1 if n.actor is Actor.P1 else 2) if op.prioridad else 0)
                nuevo = ejecutar_turno(n.estado, n.actor, op)
                camino = (*n.camino, op.tipo)
                if usados == 3:
                    return camino
                if nuevo.terminado:
                    continue
                clave = (*firma(nuevo, n.actor.rival), usados)
                if clave in vistos:
                    continue
                vistos.add(clave)
                siguientes.append(Nodo(nuevo, n.actor.rival, usados, camino))
        if not siguientes:
            break
        siguientes.sort(key=lambda n: ((2 - n.usados.bit_count()) * 100
                                       + distancia_objetivo(n.estado, n.usados)))
        frontera = siguientes[:ancho]
    raise RuntimeError(f"No se encontró un plan de exposición para {estado.p1.nombre.value} / {estado.p2.nombre.value}")


@lru_cache(maxsize=1)
def cargar_planes() -> dict[str, list[str]]:
    datos: dict[str, list[str]] = json.loads(RUTA_PLANES.read_text(encoding="utf-8"))
    return datos


@dataclass(frozen=True, slots=True)
class Paso:
    firma: tuple[object, ...]
    operador: Operador


@lru_cache(maxsize=16)
def pasos_exposicion(p1: Nombre, p2: Nombre) -> tuple[Paso, ...]:
    estado, actor = crear_estado(p1, p2), Actor.P1
    clave = f"{p1.value}|{p2.value}"
    pasos: list[Paso] = []
    for nombre in cargar_planes()[clave]:
        op = Operador(T(nombre))
        if not op.puede_aplicarse(estado, actor):
            raise ValueError(f"Plan EEO desactualizado: {clave} / {op.nombre}")
        pasos.append(Paso(firma(estado, actor), op))
        estado = ejecutar_turno(estado, actor, op)
        actor = actor.rival
    return tuple(pasos)


def decidir_exposicion(estado: Estado, actor: Actor, turno: int) -> DecisionIA | None:
    pasos = pasos_exposicion(estado.p1.nombre, estado.p2.nombre)
    if turno >= len(pasos):
        return None
    paso = pasos[turno]
    if paso.firma != firma(estado, actor):
        return None  # Una intervención externa pasa el control a Minimax.
    op = paso.operador
    motivo = ("Exposición: activar inteligente" if op.prioridad else "Exposición: preparar condiciones EEO")
    return DecisionIA(op, (EvaluacionJugada(op, evaluar(op.aplicar(estado, actor), actor)),),
                      0, motivo, "Plan EEO")


def elegir_exposicion(estado: Estado, actor: Actor, profundidad: int, turno: int,
                     *, turnos_sin_dano: int = 0) -> DecisionIA:
    """Cumple los objetivos y después cierra sin repetir los inteligentes.

    El cierre usa Minimax con ataques normales y especiales legales. Evita
    ciclos de drenajes y deja ver movimientos distintos de los ya expuestos.
    """
    paso = decidir_exposicion(estado, actor, turno)
    if paso is not None:
        return paso
    completo = turno >= len(pasos_exposicion(estado.p1.nombre, estado.p2.nombre))
    decision = elegir_operador(estado, actor, profundidad, turnos_sin_dano=turnos_sin_dano,
                              permitir_inteligentes=not completo)
    return replace(decision, estrategia="Minimax / cierre" if completo else "Minimax",
                   motivo="Ambos inteligentes mostrados; cerrar combate" if completo else
                   "Estado modificado: continúa Minimax competitivo")


def compilar() -> None:
    """Genera los 16 planes con los mismos operadores que usa el juego."""
    salida: dict[str, list[str]] = {}
    for p1 in Nombre:
        for p2 in Nombre:
            camino = buscar_plan(crear_estado(p1, p2))
            salida[f"{p1.value}|{p2.value}"] = [t.value for t in camino]
            print(f"{p1.value} / {p2.value}: {len(camino)} turnos", flush=True)
    RUTA_PLANES.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    compilar()
