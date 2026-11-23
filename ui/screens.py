"""Selección, coordinación de turnos y presentación del resultado del combate."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from math import sin

import pygame

from engine.ai import DecisionIA, elegir_operador
from engine.exhibition import elegir_exposicion
from engine.models import Actor, Hora, Lugar, Nombre, Vista, crear_estado, crear_personaje, iniciar_turno
from engine.operators import ESPECIALES, Operador
from ui.hud import (AZUL, BORDE, ESPECIAL_PERSONAJE, FONDO, ORO, PANEL, ROJO,
                    TENUE, TEXTO, VERDE, Boton, EntradaLog, HUD, fuente, panel,
                    lineas, parrafo, texto, tooltip)
from ui.renderer import Renderer, dibujar_personaje
from ui.animations import DURACION
from ui.details import DetalleMovimiento


class Modo(str, Enum):
    JUGADOR_IA = "Jugador vs IA"
    IA_IA = "IA vs IA"


@dataclass(frozen=True, slots=True)
class Configuracion:
    p1: Nombre = Nombre.JULI
    p2: Nombre = Nombre.BISON
    lugar: Lugar = Lugar.ESTADIO
    hora: Hora = Hora.TARDE
    modo: Modo = Modo.JUGADOR_IA
    profundidad: int = 3
    exposicion: bool = True

    def __post_init__(self) -> None:
        if self.profundidad not in (2, 3):
            raise ValueError("La profundidad debe ser 2 o 3")


class Portada:
    """Entrada arcade; no crea combates ni inicia trabajadores de IA."""

    def botones(self) -> list[Boton]:
        return [Boton(pygame.Rect(470, 453, 340, 72), "JUGAR", "jugar", ORO),
                Boton(pygame.Rect(540, 545, 200, 38), "SALIR", "salir", TENUE)]

    def evento(self, evento: pygame.event.Event) -> str | None:
        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return "jugar"
            if evento.key == pygame.K_ESCAPE:
                return "salir"
        for boton in self.botones():
            if boton.pulsado(evento):
                return boton.clave
        return None

    def dibujar(self, s: pygame.Surface, ahora: int, mouse: tuple[int, int]) -> None:
        tiempo = ahora / 1000
        s.fill((8, 11, 24))
        # Horizonte de neón, edificios y suelo en perspectiva.
        for y in range(100, 561):
            intensidad = max(0, 1 - abs(y - 375) / 275)
            pygame.draw.line(s, (int(11 + 30 * intensidad), 13, int(29 + 39 * intensidad)), (0, y), (1280, y))
        pygame.draw.circle(s, (78, 35, 65), (640, 375), 210)
        for y in range(220, 570, 16):
            pygame.draw.line(s, (23, 16, 37), (420, y), (860, y), 5)
        for i in range(20):
            x = i * 68
            alto = 65 + (i * 47 % 100)
            pygame.draw.rect(s, (12, 18, 32), (x, 560 - alto, 56, alto))
            for wy in range(570 - alto, 550, 19):
                pygame.draw.rect(s, (36, 49, 68), (x + 10, wy, 6, 4))
        pygame.draw.line(s, AZUL, (0, 560), (1280, 560), 2)
        for x in range(-1280, 2561, 160):
            pygame.draw.line(s, (26, 39, 63), (640 + (x - 640) // 4, 561), (x, 720))
        for i in range(9):
            avance = ((i / 9 + tiempo * 0.08) % 1) ** 2
            y = 562 + round(avance * 158)
            pygame.draw.line(s, (26, 39, 63), (0, y), (1280, y))
        # Los mismos sprites locales que aparecen en la pelea.
        dibujar_personaje(s, crear_personaje(Nombre.JULI, Vista.DERECHA), 220, 588, tiempo, escala=1.65)
        dibujar_personaje(s, crear_personaje(Nombre.BISON, Vista.IZQUIERDA), 1060, 588, tiempo, escala=1.65)
        texto(s, "E E O   /   A R C A D E", (47, 30), 16, AZUL, True)
        texto(s, "COMBATE TÁCTICO POR TURNOS", (921, 30), 14, TENUE)
        self.centrado(s, "CADA DECISIÓN CAMBIA LA PELEA", 145, 16, ORO)
        for titulo, y, tamano in (("TACTICAL", 178, 88), ("FIGHTER", 266, 102)):
            sombra = fuente(tamano, True).render(titulo, True, (139, 39, 62))
            frente = fuente(tamano, True).render(titulo, True, TEXTO if titulo == "TACTICAL" else ORO)
            s.blit(sombra, sombra.get_rect(midtop=(646, y + 6)))
            s.blit(frente, frente.get_rect(midtop=(640, y)))
        self.centrado(s, "4 LUCHADORES   /   5 ARENAS   /   UN SOLO GANADOR", 391, 14, TENUE)
        for boton in self.botones():
            hover = boton.rect.collidepoint(mouse)
            if boton.clave == "jugar":
                halo = boton.rect.inflate(12, 12)
                pygame.draw.rect(s, (80 + int(20 * sin(tiempo * 3)), 63, 30), halo, 2, border_radius=8)
                pygame.draw.rect(s, (255, 223, 132) if hover else ORO, boton.rect, border_radius=5)
                self.centrado(s, "JUGAR   /   PLAY", boton.rect.y + 17, 26, (20, 24, 36))
            else:
                pygame.draw.rect(s, BORDE if hover else (18, 24, 38), boton.rect, border_radius=5)
                self.centrado(s, "SALIR", boton.rect.y + 7, 16, TEXTO if hover else TENUE)
        self.centrado(s, "PULSA ENTER O ESPACIO PARA JUGAR", 620, 13,
                      TEXTO if sin(tiempo * 3) > -0.3 else TENUE)
        texto(s, "PYTHON / PYGAME", (32, 686), 12, TENUE)
        texto(s, "ESC: salir", (1175, 686), 12, TENUE)

    @staticmethod
    def centrado(s: pygame.Surface, contenido: str, y: int, tamano: int, color: tuple[int, int, int]) -> None:
        imagen = fuente(tamano, True).render(contenido, True, color)
        s.blit(imagen, imagen.get_rect(midtop=(640, y)))


class Seleccion:
    def __init__(self, config: Configuracion | None = None) -> None:
        self.config = config or Configuracion()

    def botones(self) -> list[Boton]:
        botones: list[Boton] = []
        for actor, x0 in ((Actor.P1, 24), (Actor.P2, 664)):
            elegido = self.config.p1 if actor is Actor.P1 else self.config.p2
            for i, nombre in enumerate(Nombre):
                botones.append(Boton(pygame.Rect(x0 + i * 150, 149, 142, 161), nombre.value,
                                     f"{actor.value}:{nombre.value}", AZUL if actor is Actor.P1 else ROJO,
                                     seleccionado=elegido is nombre))
        for i, hora in enumerate(Hora):
            botones.append(Boton(pygame.Rect(24 + i * 142, 379, 130, 42), hora.value,
                                 f"hora:{hora.value}", ORO, seleccionado=self.config.hora is hora))
        for i, modo in enumerate(Modo):
            botones.append(Boton(pygame.Rect(490 + i * 215, 379, 203, 42), modo.value,
                                 f"modo:{modo.value}", VERDE, seleccionado=self.config.modo is modo))
        for i, profundidad in enumerate((2, 3)):
            botones.append(Boton(pygame.Rect(956 + i * 150, 379, 138, 42), f"Nivel {profundidad}",
                                 f"profundidad:{profundidad}", ROJO, seleccionado=self.config.profundidad == profundidad))
        for i, (etiqueta, valor) in enumerate((("Exposición: ambos inteligentes", True), ("Competitivo: Minimax", False))):
            botones.append(Boton(pygame.Rect(24 + i * 405, 434, 393, 32), etiqueta,
                                 f"exposicion:{int(valor)}", AZUL,
                                 habilitado=self.config.modo is Modo.IA_IA,
                                 seleccionado=self.config.exposicion is valor))
        botones.append(Boton(pygame.Rect(866, 496, 384, 72), "INICIAR COMBATE  →", "iniciar", ORO, seleccionado=True))
        botones.append(Boton(pygame.Rect(1040, 26, 210, 38), "← VOLVER A PORTADA", "portada", TENUE))
        return botones

    def evento(self, evento: pygame.event.Event) -> bool:
        from dataclasses import replace

        if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return True
        for boton in self.botones():
            if not boton.pulsado(evento):
                continue
            if boton.clave == "iniciar":
                return True
            if boton.clave == "portada":
                continue  # La navegación la gestiona Aplicacion.
            campo, valor = boton.clave.split(":", 1)
            if campo == "p1":
                self.config = replace(self.config, p1=Nombre(valor))
            elif campo == "p2":
                self.config = replace(self.config, p2=Nombre(valor))
            elif campo == "hora":
                self.config = replace(self.config, hora=Hora(valor))
            elif campo == "modo":
                self.config = replace(self.config, modo=Modo(valor))
            elif campo == "profundidad":
                self.config = replace(self.config, profundidad=int(valor))
            elif campo == "exposicion":
                self.config = replace(self.config, exposicion=bool(int(valor)))
        return False

    def dibujar(self, s: pygame.Surface, ahora: int, mouse: tuple[int, int]) -> None:
        s.fill(FONDO)
        for x in range(0, 1280, 42):
            pygame.draw.line(s, (17, 23, 35), (x, 0), (x - 240, 720))
        texto(s, "EEO / TACTICAL FIGHTER", (24, 21), 16, ORO, True)
        texto(s, "ELIGE A TUS LUCHADORES", (24, 46), 36, TEXTO, True)
        texto(s, "Elige a tus luchadores y prepara el experimento.", (24, 94), 18, TENUE)
        texto(s, "01 / JUGADOR UNO", (24, 124), 14, AZUL, True)
        texto(s, "02 / JUGADOR DOS", (664, 124), 14, ROJO, True)
        botones = self.botones()
        for boton in botones:
            if boton.clave.startswith(("p1:", "p2:")):
                panel(s, boton.rect)
                pygame.draw.rect(s, boton.color if boton.seleccionado else BORDE, boton.rect, 2, border_radius=10)
                actor, valor = boton.clave.split(":", 1)
                p = crear_personaje(Nombre(valor), Vista.DERECHA if actor == "p1" else Vista.IZQUIERDA)
                dibujar_personaje(s, p, boton.rect.centerx, boton.rect.y + 103, ahora / 1000, escala=0.48)
                texto(s, p.nombre.value, (boton.rect.x + 9, boton.rect.y + 9), 19, boton.color if boton.seleccionado else TEXTO, True)
                for i, color in enumerate(p.color):
                    pygame.draw.rect(s, color, (boton.rect.x + 10 + i * 20, boton.rect.y + 111, 15, 5), border_radius=1)
                poder = ESPECIAL_PERSONAJE[p.nombre].value
                for j, fila in enumerate(lineas(poder, 126, 12)):
                    texto(s, fila, (boton.rect.x + 9, boton.rect.y + 124 + j * 15), 12, TENUE)
            else:
                boton.dibujar(s, mouse)
        texto(s, "03 / ILUMINACIÓN", (24, 348), 14, ORO, True)
        texto(s, "04 / MODO DE COMBATE", (490, 348), 14, VERDE, True)
        texto(s, "05 / MINIMAX", (956, 348), 14, ROJO, True)
        panel(s, pygame.Rect(24, 474, 801, 108))
        texto(s, "UN LABORATORIO DE DECISIONES", (42, 491), 17, ORO, True)
        parrafo(s, "Exposición prepara las condiciones legales de ambos inteligentes antes del K.O. Competitivo usa Minimax para ganar. En IA vs IA puedes pausar y avanzar paso a paso.", (42, 521), 755, 16)
        texto(s, "ESCENARIO ALEATORIO", (24, 620), 14, AZUL, True)
        texto(s, "El lugar se sortea al iniciar cada combate y cada revancha.", (246, 618), 17, TENUE)
        texto(s, "1280 × 720  /  60 FPS  /  PYTHON + PYGAME", (24, 693), 11, TENUE)
        texto(s, "ENTER: iniciar   ·   ESC: portada", (990, 693), 12, TENUE)


@dataclass(frozen=True, slots=True)
class ResumenLuchador:
    actor: Actor
    nombre: str
    salud_final: int
    dano_causado: int
    especiales: int
    inteligentes: int


class Combate:
    """El estado jugable está normalizado; Renderer conserva el impacto previo.

    Minimax usa únicamente instantáneas inmutables en un trabajador. Todos los
    eventos y cambios del combate se resuelven en el hilo principal de Pygame.
    """
    HISTORIAL_KO = pygame.Rect(670, 166, 460, 397)

    def __init__(self, config: Configuracion, ahora: int) -> None:
        self.config = config
        self.estado = iniciar_turno(crear_estado(config.p1, config.p2, config.hora, config.lugar), Actor.P1)
        self.turno = Actor.P1
        self.log: list[EntradaLog] = []
        self.turnos_sin_dano = 0
        self.hud = HUD()
        self.renderer = Renderer(self.estado)
        self.ultima_decision: DecisionIA | None = None
        self.ultimo_actor_ia: Actor | None = None
        self.pausado = False
        self.paso_pendiente = False
        self.siguiente_ia = ahora + 1200
        self.restante_pausa = 1200
        self.animacion_hasta = ahora
        self.ko_instante: int | None = None
        self.scroll_ko = 0
        self.detalle: DetalleMovimiento | None = None
        self.detalle_inicio = 0
        self.error = ""
        self.ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="eeo-minimax")
        self.futuro: Future[DecisionIA] | None = None
        self.cerrado = False

    @property
    def es_cpu(self) -> bool:
        return self.config.modo is Modo.IA_IA or self.turno is Actor.P2

    def puede_jugar(self, ahora: int) -> bool:
        return self.detalle is None and not self.es_cpu and not self.estado.terminado and ahora >= self.animacion_hasta

    def jugar(self, op: Operador, ahora: int) -> None:
        if self.cerrado or self.estado.terminado:
            return
        antes = self.estado
        despues = op.aplicar(antes, self.turno)
        self.renderer.registrar(antes, despues, self.turno, op, ahora)
        dano = sum(antes.personaje(a).puntos_salud - despues.personaje(a).puntos_salud for a in Actor)
        self.turnos_sin_dano = 0 if dano > 0 else self.turnos_sin_dano + 1
        dano_rival = antes.personaje(self.turno.rival).puntos_salud - despues.personaje(self.turno.rival).puntos_salud
        siguiente_actor = self.turno.rival
        normalizado = iniciar_turno(despues, siguiente_actor)
        self.log.append(EntradaLog(len(self.log) + 1, self.turno, antes.personaje(self.turno).nombre.value, op, dano, dano_rival,
                                   (antes.p1.medidor_super, antes.p2.medidor_super),
                                   (despues.p1.medidor_super, despues.p2.medidor_super),
                                   estado_antes=antes, estado_operador=despues, estado_despues=normalizado,
                                   condiciones=op.condiciones(antes, self.turno)))
        self.hud.scroll = 0
        self.turno = siguiente_actor
        self.estado = normalizado
        self.animacion_hasta = ahora + DURACION
        self.siguiente_ia = ahora + (1200 if self.config.modo is Modo.IA_IA else 700)
        self.restante_pausa = 1200
        if self.estado.terminado:
            self.ko_instante = ahora

    def actualizar(self, ahora: int, dt: float) -> None:
        self.renderer.actualizar(self.estado, dt)
        if self.cerrado or self.detalle is not None or self.estado.terminado or not self.es_cpu or self.error:
            return
        if self.pausado and not self.paso_pendiente:
            return
        limite = self.animacion_hasta if self.paso_pendiente else self.siguiente_ia
        if ahora < limite:
            return
        if self.futuro is None:
            if self.config.modo is Modo.IA_IA and self.config.exposicion:
                self.futuro = self.ejecutor.submit(elegir_exposicion, self.estado, self.turno,
                                                  self.config.profundidad, len(self.log),
                                                  turnos_sin_dano=self.turnos_sin_dano)
            else:
                self.futuro = self.ejecutor.submit(elegir_operador, self.estado, self.turno, self.config.profundidad,
                                                  turnos_sin_dano=self.turnos_sin_dano)
        if self.futuro.done():
            try:
                decision = self.futuro.result()
            except Exception as exc:
                self.error = f"Error de IA: {exc}"
                self.pausado = True
                self.futuro = None
                return
            self.futuro = None
            self.ultima_decision = decision
            self.ultimo_actor_ia = self.turno
            self.paso_pendiente = False
            if decision.operador is not None:
                self.jugar(decision.operador, ahora)

    def botones_transporte(self) -> list[Boton]:
        botones = [Boton(pygame.Rect(810, 461, 100, 27), "Menú", "menu", TENUE)]
        if self.config.modo is Modo.IA_IA:
            botones.extend([
                Boton(pygame.Rect(30, 461, 154, 27), "Reanudar" if self.pausado else "Pausar", "pausa", ORO),
                Boton(pygame.Rect(194, 461, 176, 27), "Siguiente paso →", "paso", AZUL, not self.paso_pendiente),
            ])
        return botones

    def botones_ko(self) -> list[Boton]:
        return [Boton(pygame.Rect(344, 613, 280, 47), "Revancha", "revancha", ORO),
                Boton(pygame.Rect(648, 613, 280, 47), "Volver al menú", "menu", AZUL)]

    def resumen_luchadores(self) -> tuple[ResumenLuchador, ...]:
        return tuple(ResumenLuchador(
            actor, self.estado.personaje(actor).nombre.value,
            self.estado.personaje(actor).puntos_salud,
            sum(e.dano_rival for e in self.log if e.actor is actor),
            sum(e.operador.tipo in ESPECIALES for e in self.log if e.actor is actor),
            sum(e.operador.prioridad > 0 for e in self.log if e.actor is actor),
        ) for actor in Actor)

    def mostrar_ko(self, ahora: int) -> bool:
        return self.ko_instante is not None and ahora >= self.ko_instante + 850

    def alternar_pausa(self, ahora: int) -> None:
        if not self.pausado:
            self.restante_pausa = max(0, self.siguiente_ia - ahora)
            self.pausado = True
            self.paso_pendiente = False
        else:
            self.pausado = False
            self.paso_pendiente = False
            self.siguiente_ia = ahora + self.restante_pausa

    def solicitar_paso(self) -> None:
        self.pausado = True
        self.paso_pendiente = True

    def abrir_detalle(self, entrada: EntradaLog, ahora: int) -> None:
        if self.detalle is None:
            self.detalle_inicio = ahora
        self.detalle = DetalleMovimiento(entrada)

    def cerrar_detalle(self, ahora: int) -> None:
        if self.detalle is not None:
            pausa = max(0, ahora - self.detalle_inicio)
            self.siguiente_ia += pausa
            self.animacion_hasta += pausa
            self.detalle = None

    def indice_detalle(self) -> int | None:
        if self.detalle is None:
            return None
        return next((i for i, e in enumerate(self.log) if e is self.detalle.entrada), None)

    def navegar_detalle(self, paso: int) -> None:
        indice = self.indice_detalle()
        if indice is not None and 0 <= indice + paso < len(self.log):
            self.detalle = DetalleMovimiento(self.log[indice + paso])

    def entrada_ko_en(self, pos: tuple[int, int]) -> EntradaLog | None:
        for i, entrada in enumerate(self.log[self.scroll_ko:self.scroll_ko + 8]):
            if pygame.Rect(676, 173 + i * 47, 445, 44).collidepoint(pos):
                return entrada
        return None

    def evento(self, evento: pygame.event.Event, ahora: int) -> str | None:
        if self.detalle is not None:
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    self.cerrar_detalle(ahora)
                elif evento.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.navegar_detalle(-1 if evento.key == pygame.K_LEFT else 1)
            elif evento.type == pygame.MOUSEWHEEL and self.detalle.TRANSICION.collidepoint(pygame.mouse.get_pos()):
                self.detalle.desplazar(-evento.y)
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                for boton in self.detalle.botones(self.indice_detalle(), len(self.log), self.estado.terminado):
                    if boton.pulsado(evento):
                        if boton.clave == "cerrar":
                            self.cerrar_detalle(ahora)
                        else:
                            self.navegar_detalle(-1 if boton.clave == "anterior" else 1)
                        break
            return None
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "menu"
        if self.mostrar_ko(ahora):
            if evento.type == pygame.MOUSEWHEEL and self.HISTORIAL_KO.collidepoint(pygame.mouse.get_pos()):
                self.scroll_ko = max(0, min(max(0, len(self.log) - 8), self.scroll_ko - evento.y * 2))
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                entrada = self.entrada_ko_en(evento.pos)
                if entrada is not None:
                    self.abrir_detalle(entrada, ahora)
                    return None
            for boton in self.botones_ko():
                if boton.pulsado(evento):
                    return boton.clave
            return None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            entrada = self.hud.entrada_en(evento.pos, self.log)
            if entrada is None and self.log and self.hud.ULTIMO_MOVIMIENTO.collidepoint(evento.pos):
                entrada = self.log[-1]
            if entrada is not None:
                self.abrir_detalle(entrada, ahora)
                return None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 3:
            actor = self.turno if self.config.modo is Modo.IA_IA else Actor.P1
            for boton, op in self.hud.botones_accion(self.estado, actor, False):
                if boton.rect.collidepoint(evento.pos):
                    previa = EntradaLog(0, actor, self.estado.personaje(actor).nombre.value, op, 0,
                                        estado_antes=self.estado, condiciones=op.condiciones(self.estado, actor))
                    self.abrir_detalle(previa, ahora)
                    return None
        if evento.type == pygame.MOUSEWHEEL:
            if self.hud.HISTORIAL.collidepoint(pygame.mouse.get_pos()):
                self.hud.desplazar(evento.y, len(self.log))
        if self.estado.terminado:
            return None
        if evento.type == pygame.KEYDOWN and self.config.modo is Modo.IA_IA:
            if evento.key == pygame.K_SPACE:
                self.alternar_pausa(ahora)
            elif evento.key == pygame.K_RIGHT:
                self.solicitar_paso()
        for boton in self.botones_transporte():
            if boton.pulsado(evento):
                if boton.clave == "menu":
                    return "menu"
                if boton.clave == "pausa":
                    self.alternar_pausa(ahora)
                elif boton.clave == "paso":
                    self.solicitar_paso()
                return None
        if self.puede_jugar(ahora):
            for boton, op in self.hud.botones_accion(self.estado, self.turno, True):
                if boton.pulsado(evento):
                    self.jugar(op, ahora)
                    break
        return None

    def dibujar_ko(self, s: pygame.Surface, mouse: tuple[int, int]) -> None:
        velo = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        velo.fill((5, 8, 16, 210))
        s.blit(velo, (0, 0))
        panel(s, pygame.Rect(126, 38, 1028, 644))
        texto(s, "K.O.", (150, 50), 66, ROJO, True)
        ganador = self.estado.ganador
        nombre = f"{ganador.value.upper()} / {self.estado.personaje(ganador).nombre.value}" if ganador else "Empate"
        texto(s, f"Ganador: {nombre}", (350, 63), 28, ORO, True)
        texto(s, f"RESUMEN DE LA PELEA / {len(self.log)} TURNOS", (350, 106), 14, TENUE, True)
        for i, resumen in enumerate(self.resumen_luchadores()):
            x = 150 + i * 249
            panel(s, pygame.Rect(x, 166, 233, 134))
            texto(s, f"{resumen.actor.value.upper()} / {resumen.nombre}", (x + 12, 176), 20, AZUL if i == 0 else ROJO, True)
            texto(s, f"Salud final: {resumen.salud_final} / 1000", (x + 12, 211), 16, TEXTO)
            texto(s, f"Daño causado: {resumen.dano_causado}", (x + 12, 235), 16, TEXTO)
            texto(s, f"Normales: {resumen.especiales} · Inteligentes: {resumen.inteligentes}", (x + 12, 269), 12, TENUE)
        texto(s, "PODERES NORMALES E INTELIGENTES USADOS", (150, 329), 14, ORO, True)
        activados = Counter((e.actor, e.operador.nombre.replace("_", " ")) for e in self.log
                            if e.operador.prioridad or e.operador.tipo in ESPECIALES)
        if not activados:
            texto(s, "Ninguno en este combate.", (150, 363), 17, TENUE)
        for i, ((actor, op), cantidad) in enumerate(activados.items()):
            texto(s, f"{actor.value.upper()} / {op} × {cantidad}", (150, 365 + i * 28), 15, TENUE, ancho=482)
        texto(s, "Este resumen permanece abierto.", (150, 535), 16, VERDE)
        texto(s, "Puedes revisar todos los turnos antes de salir.", (150, 560), 14, TENUE)
        texto(s, "HISTORIAL COMPLETO", (670, 141), 14, AZUL, True)
        pygame.draw.rect(s, FONDO, self.HISTORIAL_KO, border_radius=6)
        self.scroll_ko = min(self.scroll_ko, max(0, len(self.log) - 8))
        for i, e in enumerate(self.log[self.scroll_ko:self.scroll_ko + 8]):
            y = 176 + i * 47
            color = ROJO if e.operador.prioridad else ORO if e.operador.tipo in ESPECIALES else TEXTO
            if e.operador.prioridad:
                pygame.draw.rect(s, (64, 27, 40), (676, y - 3, 445, 44), border_radius=4)
            texto(s, f"{e.turno:03d} / {e.actor.value.upper()} {e.personaje} · rival −{e.dano_rival} · propio −{e.dano - e.dano_rival}", (682, y), 13, color, True, ancho=431)
            prefijo = f"{e.categoria} / {e.cambio_super} / " if e.cambio_super else ""
            texto(s, prefijo + e.operador.nombre.replace("_", " "), (682, y + 21), 15, color, ancho=431)
        texto(s, f"Turnos {min(len(self.log), self.scroll_ko + 1)}–{min(len(self.log), self.scroll_ko + 8)} de {len(self.log)} · usa la rueda aquí", (670, 574), 13, TENUE)
        texto(s, "Clic en cualquier movimiento: ver condiciones y efectos", (670, 594), 12, AZUL)
        for boton in self.botones_ko():
            boton.dibujar(s, mouse)

    def dibujar(self, s: pygame.Surface, ahora: int, mouse: tuple[int, int]) -> None:
        s.fill(FONDO)
        self.renderer.dibujar(s, self.estado, ahora)
        self.hud.barras(s, self.estado, self.turno, len(self.log) + 1)
        actor_control = self.turno if self.config.modo is Modo.IA_IA else Actor.P1
        ayuda = self.hud.controles(s, self.estado, actor_control, self.puede_jugar(ahora), mouse)
        if self.log:
            self.hud.ultimo_movimiento(s, self.log[-1], mouse)
        if self.estado.terminado:
            estado_turno = "Combate finalizado"
        elif self.error:
            estado_turno = self.error
        elif self.pausado:
            estado_turno = "PAUSA / → para un turno" if not self.paso_pendiente else "Procesando un paso…"
        elif self.futuro is not None:
            estado_turno = f"{self.turno.value.upper()} / CPU calculando…"
        elif self.es_cpu:
            estado_turno = f"{self.turno.value.upper()} / CPU en {max(0, self.siguiente_ia - ahora) / 1000:.1f} s"
        else:
            estado_turno = "P1 / Elige tu próximo operador"
        objetivos = tuple(any(e.actor is a and e.operador.prioridad for e in self.log) for a in Actor)
        self.hud.inspector(s, self.estado, self.log, self.ultima_decision, self.ultimo_actor_ia, estado_turno,
                           self.config.profundidad, objetivos if self.config.modo is Modo.IA_IA and self.config.exposicion else None)
        for boton in self.botones_transporte():
            boton.dibujar(s, mouse)
        self.hud.leyenda_poderes(s)
        texto(s, "Clic en historial: reglas del turno / Clic derecho en operador: condiciones actuales / Espacio: pausa en IA vs IA", (24, 707), 10, TENUE)
        if ayuda:
            tooltip(s, ayuda, mouse)
        if self.mostrar_ko(ahora):
            self.dibujar_ko(s, mouse)
        if self.detalle is not None:
            self.detalle.dibujar(s, mouse, self.indice_detalle(), len(self.log), self.estado.terminado)

    def cerrar(self) -> None:
        if not self.cerrado:
            self.cerrado = True
            self.ejecutor.shutdown(wait=False, cancel_futures=True)
