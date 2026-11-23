"""Las coreografías son visibles, espejables y no modifican el motor EEO."""
from __future__ import annotations

import os
from dataclasses import replace
from math import isfinite
from pathlib import Path
from typing import Iterator

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

from engine.models import Accion, Actor, Colision, Distancia, Estado, Nombre, Postura, crear_estado
from engine.operators import ESPECIALES, Operador, TipoOperador as T
from ui.animations import COREOGRAFIAS, DURACION, fotograma, reaccion_receptor
from ui.renderer import ARENA, Renderer
from ui.hud import fuente
from ui.sprites import ARCHIVOS, RUTA, cargar_poses, imagen_transformada


@pytest.fixture(scope="module")
def lienzo() -> Iterator[pygame.Surface]:
    pygame.init()
    yield pygame.display.set_mode((1280, 720))
    # Libera las fuentes SDL antes de cerrar/reiniciar Pygame en otro módulo.
    fuente.cache_clear()
    pygame.quit()


def preparar(tipo: T, actor: Actor) -> Estado:
    nombres = {T.LIBERAR: Nombre.JULI, T.FINTA: Nombre.CAMMY,
               T.DRENAR: Nombre.BISON, T.LECTURA: Nombre.MAKOTO}
    nombre = ESPECIALES[tipo][0] if tipo in ESPECIALES else nombres.get(tipo, Nombre.JULI)
    s = crear_estado(nombre, Nombre.CAMMY) if actor is Actor.P1 else crear_estado(Nombre.CAMMY, nombre)
    distancia = (ESPECIALES[tipo][1][0] if tipo in ESPECIALES else
                 Distancia.LEJOS if tipo is T.DESPLAZAR else
                 Distancia.MEDIA if tipo is T.FINTA else
                 Distancia.CONTACTO if tipo is T.LIBERAR else Distancia.CERCA)
    p = replace(s.personaje(actor), distancia=distancia)
    r = replace(s.personaje(actor.rival), distancia=distancia)
    if tipo in ESPECIALES or tipo is T.LIBERAR:
        p = replace(p, medidor_super=3)
    if tipo is T.LIBERAR:
        p = replace(p, puntos_salud=400)
    if tipo in (T.BLOQUEAR, T.SALTAR, T.LIBERAR, T.DRENAR, T.LECTURA):
        r = replace(r, acciones=Accion.ATACANDO)
    if tipo in (T.FINTA, T.AGARRAR):
        r = replace(r, acciones=Accion.DEFENDIENDO, colision=Colision.INVULNERABLE)
    if tipo is T.FINTA:
        p = replace(p, medidor_super=2)
    if tipo is T.ATERRIZAR:
        p = replace(p, postura=Postura.AEREO)
    if tipo is T.CARGAR:
        p = replace(p, recarga_energia=1)
    return s.con_personajes(actor, p, r)


def test_cada_operador_tiene_coreografia_propia() -> None:
    assert set(COREOGRAFIAS) == set(T)
    assert len({c.estilo for c in COREOGRAFIAS.values()}) == len(T)


@pytest.mark.parametrize("nombre", list(Nombre))
def test_sprites_locales_tienen_ocho_poses_y_transparencia(lienzo: pygame.Surface, nombre: Nombre) -> None:
    assert (RUTA / ARCHIVOS[nombre]).is_file()
    poses = cargar_poses(nombre)
    assert len(poses) == 8
    assert len({pygame.image.tostring(c.imagen, "RGBA") for c in poses}) == 8
    for c in poses:
        assert c.imagen.get_flags() & pygame.SRCALPHA
        assert c.imagen.get_bounding_rect().width > 0
        assert 0 <= c.pie_x <= c.imagen.get_width() + 1
    imagen = imagen_transformada(nombre, 0, 360, 0, False, False)
    assert imagen.get_at((0, 0)).a == 0
    espejo = imagen_transformada(nombre, 0, 360, 0, True, False)
    assert pygame.image.tostring(espejo, "RGBA") == pygame.image.tostring(pygame.transform.flip(imagen, True, False), "RGBA")


def test_sprites_no_dependen_del_directorio_de_ejecucion(lienzo: pygame.Surface, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert RUTA.is_absolute()
    for nombre in Nombre:
        assert len(cargar_poses(nombre)) == 8


@pytest.mark.parametrize("tipo", list(T))
def test_preparacion_impacto_y_hit_stop_sin_bloquear(tipo: T) -> None:
    c = COREOGRAFIAS[tipo]
    assert not fotograma(tipo, c.impacto - 1).impacto
    assert fotograma(tipo, c.impacto).impacto
    if c.pausa:
        a = fotograma(tipo, c.impacto + 5)
        b = fotograma(tipo, c.impacto + c.pausa - 5)
        assert a.congelado and b.congelado and a.pose == b.pose and a.tiempo == b.tiempo
        assert fotograma(tipo, c.impacto + c.pausa + 40).pose != a.pose
    for edad in (-100, 0, 100, 250, 500, DURACION, 100_000):
        frame = fotograma(tipo, edad)
        assert 0 <= frame.progreso <= 1
        assert isfinite(frame.pose.giro) and isfinite(frame.pose.avance)
        assert frame.pose.elevacion is None or isfinite(frame.pose.elevacion)


@pytest.mark.parametrize("actor", list(Actor))
@pytest.mark.parametrize("tipo", list(T))
def test_animacion_completa_desde_ambos_lados_sin_cambiar_estado(
    lienzo: pygame.Surface, tipo: T, actor: Actor,
) -> None:
    antes = preparar(tipo, actor)
    despues = Operador(tipo).aplicar(antes, actor)
    firma = (hash(antes), hash(despues))
    renderer = Renderer(antes)
    renderer.registrar(antes, despues, actor, Operador(tipo), 100)
    imagenes = set()
    for edad in (0, 100, COREOGRAFIAS[tipo].impacto + 10, 400, 590, 700, 1300):
        renderer.actualizar(despues, 1 / 60)
        renderer.dibujar(lienzo, despues, 100 + edad)
        imagenes.add(pygame.image.tostring(lienzo.subsurface(ARENA), "RGB"))
    assert len(imagenes) >= 4, tipo
    assert (hash(antes), hash(despues)) == firma


def test_derribo_se_anima_antes_de_quedar_en_el_suelo(lienzo: pygame.Surface) -> None:
    antes = preparar(T.GOLPEAR, Actor.P1)
    antes = replace(antes, p2=replace(antes.p2, puntos_salud=50))
    despues = Operador(T.GOLPEAR).aplicar(antes, Actor.P1)
    renderer = Renderer(antes)
    renderer.registrar(antes, despues, Actor.P1, Operador(T.GOLPEAR), 0)
    for edad in (0, 210, 250, 400, 599, 850):
        renderer.dibujar(lienzo, despues, edad)
    assert despues.terminado and despues.p2.puntos_salud == 0
    assert reaccion_receptor(fotograma(T.GOLPEAR, 450), T.GOLPEAR, True, False).caida > 0


def test_contacto_en_todas_las_coreografias(lienzo: pygame.Surface, tmp_path: Path) -> None:
    """Hoja temporal para inspeccionar las 17 coreografías al contacto."""
    hoja = pygame.Surface((454 * 4, 205 * 5))
    hoja.fill((11, 15, 24))
    font = pygame.font.SysFont("segoeui", 14)
    for i, tipo in enumerate(T):
        antes = preparar(tipo, Actor.P1)
        despues = Operador(tipo).aplicar(antes, Actor.P1)
        renderer = Renderer(antes)
        renderer.registrar(antes, despues, Actor.P1, Operador(tipo), 0)
        renderer.dibujar(lienzo, despues, COREOGRAFIAS[tipo].impacto + 20)
        x, y = i % 4 * 454, i // 4 * 205
        hoja.blit(pygame.transform.smoothscale(lienzo.subsurface(ARENA), (454, 176)), (x, y + 24))
        hoja.blit(font.render(tipo.value.replace("_", " "), True, (234, 240, 247)), (x + 8, y + 3))
    ruta = tmp_path / "animaciones.png"
    pygame.image.save(hoja, str(ruta))
    print(f"VISTA_ANIMACIONES={ruta}")
