"""Arena estilizada, sprites arcade y coreografías sincronizadas con el EEO."""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import cos, exp, pi, sin

import pygame

from engine.models import Accion, Actor, Colision, Distancia, Estado, Hora, Lugar, Nombre, Personaje, Postura, Vista
from engine.operators import ESPECIALES, Operador, TipoOperador as T
from ui.animations import (COREOGRAFIAS, DURACION, Estilo, Fotograma, Pose,
                           fotograma, reaccion_receptor, suave)
from ui.hud import AZUL, ORO, ROJO, TENUE, TEXTO, fuente, texto
from ui.sprites import dibujar_sprite

ARENA = pygame.Rect(16, 144, 908, 352)
SEPARACION = {Distancia.LEJOS: 282.0, Distancia.MEDIA: 190.0, Distancia.CERCA: 110.0, Distancia.CONTACTO: 52.0}


def dibujar_personaje(s: pygame.Surface, p: Personaje, x: float, suelo: float,
                      tiempo: float = 0, escala: float = 1, golpe: bool = False,
                      ataque: float = 0, pose: Pose | None = None) -> None:
    """Sprite arcade con respaldo geométrico si falta un recurso local."""
    if dibujar_sprite(s, p, x, suelo, tiempo, escala, golpe, pose):
        return
    direccion = 1 if p.vista is Vista.DERECHA else -1
    base, detalle, acento = p.color
    borde = (9, 13, 23)
    piel = (228, 186, 153)
    if golpe:
        base, detalle, acento, piel = (255, 241, 235), ROJO, (255, 255, 255), (255, 220, 220)
    animada = pose is not None
    pose = pose or Pose(extension=ataque, avance=ataque * 17)
    if p.puntos_salud == 0 and (not animada or pose.caida >= 1):
        pygame.draw.ellipse(s, (12, 15, 23), (int(x - 78 * escala), int(suelo - 4 * escala), int(156 * escala), max(1, int(14 * escala))))
        pygame.draw.line(s, borde, (int(x - 58 * escala), int(suelo - 12 * escala)), (int(x + 43 * escala), int(suelo - 12 * escala)), max(1, int(30 * escala)))
        pygame.draw.line(s, base, (int(x - 58 * escala), int(suelo - 14 * escala)), (int(x + 43 * escala), int(suelo - 14 * escala)), max(1, int(22 * escala)))
        pygame.draw.circle(s, piel, (int(x + 62 * escala), int(suelo - 15 * escala)), max(1, int(15 * escala)))
        return
    altura = 1.0
    aire = pose.elevacion if pose.elevacion is not None else (62 + sin(tiempo * 5) * 7 if p.postura is Postura.AEREO else 0)
    respiracion = sin(tiempo * 3.2) * 2
    y = suelo - aire + respiracion
    x += pose.avance * direccion
    angulo = (pose.giro + pose.inclinacion) * pi / 180

    def punto(a: float, b: float) -> tuple[int, int]:
        # Rota la figura articulada alrededor de la cadera, no del escenario.
        local_y = b + 70
        rot_x = a * cos(angulo) - local_y * sin(angulo)
        rot_y = a * sin(angulo) + local_y * cos(angulo) - 70
        return round(x + rot_x * escala * direccion), round(y + rot_y * escala * altura)

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
    paso = pose.zancada * 30
    pie_trasero = (-27 - paso, -8 - max(0, paso) * 0.35)
    pie_delantero = (32 + paso + pose.patada * 47, -8 - pose.patada * 100 - max(0, -paso) * 0.35)
    miembro((-11, -62), (-22 - paso * 0.5, -36), piernas, 18)
    miembro((-22 - paso * 0.5, -36), pie_trasero, piernas, 16)
    rodilla = (25 + paso * 0.5 + pose.patada * 21, -36 - pose.patada * 50)
    miembro((11, -62), rodilla, piernas, 18)
    miembro(rodilla, pie_delantero, piernas, 16)
    zapato = detalle if p.nombre is Nombre.BISON else acento
    miembro(pie_trasero, (pie_trasero[0] + 15, pie_trasero[1]), zapato, 12)
    miembro(pie_delantero, (pie_delantero[0] + 15, pie_delantero[1]), zapato, 12)
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
    defensa = max(pose.guardia, 1.0 if p.acciones is Accion.DEFENDIENDO else 0.0)
    codo_trasero = (-34 + pose.agarre * 47, -86 - pose.agarre * 24)
    mano_trasera = (-19 + pose.agarre * 70, -97 - pose.agarre * 22)
    miembro((-21, -115), codo_trasero, base, 13)
    miembro(codo_trasero, mano_trasera, detalle, 12)
    codo = (35.0 + pose.extension * 15, -110.0 - pose.extension * 3)
    mano = (23.0 + pose.extension * 68, -133.0 + pose.extension * 20)
    if defensa > 0:
        mano = (mano[0] * (1 - defensa) + 23 * defensa, mano[1] * (1 - defensa) - 148 * defensa)
    if pose.agarre:
        codo, mano = (40, -110), (23 + pose.agarre * 53, -122)
    if pose.uppercut:
        codo = (35, -110 - pose.uppercut * 20)
        mano = (23 + pose.uppercut * 17, -133 - pose.uppercut * 67)
    if pose.carga:
        mano = (34, -110 - pose.carga * 12)
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
    posiciones: tuple[float, float]


def dibujar_efectos(s: pygame.Surface, tipo: T, f: Fotograma, x: float,
                    rival_x: float, edad: int, dano: int) -> None:
    """Efectos deterministas por movimiento, sincronizados con su contacto."""
    if not 0 <= edad < DURACION:
        return
    c = COREOGRAFIAS[tipo]
    e, color = c.estilo, c.color
    direccion = 1 if rival_x >= x else -1
    elevacion = f.pose.elevacion or 0
    centro = (round(x), round(190 - elevacion))
    capa = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    pulso = sin(pi * f.progreso)
    if e in (Estilo.DASH, Estilo.PASO, Estilo.RETIRADA):
        for i in range(7):
            y = 178 + i * 15
            inicio = round(x - direccion * (55 + i * 5))
            pygame.draw.line(capa, (*color, round(150 * pulso)), (inicio, y), (inicio - direccion * 32, y), 2)
    elif e is Estilo.ESCUDO:
        cx = round(x + direccion * 48)
        vertices = [(cx, 133), (cx + 27, 150), (cx + 27, 211), (cx, 231), (cx - 27, 211), (cx - 27, 150)]
        pygame.draw.polygon(capa, (*color, 55 + round(45 * pulso)), vertices)
        pygame.draw.polygon(capa, (*color, 230), vertices, 3)
        pygame.draw.line(capa, (*color, 230), (cx, 145), (cx, 216), 2)
    elif e in (Estilo.CARGA, Estilo.DRENAJE):
        pygame.draw.ellipse(capa, (*color, 130), (round(x - 47), 273, 94, 17), 3)
        for i in range(18):
            fase = (f.progreso * 2 + i / 18) % 1
            if e is Estilo.DRENAJE:
                px = rival_x + (x - rival_x) * fase
                py = 183 + sin(fase * pi * 3 + i) * 18
            else:
                px = x + sin(i * 2.4 + f.progreso * 7) * (20 + 18 * fase)
                py = 278 - fase * 140
            pygame.draw.circle(capa, (*color, 190), (round(px), round(py)), 2 + i % 3)
        pygame.draw.circle(capa, (*color, 50), centro, round(24 + pulso * 20))
        pygame.draw.circle(capa, (*color, 215), centro, round(16 + pulso * 10), 2)
    elif e in (Estilo.GIRO, Estilo.LIBERACION, Estilo.FINTA):
        radio = 48 + round(18 * pulso)
        aro = pygame.Rect(centro[0] - radio, centro[1] - radio, radio * 2, radio * 2)
        for i in range(3):
            angulo = f.progreso * pi * 5 + i * 2 * pi / 3
            pygame.draw.arc(capa, (*color, 230 - i * 45), aro.inflate(i * 10, i * 10), angulo, angulo + 1.6, 4)
        if e is Estilo.LIBERACION and f.impacto:
            radio = 30 + round((1 - f.reaccion) * 140)
            pygame.draw.circle(capa, (*color, round(180 * f.reaccion)), centro, radio, 4)
            for i in range(10):
                angulo = i * pi / 5
                px, py = centro[0] + cos(angulo) * radio, centro[1] + sin(angulo) * radio
                pygame.draw.line(capa, (*color, 210), (round(px), round(py)),
                                 (round(px + cos(angulo) * 12), round(py + sin(angulo) * 12)), 3)
    elif e is Estilo.CRUSHER:
        for i in range(9):
            fase = f.progreso * pi * 8 + i * 0.7
            px = x - direccion * (i * 13 + 15)
            py = 188 - elevacion + sin(fase) * 35
            pygame.draw.circle(capa, (*color, 200 - i * 17), (round(px), round(py)), 13 - i)
        pygame.draw.ellipse(capa, (*color, 170), (round(x - 80), round(146 - elevacion), 160, 82), 4)
    elif e is Estilo.PATADA:
        for i in range(5):
            pygame.draw.line(capa, (*color, 190 - i * 25),
                             (round(x - direccion * (30 + i * 13)), round(175 - elevacion + i * 9)),
                             (round(x - direccion * (90 + i * 13)), round(188 - elevacion + i * 9)), 3)
    elif e in (Estilo.RAFAGA, Estilo.PARRY):
        alcance = 50 + 55 * f.pose.extension
        for i in range(4):
            px = x + direccion * (alcance - i * 12)
            py = 151 - (i * 14 if e is Estilo.RAFAGA else -i * 7)
            pygame.draw.circle(capa, (*color, 150 - i * 22), (round(px), round(py)), 12 - i)
        if e is Estilo.PARRY:
            aro = pygame.Rect(round(x + direccion * 30) - 35, 130, 70, 104)
            pygame.draw.arc(capa, (*color, 220), aro, -1.5, 1.5, 4)
    if e in (Estilo.SALTO, Estilo.ATERRIZAJE, Estilo.AGARRE):
        for i in range(9):
            dispersion = 12 + f.progreso * 65
            px = x + (i - 4) * dispersion / 4
            py = 284 - sin(pi * f.progreso) * (7 + i % 3 * 4)
            pygame.draw.circle(capa, (*color, round(150 * (1 - f.progreso))), (round(px), round(py)), 3 + i % 3)
    if f.impacto and dano > 0 and f.reaccion > 0:
        golpe_x, golpe_y = round(rival_x), 178
        radio = 12 + (1 - f.reaccion) * 30
        vertices = []
        for i in range(16):
            angulo = i * pi / 8
            r = radio if i % 2 else radio * 0.38
            vertices.append((round(golpe_x + cos(angulo) * r), round(golpe_y + sin(angulo) * r)))
        pygame.draw.polygon(capa, (*color, round(240 * f.reaccion)), vertices)
        pygame.draw.circle(capa, (255, 255, 240, round(240 * f.reaccion)), (golpe_x, golpe_y), max(2, round(8 * f.reaccion)))
        for i in range(12):
            angulo = i * pi / 6
            recorrido = radio + (1 - f.reaccion) * 45
            px, py = golpe_x + cos(angulo) * recorrido, golpe_y + sin(angulo) * recorrido
            pygame.draw.line(capa, (*color, round(220 * f.reaccion)), (round(px), round(py)),
                             (round(px + cos(angulo) * 9), round(py + sin(angulo) * 9)), 2)
    s.blit(capa, (0, 0))


class Renderer:
    def __init__(self, estado: Estado) -> None:
        separacion = SEPARACION[estado.p1.distancia]
        self.posiciones = {Actor.P1: 454 - separacion, Actor.P2: 454 + separacion}
        self.impacto: Impacto | None = None
        self.fondos: dict[tuple[Hora, Lugar], pygame.Surface] = {}

    def registrar(self, antes: Estado, despues: Estado, actor: Actor, op: Operador, ahora: int) -> None:
        self.impacto = Impacto(antes, despues, actor, op, ahora,
                               (self.posiciones[Actor.P1], self.posiciones[Actor.P2]))

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
        evento = self.impacto
        edad = ahora - evento.instante if evento else 10_000
        activo = evento is not None and 0 <= edad < DURACION
        frame = fotograma(evento.operador.tipo, edad) if evento and activo else None
        t = (evento.instante + frame.tiempo) / 1000 if evento and frame else ahora / 1000
        visual = evento.despues if evento and activo else estado
        ubicaciones = dict(self.posiciones)
        if evento and frame:
            separacion = SEPARACION[evento.despues.p1.distancia]
            for i, actor in enumerate(Actor):
                destino = 454 + (-separacion if actor is Actor.P1 else separacion)
                ubicaciones[actor] = evento.posiciones[i] + (destino - evento.posiciones[i]) * frame.llegada
        dano_rival = (evento.antes.personaje(evento.actor.rival).puntos_salud
                      - evento.despues.personaje(evento.actor.rival).puntos_salud) if evento else 0
        if evento and evento.operador.prioridad and 0 <= edad < 420:
            flash = pygame.Surface(ARENA.size, pygame.SRCALPHA)
            flash.fill((240, 27, 52, round(75 * (1 - edad / 420))))
            s.blit(flash, (0, 0))
        for actor in Actor:
            p = visual.personaje(actor)
            dano = evento.antes.personaje(actor).puntos_salud - evento.despues.personaje(actor).puntos_salud if evento else 0
            pose: Pose | None = None
            if evento and frame:
                if not frame.impacto:
                    p = evento.antes.personaje(actor)
                if actor is evento.actor:
                    pose = frame.pose
                    if dano_rival > 0:
                        alcance = max(0.0, abs(ubicaciones[actor] - ubicaciones[actor.rival]) - 112)
                        intensidad = max(pose.extension, pose.patada, pose.agarre, pose.uppercut)
                        pose = replace(pose, avance=pose.avance + alcance * intensidad)
                elif dano > 0 and frame.impacto:
                    pose = reaccion_receptor(frame, evento.operador.tipo, p.puntos_salud == 0,
                                              evento.antes.personaje(actor).postura is Postura.AEREO)
            x = ubicaciones[actor]
            if evento and frame and actor is evento.actor and COREOGRAFIAS[evento.operador.tipo].estilo in (
                    Estilo.DASH, Estilo.GIRO, Estilo.LIBERACION, Estilo.FINTA, Estilo.CRUSHER, Estilo.PATADA):
                direccion = 1 if p.vista is Vista.DERECHA else -1
                for i in (3, 2, 1):
                    estela = pygame.Surface(ARENA.size, pygame.SRCALPHA)
                    dibujar_personaje(estela, p, x - direccion * i * 19, 287, t, pose=pose)
                    estela.set_alpha(85 - i * 20)
                    s.blit(estela, (0, 0))
            reaccion = frame.reaccion if frame and frame.impacto else 0
            flash_impacto = bool(frame and dano > 0 and reaccion > 0.2 and (int(frame.tiempo) // 65) % 2 == 1)
            dibujar_personaje(s, p, x, 287, t, pose=pose, golpe=flash_impacto)
            desde_impacto = edad - COREOGRAFIAS[evento.operador.tipo].impacto if evento else 10_000
            if dano > 0 and 0 <= desde_impacto < 650:
                valor = fuente(28, True).render(f"−{dano}", True, ROJO if dano >= 250 else TEXTO)
                valor.set_alpha(round(255 * max(0, 1 - desde_impacto / 650)))
                s.blit(valor, (int(x - 30), int(122 - desde_impacto * 0.045)))
        if evento and frame:
            tipo = evento.operador.tipo
            dibujar_efectos(s, tipo, frame, ubicaciones[evento.actor],
                           ubicaciones[evento.actor.rival], edad, dano_rival)
            if dano_rival > 0 and frame.impacto and edad < COREOGRAFIAS[tipo].impacto + 180:
                fuerza = COREOGRAFIAS[tipo].fuerza * frame.reaccion * 3
                s.scroll(round(sin(edad * 0.15) * fuerza), round(cos(edad * 0.19) * fuerza * 0.6))
            fase = "IMPACTO" if frame.congelado else "RECUPERACIÓN" if frame.impacto else "PREPARACIÓN"
            if tipo is T.CARGAR:
                fase = "CANALIZANDO ENERGÍA"
            elif tipo in (T.DESPLAZAR, T.ACERCAR, T.ALEJAR):
                fase = "DESPLAZAMIENTO"
            elif tipo is T.BLOQUEAR:
                fase = "GUARDIA"
            pygame.draw.rect(s, (12, 19, 30), (8, 321, 350, 25), border_radius=4)
            texto(s, f"{evento.operador.nombre.replace('_', ' ')} / {fase}", (15, 325),
                  12, COREOGRAFIAS[tipo].color, True, ancho=336)
        pygame.draw.rect(s, (12, 19, 30), (0, 0, 908, 29))
        texto(s, f"{estado.escenario.lugar.value} / {estado.escenario.hora.value}", (12, 5), 13, TENUE)
        texto(s, f"DISTANCIA: {estado.p1.distancia.value.upper()}", (682, 5), 13, ORO)
        if evento and (evento.operador.prioridad or evento.operador.tipo in ESPECIALES) and 0 <= edad < 1100:
            color_banner = (111, 26, 46) if evento.operador.prioridad else (91, 66, 26)
            # Esquina superior: deja libre el centro para giros y saltos.
            pygame.draw.rect(s, color_banner, (8, 35, 350, 69), border_radius=5)
            acento = ROJO if evento.operador.prioridad else ORO
            pygame.draw.rect(s, acento, (8, 35, 350, 69), 2, border_radius=5)
            pygame.draw.circle(s, acento, (27, 67), 12)
            icono = fuente(15, True).render("I" if evento.operador.prioridad else "N", True, (12, 19, 30))
            s.blit(icono, icono.get_rect(center=(27, 67)))
            categoria = "INTELIGENTE / REACCIÓN CONDICIONAL" if evento.operador.prioridad else "PODER NORMAL / CONSUME 3 SUPER"
            etiqueta = fuente(10, True).render(categoria, True, acento)
            s.blit(etiqueta, etiqueta.get_rect(center=(198, 46)))
            nombre = "¡" + evento.operador.nombre.replace("_", " ").upper() + "!"
            imagen = fuente(15, True).render(nombre, True, TEXTO)
            s.blit(imagen, imagen.get_rect(center=(198, 63)))
            super_antes = evento.antes.personaje(evento.actor).medidor_super
            super_despues = evento.despues.personaje(evento.actor).medidor_super
            diferencia = super_despues - super_antes
            efecto = f"CONSUME {abs(diferencia)}" if diferencia < 0 else f"GANA {diferencia}" if diferencia > 0 else "SIN CONSUMO SEGÚN TABLA EEO"
            detalle = fuente(11, True).render(f"{evento.actor.value.upper()} / SUPER {super_antes} → {super_despues} / {efecto}", True, acento)
            s.blit(detalle, detalle.get_rect(center=(183, 86)))
        pygame.draw.rect(s, (49, 62, 80), s.get_rect(), 1, border_radius=8)
        pantalla.blit(s, ARENA)
