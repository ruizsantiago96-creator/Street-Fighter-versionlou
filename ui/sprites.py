"""Sprites arcade locales: ocho poses por luchador, anclajes y caché de dibujo."""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from math import sin
from pathlib import Path

import pygame

from engine.models import Accion, Colision, Nombre, Personaje, Postura, Vista
from ui.animations import Pose


RUTA = Path(__file__).resolve().parents[1] / "assets" / "fighters"
ARCHIVOS = {Nombre.JULI: "juli.png", Nombre.CAMMY: "cammy.png",
            Nombre.BISON: "bison.png", Nombre.MAKOTO: "makoto.png"}


@dataclass(frozen=True, slots=True)
class Celda:
    imagen: pygame.Surface
    pie_x: float
    pie_y: float


@lru_cache(maxsize=4)
def cargar_poses(nombre: Nombre) -> tuple[Celda, ...]:
    hoja = pygame.image.load(str(RUTA / ARCHIVOS[nombre])).convert_alpha()
    originales: list[pygame.Surface] = []
    for fila in range(2):
        for columna in range(4):
            x0, x1 = hoja.get_width() * columna // 4, hoja.get_width() * (columna + 1) // 4
            y0, y1 = hoja.get_height() * fila // 2, hoja.get_height() * (fila + 1) // 2
            originales.append(hoja.subsurface((x0, y0, x1 - x0, y1 - y0)).copy())
    altura = originales[0].get_bounding_rect(min_alpha=100).height
    if not altura:
        raise ValueError(f"Hoja de sprites vacía: {nombre.value}")
    factor = 96 / altura
    poses: list[Celda] = []
    for original in originales:
        rect = original.get_bounding_rect(min_alpha=100)
        if not rect.width or not rect.height:
            raise ValueError(f"Pose vacía en {nombre.value}")
        mask = pygame.mask.from_surface(original, 100)
        pies = [x for x in range(rect.left, rect.right)
                if any(mask.get_at((x, y)) for y in range(max(rect.top, rect.bottom - rect.height // 12), rect.bottom))]
        pie_x = ((min(pies) + max(pies)) / 2 if pies else rect.centerx) - rect.x
        recorte = original.subsurface(rect)
        imagen = pygame.transform.scale(recorte, (max(1, round(rect.width * factor)), max(1, round(rect.height * factor))))
        poses.append(Celda(imagen, pie_x * factor, rect.height * factor))
    return tuple(poses)


def indice_pose(p: Personaje, pose: Pose, golpe: bool) -> int:
    if golpe or pose.caida > 0 or p.puntos_salud == 0 or pose.avance < -10:
        return 7
    if pose.agarre > 0.25:
        return 5
    if pose.uppercut > 0.2 or (pose.carga > 0.2 and pose.guardia < 0.8):
        return 6
    if pose.patada > 0.25 or (p.postura is Postura.AEREO and pose.elevacion is None):
        return 4
    if pose.extension > 0.25:
        return 2
    if pose.guardia > 0.6 or p.acciones is Accion.DEFENDIENDO or pose.extension < -0.05:
        return 3
    if abs(pose.zancada) > 0.1:
        return 1
    return 0


@lru_cache(maxsize=96)
def imagen_transformada(nombre: Nombre, indice: int, tamano: int, angulo: int,
                        izquierda: bool, golpe: bool) -> pygame.Surface:
    celda = cargar_poses(nombre)[indice]
    lienzo = pygame.Surface((192, 192), pygame.SRCALPHA)
    lienzo.blit(celda.imagen, (round(96 - celda.pie_x), round(140 - celda.pie_y)))
    if golpe:
        lienzo.fill((155, 110, 110), special_flags=pygame.BLEND_RGB_ADD)
    lienzo = pygame.transform.scale(lienzo, (tamano, tamano))
    if izquierda:
        lienzo = pygame.transform.flip(lienzo, True, False)
    return pygame.transform.rotate(lienzo, angulo) if angulo else lienzo


def dibujar_sprite(s: pygame.Surface, p: Personaje, x: float, suelo: float,
                    tiempo: float, escala: float, golpe: bool, pose: Pose | None) -> bool:
    """Devuelve False si falta el recurso, para permitir el dibujo geométrico."""
    if not (RUTA / ARCHIVOS[p.nombre]).is_file():
        return False
    animando = pose is not None
    pose = pose or Pose()
    if p.puntos_salud == 0 and not animando:
        pose = replace(pose, giro=-88, elevacion=-65, caida=1)
    direccion = 1 if p.vista is Vista.DERECHA else -1
    aire = pose.elevacion if pose.elevacion is not None else (62 if p.postura is Postura.AEREO else 0)
    x += pose.avance * direccion * escala
    y = suelo - aire * escala
    if p.puntos_salud:
        pygame.draw.ellipse(s, (13, 18, 26), (round(x - 43 * escala), round(suelo - 3),
                                            max(1, round(86 * escala)), max(1, round(10 * escala))))
        if p.colision in (Colision.INVULNERABLE, Colision.INVENCIBLE):
            color = (77, 188, 222) if p.colision is Colision.INVULNERABLE else (255, 204, 87)
            pygame.draw.ellipse(s, color, (round(x - 52 * escala), round(y - 182 * escala),
                                           max(1, round(104 * escala)), max(1, round(185 * escala))), max(1, round(2 * escala)))
    angulo = round(-(pose.giro + pose.inclinacion) * direccion / 5) * 5 % 360
    imagen = imagen_transformada(p.nombre, indice_pose(p, pose, golpe), max(1, round(360 * escala)),
                                 angulo, direccion < 0, golpe)
    respiracion = sin(tiempo * 3.2) * 1.5 * escala if p.puntos_salud else 0
    centro = (round(x), round(y - 82.5 * escala + respiracion))
    s.blit(imagen, imagen.get_rect(center=centro))
    return True


def limpiar_cache() -> None:
    imagen_transformada.cache_clear()
    cargar_poses.cache_clear()
