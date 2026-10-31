"""Modèle de données d'une esquisse 2D (exigences GEO-01 à GEO-04, GEO-09, ESQ-08).

Une esquisse est posée sur un plan et contient des entités, chacune avec un
identifiant stable :
    P1, P2…  points (extrémités, centres, points libres)
    L1…      lignes, définies par deux points
    C1…      cercles, définis par un point centre et un rayon
    A1…      arcs, définis par un centre, un point de début et un point de fin
             (parcourus en sens trigonométrique du début vers la fin)
Les courbes ne stockent pas de coordonnées : elles désignent des points. Deux
lignes qui partagent un point sont donc reliées (contour fermé possible).

Une entité « de construction » sert d'aide au tracé (axe, ligne de rappel) et
n'est pas prise en compte dans le profil d'une fonction volumique (ESQ-08).

Ce module ne dépend ni de Qt ni d'OpenCascade. Les relations géométriques et les
cotes s'ajouteront à l'étape 2.2.
"""

import math
import re
from dataclasses import asdict, dataclass
from itertools import pairwise
from typing import Any

from cao.esquisse.geometrie import (
    TOLERANCE,
    GeometrieImpossible,
    Point2D,
    angle_de,
    arc_tangent,
    arc_trois_points,
    balayage,
    cercle_trois_points,
    distance,
    rectangle_centre,
    rectangle_deux_coins,
    rectangle_trois_points,
)


@dataclass
class Point:
    id: str
    x: float
    y: float
    construction: bool = False


@dataclass
class Ligne:
    id: str
    debut: str
    fin: str
    construction: bool = False


@dataclass
class Cercle:
    id: str
    centre: str
    rayon: float
    construction: bool = False


@dataclass
class Arc:
    id: str
    centre: str
    debut: str
    fin: str
    construction: bool = False


Entite = Point | Ligne | Cercle | Arc
Courbe = Ligne | Cercle | Arc
# Un point se désigne par son identifiant (point existant, partagé) ou par ses coordonnées.
RefPoint = str | Point2D | tuple[float, float]

_PREFIXES: dict[type, str] = {Point: "P", Ligne: "L", Cercle: "C", Arc: "A"}
_GENRES: dict[str, type] = {"point": Point, "ligne": Ligne, "cercle": Cercle, "arc": Arc}
_NOMS_GENRES = {classe: nom for nom, classe in _GENRES.items()}


class EntiteInconnue(KeyError):
    pass


class Esquisse:
    def __init__(self, nom: str = "Esquisse1", plan: str = "face") -> None:
        self.nom = nom
        self.plan = plan  # « face », « dessus », « droite » ou référence d'une face (lot 3)
        self.entites: dict[str, Entite] = {}
        self._compteurs = dict.fromkeys(_PREFIXES.values(), 0)

    # --- Accès ---

    def __getitem__(self, identifiant: str) -> Entite:
        try:
            return self.entites[identifiant]
        except KeyError:
            raise EntiteInconnue(identifiant) from None

    def point(self, identifiant: str) -> Point:
        entite = self[identifiant]
        if not isinstance(entite, Point):
            raise EntiteInconnue(f"{identifiant} n'est pas un point")
        return entite

    def position(self, identifiant: str) -> Point2D:
        p = self.point(identifiant)
        return Point2D(p.x, p.y)

    def points(self) -> list[Point]:
        return [e for e in self.entites.values() if isinstance(e, Point)]

    def courbes(self) -> list[Courbe]:
        return [e for e in self.entites.values() if not isinstance(e, Point)]

    def points_de(self, courbe: Courbe) -> list[str]:
        if isinstance(courbe, Ligne):
            return [courbe.debut, courbe.fin]
        if isinstance(courbe, Cercle):
            return [courbe.centre]
        return [courbe.centre, courbe.debut, courbe.fin]

    def utilisateurs(self, identifiant_point: str) -> list[str]:
        """Courbes qui utilisent ce point."""
        return [c.id for c in self.courbes() if identifiant_point in self.points_de(c)]

    # --- Mesures ---

    def longueur(self, identifiant: str) -> float:
        courbe = self[identifiant]
        if isinstance(courbe, Ligne):
            return distance(self.position(courbe.debut), self.position(courbe.fin))
        if isinstance(courbe, Cercle):
            return 2 * math.pi * courbe.rayon
        if isinstance(courbe, Arc):
            return self.rayon(courbe.id) * self.angle_arc(courbe.id)
        raise EntiteInconnue(f"{identifiant} n'a pas de longueur")

    def rayon(self, identifiant: str) -> float:
        courbe = self[identifiant]
        if isinstance(courbe, Cercle):
            return courbe.rayon
        if isinstance(courbe, Arc):
            return distance(self.position(courbe.centre), self.position(courbe.debut))
        raise EntiteInconnue(f"{identifiant} n'a pas de rayon")

    def angle_arc(self, identifiant: str) -> float:
        """Angle balayé par un arc, en radians."""
        arc = self[identifiant]
        if not isinstance(arc, Arc):
            raise EntiteInconnue(f"{identifiant} n'est pas un arc")
        centre = self.position(arc.centre)
        return balayage(
            angle_de(centre, self.position(arc.debut)), angle_de(centre, self.position(arc.fin))
        )

    # --- Création (une méthode par mode de tracé du cahier des charges) ---

    def _nouvel_id(self, classe: type) -> str:
        prefixe = _PREFIXES[classe]
        self._compteurs[prefixe] += 1
        return f"{prefixe}{self._compteurs[prefixe]}"

    def ajouter_point(self, x: float, y: float, construction: bool = False) -> str:
        """Point libre ou point de construction (GEO-09)."""
        identifiant = self._nouvel_id(Point)
        self.entites[identifiant] = Point(identifiant, float(x), float(y), construction)
        return identifiant

    def _point(self, reference: RefPoint, construction: bool = False) -> str:
        """Identifiant d'un point existant, ou d'un nouveau point créé aux coordonnées données."""
        if isinstance(reference, str):
            self.point(reference)  # vérifie qu'il existe
            return reference
        x, y = reference
        return self.ajouter_point(x, y, construction)

    def ajouter_ligne(self, debut: RefPoint, fin: RefPoint, construction: bool = False) -> str:
        """Ligne point à point (GEO-01)."""
        a, b = self._point(debut, construction), self._point(fin, construction)
        if a == b or distance(self.position(a), self.position(b)) < TOLERANCE:
            # On ne retire que les points créés par cette tentative, jamais un point existant.
            crees = [i for i, ref in ((a, debut), (b, fin)) if not isinstance(ref, str)]
            self._nettoyer_points(crees)
            raise GeometrieImpossible("Une ligne doit relier deux points distincts.")
        identifiant = self._nouvel_id(Ligne)
        self.entites[identifiant] = Ligne(identifiant, a, b, construction)
        return identifiant

    def ajouter_lignes_chainees(
        self, points: list[RefPoint], fermer: bool = False, construction: bool = False
    ) -> list[str]:
        """Lignes chaînées (GEO-01) : chaque ligne commence où finit la précédente."""
        if len(points) < 2:
            raise GeometrieImpossible("Il faut au moins deux points pour tracer une ligne.")
        ids = [self._point(p, construction) for p in points]
        if fermer:
            ids.append(ids[0])
        return [self.ajouter_ligne(a, b, construction) for a, b in pairwise(ids)]

    def _ajouter_contour(self, coins: list[Point2D], construction: bool) -> list[str]:
        return self.ajouter_lignes_chainees(list(coins), fermer=True, construction=construction)

    def ajouter_rectangle(
        self, coin: Point2D, coin_oppose: Point2D, construction: bool = False
    ) -> list[str]:
        """Rectangle par deux coins (GEO-02) : quatre lignes partageant leurs coins."""
        return self._ajouter_contour(rectangle_deux_coins(coin, coin_oppose), construction)

    def ajouter_rectangle_centre(
        self, centre: Point2D, coin: Point2D, construction: bool = False
    ) -> list[str]:
        """Rectangle centré (GEO-02)."""
        return self._ajouter_contour(rectangle_centre(centre, coin), construction)

    def ajouter_rectangle_incline(
        self, a: Point2D, b: Point2D, c: Point2D, construction: bool = False
    ) -> list[str]:
        """Rectangle incliné par trois points (GEO-02)."""
        return self._ajouter_contour(rectangle_trois_points(a, b, c), construction)

    def ajouter_cercle(self, centre: RefPoint, rayon: float, construction: bool = False) -> str:
        """Cercle centre–rayon (GEO-03)."""
        if rayon < TOLERANCE:
            raise GeometrieImpossible("Le rayon d'un cercle doit être positif.")
        c = self._point(centre, construction)
        identifiant = self._nouvel_id(Cercle)
        self.entites[identifiant] = Cercle(identifiant, c, float(rayon), construction)
        return identifiant

    def ajouter_cercle_trois_points(
        self, a: Point2D, b: Point2D, c: Point2D, construction: bool = False
    ) -> str:
        """Cercle passant par trois points (GEO-03)."""
        centre, rayon = cercle_trois_points(a, b, c)
        return self.ajouter_cercle(centre, rayon, construction)

    def _ajouter_arc(self, centre: str, debut: str, fin: str, construction: bool) -> str:
        identifiant = self._nouvel_id(Arc)
        self.entites[identifiant] = Arc(identifiant, centre, debut, fin, construction)
        return identifiant

    def ajouter_arc(
        self, centre: RefPoint, debut: RefPoint, fin: RefPoint, construction: bool = False
    ) -> str:
        """Arc centre–extrémités (GEO-04) : le rayon est donné par le début ; la fin ne
        donne que l'angle (elle est ramenée sur le cercle), comme dans SolidWorks."""
        c = self._point(centre, construction)
        d = self._point(debut, construction)
        pc, pd = self.position(c), self.position(d)
        rayon = distance(pc, pd)
        if rayon < TOLERANCE:
            raise GeometrieImpossible("Le début de l'arc ne peut pas être sur son centre.")
        if isinstance(fin, str):
            f = self._point(fin)
        else:
            pf = Point2D(*fin)
            if distance(pc, pf) < TOLERANCE:
                raise GeometrieImpossible("La fin de l'arc ne peut pas être sur son centre.")
            sur_cercle = pc + (pf - pc).fois(rayon / distance(pc, pf))
            f = self.ajouter_point(sur_cercle.x, sur_cercle.y, construction)
        return self._ajouter_arc(c, d, f, construction)

    def ajouter_arc_trois_points(
        self, debut: Point2D, passage: Point2D, fin: Point2D, construction: bool = False
    ) -> str:
        """Arc passant par trois points (GEO-04)."""
        centre, d, f = arc_trois_points(Point2D(*debut), Point2D(*passage), Point2D(*fin))
        ids = [self.ajouter_point(p.x, p.y, construction) for p in (centre, d, f)]
        return self._ajouter_arc(ids[0], ids[1], ids[2], construction)

    def ajouter_arc_tangent(self, ligne: str, arrivee: Point2D, construction: bool = False) -> str:
        """Arc tangent (GEO-04) : prolonge sans cassure la ligne donnée, depuis sa fin."""
        segment = self[ligne]
        if not isinstance(segment, Ligne):
            raise GeometrieImpossible("Un arc tangent part de l'extrémité d'une ligne.")
        depart = self.position(segment.fin)
        direction = depart - self.position(segment.debut)
        centre, debut, fin = arc_tangent(depart, direction, Point2D(*arrivee))
        c = self.ajouter_point(centre.x, centre.y, construction)
        nouveau = self.ajouter_point(*(fin if debut == depart else debut), construction)
        if debut == depart:
            return self._ajouter_arc(c, segment.fin, nouveau, construction)
        return self._ajouter_arc(c, nouveau, segment.fin, construction)

    # --- Modification ---

    def basculer_construction(self, identifiant: str) -> None:
        """Passe une entité en construction ou l'en retire (ESQ-08)."""
        entite = self[identifiant]
        entite.construction = not entite.construction

    def deplacer_point(self, identifiant: str, x: float, y: float) -> None:
        p = self.point(identifiant)
        p.x, p.y = float(x), float(y)

    def supprimer(self, identifiant: str) -> list[str]:
        """Supprime une entité ; renvoie tout ce qui a été supprimé.

        Supprimer un point supprime les courbes qui s'en servent. Supprimer une
        courbe supprime ses points devenus inutiles (non partagés).
        """
        entite = self[identifiant]
        supprimes: list[str] = []
        if isinstance(entite, Point):
            for courbe in self.utilisateurs(identifiant):
                supprimes += self.supprimer(courbe)
            if identifiant in self.entites:
                del self.entites[identifiant]
                supprimes.append(identifiant)
            return supprimes
        points = self.points_de(entite)
        del self.entites[identifiant]
        supprimes.append(identifiant)
        supprimes += self._nettoyer_points(points)
        return supprimes

    def _nettoyer_points(self, identifiants: list[str]) -> list[str]:
        """Retire les points qui ne servent plus à aucune courbe (sauf les points libres
        créés exprès par l'utilisateur, qui n'ont jamais servi : ils ne sont pas passés ici)."""
        retires = []
        for identifiant in dict.fromkeys(identifiants):
            if identifiant in self.entites and not self.utilisateurs(identifiant):
                del self.entites[identifiant]
                retires.append(identifiant)
        return retires

    # --- Enregistrement (format natif, docs/format_fichier.md) ---

    def vers_dict(self) -> dict[str, Any]:
        return {
            "nom": self.nom,
            "plan": self.plan,
            "entites": [
                {"genre": _NOMS_GENRES[type(e)], **asdict(e)} for e in self.entites.values()
            ],
        }

    @classmethod
    def depuis_dict(cls, donnees: dict[str, Any]) -> "Esquisse":
        esquisse = cls(donnees["nom"], donnees["plan"])
        for brut in donnees["entites"]:
            champs = dict(brut)
            classe = _GENRES[champs.pop("genre")]
            entite = classe(**champs)
            esquisse.entites[entite.id] = entite
            prefixe, numero = re.fullmatch(r"([A-Z]+)(\d+)", entite.id).groups()  # type: ignore[union-attr]
            esquisse._compteurs[prefixe] = max(esquisse._compteurs[prefixe], int(numero))
        return esquisse
