"""Ejecuta el juego de escritorio: .venv/Scripts/python.exe main.py."""
from __future__ import annotations

import argparse
import os
from dataclasses import replace
from pathlib import Path
from random import choice

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from engine.models import Lugar
from ui.screens import Combate, Seleccion

RESOLUCION = (1280, 720)
FPS = 60


class Aplicacion:
    def __init__(self) -> None:
        self.seleccion = Seleccion()
        self.combate: Combate | None = None
        self.ejecutando = True

    def iniciar(self, ahora: int) -> None:
        if self.combate is not None:
            self.combate.cerrar()
        config = replace(self.seleccion.config, lugar=choice(tuple(Lugar)))
        self.combate = Combate(config, ahora)

    def evento(self, evento: pygame.event.Event, ahora: int) -> None:
        if evento.type == pygame.QUIT:
            self.ejecutando = False
            return
        if self.combate is None:
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                self.ejecutando = False
            elif self.seleccion.evento(evento):
                self.iniciar(ahora)
        else:
            accion = self.combate.evento(evento, ahora)
            if accion == "menu":
                self.combate.cerrar()
                self.combate = None
            elif accion == "revancha":
                self.iniciar(ahora)

    def actualizar(self, ahora: int, dt: float) -> None:
        if self.combate is not None:
            self.combate.actualizar(ahora, dt)

    def dibujar(self, s: pygame.Surface, ahora: int, mouse: tuple[int, int]) -> None:
        if self.combate is None:
            self.seleccion.dibujar(s, ahora, mouse)
        else:
            self.combate.dibujar(s, ahora, mouse)

    def cerrar(self) -> None:
        if self.combate is not None:
            self.combate.cerrar()


def main() -> None:
    parser = argparse.ArgumentParser(description="Combate táctico EEO en Pygame")
    parser.add_argument("--smoke-test", action="store_true", help="Prueba el bucle en modo gráfico virtual durante 6 fotogramas")
    parser.add_argument("--capturas", type=Path, help="Guarda capturas del menú y el combate durante --smoke-test")
    args = parser.parse_args()
    if args.smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    pantalla = pygame.display.set_mode(RESOLUCION)
    pygame.display.set_caption("EEO / Tactical Fighter")
    reloj = pygame.time.Clock()
    app = Aplicacion()
    frames = 0
    try:
        while app.ejecutando:
            dt = min(reloj.tick(FPS) / 1000, 0.1)
            ahora = pygame.time.get_ticks()
            for evento in pygame.event.get():
                app.evento(evento, ahora)
            app.actualizar(ahora, dt)
            app.dibujar(pantalla, ahora, pygame.mouse.get_pos())
            pygame.display.flip()
            if args.smoke_test:
                frames += 1
                if args.capturas and frames in (2, 5):
                    args.capturas.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(pantalla, str(args.capturas / ("seleccion.png" if frames == 2 else "combate.png")))
                if frames == 3:
                    app.iniciar(ahora)
                if frames >= 6:
                    app.ejecutando = False
    finally:
        app.cerrar()
        pygame.quit()


if __name__ == "__main__":
    main()
