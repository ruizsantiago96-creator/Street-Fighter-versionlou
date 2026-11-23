"""Componentes, controles y explicación visual del estado y los operadores."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pygame

from engine.ai import DecisionIA
from engine.models import Actor, Estado, Nombre, RGB
from engine.operators import Condicion, ESPECIALES, INTELIGENTES, OPERADORES, Operador, TipoOperador as T

FONDO: RGB = (11, 15, 24)
PANEL: RGB = (20, 27, 40)
BORDE: RGB = (49, 62, 80)
TEXTO: RGB = (234, 240, 247)
TENUE: RGB = (151, 166, 185)
ORO: RGB = (255, 204, 87)
AZUL: RGB = (77, 188, 222)
ROJO: RGB = (255, 94, 106)
VERDE: RGB = (95, 220, 164)


@lru_cache(maxsize=24)
def fuente(tamano: int = 18, negrita: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont("segoeui,dejavusans,arial", tamano, bold=negrita)


def texto(superficie: pygame.Surface, contenido: str, xy: tuple[int, int], tamano: int = 18,
          color: RGB = TEXTO, negrita: bool = False, ancho: int | None = None) -> None:
    font = fuente(tamano, negrita)
    if ancho is not None:
        original = contenido
        while original and font.size(contenido)[0] > ancho:
            original = original[:-1]
            contenido = original + "…"
        if font.size(contenido)[0] > ancho:
            contenido = ""
    superficie.blit(font.render(contenido, True, color), xy)


def lineas(contenido: str, ancho: int, tamano: int = 16) -> list[str]:
    resultado: list[str] = []
    for parrafo in contenido.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            candidata = f"{actual} {palabra}".strip()
            if actual and fuente(tamano).size(candidata)[0] > ancho:
                resultado.append(actual)
                actual = palabra
            else:
                actual = candidata
        resultado.append(actual)
    return resultado


def parrafo(s: pygame.Surface, contenido: str, xy: tuple[int, int], ancho: int,
            tamano: int = 16, color: RGB = TENUE) -> int:
    x, y = xy
    for linea in lineas(contenido, ancho, tamano):
        texto(s, linea, (x, y), tamano, color)
        y += tamano + 5
    return y


def panel(s: pygame.Surface, rect: pygame.Rect, color: RGB = PANEL) -> None:
    pygame.draw.rect(s, color, rect, border_radius=10)
    pygame.draw.rect(s, BORDE, rect, 1, border_radius=10)


@dataclass(frozen=True, slots=True)
class Boton:
    rect: pygame.Rect
    etiqueta: str
    clave: str
    color: RGB = AZUL
    habilitado: bool = True
    seleccionado: bool = False
    ayuda: str = ""

    def dibujar(self, s: pygame.Surface, mouse: tuple[int, int]) -> None:
        hover = self.rect.collidepoint(mouse)
        relleno = tuple(min(255, c + 15) for c in PANEL) if hover and self.habilitado else PANEL
        pygame.draw.rect(s, relleno, self.rect, border_radius=6)
        borde = self.color if self.habilitado or self.seleccionado else BORDE
        pygame.draw.rect(s, borde, self.rect, 2 if self.seleccionado or hover else 1, border_radius=6)
        texto(s, self.etiqueta, (self.rect.x + 10, self.rect.centery - 11), 16,
              self.color if self.habilitado else (100, 113, 130), self.seleccionado,
              ancho=self.rect.width - 20)

    def pulsado(self, evento: pygame.event.Event) -> bool:
        return self.habilitado and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self.rect.collidepoint(evento.pos)


def tooltip(s: pygame.Surface, contenido: str, mouse: tuple[int, int]) -> None:
    filas = lineas(contenido, 404, 16)
    caja = pygame.Rect(mouse[0] + 12, mouse[1] + 18, 430, len(filas) * 21 + 22)
    caja.clamp_ip(s.get_rect().inflate(-16, -16))
    panel(s, caja, (30, 39, 56))
    for i, fila in enumerate(filas):
        texto(s, fila, (caja.x + 12, caja.y + 10 + i * 21), 16)


EFECTOS: dict[T, str] = {
    T.DESPLAZAR: "Ambos pasan de Lejos a Media, en Desplazamiento / Reposo / Vulnerable.",
    T.GOLPEAR: "100 de daño en Cerca o Contacto; activa recarga = 1. Un impacto derriba al rival aéreo.",
    T.BLOQUEAR: "Invulnerable / Defendiendo. Solo pierdes 10 HP si el rival está Atacando; no revierte daño previo.",
    T.SALTAR: "Salto invulnerable en Reposo; Cerca → Media o Media → Lejos. Después debes Aterrizar, salvo derribo.",
    T.ATERRIZAR: "Desciende voluntariamente: Neutral / Reposo / Vulnerable. No consume super.",
    T.AGARRAR: "Rompe guardia en Cerca o Contacto: 150 de daño, activa recarga = 1 y conserva la distancia.",
    T.SPIN_DRIVE: "300 de daño, invencibilidad; consume 3 de super y apaga recarga.",
    T.KILLER_BEE: "300 de daño desde Media o Contacto; consume 3 de super, apaga recarga y lleva a Contacto.",
    T.PSYCHO_CRUSHER: "350 de daño desde Media o Cerca; consume 3 de super y apaga recarga. Contacto / Desplazamiento.",
    T.SEICHUSEN: "350 de daño desde Cerca o Contacto; consume 3 de super, apaga recarga y lleva a Contacto.",
    T.LIBERAR: "350 de daño; Juli Liberada e invencible; consume 3 de super y conserva su salud actual.",
    T.FINTA: "250 de daño contra Defendiendo en Media. Contacto / Aéreo, activa recarga y conserva el super.",
    T.DRENAR: "Ganas 1 de super; el rival pierde hasta 1 y entra en Recuperacion. Conservas tu salud actual.",
    T.LECTURA: "150 de daño y Contacto; llena super a 3. Conservas tu salud; rival en Recuperacion.",
    T.ACERCAR: "Lejos → Media → Cerca → Contacto; Desplazamiento / Reposo / Vulnerable.",
    T.ALEJAR: "Contacto → Cerca → Media → Lejos; Desplazamiento / Reposo / Vulnerable.",
    T.CARGAR: "Consume recarga = 1 para sumar 1 de super (máximo 3). Requiere Reposo o Cargando en tierra.",
}


def explicar_operador(op: Operador, estado: Estado, actor: Actor) -> str:
    """La explicación usa el mismo contrato del motor, sin duplicar reglas."""
    if estado.terminado:
        return "El combate terminó: ningún operador se puede aplicar."
    faltantes = [c.regla for c in op.condiciones(estado, actor) if not c.cumple]
    if not faltantes:
        return "Efecto: " + EFECTOS[op.tipo]
    return "Falta: " + "; ".join(faltantes) + "."

ESPECIAL_PERSONAJE = {Nombre.JULI: T.SPIN_DRIVE, Nombre.CAMMY: T.KILLER_BEE, Nombre.BISON: T.PSYCHO_CRUSHER, Nombre.MAKOTO: T.SEICHUSEN}
INTELIGENTE_PERSONAJE = {Nombre.JULI: T.LIBERAR, Nombre.CAMMY: T.FINTA, Nombre.BISON: T.DRENAR, Nombre.MAKOTO: T.LECTURA}


@dataclass(frozen=True, slots=True)
class EntradaLog:
    turno: int
    actor: Actor
    personaje: str
    operador: Operador
    dano: int
    dano_rival: int = 0
    super_antes: tuple[int, int] = (0, 0)
    super_despues: tuple[int, int] = (0, 0)
    estado_antes: Estado | None = None
    estado_operador: Estado | None = None
    estado_despues: Estado | None = None
    condiciones: tuple[Condicion, ...] = ()

    @property
    def categoria(self) -> str:
        if self.operador.prioridad:
            return "Inteligente"
        if self.operador.tipo in ESPECIALES:
            return "Poder normal"
        return "Acción"

    @property
    def cambio_super(self) -> str:
        indice = 0 if self.actor is Actor.P1 else 1
        antes, despues = self.super_antes[indice], self.super_despues[indice]
        if self.operador.prioridad or self.operador.tipo in ESPECIALES or antes != despues:
            return f"S{antes}→{despues}"
        return ""


class HUD:
    HISTORIAL = pygame.Rect(950, 329, 294, 145)
    ULTIMO_MOVIMIENTO = pygame.Rect(174, 515, 730, 28)

    def __init__(self) -> None:
        self.scroll = 0

    def barras(self, s: pygame.Surface, estado: Estado, turno: Actor, numero: int) -> None:
        for actor, x in ((Actor.P1, 20), (Actor.P2, 482)):
            p = estado.personaje(actor)
            panel(s, pygame.Rect(x, 16, 434, 115))
            texto(s, f"{actor.value.upper()}  {p.nombre.value}", (x + 14, 23), 23, ORO if turno is actor else TEXTO, True)
            texto(s, f"{p.puntos_salud} / 1000", (x + 303, 30), 16, TEXTO)
            pygame.draw.rect(s, (47, 37, 47), (x + 14, 59, 406, 12), border_radius=4)
            if p.puntos_salud:
                pygame.draw.rect(s, VERDE if p.puntos_salud > 400 else ROJO, (x + 14, 59, round(406 * p.puntos_salud / 1000), 12), border_radius=4)
            for i in range(3):
                pygame.draw.rect(s, ORO if i < p.medidor_super else BORDE, (x + 14 + i * 32, 79, 26, 10), border_radius=2)
            texto(s, f"SUPER {p.medidor_super}/3", (x + 112, 75), 13, ORO if p.medidor_super else TENUE, True)
            texto(s, f"{p.postura.value} · {p.colision.value}", (x + 205, 75), 14, TENUE, ancho=214)
            texto(s, f"{p.especial.value} / {p.acciones.value} / Recarga {p.recarga_energia}", (x + 14, 99), 14, TENUE, ancho=399)
        texto(s, f"{numero:02d}", (440, 4), 14, ORO)

    def botones_accion(self, estado: Estado, actor: Actor, habilitado: bool) -> list[tuple[Boton, Operador]]:
        p = estado.personaje(actor)
        grupos = [
            ([T.DESPLAZAR, T.GOLPEAR, T.BLOQUEAR, T.SALTAR, T.AGARRAR], 548, 5, AZUL),
            ([ESPECIAL_PERSONAJE[p.nombre], INTELIGENTE_PERSONAJE[p.nombre]], 600, 2, ORO),
            ([T.ACERCAR, T.ALEJAR, T.CARGAR, T.ATERRIZAR], 654, 4, VERDE),
        ]
        resultado: list[tuple[Boton, Operador]] = []
        for tipos, y, columnas, color in grupos:
            ancho = (884 - (columnas - 1) * 8) // columnas
            for i, tipo in enumerate(tipos):
                op = next(o for o in OPERADORES if o.tipo is tipo)
                valido = op.puede_aplicarse(estado, actor)
                ayuda = explicar_operador(op, estado, actor)
                etiqueta = op.nombre.replace("_", " ")
                if tipo in ESPECIALES:
                    etiqueta = "NORMAL / " + etiqueta
                    ayuda = "PODER NORMAL: consume 3 bloques de super. " + ayuda
                elif tipo in INTELIGENTES:
                    etiqueta = "INTELIGENTE / " + etiqueta
                    ayuda = "OPERADOR INTELIGENTE: reacción condicional; aplica su propia regla de super. " + ayuda
                if not habilitado and not estado.terminado:
                    ayuda = "Controles bloqueados durante el turno de la CPU o la animación. " + ayuda
                boton = Boton(pygame.Rect(24 + i * (ancho + 8), y, ancho, 32), etiqueta, tipo.value,
                              ROJO if tipo in INTELIGENTES else color, habilitado and valido, ayuda=ayuda)
                resultado.append((boton, op))
        return resultado

    def controles(self, s: pygame.Surface, estado: Estado, actor: Actor, habilitado: bool, mouse: tuple[int, int]) -> str:
        panel(s, pygame.Rect(16, 508, 908, 196))
        texto(s, "01 / GENERALES", (24, 523), 12, AZUL, True)
        texto(s, "02 / PODER NORMAL · CONSUME 3 SUPER", (24, 579), 12, ORO, True)
        texto(s, "03 / OPERADOR INTELIGENTE · CONDICIONAL", (474, 579), 12, ROJO, True)
        texto(s, "04 / AUXILIARES", (24, 634), 12, VERDE, True)
        ayuda = ""
        for boton, op in self.botones_accion(estado, actor, habilitado):
            boton.dibujar(s, mouse)
            if op.prioridad or op.tipo in ESPECIALES:
                pygame.draw.rect(s, ROJO if op.prioridad else ORO,
                                 (boton.rect.x, boton.rect.y + 3, 3, boton.rect.height - 6), border_radius=1)
            if boton.rect.collidepoint(mouse):
                ayuda = boton.ayuda
        return ayuda

    def leyenda_poderes(self, s: pygame.Surface) -> None:
        """Leyenda permanente, visible entre los turnos y durante la pausa."""
        pygame.draw.rect(s, FONDO, (390, 461, 408, 27), border_radius=4)
        pygame.draw.rect(s, ORO, (398, 472, 7, 7))
        texto(s, "Poder normal: 3 super", (411, 466), 12, ORO, True)
        pygame.draw.rect(s, ROJO, (594, 472, 7, 7))
        texto(s, "Inteligente: condicional", (607, 466), 12, ROJO, True)

    def desplazar(self, pasos: int, total: int) -> None:
        self.scroll = max(0, min(max(0, total - 4), self.scroll + pasos))

    def entrada_en(self, pos: tuple[int, int], log: list[EntradaLog]) -> EntradaLog | None:
        fin = len(log) - min(self.scroll, max(0, len(log) - 4))
        visibles = log[max(0, fin - 4):fin]
        for i, entrada in enumerate(visibles):
            if pygame.Rect(954, 334 + i * 34, 280, 34).collidepoint(pos):
                return entrada
        return None

    def ultimo_movimiento(self, s: pygame.Surface, entrada: EntradaLog, mouse: tuple[int, int]) -> None:
        cumplidas = sum(c.cumple for c in entrada.condiciones)
        etiqueta = f"Último: {entrada.operador.nombre.replace('_', ' ')} · {cumplidas}/{len(entrada.condiciones)} reglas OK · Ver reglas →"
        Boton(self.ULTIMO_MOVIMIENTO, etiqueta, "detalle", VERDE).dibujar(s, mouse)

    def inspector(self, s: pygame.Surface, estado: Estado, log: list[EntradaLog], decision: DecisionIA | None,
                  actor_ia: Actor | None, estado_turno: str, profundidad: int,
                  objetivos: tuple[bool, ...] | None = None) -> None:
        panel(s, pygame.Rect(934, 16, 330, 688))
        texto(s, "INSPECTOR EEO + IA", (950, 30), 20, ORO, True)
        subtitulo = ("EXPOSICIÓN / " + " · ".join(f"P{i + 1} {'OK' if usado else 'PENDIENTE'}"
                      for i, usado in enumerate(objetivos))) if objetivos is not None else "ESPACIO DE ESTADOS / EN VIVO"
        texto(s, subtitulo, (950, 57), 11, VERDE if objetivos and all(objetivos) else TENUE)
        texto(s, f"[ ({estado.escenario.hora.value},", (950, 82), 16, AZUL)
        fin = parrafo(s, estado.escenario.lugar.value + "),", (965, 105), 275, 15, AZUL)
        for actor, y in ((Actor.P1, max(156, fin + 5)), (Actor.P2, max(228, fin + 77))):
            p = estado.personaje(actor)
            texto(s, f"({actor.value.upper()}: {p.nombre.value}, {p.puntos_salud} HP, S{p.medidor_super},", (950, y), 15, TEXTO, True)
            texto(s, f"{p.distancia.value}, {p.especial.value}),", (965, y + 22), 15, TENUE)
            texto(s, f"{p.acciones.value} / daño={p.dano_recibido}", (965, y + 43), 13, TENUE)
        texto(s, "]", (950, 294), 15, AZUL)
        texto(s, "HISTORIAL", (950, 308), 12, AZUL, True)
        texto(s, f"{len(log)} turnos · clic: ver reglas", (1040, 308), 11, TENUE)
        pygame.draw.rect(s, FONDO, self.HISTORIAL, border_radius=5)
        self.scroll = min(self.scroll, max(0, len(log) - 4))
        fin_log = len(log) - self.scroll
        visibles = log[max(0, fin_log - 4):fin_log]
        for i, entrada in enumerate(visibles):
            y = 335 + i * 34
            color = ROJO if entrada.operador.prioridad else ORO if entrada.operador.tipo in ESPECIALES else TENUE
            if entrada.operador.prioridad:
                pygame.draw.rect(s, (64, 27, 40), (954, y - 1, 280, 33), border_radius=3)
            texto(s, f"{entrada.turno:03d} / {entrada.actor.value.upper()} {entrada.personaje}  −{entrada.dano} {entrada.cambio_super}", (958, y), 12, color, True, ancho=275)
            prefijo = f"{entrada.categoria} / " if entrada.operador.prioridad or entrada.operador.tipo in ESPECIALES else ""
            texto(s, prefijo + entrada.operador.nombre.replace("_", " "), (958, y + 16), 13, color, ancho=275)
        if not log:
            parrafo(s, "Aquí se registran las transiciones de cada turno.", (960, 349), 270)
        if len(log) > 4:
            alto = max(12, 137 * 4 // len(log))
            pos = 333 + round((137 - alto) * (1 - self.scroll / max(1, len(log) - 4)))
            pygame.draw.rect(s, AZUL, (1238, pos, 3, alto), border_radius=1)
        plan = decision is not None and decision.estrategia == "Plan EEO"
        titulo = ("PLAN EEO / EXPOSICIÓN" if plan or (decision is None and objetivos is not None)
                  else "MINIMAX / CIERRE" if decision and "cierre" in decision.estrategia else "PENSAMIENTO MINIMAX")
        texto(s, titulo, (950, 490), 15, ORO, True)
        if decision is None:
            parrafo(s, "Esperando la primera decisión de la CPU…", (950, 527), 290)
        else:
            detalle = ("Paso planificado · puntaje de referencia" if plan else
                       f"{actor_ia.value.upper() if actor_ia else 'CPU'} · profundidad {profundidad} · {decision.nodos_visitados} nodos")
            texto(s, detalle, (950, 515), 12, TENUE)
            for i, jugada in enumerate(decision.evaluaciones):
                y = 541 + i * 23
                elegida = jugada.operador == decision.operador
                color = ORO if elegida else TENUE
                texto(s, ("› " if elegida else "  ") + jugada.operador.nombre.replace("_", " "), (950, y), 12, color, elegida, ancho=220)
                texto(s, f"{jugada.puntuacion:+.0f}", (1180, y), 13, color)
            if decision.motivo:
                texto(s, decision.motivo, (950, 658), 11, AZUL, ancho=293)
        texto(s, estado_turno, (950, 677), 13, VERDE, ancho=292)
