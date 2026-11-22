"""Explicación auditable de una transición histórica o un operador previsto."""
from __future__ import annotations

from enum import Enum

import pygame

from engine.models import Actor, Estado
from ui.hud import (AZUL, EFECTOS, FONDO, ORO, ROJO, TENUE, TEXTO, VERDE,
                    Boton, EntradaLog, lineas, panel, texto)


def valor_visible(valor: object) -> str:
    return str(valor.value) if isinstance(valor, Enum) else str(valor)


def cambios(antes: Estado, despues: Estado) -> tuple[str, ...]:
    """Diferencias reales de todos los atributos EEO mutables del personaje."""
    filas: list[str] = []
    atributos = ("puntos_salud", "postura", "distancia", "acciones", "medidor_super",
                 "recarga_energia", "colision", "vista", "especial", "dano_recibido")
    for actor in Actor:
        p, q = antes.personaje(actor), despues.personaje(actor)
        propios: list[str] = []
        for atributo in atributos:
            inicial, final = getattr(p, atributo), getattr(q, atributo)
            if inicial != final:
                propios.append(f"  {atributo}: {valor_visible(inicial)} → {valor_visible(final)}")
        filas.append(f"{actor.value.upper()} / {p.nombre.value}")
        filas.extend(propios or ["  Sin cambios."])
    return tuple(filas)


class DetalleMovimiento:
    TRANSICION = pygame.Rect(638, 175, 554, 425)

    def __init__(self, entrada: EntradaLog) -> None:
        self.entrada = entrada
        self.scroll = 0

    def filas(self) -> list[str]:
        e = self.entrada
        filas = ["REGLA DE EFECTO", EFECTOS[e.operador.tipo], ""]
        if e.estado_antes is None:
            return filas + ["Esta entrada no contiene una instantánea verificable."]
        filas += [f"Escenario: {e.estado_antes.escenario.hora.value}", e.estado_antes.escenario.lugar.value, ""]
        if e.estado_operador is None:
            return filas + ["VISTA PREVIA / AÚN NO EJECUTADO", "Los indicadores muestran qué condiciones se cumplen en este momento."]
        filas += ["1 / APLICAR EL OPERADOR", *cambios(e.estado_antes, e.estado_operador), ""]
        if e.estado_despues is not None:
            filas += ["2 / PREPARAR EL SIGUIENTE TURNO", "La normalización es una regla auxiliar, posterior al operador.",
                      *cambios(e.estado_operador, e.estado_despues)]
        return filas

    def filas_envueltas(self) -> list[str]:
        return [linea for fila in self.filas() for linea in lineas(fila, 520, 14)]

    def desplazar(self, pasos: int) -> None:
        maximo = max(0, len(self.filas_envueltas()) - 18)
        self.scroll = max(0, min(maximo, self.scroll + pasos * 3))

    def botones(self, indice: int | None, total: int, terminado: bool) -> tuple[Boton, ...]:
        return (Boton(pygame.Rect(84, 639, 155, 37), "← Anterior", "anterior", AZUL, indice is not None and indice > 0),
                Boton(pygame.Rect(249, 639, 155, 37), "Siguiente →", "siguiente", AZUL, indice is not None and indice < total - 1),
                Boton(pygame.Rect(972, 639, 220, 37), "Volver al resumen" if terminado else "Volver al combate", "cerrar", ORO))

    def dibujar(self, s: pygame.Surface, mouse: tuple[int, int], indice: int | None, total: int, terminado: bool) -> None:
        e = self.entrada
        velo = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        velo.fill((5, 8, 16, 225))
        s.blit(velo, (0, 0))
        panel(s, pygame.Rect(60, 24, 1156, 672))
        titulo = f"REGLAS DEL TURNO {e.turno:03d}" if e.turno else "CONSULTA DEL OPERADOR / SIN EJECUTAR"
        texto(s, f"{titulo} / {e.actor.value.upper()} {e.personaje}", (84, 40), 15, AZUL, True)
        color = ROJO if e.operador.prioridad else ORO
        texto(s, e.operador.nombre.replace("_", " "), (84, 67), 28, color, True)
        texto(s, f"{e.categoria.upper()} · condiciones evaluadas ANTES del movimiento", (84, 108), 14, TENUE)
        cumplidas = sum(c.cumple for c in e.condiciones)
        texto(s, f"PRECONDICIONES / {cumplidas} DE {len(e.condiciones)} CUMPLIDAS", (84, 147), 15,
              VERDE if cumplidas == len(e.condiciones) else ROJO, True)
        for i, condicion in enumerate(e.condiciones):
            y = 186 + i * 48
            color_regla = VERDE if condicion.cumple else ROJO
            pygame.draw.circle(s, color_regla, (92, y + 12), 5)
            texto(s, condicion.regla, (108, y), 16, TEXTO, ancho=462)
            texto(s, f"{'CUMPLE' if condicion.cumple else 'NO CUMPLE'} · valor: {condicion.observado}", (108, y + 22), 13, color_regla, ancho=482)
        texto(s, "ESTADO ANTERIOR → OPERADOR → ESTADO RESULTANTE", (638, 147), 13, AZUL, True)
        pygame.draw.rect(s, FONDO, self.TRANSICION, border_radius=5)
        clip_anterior = s.get_clip()
        s.set_clip(self.TRANSICION)
        filas = self.filas_envueltas()
        for i, fila in enumerate(filas):
            y = 183 + (i - self.scroll) * 22
            if 153 <= y <= 600:
                encabezado = fila.startswith(("REGLA", "1 /", "2 /", "VISTA PREVIA"))
                texto(s, fila, (650, y), 14, ORO if encabezado else TEXTO, encabezado, ancho=530)
        s.set_clip(clip_anterior)
        texto(s, "Rueda sobre este panel: ver todos los cambios", (638, 607), 12, TENUE)
        texto(s, "Esc: cerrar · La pelea se detiene mientras consultas", (426, 650), 12, TENUE)
        for boton in self.botones(indice, total, terminado):
            boton.dibujar(s, mouse)
