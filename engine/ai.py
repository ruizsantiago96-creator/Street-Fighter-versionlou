"""Minimax determinista con poda alfa-beta y explicación de candidatos."""
from __future__ import annotations

from dataclasses import dataclass
from math import inf

from engine.models import Accion, Actor, Colision, Distancia, Estado, Nombre, Postura
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


def opciones_con_iniciativa(estado: Estado, actor: Actor) -> tuple[Operador, ...]:
    """Política de progreso: atacar o preparar un ataque con operadores legales.

    Se activa tras tres turnos sin daño, o desde el inicio entre dos Bison.
    No modifica precondiciones, salud, medidores ni normalización.
    Los inteligentes mantienen máxima prioridad.
    """
    opciones = operadores_prioritarios(estado, actor)
    if not opciones or opciones[0].prioridad:
        return opciones
    rival = estado.personaje(actor.rival)
    p = estado.personaje(actor)
    espejo_psycho = p.nombre is Nombre.BISON and rival.nombre is Nombre.BISON
    # Un golpe Cerca entre dos Bison provoca drenajes obligatorios alternados.
    # Planear Psycho Crusher en Media evita entrar en ese componente cíclico.
    ataques = tuple(op for op in opciones if (not espejo_psycho or op.tipo is not TipoOperador.GOLPEAR)
                    and op.aplicar(estado, actor).personaje(actor.rival).puntos_salud < rival.puntos_salud)
    if ataques:
        return ataques
    if espejo_psycho:
        if p.acciones is Accion.ATACANDO or p.postura is not Postura.NEUTRAL:
            preparar = TipoOperador.REPOSAR
        elif p.distancia is Distancia.CONTACTO and rival.acciones is Accion.ATACANDO:
            preparar = TipoOperador.REPOSAR
        elif p.medidor_super < 3:
            preparar = TipoOperador.CARGAR
        elif p.distancia is Distancia.LEJOS:
            preparar = TipoOperador.DESPLAZAR
        else:
            preparar = TipoOperador.ALEJAR
    elif p.distancia is Distancia.CONTACTO:
        # Golpear exige Cerca: salir de Contacto también recupera Neutral/Reposo.
        preparar = TipoOperador.ALEJAR
    elif p.postura is not Postura.NEUTRAL or p.acciones is Accion.ATACANDO:
        preparar = TipoOperador.REPOSAR
    elif p.distancia is Distancia.LEJOS:
        preparar = TipoOperador.DESPLAZAR
    elif p.distancia is Distancia.MEDIA:
        preparar = TipoOperador.ACERCAR
    elif p.medidor_super < 3:
        preparar = TipoOperador.CARGAR
    else:
        # El rival aún no es Vulnerable: preparar el golpe para su próximo turno.
        preparar = TipoOperador.REPOSAR
    return tuple(op for op in opciones if op.tipo is preparar) or opciones


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
                   *, turnos_sin_dano: int = 0) -> DecisionIA:
    """Recibe el estado al inicio del turno, igual que el futuro HUD.

    La profundidad cuenta jugadas e incluye la acción raíz. Las evaluaciones
    raíz son exactas para esa profundidad; la lista se ordena de mejor a peor.
    Tras tres turnos sin daño limita las opciones raíz a ataques o preparación
    inmediata. Minimax sigue comparando sus respuestas y conserva la prioridad
    de los operadores inteligentes. El árbol descendiente mantiene sus opciones.
    Entre dos Bison prepara especiales desde el inicio para no entrar en un
    intercambio obligatorio y reversible de Drenar_Energia_Psycho en Cerca.
    """
    if profundidad not in (2, 3):
        raise ValueError("Minimax admite profundidad 2 o 3")
    if limite_evaluaciones < 1:
        raise ValueError("Se debe mostrar al menos una evaluación")
    if turnos_sin_dano < 0:
        raise ValueError("El contador de inactividad no puede ser negativo")
    nodos = 0

    def minimax(s: Estado, turno: Actor, restante: int, alfa: float, beta: float) -> float:
        nonlocal nodos
        nodos += 1
        if restante == 0 or s.terminado:
            return evaluar(s, actor)
        opciones = operadores_prioritarios(s, turno)
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
    opciones = opciones_con_iniciativa(estado, actor) if iniciativa else operadores_prioritarios(estado, actor)
    jugadas = [EvaluacionJugada(op, minimax(ejecutar_turno(estado, actor, op), actor.rival, profundidad - 1, -inf, inf))
               for op in opciones]
    jugadas.sort(key=lambda j: j.puntuacion, reverse=True)
    return DecisionIA(jugadas[0].operador if jugadas else None, tuple(jugadas[:limite_evaluaciones]), nodos,
                      "Iniciativa: atacar o preparar un ataque" if iniciativa else "")
