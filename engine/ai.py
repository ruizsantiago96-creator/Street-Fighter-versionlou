"""Minimax determinista con poda alfa-beta y explicación de candidatos."""
from __future__ import annotations

from dataclasses import dataclass
from math import inf

from engine.models import Accion, Actor, Colision, Distancia, Estado, Nombre, iniciar_turno
from engine.operators import Operador, TipoOperador, ejecutar_turno, operadores_prioritarios, operadores_validos


@dataclass(frozen=True, slots=True)
class EvaluacionJugada:
    operador: Operador
    puntuacion: float


@dataclass(frozen=True, slots=True)
class DecisionIA:
    operador: Operador | None
    evaluaciones: tuple[EvaluacionJugada, ...]
    nodos_visitados: int
    motivo: str = ""
    estrategia: str = "Minimax"


def opciones_con_iniciativa(estado: Estado, actor: Actor, permitir_inteligentes: bool = True) -> tuple[Operador, ...]:
    """Tras inactividad, ataca o prepara un ataque respetando la v7.

    Dos Bison se acercan hasta Contacto antes de golpearse: en Cerca sus
    drenajes obligatorios pueden alternarse sin daño ni ganancia neta.
    No crea energía, no omite contraataques ni añade operadores auxiliares.
    """
    opciones = (operadores_prioritarios(estado, actor) if permitir_inteligentes else
                tuple(op for op in operadores_validos(estado, actor) if not op.prioridad))
    if not opciones or opciones[0].prioridad:
        return opciones
    p, rival = estado.personaje(actor), estado.personaje(actor.rival)
    espejo = p.nombre is Nombre.BISON and rival.nombre is Nombre.BISON
    ataques = tuple(op for op in opciones
                    if not (espejo and p.distancia is Distancia.CERCA and op.tipo is TipoOperador.GOLPEAR)
                    and op.aplicar(estado, actor).personaje(actor.rival).puntos_salud < rival.puntos_salud)
    if ataques:
        return ataques
    preferidos = [TipoOperador.ATERRIZAR, TipoOperador.CARGAR]
    if p.distancia is Distancia.LEJOS:
        preferidos += [TipoOperador.DESPLAZAR, TipoOperador.ACERCAR]
    elif p.distancia in (Distancia.MEDIA, Distancia.CERCA):
        preferidos += [TipoOperador.ACERCAR]
    else:
        preferidos += [TipoOperador.ALEJAR]
    for tipo in preferidos:
        preparacion = tuple(op for op in opciones if op.tipo is tipo)
        if preparacion:
            return preparacion
    return opciones

def evaluar(estado: Estado, perspectiva: Actor) -> float:
    if estado.terminado:
        if estado.ganador is None:
            return 0.0
        return 100_000.0 if estado.ganador is perspectiva else -100_000.0

    def valor(actor: Actor) -> float:
        p = estado.personaje(actor)
        inteligentes = sum(op.prioridad > 0 for op in operadores_validos(estado, actor))
        return (p.puntos_salud + 45.0 * p.medidor_super + 90.0 * inteligentes
                - (35.0 if p.acciones is Accion.RECUPERACION else 0.0)
                - (15.0 if p.colision is Colision.VULNERABLE else 0.0))

    return valor(perspectiva) - valor(perspectiva.rival)


def elegir_operador(estado: Estado, actor: Actor, profundidad: int = 3, limite_evaluaciones: int = 5,
                   *, turnos_sin_dano: int = 0, permitir_inteligentes: bool = True) -> DecisionIA:
    """Recibe el estado al inicio del turno, igual que el futuro HUD.

    La profundidad cuenta jugadas e incluye la acción raíz. Las evaluaciones
    raíz son exactas para esa profundidad; la lista se ordena de mejor a peor.
    Tras tres turnos sin daño limita las opciones raíz a ataques o preparación
    inmediata. Minimax sigue comparando sus respuestas y conserva la prioridad
    de los operadores inteligentes. El árbol descendiente mantiene sus opciones.
    Entre dos Bison prepara golpes en Contacto desde el inicio para evitar
    intercambios reversibles de Drenar_Energia_Psycho en Cerca.
    """
    if profundidad not in (2, 3):
        raise ValueError("Minimax admite profundidad 2 o 3")
    if limite_evaluaciones < 1:
        raise ValueError("Se debe mostrar al menos una evaluación")
    if turnos_sin_dano < 0:
        raise ValueError("El contador de inactividad no puede ser negativo")
    estado = iniciar_turno(estado, actor)
    nodos = 0

    def opciones_para(s: Estado, turno: Actor) -> tuple[Operador, ...]:
        if permitir_inteligentes:
            return operadores_prioritarios(s, turno)
        return tuple(op for op in operadores_validos(s, turno) if not op.prioridad)

    def minimax(s: Estado, turno: Actor, restante: int, alfa: float, beta: float) -> float:
        nonlocal nodos
        nodos += 1
        if restante == 0 or s.terminado:
            return evaluar(s, actor)
        opciones = opciones_para(s, turno)
        if not opciones:
            return evaluar(s, actor)
        maximizar = turno is actor
        mejor = -inf if maximizar else inf
        for op in opciones:
            puntuacion = minimax(ejecutar_turno(s, turno, op), turno.rival, restante - 1, alfa, beta)
            if maximizar:
                mejor = max(mejor, puntuacion)
                alfa = max(alfa, mejor)
            else:
                mejor = min(mejor, puntuacion)
                beta = min(beta, mejor)
            if beta <= alfa:
                break
        return mejor

    espejo_psycho = estado.p1.nombre is Nombre.BISON and estado.p2.nombre is Nombre.BISON
    iniciativa = (turnos_sin_dano >= 3 or espejo_psycho) and not estado.terminado
    opciones = opciones_con_iniciativa(estado, actor, permitir_inteligentes) if iniciativa else opciones_para(estado, actor)
    jugadas = [EvaluacionJugada(op, minimax(ejecutar_turno(estado, actor, op), actor.rival, profundidad - 1, -inf, inf))
               for op in opciones]
    jugadas.sort(key=lambda j: j.puntuacion, reverse=True)
    return DecisionIA(jugadas[0].operador if jugadas else None, tuple(jugadas[:limite_evaluaciones]), nodos,
                      "Iniciativa: atacar o preparar un ataque" if iniciativa else "")
