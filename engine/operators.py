"""Operadores EEO v7: contratos, transiciones inmutables y normalización N0–N3."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from engine.models import (Accion, Actor, Colision, Distancia, Especial, Estado,
                           Nombre, Personaje, Postura, iniciar_turno)


class TipoOperador(str, Enum):
    DESPLAZAR = "Desplazar"
    GOLPEAR = "Golpear"
    BLOQUEAR = "Bloquear"
    SALTAR = "Saltar"
    ATERRIZAR = "Aterrizar"
    AGARRAR = "Agarrar"
    SPIN_DRIVE = "Spin Drive Smasher"
    KILLER_BEE = "Killer Bee Assault"
    PSYCHO_CRUSHER = "Psycho Crusher Nightmare"
    SEICHUSEN = "Seichusen Godanzuki"
    LIBERAR = "Liberar_Asalto_Psycho"
    FINTA = "Finta_Aerea_Delta"
    DRENAR = "Drenar_Energia_Psycho"
    LECTURA = "Lectura_Intuitiva_Karate"
    ACERCAR = "Acercarse"
    ALEJAR = "Alejarse"
    CARGAR = "Cargar energía"


INTELIGENTES = frozenset((TipoOperador.LIBERAR, TipoOperador.FINTA, TipoOperador.DRENAR, TipoOperador.LECTURA))
ESPECIALES = {
    TipoOperador.SPIN_DRIVE: (Nombre.JULI, (Distancia.CONTACTO,), 300),
    TipoOperador.KILLER_BEE: (Nombre.CAMMY, (Distancia.MEDIA, Distancia.CONTACTO), 300),
    TipoOperador.PSYCHO_CRUSHER: (Nombre.BISON, (Distancia.MEDIA, Distancia.CERCA), 350),
    TipoOperador.SEICHUSEN: (Nombre.MAKOTO, (Distancia.CERCA, Distancia.CONTACTO), 350),
}
DISTANCIAS = (Distancia.LEJOS, Distancia.MEDIA, Distancia.CERCA, Distancia.CONTACTO)
TERRESTRES = (Postura.NEUTRAL, Postura.DESPLAZAMIENTO)


class OperadorInvalido(ValueError):
    """La aplicación de un operador exige satisfacer sus precondiciones."""


@dataclass(frozen=True, slots=True)
class Condicion:
    regla: str
    cumple: bool
    observado: str


def _danar(p: Personaje, cantidad: int, accion: Accion = Accion.DANO) -> Personaje:
    """N1: un impacto normaliza la postura terrestre o derriba al receptor aéreo."""
    return replace(p, puntos_salud=max(0, p.puntos_salud - cantidad),
                   postura=Postura.NEUTRAL, colision=Colision.VULNERABLE,
                   dano_recibido=1, acciones=accion)


@dataclass(frozen=True, slots=True)
class Operador:
    tipo: TipoOperador

    @property
    def nombre(self) -> str:
        return self.tipo.value

    @property
    def prioridad(self) -> int:
        return 100 if self.tipo in INTELIGENTES else 0

    def condiciones(self, estado: Estado, actor: Actor) -> tuple[Condicion, ...]:
        """Contrato evaluado tras N2/N3, igual que puede_aplicarse y aplicar."""
        estado = iniciar_turno(estado, actor)
        p, r = estado.personaje(actor), estado.personaje(actor.rival)
        t = self.tipo
        reglas = [Condicion("Salud del actor > 0", p.puntos_salud > 0, str(p.puntos_salud)),
                  Condicion("Salud del rival > 0", r.puntos_salud > 0, str(r.puntos_salud))]

        def exigir(regla: str, cumple: bool, observado: str) -> None:
            reglas.append(Condicion(regla, cumple, observado))

        def distancia(*valores: Distancia) -> None:
            exigir("distancia " + " o ".join(v.value for v in valores),
                   p.distancia in valores, p.distancia.value)

        def postura(*valores: Postura) -> None:
            exigir("postura " + " o ".join(v.value for v in valores),
                   p.postura in valores, p.postura.value)

        def ataque_rival() -> None:
            exigir("rival Atacando", r.acciones is Accion.ATACANDO, r.acciones.value)

        def nombre(valor: Nombre) -> None:
            exigir(f"personaje {valor.value}", p.nombre is valor, p.nombre.value)

        def super_completo() -> None:
            exigir("super = 3", p.medidor_super == 3, str(p.medidor_super))

        if t is TipoOperador.ATERRIZAR:
            postura(Postura.AEREO)
            return tuple(reglas)
        if t in (TipoOperador.DESPLAZAR, TipoOperador.SALTAR, TipoOperador.KILLER_BEE):
            postura(Postura.NEUTRAL)
        else:
            postura(*TERRESTRES)
        if t is TipoOperador.DESPLAZAR:
            distancia(Distancia.LEJOS)
            exigir("postura rival Neutral", r.postura is Postura.NEUTRAL, r.postura.value)
        elif t is TipoOperador.GOLPEAR:
            distancia(Distancia.CERCA, Distancia.CONTACTO)
            exigir("Actor no está Atacando", p.acciones is not Accion.ATACANDO, p.acciones.value)
            exigir("rival Vulnerable", r.colision is Colision.VULNERABLE, r.colision.value)
        elif t is TipoOperador.BLOQUEAR:
            distancia(Distancia.MEDIA, Distancia.CERCA, Distancia.CONTACTO)
            exigir("Actor no está Atacando", p.acciones is not Accion.ATACANDO, p.acciones.value)
        elif t is TipoOperador.SALTAR:
            distancia(Distancia.CERCA, Distancia.MEDIA)
            ataque_rival()
        elif t is TipoOperador.AGARRAR:
            distancia(Distancia.CERCA, Distancia.CONTACTO)
            exigir("rival Defendiendo", r.acciones is Accion.DEFENDIENDO, r.acciones.value)
        elif t in ESPECIALES:
            luchador, alcance, _ = ESPECIALES[t]
            nombre(luchador)
            super_completo()
            distancia(*alcance)
            if t is TipoOperador.SPIN_DRIVE:
                exigir("especial Activo", p.especial is Especial.ACTIVO, p.especial.value)
        elif t is TipoOperador.LIBERAR:
            nombre(Nombre.JULI)
            exigir("Salud del actor <= 450", p.puntos_salud <= 450, str(p.puntos_salud))
            exigir("especial Activo", p.especial is Especial.ACTIVO, p.especial.value)
            super_completo()
            ataque_rival()
            distancia(Distancia.CONTACTO)
        elif t is TipoOperador.FINTA:
            nombre(Nombre.CAMMY)
            exigir("super >= 2", p.medidor_super >= 2, str(p.medidor_super))
            distancia(Distancia.MEDIA)
            exigir("Rival en Media", r.distancia is Distancia.MEDIA, r.distancia.value)
            exigir("rival Defendiendo", r.acciones is Accion.DEFENDIENDO, r.acciones.value)
        elif t is TipoOperador.DRENAR:
            nombre(Nombre.BISON)
            exigir("super < 3", p.medidor_super < 3, str(p.medidor_super))
            ataque_rival()
            distancia(Distancia.CERCA)
        elif t is TipoOperador.LECTURA:
            nombre(Nombre.MAKOTO)
            ataque_rival()
            distancia(Distancia.CERCA, Distancia.CONTACTO)
        elif t is TipoOperador.ACERCAR:
            exigir("Distancia distinta de Contacto", p.distancia is not Distancia.CONTACTO, p.distancia.value)
        elif t is TipoOperador.ALEJAR:
            exigir("Distancia distinta de Lejos", p.distancia is not Distancia.LEJOS, p.distancia.value)
        elif t is TipoOperador.CARGAR:
            exigir("super < 3", p.medidor_super < 3, str(p.medidor_super))
            exigir("recarga_energia = 1", p.recarga_energia == 1, str(p.recarga_energia))
            exigir("acciones Reposo o Cargando", p.acciones in (Accion.REPOSO, Accion.CARGANDO), p.acciones.value)
        return tuple(reglas)

    def puede_aplicarse(self, estado: Estado, actor: Actor) -> bool:
        """Las colisiones ofensivas rivales caducan por N2 antes de comprobar."""
        if estado.terminado:
            return False
        p, r = estado.personaje(actor), estado.personaje(actor.rival)
        t = self.tipo
        if t is TipoOperador.ATERRIZAR:
            return p.postura is Postura.AEREO
        if p.postura not in TERRESTRES:
            return False
        if t is TipoOperador.DESPLAZAR:
            return p.distancia is Distancia.LEJOS and p.postura is Postura.NEUTRAL and r.postura is Postura.NEUTRAL
        if t is TipoOperador.GOLPEAR:
            return p.distancia in (Distancia.CERCA, Distancia.CONTACTO) and p.acciones is not Accion.ATACANDO and r.colision is not Colision.INVULNERABLE
        if t is TipoOperador.BLOQUEAR:
            return p.distancia is not Distancia.LEJOS and p.acciones is not Accion.ATACANDO
        if t is TipoOperador.SALTAR:
            return p.distancia in (Distancia.CERCA, Distancia.MEDIA) and r.acciones is Accion.ATACANDO and p.postura is Postura.NEUTRAL
        if t is TipoOperador.AGARRAR:
            return p.distancia in (Distancia.CERCA, Distancia.CONTACTO) and r.acciones is Accion.DEFENDIENDO
        if t in ESPECIALES:
            nombre, alcance, _ = ESPECIALES[t]
            return (p.nombre is nombre and p.medidor_super == 3 and p.distancia in alcance
                    and (t is not TipoOperador.SPIN_DRIVE or p.especial is Especial.ACTIVO)
                    and (t is not TipoOperador.KILLER_BEE or p.postura is Postura.NEUTRAL))
        if t is TipoOperador.LIBERAR:
            return p.nombre is Nombre.JULI and p.puntos_salud <= 450 and p.especial is Especial.ACTIVO and p.medidor_super == 3 and r.acciones is Accion.ATACANDO and p.distancia is Distancia.CONTACTO
        if t is TipoOperador.FINTA:
            return p.nombre is Nombre.CAMMY and p.medidor_super >= 2 and p.distancia is Distancia.MEDIA and r.acciones is Accion.DEFENDIENDO
        if t is TipoOperador.DRENAR:
            return p.nombre is Nombre.BISON and p.medidor_super < 3 and r.acciones is Accion.ATACANDO and p.distancia is Distancia.CERCA
        if t is TipoOperador.LECTURA:
            return p.nombre is Nombre.MAKOTO and r.acciones is Accion.ATACANDO and p.distancia in (Distancia.CERCA, Distancia.CONTACTO)
        if t is TipoOperador.ACERCAR:
            return p.distancia is not Distancia.CONTACTO
        if t is TipoOperador.ALEJAR:
            return p.distancia is not Distancia.LEJOS
        if t is TipoOperador.CARGAR:
            return p.medidor_super < 3 and p.recarga_energia == 1 and p.acciones in (Accion.REPOSO, Accion.CARGANDO)
        return False

    def aplicar(self, estado: Estado, actor: Actor) -> Estado:
        if not self.puede_aplicarse(estado, actor):
            raise OperadorInvalido(f"{self.nombre} no es válido para {actor.value}")
        estado = iniciar_turno(estado, actor)
        p, r = estado.personaje(actor), estado.personaje(actor.rival)
        t = self.tipo
        if t is TipoOperador.DESPLAZAR:
            p = replace(p, distancia=Distancia.MEDIA, postura=Postura.DESPLAZAMIENTO, acciones=Accion.REPOSO, colision=Colision.VULNERABLE)
            r = replace(r, distancia=Distancia.MEDIA, postura=Postura.DESPLAZAMIENTO, acciones=Accion.REPOSO, colision=Colision.VULNERABLE)
        elif t is TipoOperador.GOLPEAR:
            p = replace(p, postura=Postura.NEUTRAL, acciones=Accion.ATACANDO, colision=Colision.ATACANDO, recarga_energia=1)
            r = _danar(r, 100)
        elif t is TipoOperador.BLOQUEAR:
            chip = 10 if r.acciones is Accion.ATACANDO else 0
            p = replace(p, postura=Postura.NEUTRAL, colision=Colision.INVULNERABLE, puntos_salud=max(0, p.puntos_salud - chip), acciones=Accion.DEFENDIENDO)
        elif t is TipoOperador.SALTAR:
            distancia = Distancia.MEDIA if p.distancia is Distancia.CERCA else Distancia.LEJOS
            p = replace(p, postura=Postura.AEREO, colision=Colision.INVULNERABLE, acciones=Accion.REPOSO, distancia=distancia)
            r = replace(r, distancia=distancia)
        elif t is TipoOperador.ATERRIZAR:
            p = replace(p, postura=Postura.NEUTRAL, acciones=Accion.REPOSO, colision=Colision.VULNERABLE)
        elif t is TipoOperador.AGARRAR:
            p = replace(p, postura=Postura.NEUTRAL, acciones=Accion.AGARRE, colision=Colision.VULNERABLE, recarga_energia=1)
            r = _danar(r, 150)
        elif t in ESPECIALES:
            _, _, dano = ESPECIALES[t]
            p = replace(p, postura=Postura.DESPLAZAMIENTO if t is TipoOperador.PSYCHO_CRUSHER else Postura.NEUTRAL,
                        medidor_super=0, acciones=Accion.ATACANDO, colision=Colision.INVENCIBLE, recarga_energia=0)
            r = _danar(r, dano)
            if t is not TipoOperador.SPIN_DRIVE:
                p, r = replace(p, distancia=Distancia.CONTACTO), replace(r, distancia=Distancia.CONTACTO)
        elif t is TipoOperador.LIBERAR:
            p = replace(p, postura=Postura.NEUTRAL, especial=Especial.LIBERADA, medidor_super=0, acciones=Accion.ATACANDO, colision=Colision.INVENCIBLE)
            r = _danar(r, 350)
        elif t is TipoOperador.FINTA:
            p = replace(p, distancia=Distancia.CONTACTO, postura=Postura.AEREO, colision=Colision.INVENCIBLE, acciones=Accion.ATACANDO, recarga_energia=1)
            r = replace(_danar(r, 250), distancia=Distancia.CONTACTO)
        elif t is TipoOperador.DRENAR:
            p = replace(p, postura=Postura.NEUTRAL, colision=Colision.INVENCIBLE, medidor_super=min(3, p.medidor_super + 1), acciones=Accion.ATACANDO)
            r = replace(r, postura=Postura.NEUTRAL, medidor_super=max(0, r.medidor_super - 1), acciones=Accion.RECUPERACION, colision=Colision.VULNERABLE)
        elif t is TipoOperador.LECTURA:
            p = replace(p, postura=Postura.NEUTRAL, distancia=Distancia.CONTACTO, colision=Colision.INVENCIBLE, medidor_super=3, acciones=Accion.ATACANDO)
            r = replace(_danar(r, 150, Accion.RECUPERACION), distancia=Distancia.CONTACTO)
        elif t in (TipoOperador.ACERCAR, TipoOperador.ALEJAR):
            paso = 1 if t is TipoOperador.ACERCAR else -1
            distancia = DISTANCIAS[DISTANCIAS.index(p.distancia) + paso]
            p = replace(p, distancia=distancia, postura=Postura.DESPLAZAMIENTO, acciones=Accion.REPOSO, colision=Colision.VULNERABLE)
            r = replace(r, distancia=distancia)
        elif t is TipoOperador.CARGAR:
            p = replace(p, postura=Postura.NEUTRAL, acciones=Accion.CARGANDO, medidor_super=min(3, p.medidor_super + 1), recarga_energia=0, colision=Colision.VULNERABLE)
        return estado.con_personajes(actor, p, r)


OPERADORES = tuple(Operador(tipo) for tipo in TipoOperador)


def operadores_validos(estado: Estado, actor: Actor) -> tuple[Operador, ...]:
    """Todos los aplicables, con los inteligentes primero para el HUD."""
    return tuple(sorted((op for op in OPERADORES if op.puede_aplicarse(estado, actor)), key=lambda op: -op.prioridad))


def operadores_prioritarios(estado: Estado, actor: Actor) -> tuple[Operador, ...]:
    """La CPU considera exclusivamente contraataques si hay alguno válido."""
    validos = operadores_validos(estado, actor)
    inteligentes = tuple(op for op in validos if op.prioridad > 0)
    return inteligentes or validos


def ejecutar_turno(estado: Estado, actor: Actor, operador: Operador) -> Estado:
    """Aplica N2/N3 al actor, ejecuta y prepara el turno contrario."""
    return iniciar_turno(operador.aplicar(estado, actor), actor.rival)
