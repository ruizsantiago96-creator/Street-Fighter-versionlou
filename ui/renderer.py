"""Arena geométrica y luchadores originales dibujados sin recursos externos."""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, exp, pi, sin

import pygame

from engine.models import Accion, Actor, Colision, Distancia, Estado, Hora, Lugar, Nombre, Personaje, Postura, Vista
from engine.operators import ESPECIALES, Operador
from ui.hud import AZUL, ORO, ROJO, TENUE, TEXTO, fuente, texto

ARENA = pygame.Rect(16, 144, 908, 352)
SEPARACION = {Distancia.LEJOS: 282.0, Distancia.MEDIA: 190.0, Distancia.CERCA: 110.0, Distancia.CONTACTO: 52.0}


def dibujar_personaje(s: pygame.Surface, p: Personaje, x: float, suelo: float,
                      tiempo: float = 0, escala: float = 1, golpe: bool = False,
                      ataque: float = 0) -> None:
    """Figura articulada: coordenadas relativas a los pies, orientación del modelo."""
    direccion = 1 if p.vista is Vista.DERECHA else -1
    base, detalle, acento = p.color
    borde = (9, 13, 23)
    piel = (228, 186, 153)
    if golpe:
        base, detalle, acento, piel = (255, 241, 235), ROJO, (255, 255, 255), (255, 220, 220)
    if p.postura is Postura.FINAL:
        pygame.draw.ellipse(s, (12, 15, 23), (int(x - 78 * escala), int(suelo - 4 * escala), int(156 * escala), max(1, int(14 * escala))))
        pygame.draw.line(s, borde, (int(x - 58 * escala), int(suelo - 12 * escala)), (int(x + 43 * escala), int(suelo - 12 * escala)), max(1, int(30 * escala)))
        pygame.draw.line(s, base, (int(x - 58 * escala), int(suelo - 14 * escala)), (int(x + 43 * escala), int(suelo - 14 * escala)), max(1, int(22 * escala)))
        pygame.draw.circle(s, piel, (int(x + 62 * escala), int(suelo - 15 * escala)), max(1, int(15 * escala)))
        return
    agachada = p.postura is Postura.AGACHADA
    altura = 0.70 if agachada else 1.0
    aire = 62 + sin(tiempo * 5) * 7 if p.postura is Postura.AEREO else 0
    respiracion = sin(tiempo * 3.2) * 2
    y = suelo - aire + respiracion
    x += ataque * direccion * 17

    def punto(a: float, b: float) -> tuple[int, int]:
        return round(x + a * escala * direccion), round(y + b * escala * altura)

    def miembro(a: tuple[float, float], b: tuple[float, float], color: tuple[int, int, int], grosor: int) -> None:
        pygame.draw.line(s, borde, punto(*a), punto(*b), max(1, round((grosor + 5) * escala)))
        pygame.draw.line(s, color, punto(*a), punto(*b), max(1, round(grosor * escala)))
        pygame.draw.circle(s, color, punto(*b), max(1, round(grosor / 2 * escala)))

    pygame.draw.ellipse(s, (13, 18, 26), (round(x - 53 * escala), round(suelo - 4), round(106 * escala), max(2, round(12 * escala))))
    if p.colision in (Colision.INVULNERABLE, Colision.INVENCIBLE) or p.acciones is Accion.DEFENDIENDO:
        aura = pygame.Rect(round(x - 53 * escala), round(y - 166 * escala * altura), round(106 * escala), round(175 * escala * altura))
        color = AZUL if p.colision is not Colision.INVENCIBLE else ORO
        pygame.draw.ellipse(s, color, aura, max(1, round(2 * escala)))
        pygame.draw.arc(s, color, aura.inflate(12, 8), -1.2 + tiempo, 1.0 + tiempo, max(1, round(3 * escala)))
    piernas = base if p.nombre is Nombre.MAKOTO else acento
    miembro((-11, -62), (-27, -8), piernas, 18)
    miembro((11, -62), (32, -8), piernas, 18)
    miembro((-28, -6), (-13, -6), detalle if p.nombre is Nombre.BISON else acento, 12)
    miembro((29, -6), (44, -6), detalle if p.nombre is Nombre.BISON else acento, 12)
    torso = [punto(-24, -125), punto(20, -125), punto(17, -65), punto(-17, -65)]
    pygame.draw.polygon(s, borde, torso)
    pygame.draw.polygon(s, base, [punto(-21, -122), punto(17, -122), punto(14, -68), punto(-14, -68)])
    miembro((-14, -69), (17, -69), detalle, 7)
    if p.nombre is Nombre.MAKOTO:
        miembro((-9, -120), (11, -90), acento, 3)
        miembro((9, -69), (20, -41), detalle, 5)
    elif p.nombre is Nombre.BISON:
        miembro((-25, -121), (-12, -121), detalle, 12)
        miembro((13, -121), (25, -121), detalle, 12)
    else:
        miembro((-12, -117), (-10, -91), detalle, 3)
    defensa = p.acciones is Accion.DEFENDIENDO
    miembro((-21, -115), (-34, -86), base, 13)
    miembro((-34, -86), (-19, -97), detalle, 12)
    codo = (35.0 + ataque * 15, -110.0 - ataque * 3)
    mano = (23.0 + ataque * 68, -133.0 + ataque * 20)
    if defensa:
        codo, mano = (29, -116), (23, -148)
    miembro((20, -116), codo, base, 13)
    miembro(codo, mano, detalle, 13)
    pygame.draw.circle(s, borde, punto(0, -145), max(1, round(21 * escala)))
    pygame.draw.circle(s, piel, punto(0, -145), max(1, round(17 * escala)))
    if p.nombre in (Nombre.JULI, Nombre.BISON):
        pygame.draw.polygon(s, acento if p.nombre is Nombre.JULI else base,
                            [punto(-23, -158), punto(14, -164), punto(25, -153), punto(-18, -150)])
        pygame.draw.circle(s, detalle, punto(12, -155), max(1, round(3 * escala)))
    elif p.nombre is Nombre.CAMMY:
        cabello = pygame.Rect(0, 0, round(36 * escala), round(33 * escala))
        cabello.center = punto(0, -150)
        pygame.draw.arc(s, acento, cabello, 0, pi, max(1, round(8 * escala)))
        miembro((-14, -153), (-28, -107), acento, 7)
        pygame.draw.polygon(s, detalle, [punto(-20, -159), punto(14, -165), punto(20, -155), punto(-18, -152)])
    else:
        pygame.draw.polygon(s, acento, [punto(-20, -145), punto(-19, -163), punto(3, -167), punto(20, -154), punto(8, -156), punto(-8, -149)])
    pygame.draw.line(s, borde, punto(7, -145), punto(13, -145), max(1, round(2 * escala)))


@dataclass(frozen=True, slots=True)
class Impacto:
    antes: Estado
    despues: Estado
    actor: Actor
    operador: Operador
    instante: int


class Renderer:
    def __init__(self, estado: Estado) -> None:
        separacion = SEPARACION[estado.p1.distancia]
        self.posiciones = {Actor.P1: 454 - separacion, Actor.P2: 454 + separacion}
        self.impacto: Impacto | None = None
        self.fondos: dict[tuple[Hora, Lugar], pygame.Surface] = {}

    def registrar(self, antes: Estado, despues: Estado, actor: Actor, op: Operador, ahora: int) -> None:
        self.impacto = Impacto(antes, despues, actor, op, ahora)

    def actualizar(self, estado: Estado, dt: float) -> None:
        separacion = SEPARACION[estado.p1.distancia]
        for actor, destino in ((Actor.P1, 454 - separacion), (Actor.P2, 454 + separacion)):
            self.posiciones[actor] += (destino - self.posiciones[actor]) * (1 - exp(-12 * max(0, dt)))

    def fondo(self, estado: Estado) -> pygame.Surface:
        clave = (estado.escenario.hora, estado.escenario.lugar)
        if clave in self.fondos:
            return self.fondos[clave]
        s = pygame.Surface(ARENA.size)
        hora, lugar = clave
        cielo, horizonte, estructura = {
            Hora.DIA: ((66, 112, 149), (152, 185, 191), (52, 73, 89)),
            Hora.TARDE: ((94, 61, 111), (215, 130, 111), (62, 49, 75)),
            Hora.NOCHE: ((14, 24, 47), (42, 68, 101), (26, 38, 58)),
        }[hora]
        for y in range(286):
            mezcla = y / 285
            color = tuple(round(a + (b - a) * mezcla) for a, b in zip(cielo, horizonte))
            pygame.draw.line(s, color, (0, y), (908, y))
        if hora is Hora.NOCHE:
            for i in range(42):
                pygame.draw.circle(s, (169, 198, 220), ((i * 131 + 47) % 908, (i * 43 + 19) % 188), 1)
            pygame.draw.circle(s, (218, 228, 229), (755, 65), 23)
        else:
            pygame.draw.circle(s, (249, 213, 156) if hora is Hora.DIA else (255, 177, 113), (755, 88), 33)
        if lugar is Lugar.BASE:
            for x in range(18, 908, 144):
                pygame.draw.rect(s, estructura, (x, 0, 48, 286))
                pygame.draw.polygon(s, estructura, [(x, 0), (x + 140, 0), (x + 48, 68), (x, 68)])
                pygame.draw.rect(s, (224, 173, 70), (x + 10, 183, 28, 6))
            pygame.draw.circle(s, (95, 42, 55), (454, 160), 72)
            pygame.draw.polygon(s, (176, 75, 81), [(454, 116), (412, 165), (454, 194), (496, 165)], 4)
            texto(s, "SHADALOO", (396, 222), 18, (203, 151, 128), True)
        elif lugar is Lugar.LABORATORIO:
            for x in (55, 260, 575, 780):
                pygame.draw.rect(s, estructura, (x, 72, 73, 215), border_radius=16)
                pygame.draw.rect(s, (56, 139, 151), (x + 8, 89, 57, 167), 3, border_radius=16)
                for i in range(6):
                    pygame.draw.circle(s, (100, 201, 195), (x + 20 + (i * 13) % 35, 110 + i * 24), 3)
            for x in (365, 449):
                pygame.draw.rect(s, estructura, (x, 154, 78, 73), border_radius=4)
                pygame.draw.lines(s, AZUL, False, [(x + 6, 194), (x + 25, 194), (x + 31, 168), (x + 43, 212), (x + 56, 188), (x + 70, 188)], 2)
        elif lugar is Lugar.PSYCHO_DRIVE:
            for radio in (128, 96, 65):
                pygame.draw.circle(s, estructura, (454, 160), radio, 13)
            pygame.draw.circle(s, (126, 56, 150), (454, 160), 53)
            pygame.draw.circle(s, (197, 115, 235), (454, 160), 27)
            for x in (95, 760):
                pygame.draw.rect(s, estructura, (x, 0, 50, 288))
                pygame.draw.rect(s, (170, 68, 179), (x + 20, 35, 10, 215))
        elif lugar is Lugar.DOJO:
            pygame.draw.polygon(s, estructura, [(0, 111), (145, 27), (454, 70), (760, 26), (908, 110)])
            for x in (30, 185, 340, 495, 650, 805):
                pygame.draw.rect(s, (80, 53, 47), (x, 110, 15, 178))
                pygame.draw.rect(s, (178, 163, 136), (x + 18, 123, 133, 143))
                pygame.draw.line(s, estructura, (x + 84, 123), (x + 84, 266), 3)
                pygame.draw.line(s, estructura, (x + 18, 195), (x + 151, 195), 3)
            pygame.draw.rect(s, (231, 219, 179), (424, 94, 57, 124))
            for a, b in (((436, 116), (468, 116)), ((452, 110), (452, 164)), ((436, 137), (468, 137)), ((452, 140), (434, 166)), ((452, 140), (470, 166))):
                pygame.draw.line(s, (62, 49, 50), a, b, 3)
            texto(s, "RINDOKAN", (397, 245), 20, ORO, True)
        else:
            for fila in range(5):
                y = 145 + fila * 25
                pygame.draw.rect(s, estructura, (0, y, 908, 23))
                for x in range(10, 908, 22):
                    pygame.draw.circle(s, (112 + (x % 70), 121, 144), (x + fila % 2 * 8, y + 10), 4)
            for x in (55, 838):
                pygame.draw.line(s, estructura, (x, 35), (x, 280), 8)
                pygame.draw.rect(s, (226, 221, 179), (x - 24, 32, 48, 12))
            pygame.draw.rect(s, estructura, (324, 45, 260, 73), border_radius=8)
            texto(s, "WORLD FIGHTER", (348, 65), 24, ORO, True)
        pygame.draw.rect(s, (43, 46, 56) if lugar is not Lugar.DOJO else (104, 82, 59), (0, 286, 908, 66))
        pygame.draw.line(s, (158, 141, 117), (0, 286), (908, 286), 3)
        for x in range(-454, 1400, 110):
            pygame.draw.line(s, (69, 67, 69), (454 + (x - 454) // 2, 288), (x, 352), 1)
        for y in (308, 340):
            pygame.draw.line(s, (69, 67, 69), (0, y), (908, y), 1)
        self.fondos[clave] = s
        return s

    def dibujar(self, pantalla: pygame.Surface, estado: Estado, ahora: int) -> None:
        s = self.fondo(estado).copy()
        t = ahora / 1000
        evento = self.impacto
        edad = ahora - evento.instante if evento else 10_000
        visual = evento.despues if evento and edad < 600 else estado
        if evento and evento.operador.prioridad and edad < 420:
            flash = pygame.Surface(ARENA.size, pygame.SRCALPHA)
            flash.fill((240, 27, 52, round(100 * (1 - edad / 420))))
            s.blit(flash, (0, 0))
        for actor in Actor:
            p = visual.personaje(actor)
            dano = evento.antes.personaje(actor).puntos_salud - evento.despues.personaje(actor).puntos_salud if evento else 0
            ataque = max(0.0, sin(pi * edad / 420)) if evento and actor is evento.actor and edad < 420 and p.acciones in (Accion.ATACANDO, Accion.AGARRE) else 0.0
            x = self.posiciones[actor]
            dibujar_personaje(s, p, x, 287, t, golpe=dano > 0 and edad < 380 and edad // 70 % 2 == 0, ataque=ataque)
            if dano > 0 and edad < 950:
                valor = fuente(28, True).render(f"−{dano}", True, ROJO if dano >= 250 else TEXTO)
                valor.set_alpha(round(255 * max(0, 1 - edad / 950)))
                s.blit(valor, (int(x - 30), int(108 - edad * 0.04)))
                if edad < 260:
                    for i in range(8):
                        angulo = i * pi / 4
                        radio = 13 + edad * 0.07
                        pygame.draw.line(s, ORO, (round(x + cos(angulo) * radio), round(198 + sin(angulo) * radio)), (round(x + cos(angulo) * (radio + 13)), round(198 + sin(angulo) * (radio + 13))), 3)
        pygame.draw.rect(s, (12, 19, 30), (0, 0, 908, 29))
        texto(s, f"{estado.escenario.lugar.value} / {estado.escenario.hora.value}", (12, 5), 13, TENUE)
        texto(s, f"DISTANCIA: {estado.p1.distancia.value.upper()}", (682, 5), 13, ORO)
        if evento and (evento.operador.prioridad or evento.operador.tipo in ESPECIALES) and edad < 1100:
            color_banner = (111, 26, 46) if evento.operador.prioridad else (91, 66, 26)
            pygame.draw.rect(s, color_banner, (90, 38, 728, 76), border_radius=5)
            acento = ROJO if evento.operador.prioridad else ORO
            pygame.draw.rect(s, acento, (90, 38, 728, 76), 2, border_radius=5)
            pygame.draw.circle(s, acento, (117, 76), 17)
            icono = fuente(19, True).render("I" if evento.operador.prioridad else "N", True, (12, 19, 30))
            s.blit(icono, icono.get_rect(center=(117, 76)))
            categoria = "OPERADOR INTELIGENTE / REACCIÓN CONDICIONAL" if evento.operador.prioridad else "PODER NORMAL / ESPECIAL / CONSUME 3 DE SUPER"
            etiqueta = fuente(12, True).render(categoria, True, acento)
            s.blit(etiqueta, etiqueta.get_rect(center=(454, 50)))
            nombre = "¡" + evento.operador.nombre.replace("_", " ").upper() + "!"
            imagen = fuente(21, True).render(nombre, True, TEXTO)
            s.blit(imagen, imagen.get_rect(center=(454, 74)))
            super_antes = evento.antes.personaje(evento.actor).medidor_super
            super_despues = evento.despues.personaje(evento.actor).medidor_super
            diferencia = super_despues - super_antes
            efecto = f"CONSUME {abs(diferencia)}" if diferencia < 0 else f"GANA {diferencia}" if diferencia > 0 else "SIN CONSUMO SEGÚN TABLA EEO"
            detalle = fuente(13, True).render(f"{evento.actor.value.upper()} / SUPER {super_antes} → {super_despues} / {efecto}", True, acento)
            s.blit(detalle, detalle.get_rect(center=(454, 101)))
        pygame.draw.rect(s, (49, 62, 80), s.get_rect(), 1, border_radius=8)
        pantalla.blit(s, ARENA)
