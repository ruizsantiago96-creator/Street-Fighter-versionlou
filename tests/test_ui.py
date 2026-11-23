"""Integración Pygame con vídeo virtual: eventos, turnos y render completo."""
from __future__ import annotations

import os
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path
from typing import Iterator

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
import pytest

from engine.ai import DecisionIA, elegir_operador
from engine.models import Accion, Actor, Colision, Distancia, Hora, Lugar, Nombre, Postura, crear_estado
from engine.operators import ESPECIALES, Operador, TipoOperador as T
from main import Aplicacion
from ui.hud import BORDE, ORO, EntradaLog, explicar_operador
from ui.renderer import Renderer
from ui.screens import Combate, Configuracion, Modo, Seleccion


@pytest.fixture(scope="module")
def pantalla() -> Iterator[pygame.Surface]:
    pygame.init()
    superficie = pygame.display.set_mode((1280, 720))
    yield superficie
    pygame.quit()


@pytest.fixture
def combate(pantalla: pygame.Surface) -> Iterator[Combate]:
    c = Combate(Configuracion(), 0)
    yield c
    c.cerrar()


def clic(rect: pygame.Rect) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)


@pytest.mark.parametrize("campo,valor", [("p1", n) for n in Nombre] + [("p2", n) for n in Nombre] + [("hora", h) for h in Hora] + [("modo", m) for m in Modo] + [("profundidad", 2), ("profundidad", 3)])
def test_seleccion_por_clic(pantalla: pygame.Surface, campo: str, valor: object) -> None:
    seleccion = Seleccion()
    cadena = str(valor.value) if isinstance(valor, (Nombre, Lugar, Hora, Modo)) else str(valor)
    boton = next(b for b in seleccion.botones() if b.clave == f"{campo}:{cadena}")
    assert not seleccion.evento(clic(boton.rect))
    assert getattr(seleccion.config, campo) == valor
    seleccion.dibujar(pantalla, 150, boton.rect.center)


def test_menu_sin_eleccion_de_escenario(pantalla: pygame.Surface) -> None:
    seleccion = Seleccion()
    assert not any(b.clave.startswith("lugar:") for b in seleccion.botones())
    seleccion.dibujar(pantalla, 0, (0, 0))


@pytest.mark.parametrize("lugar", Lugar)
def test_inicio_sortea_entre_todos_los_escenarios(pantalla: pygame.Surface, monkeypatch: pytest.MonkeyPatch, lugar: Lugar) -> None:
    def sortear(opciones: tuple[Lugar, ...]) -> Lugar:
        assert opciones == tuple(Lugar)
        return lugar
    monkeypatch.setattr("main.choice", sortear)
    app = Aplicacion()
    try:
        config = app.seleccion.config
        app.evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN), 0)
        assert app.combate is not None
        assert app.combate.estado.escenario.lugar is lugar
        assert app.combate.estado.escenario.hora is config.hora
        assert app.seleccion.config == config
    finally:
        app.cerrar()


def test_revancha_sortea_otra_vez(pantalla: pygame.Surface, monkeypatch: pytest.MonkeyPatch) -> None:
    sorteos = iter((Lugar.LABORATORIO, Lugar.DOJO))
    monkeypatch.setattr("main.choice", lambda opciones: next(sorteos))
    app = Aplicacion()
    try:
        app.iniciar(0)
        assert app.combate is not None
        anterior = app.combate
        assert anterior.estado.escenario.lugar is Lugar.LABORATORIO
        anterior.estado = replace(anterior.estado, p2=replace(anterior.estado.p2, puntos_salud=0))
        anterior.ko_instante = 0
        app.evento(clic(anterior.botones_ko()[0].rect), 1000)
        assert anterior.cerrado and app.combate is not anterior
        assert app.combate.estado.escenario.lugar is Lugar.DOJO
        assert app.combate.estado.p1.puntos_salud == app.combate.estado.p2.puntos_salud == 1000
    finally:
        app.cerrar()


def test_inicio_menu_y_revancha(pantalla: pygame.Surface) -> None:
    app = Aplicacion()
    try:
        app.evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN), 0)
        assert app.combate is not None
        anterior = app.combate
        app.iniciar(10)
        assert anterior.cerrado
        assert app.combate is not None and app.combate is not anterior
        assert app.combate.estado.p1.puntos_salud == 1000
        app.evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE), 20)
        assert app.combate is None
        app.evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE), 30)
        assert not app.ejecutando
    finally:
        app.cerrar()


@pytest.mark.parametrize("hora", Hora)
@pytest.mark.parametrize("lugar", Lugar)
def test_escenarios_renderizan(pantalla: pygame.Surface, hora: Hora, lugar: Lugar) -> None:
    s = crear_estado(hora=hora, lugar=lugar)
    renderer = Renderer(s)
    renderer.dibujar(pantalla, s, 50)
    assert renderer.fondo(s).get_size() == (908, 352)
    assert renderer.fondo(s) is renderer.fondo(s)


def test_fondos_distintos(pantalla: pygame.Surface) -> None:
    renderer = Renderer(crear_estado())
    fondos = {pygame.image.tostring(renderer.fondo(crear_estado(hora=h, lugar=l)), "RGB") for h in Hora for l in Lugar}
    assert len(fondos) == 15


def test_movimiento_interpolado(combate: Combate) -> None:
    inicio = combate.renderer.posiciones[Actor.P1]
    s = combate.estado
    s = replace(s, p1=replace(s.p1, distancia=Distancia.CONTACTO), p2=replace(s.p2, distancia=Distancia.CONTACTO))
    combate.renderer.actualizar(s, 1 / 60)
    primero = combate.renderer.posiciones[Actor.P1]
    assert inicio < primero < 402
    for _ in range(60):
        combate.renderer.actualizar(s, 1 / 60)
    assert abs(combate.renderer.posiciones[Actor.P1] - 402) < 1
    assert abs(combate.renderer.posiciones[Actor.P2] - 506) < 1


@pytest.mark.parametrize("nombre", Nombre)
@pytest.mark.parametrize("postura,accion,colision", [(Postura.DESPLAZAMIENTO, Accion.REPOSO, Colision.VULNERABLE), (Postura.AEREO, Accion.ATACANDO, Colision.INVENCIBLE), (Postura.NEUTRAL, Accion.DEFENDIENDO, Colision.INVULNERABLE), (Postura.NEUTRAL, Accion.REPOSO, Colision.VULNERABLE)])
def test_figuras_y_estados_visuales(pantalla: pygame.Surface, nombre: Nombre, postura: Postura, accion: Accion, colision: Colision) -> None:
    s = crear_estado(nombre, nombre)
    s = replace(s, p1=replace(s.p1, postura=postura, acciones=accion, colision=colision), p2=replace(s.p2, postura=postura, acciones=accion, colision=colision))
    Renderer(s).dibujar(pantalla, s, 100)


def test_accion_jugador_bloquea_doble_clic_y_espera_700_ms(combate: Combate) -> None:
    combate.estado = replace(combate.estado, p1=replace(combate.estado.p1, recarga_energia=1))
    boton, _ = next((b, op) for b, op in combate.hud.botones_accion(combate.estado, Actor.P1, True) if op.tipo is T.CARGAR)
    combate.evento(clic(boton.rect), 0)
    assert len(combate.log) == 1 and combate.turno is Actor.P2
    combate.evento(clic(boton.rect), 1)
    assert len(combate.log) == 1
    combate.actualizar(699, 0.016)
    assert combate.futuro is None and len(combate.log) == 1
    combate.actualizar(700, 0.016)
    if combate.futuro is not None:
        combate.futuro.result(timeout=10)
        combate.actualizar(701, 0.016)
    assert len(combate.log) == 2 and combate.turno is Actor.P1
    assert combate.ultima_decision is not None
    assert not combate.puede_jugar(702)
    assert combate.puede_jugar(1400)


def test_operadores_deshabilitados_y_tooltips(combate: Combate) -> None:
    botones = combate.hud.botones_accion(combate.estado, Actor.P1, True)
    golpe = next(b for b, op in botones if op.tipo is T.GOLPEAR)
    assert not golpe.habilitado
    assert "distancia Cerca" in golpe.ayuda
    combate.evento(clic(golpe.rect), 0)
    assert not combate.log
    carga = next(b for b, op in botones if op.tipo is T.CARGAR)
    assert not carga.habilitado and "recarga_energia = 1" in carga.ayuda


def test_ui_transmite_inactividad_y_la_reinicia_con_dano(combate: Combate) -> None:
    combate.turno = Actor.P2
    combate.turnos_sin_dano = 3
    combate.actualizar(1200, 0.016)
    if combate.futuro is not None:
        combate.futuro.result(timeout=10)
        combate.actualizar(1201, 0.016)
    assert combate.ultima_decision is not None and combate.ultima_decision.motivo
    assert combate.log[-1].operador.tipo is T.DESPLAZAR
    assert combate.turnos_sin_dano == 4
    s = combate.estado
    combate.estado = replace(s, p1=replace(s.p1, distancia=Distancia.CERCA, postura=Postura.NEUTRAL),
                             p2=replace(s.p2, distancia=Distancia.CERCA, colision=Colision.VULNERABLE))
    combate.jugar(Operador(T.GOLPEAR), 2000)
    assert combate.turnos_sin_dano == 0


@pytest.mark.parametrize("profundidad", [2, 3])
def test_ia_vs_ia_llega_a_ko_con_temporizador_y_trabajador_real(pantalla: pygame.Surface, profundidad: int) -> None:
    c = Combate(Configuracion(p1=Nombre.MAKOTO, p2=Nombre.BISON, modo=Modo.IA_IA, profundidad=profundidad), 0)
    try:
        for _ in range(100):
            ahora = c.siguiente_ia
            c.actualizar(ahora, 0.016)
            if c.futuro is not None:
                c.futuro.result(timeout=10)
                c.actualizar(ahora, 0.016)
            assert not c.error
            if c.estado.terminado:
                break
        assert c.estado.terminado
        assert {e.actor for e in c.log} == {Actor.P1, Actor.P2}
        assert any(e.operador.prioridad for e in c.log)
        assert c.mostrar_ko(ahora + 850)
        c.dibujar(pantalla, ahora + 850, (0, 0))
    finally:
        c.cerrar()


def test_animacion_preserva_dano_antes_de_normalizar(combate: Combate, pantalla: pygame.Surface) -> None:
    s = combate.estado
    combate.estado = replace(s, p1=replace(s.p1, distancia=Distancia.CERCA), p2=replace(s.p2, distancia=Distancia.CERCA))
    combate.jugar(Operador(T.GOLPEAR), 0)
    assert combate.estado.p2.acciones is Accion.DANO
    assert combate.estado.p1.colision is Colision.VULNERABLE
    assert combate.renderer.impacto is not None
    assert combate.renderer.impacto.despues.p2.acciones is Accion.DANO
    assert combate.log[-1].dano == 100
    combate.dibujar(pantalla, 100, (20, 20))


def test_pausa_y_paso_no_consumen_decision_pendiente(pantalla: pygame.Surface) -> None:
    c = Combate(Configuracion(modo=Modo.IA_IA, profundidad=2), 0)
    try:
        c.alternar_pausa(100)
        c.actualizar(5000, 0.016)
        assert not c.log and c.futuro is None
        futuro: Future[DecisionIA] = Future()
        futuro.set_result(elegir_operador(c.estado, c.turno, 2))
        c.futuro = futuro
        c.actualizar(6000, 0.016)
        assert not c.log and c.futuro is futuro
        c.solicitar_paso()
        c.actualizar(6000, 0.016)
        assert len(c.log) == 1 and c.pausado and not c.paso_pendiente
        c.actualizar(12000, 0.016)
        assert len(c.log) == 1
        c.alternar_pausa(12000)
        assert not c.pausado and c.siguiente_ia == 13200
        c.actualizar(13199, 0.016)
        assert len(c.log) == 1
    finally:
        c.cerrar()


def test_ia_vs_ia_no_juega_antes_de_1200_ms(pantalla: pygame.Surface) -> None:
    c = Combate(Configuracion(modo=Modo.IA_IA), 0)
    try:
        c.actualizar(1199, 0.016)
        assert c.futuro is None and not c.log
        c.actualizar(1200, 0.016)
        if c.futuro is not None:
            c.futuro.result(timeout=10)
            c.actualizar(1201, 0.016)
        assert len(c.log) == 1
        assert c.siguiente_ia in (2400, 2401)
    finally:
        c.cerrar()


def test_ko_overlay_no_mas_turnos_y_botones(combate: Combate, pantalla: pygame.Surface, tmp_path: Path) -> None:
    s = combate.estado
    combate.estado = replace(s, p1=replace(s.p1, distancia=Distancia.CERCA), p2=replace(s.p2, distancia=Distancia.CERCA, puntos_salud=50))
    combate.jugar(Operador(T.GOLPEAR), 0)
    assert combate.estado.terminado and combate.estado.ganador is Actor.P1
    assert not combate.mostrar_ko(849) and combate.mostrar_ko(850)
    combate.actualizar(5000, 0.016)
    assert len(combate.log) == 1 and combate.futuro is None
    combate.dibujar(pantalla, 1000, (0, 0))
    pygame.image.save(pantalla, str(tmp_path / "ko.png"))
    assert "terminó" in explicar_operador(Operador(T.CARGAR), combate.estado, Actor.P1)
    assert combate.evento(clic(combate.botones_ko()[0].rect), 1000) == "revancha"
    assert combate.evento(clic(combate.botones_ko()[1].rect), 1000) == "menu"
    combate.actualizar(1_000_000, 0.016)
    assert combate.mostrar_ko(1_000_000) and len(combate.log) == 1
    resumen = combate.resumen_luchadores()
    assert resumen[0].dano_causado == 50
    assert resumen[1].salud_final == 0


def test_contraataque_banner_y_pensamiento(combate: Combate, pantalla: pygame.Surface, tmp_path: Path) -> None:
    s = crear_estado(Nombre.MAKOTO, Nombre.CAMMY)
    combate.estado = replace(s, p1=replace(s.p1, distancia=Distancia.CERCA), p2=replace(s.p2, distancia=Distancia.CERCA, acciones=Accion.ATACANDO))
    combate.ultima_decision = elegir_operador(combate.estado, Actor.P1, 3)
    combate.ultimo_actor_ia = Actor.P1
    combate.jugar(Operador(T.LECTURA), 0)
    assert combate.log[-1].operador.prioridad == 100
    assert combate.log[-1].dano == 150
    assert combate.estado.p1.medidor_super == 3
    assert combate.resumen_luchadores()[0].inteligentes == 1
    assert combate.renderer.impacto is not None
    assert combate.renderer.impacto.despues.p2.acciones is Accion.RECUPERACION
    combate.renderer.actualizar(combate.estado, 0.1)
    combate.dibujar(pantalla, 100, (0, 0))
    pygame.image.save(pantalla, str(tmp_path / "inteligente.png"))


def test_error_ia_pausa_sin_corromper_estado(combate: Combate) -> None:
    combate.turno = Actor.P2
    antes = combate.estado
    futuro: Future[DecisionIA] = Future()
    futuro.set_exception(RuntimeError("fallo simulado"))
    combate.futuro = futuro
    combate.actualizar(1200, 0.016)
    assert combate.pausado and "fallo simulado" in combate.error
    assert combate.estado == antes and not combate.log


def test_historial_desplazable(combate: Combate, pantalla: pygame.Surface, monkeypatch: pytest.MonkeyPatch) -> None:
    combate.log = [EntradaLog(i + 1, Actor.P1, "Juli", Operador(T.LIBERAR if i % 2 else T.CARGAR), 350 if i % 2 else 0) for i in range(20)]
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: combate.hud.HISTORIAL.center)
    combate.evento(pygame.event.Event(pygame.MOUSEWHEEL, y=3, x=0), 0)
    assert combate.hud.scroll == 3
    combate.dibujar(pantalla, 0, (0, 0))
    combate.hud.desplazar(1000, len(combate.log))
    assert combate.hud.scroll == 16
    combate.hud.desplazar(-1000, len(combate.log))
    assert combate.hud.scroll == 0


def test_resumen_separa_dano_al_rival_y_dano_propio(combate: Combate) -> None:
    s = combate.estado
    combate.estado = replace(s, p1=replace(s.p1, distancia=Distancia.CERCA), p2=replace(s.p2, distancia=Distancia.CERCA))
    for i, tipo in enumerate((T.GOLPEAR, T.BLOQUEAR, T.AGARRAR)):
        combate.jugar(Operador(tipo), i * 1200)
    p1, p2 = combate.resumen_luchadores()
    assert p1.dano_causado == 250
    assert p2.dano_causado == 0 and p2.salud_final == 740
    assert combate.log[1].dano == 10 and combate.log[1].dano_rival == 0


def test_resumen_registra_especiales_de_ambos_personajes(combate: Combate) -> None:
    s = crear_estado(Nombre.JULI, Nombre.MAKOTO)
    combate.estado = replace(s, p1=replace(s.p1, distancia=Distancia.CONTACTO, medidor_super=3),
                             p2=replace(s.p2, distancia=Distancia.CONTACTO, medidor_super=3))
    combate.jugar(Operador(T.SPIN_DRIVE), 0)
    combate.jugar(Operador(T.SEICHUSEN), 1200)
    p1, p2 = combate.resumen_luchadores()
    assert p1.especiales == p2.especiales == 1
    assert p1.dano_causado == 300 and p2.dano_causado == 350
    assert combate.estado.p1.medidor_super == combate.estado.p2.medidor_super == 0


@pytest.mark.parametrize("actor", Actor)
@pytest.mark.parametrize("tipo", list(ESPECIALES))
def test_especial_consume_super_y_apaga_los_tres_bloques_del_hud(
    combate: Combate, pantalla: pygame.Surface, actor: Actor, tipo: T, tmp_path: Path,
) -> None:
    nombre, distancias, _ = ESPECIALES[tipo]
    distancia = distancias[0]
    s = crear_estado(nombre, nombre)
    s = replace(s, p1=replace(s.p1, distancia=distancia, medidor_super=2),
                p2=replace(s.p2, distancia=distancia, medidor_super=2))
    combate.estado = s.con_personajes(actor, replace(s.personaje(actor), medidor_super=3), s.personaje(actor.rival))
    combate.turno = actor
    x = 20 if actor is Actor.P1 else 482
    centros = [(x + 27 + i * 32, 83) for i in range(3)]
    combate.dibujar(pantalla, 0, (0, 0))
    assert all(tuple(pantalla.get_at(pos))[:3] == ORO for pos in centros)
    combate.jugar(Operador(tipo), 0)
    assert combate.estado.personaje(actor).medidor_super == 0
    assert combate.estado.personaje(actor.rival).medidor_super == 2
    assert combate.log[-1].categoria == "Poder normal"
    assert combate.log[-1].cambio_super == "S3→0"
    combate.dibujar(pantalla, 100, (0, 0))
    assert all(tuple(pantalla.get_at(pos))[:3] == BORDE for pos in centros)
    assert combate.renderer.impacto is not None
    assert combate.renderer.impacto.antes.personaje(actor).medidor_super == 3
    assert combate.renderer.impacto.despues.personaje(actor).medidor_super == 0
    pygame.image.save(pantalla, str(tmp_path / "super_consumido.png"))
    # Ni la animación ni el siguiente turno restauran el medidor gastado.
    combate.jugar(Operador(T.BLOQUEAR), 700)
    combate.dibujar(pantalla, 800, (0, 0))
    assert combate.estado.personaje(actor).medidor_super == 0
    assert all(tuple(pantalla.get_at(pos))[:3] == BORDE for pos in centros)


@pytest.mark.parametrize("p1,p2", [(Nombre.JULI, Nombre.MAKOTO), (Nombre.BISON, Nombre.BISON), (Nombre.CAMMY, Nombre.CAMMY)])
def test_auditoria_super_en_partida_real(pantalla: pygame.Surface, p1: Nombre, p2: Nombre) -> None:
    c = Combate(Configuracion(p1=p1, p2=p2, modo=Modo.IA_IA), 0)
    poderes = 0
    try:
        for turno in range(100):
            decision = elegir_operador(c.estado, c.turno, 3, turnos_sin_dano=c.turnos_sin_dano)
            assert decision.operador is not None
            c.jugar(decision.operador, turno * 1200)
            entrada = c.log[-1]
            if entrada.operador.tipo in ESPECIALES or entrada.operador.prioridad:
                poderes += 1
                cambio = entrada.cambio_super.replace("→", "->")
                print(f"{p1.value} vs {p2.value}: turno {entrada.turno}, {entrada.actor.value}, {entrada.categoria}, {entrada.operador.nombre}, {cambio}")
                if entrada.operador.tipo in ESPECIALES:
                    assert entrada.cambio_super == "S3→0"
                    assert c.estado.personaje(entrada.actor).medidor_super == 0
                c.dibujar(pantalla, turno * 1200 + 100, (0, 0))
            if c.estado.terminado:
                break
        assert c.estado.terminado
        if p2 is Nombre.MAKOTO:
            assert poderes > 0
        if p1 is Nombre.JULI and p2 is Nombre.MAKOTO:
            # Lectura puede mantener la barra llena por prioridad inteligente.
            assert any(e.operador.tipo is T.LECTURA and e.cambio_super == "S3→3" for e in c.log)
            # La prioridad inteligente puede mantener Lectura en cada turno;
            # el drenaje de los especiales se comprueba aparte para ambos lados.
    finally:
        c.cerrar()


def test_resumen_ko_permite_revisar_toda_la_pelea(combate: Combate, pantalla: pygame.Surface, monkeypatch: pytest.MonkeyPatch) -> None:
    combate.log = [EntradaLog(i + 1, Actor.P1, "Juli", Operador(T.CARGAR), 0) for i in range(20)]
    combate.estado = replace(combate.estado, p2=replace(combate.estado.p2, puntos_salud=0, postura=Postura.NEUTRAL))
    combate.ko_instante = 0
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: combate.HISTORIAL_KO.center)
    combate.evento(pygame.event.Event(pygame.MOUSEWHEEL, y=-3, x=0), 1000)
    assert combate.scroll_ko == 6
    combate.evento(pygame.event.Event(pygame.MOUSEWHEEL, y=-30, x=0), 1000)
    assert combate.scroll_ko == 12
    combate.dibujar(pantalla, 1000, (0, 0))
    combate.evento(pygame.event.Event(pygame.MOUSEWHEEL, y=30, x=0), 1000)
    assert combate.scroll_ko == 0


def test_clic_historial_explica_estado_historico_y_normalizacion(combate: Combate, pantalla: pygame.Surface, tmp_path: Path) -> None:
    s = combate.estado
    combate.estado = replace(s, p1=replace(s.p1, distancia=Distancia.CERCA), p2=replace(s.p2, distancia=Distancia.CERCA))
    combate.jugar(Operador(T.GOLPEAR), 0)
    primero = combate.log[0]
    combate.jugar(Operador(T.BLOQUEAR), 700)
    assert primero.estado_antes is not None and primero.estado_antes.p2.puntos_salud == 1000
    assert primero.estado_operador is not None and primero.estado_operador.p2.acciones is Accion.DANO
    assert primero.estado_despues is not None and primero.estado_despues.p2.acciones is Accion.DANO
    assert all(c.cumple for c in primero.condiciones)
    combate.evento(clic(pygame.Rect(958, 335, 275, 30)), 800)
    assert combate.detalle is not None and combate.detalle.entrada is primero
    assert any("Atacando → Vulnerable" in fila for fila in combate.detalle.filas())
    combate.dibujar(pantalla, 800, (0, 0))
    pygame.image.save(pantalla, str(tmp_path / "reglas_historicas.png"))
    estado = combate.estado
    combate.actualizar(100_000, 0.016)
    assert combate.estado == estado and len(combate.log) == 2
    assert combate.evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE), 1800) is None
    assert combate.detalle is None
    assert combate.siguiente_ia == 2400


def test_ko_clic_movimiento_muestra_reglas_previas_al_ko(combate: Combate, pantalla: pygame.Surface, tmp_path: Path) -> None:
    s = combate.estado
    combate.estado = replace(s, p1=replace(s.p1, distancia=Distancia.CERCA),
                             p2=replace(s.p2, distancia=Distancia.CERCA, puntos_salud=50))
    combate.jugar(Operador(T.GOLPEAR), 0)
    combate.evento(clic(pygame.Rect(680, 176, 430, 40)), 1000)
    assert combate.detalle is not None
    assert all(c.cumple for c in combate.detalle.entrada.condiciones)
    rival_vivo = combate.detalle.entrada.condiciones[1]
    assert rival_vivo.observado == "50" and rival_vivo.cumple
    assert any("50 → 0" in fila for fila in combate.detalle.filas())
    combate.dibujar(pantalla, 1000, (0, 0))
    pygame.image.save(pantalla, str(tmp_path / "reglas_ko.png"))
    cerrar = combate.detalle.botones(0, 1, True)[-1]
    assert combate.evento(clic(cerrar.rect), 1500) is None
    assert combate.detalle is None and combate.mostrar_ko(1500)


def test_clic_derecho_consulta_requisitos_sin_ejecutar(combate: Combate, pantalla: pygame.Surface) -> None:
    boton, _ = next((b, op) for b, op in combate.hud.botones_accion(combate.estado, Actor.P1, True) if op.tipo is T.GOLPEAR)
    anterior = combate.estado
    combate.evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=boton.rect.center), 0)
    assert combate.detalle is not None and combate.detalle.entrada.turno == 0
    assert any(not c.cumple and c.regla == "distancia Cerca o Contacto" for c in combate.detalle.entrada.condiciones)
    assert combate.estado == anterior and not combate.log and not combate.puede_jugar(0)
    combate.dibujar(pantalla, 10, (0, 0))


def test_detalle_navega_y_congela_decision_cpu_pendiente(combate: Combate) -> None:
    combate.jugar(Operador(T.DESPLAZAR), 0)
    combate.jugar(Operador(T.ACERCAR), 700)
    combate.turno = Actor.P2
    futuro: Future[DecisionIA] = Future()
    futuro.set_result(elegir_operador(combate.estado, Actor.P2))
    combate.futuro = futuro
    combate.abrir_detalle(combate.log[0], 800)
    combate.evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT), 900)
    assert combate.indice_detalle() == 1
    combate.actualizar(1200, 0.016)
    assert combate.futuro is futuro and len(combate.log) == 2
    combate.evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT), 1250)
    assert combate.indice_detalle() == 0
    combate.cerrar_detalle(1800)
    assert combate.siguiente_ia == 2400
    combate.actualizar(2399, 0.016)
    assert len(combate.log) == 2
    combate.actualizar(2400, 0.016)
    assert len(combate.log) == 3


@pytest.mark.parametrize("p1", list(Nombre))
@pytest.mark.parametrize("p2", list(Nombre))
def test_exposicion_completa_desde_ui_y_resumen(pantalla: pygame.Surface, p1: Nombre, p2: Nombre) -> None:
    c = Combate(Configuracion(p1=p1, p2=p2, modo=Modo.IA_IA, profundidad=2), 0)
    try:
        for _ in range(90):
            ahora = c.siguiente_ia
            c.actualizar(ahora, 1 / 60)
            if c.futuro is not None:
                c.futuro.result(timeout=10)
                c.actualizar(ahora, 1 / 60)
            assert not c.error
            if c.estado.terminado:
                break
        assert c.estado.terminado
        assert {e.actor for e in c.log if e.operador.prioridad} == set(Actor)
        assert all(r.inteligentes >= 1 for r in c.resumen_luchadores())
        assert any(e.operador.tipo is not T.LECTURA for e in c.log)
        assert all(all(cond.cumple for cond in e.condiciones) for e in c.log)
        c.dibujar(pantalla, ahora + 900, (0, 0))
    finally:
        c.cerrar()


def test_menu_permite_elegir_exposicion_o_competitivo() -> None:
    seleccion = Seleccion(Configuracion(modo=Modo.IA_IA))
    competitivo = next(b for b in seleccion.botones() if b.clave == "exposicion:0")
    seleccion.evento(clic(competitivo.rect))
    assert not seleccion.config.exposicion
    exposicion = next(b for b in seleccion.botones() if b.clave == "exposicion:1")
    seleccion.evento(clic(exposicion.rect))
    assert seleccion.config.exposicion


def test_ia_vs_ia_competitivo_conserva_minimax(pantalla: pygame.Surface) -> None:
    c = Combate(Configuracion(modo=Modo.IA_IA, exposicion=False), 0)
    try:
        c.actualizar(1200, 1 / 60)
        if c.futuro is not None:
            c.futuro.result(timeout=10)
            c.actualizar(1200, 1 / 60)
        assert c.ultima_decision is not None
        assert c.ultima_decision.estrategia == "Minimax"
    finally:
        c.cerrar()
