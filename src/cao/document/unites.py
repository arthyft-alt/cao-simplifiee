"""Unités d'affichage et de saisie des longueurs (exigence COT-06).

Les valeurs sont toujours enregistrées en millimètres ; l'unité et le nombre de
décimales ne servent qu'à l'affichage et à la lecture de ce que tape l'utilisateur.
Écriture française : virgule décimale (le point est aussi accepté à la saisie).
"""

import math
import re
from dataclasses import dataclass
from enum import Enum


class UniteLongueur(Enum):
    MM = "mm"
    CM = "cm"
    M = "m"
    POUCE = "in"

    @property
    def millimetres(self) -> float:
        """Nombre de millimètres dans une unité."""
        return {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}[self.value]

    @property
    def libelle(self) -> str:
        return {"mm": "millimètre", "cm": "centimètre", "m": "mètre", "in": "pouce"}[self.value]


class SaisieInvalide(ValueError):
    """Ce qui a été tapé n'est pas une valeur lisible (message pour l'utilisateur)."""


@dataclass
class Unites:
    longueur: UniteLongueur = UniteLongueur.MM
    decimales: int = 2

    def formater_longueur(self, valeur_mm: float) -> str:
        """« 80,00 mm », dans l'unité et avec la précision choisies."""
        nombre = _nombre(valeur_mm / self.longueur.millimetres, self.decimales)
        return f"{nombre} {self.longueur.value}"

    def formater_angle(self, degres: float) -> str:
        return f"{_nombre(degres, self.decimales)}°"

    def valeur_saisie_longueur(self, valeur_mm: float) -> str:
        """Valeur proposée dans le champ de saisie, sans l'unité (« 80 » ou « 12,5 »)."""
        return _sans_zeros(valeur_mm / self.longueur.millimetres)

    def lire_longueur(self, texte: str) -> float:
        """Valeur en mm. Accepte « 12,5 », « 12.5 », « 25 mm », « 1 in », « 2,5 cm »."""
        nombre, unite = _decouper(texte)
        if unite is None:
            return nombre * self.longueur.millimetres
        if unite not in _UNITES_TAPEES:
            raise SaisieInvalide(f"Unité inconnue : « {unite} » (mm, cm, m ou in).")
        return nombre * _UNITES_TAPEES[unite].millimetres

    def lire_angle(self, texte: str) -> float:
        nombre, unite = _decouper(texte.replace("°", " deg"))
        if unite not in (None, "deg"):
            raise SaisieInvalide("Un angle s'écrit en degrés, par exemple « 30 » ou « 30° ».")
        return nombre

    def vers_dict(self) -> dict[str, object]:
        return {"longueur": self.longueur.value, "decimales": self.decimales}

    @classmethod
    def depuis_dict(cls, donnees: dict[str, object]) -> "Unites":
        unite = UniteLongueur(str(donnees.get("longueur", "mm")))
        decimales = int(donnees.get("decimales", 2))  # type: ignore[call-overload]
        return cls(unite, max(0, min(6, decimales)))


_UNITES_TAPEES = {
    "mm": UniteLongueur.MM,
    "cm": UniteLongueur.CM,
    "m": UniteLongueur.M,
    "in": UniteLongueur.POUCE,
    "po": UniteLongueur.POUCE,
    "pouce": UniteLongueur.POUCE,
    "pouces": UniteLongueur.POUCE,
}


def _nombre(valeur: float, decimales: int) -> str:
    if round(valeur, decimales) == 0:
        valeur = 0.0  # évite d'afficher « -0,00 »
    return f"{valeur:.{decimales}f}".replace(".", ",")


def _sans_zeros(valeur: float) -> str:
    texte = f"{valeur:.6f}".rstrip("0").rstrip(".")
    return texte.replace(".", ",") if texte not in ("", "-0") else "0"


def _decouper(texte: str) -> tuple[float, str | None]:
    morceaux = re.fullmatch(r"\s*([-+]?\d+(?:[.,]\d*)?|[-+]?[.,]\d+)\s*([a-zA-Zé]*)\s*", texte)
    if morceaux is None:
        raise SaisieInvalide(f"« {texte.strip()} » n'est pas un nombre.")
    nombre = float(morceaux.group(1).replace(",", "."))
    if not math.isfinite(nombre):
        raise SaisieInvalide("La valeur doit être un nombre.")
    unite = morceaux.group(2).lower() or None
    return nombre, unite
