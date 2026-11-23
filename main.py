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
from ui.screens import Combate, Portada, Seleccion

RESOLUCION = (1280, 720)
FPS = 60


class Aplicacion:
    def __init__(self) -> None:
        self.portada = Portada()
        self.en_portada = True
        self.seleccion = Seleccion()
        self.combate: Combate | None = None
        self.ejecutando = True

    def iniciar(self, ahora: int) -> None:
        self.en_portada = False
        if self.combate is not None:
            self.combate.cerrar()
        config = replace(self.seleccion.config, lugar=choice(tuple(Lugar)))
        self.combate = Combate(config, ahora)

    def evento(self, evento: pygame.event.Event, ahora: int) -> None:
        if evento.type == pygame.QUIT:
            self.ejecutando = False
            return
        if self.combate is None:
            if self.en_portada:
                accion = self.portada.evento(evento)
                if accion == "jugar":
                    self.en_portada = False
                elif accion == "salir":
                    self.ejecutando = False
                return
            volver = any(b.clave == "portada" and b.pulsado(evento) for b in self.seleccion.botones())
            if volver or (evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE):
                self.en_portada = True
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
            if self.en_portada:
                self.portada.dibujar(s, ahora, mouse)
            else:
                self.seleccion.dibujar(s, ahora, mouse)
        else:
            self.combate.dibujar(s, ahora, mouse)

    def cerrar(self) -> None:
        if self.combate is not None:
            self.combate.cerrar()


def main() -> None:
    parser = argparse.ArgumentParser(description="Combate táctico EEO en Pygame")
    parser.add_argument("--smoke-test", action="store_true", help="Prueba portada, selección y combate durante 8 fotogramas")
    parser.add_argument("--capturas", type=Path, help="Guarda capturas de portada, selección y combate durante --smoke-test")
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
                nombres_captura = {2: "portada.png", 4: "seleccion.png", 7: "combate.png"}
                if args.capturas and frames in nombres_captura:
                    args.capturas.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(pantalla, str(args.capturas / nombres_captura[frames]))
                if frames in (2, 4):
                    app.evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN), ahora)
                if frames >= 8:
                    app.ejecutando = False
    finally:
        app.cerrar()
        pygame.quit()


if __name__ == "__main__":
    main()
