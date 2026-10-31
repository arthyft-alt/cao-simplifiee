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
from enum import Enum
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


class GenreRelation(Enum):
    """Relations géométriques (REL-01 à REL-05)."""

    HORIZONTALE = "horizontale"  # 1 ligne, ou 2 points à la même hauteur
    VERTICALE = "verticale"  # 1 ligne, ou 2 points l'un au-dessus de l'autre
    COINCIDENTE = "coincidente"  # point + point, ou point + courbe (point sur la courbe)
    POINT_MILIEU = "point_milieu"  # point + ligne
    FIXE = "fixe"  # 1 point
    PARALLELE = "parallele"  # 2 lignes
    PERPENDICULAIRE = "perpendiculaire"  # 2 lignes
    COLINEAIRE = "colineaire"  # 2 lignes
    TANGENTE = "tangente"  # ligne + arc/cercle, ou arc/cercle + arc/cercle
    CONCENTRIQUE = "concentrique"  # 2 arcs/cercles
    EGALE = "egale"  # 2 lignes (longueurs) ou 2 arcs/cercles (rayons)


@dataclass
class Relation:
    id: str
    genre: GenreRelation
    entites: list[str]


class RelationImpossible(ValueError):
    """Les entités choisies ne conviennent pas à cette relation (message pour l'utilisateur)."""


class GenreCote(Enum):
    """Cotes (COT-01) : le type est déduit de la sélection par la cotation intelligente (2.6)."""

    LONGUEUR = "longueur"  # 1 ligne, ou 2 points (distance en ligne droite)
    HORIZONTALE = "horizontale"  # 2 points ou 1 ligne : écart en x
    VERTICALE = "verticale"  # 2 points ou 1 ligne : écart en y
    DISTANCE = "distance"  # point + ligne, ou 2 lignes parallèles
    ANGLE = "angle"  # 2 lignes, en degrés
    RAYON = "rayon"  # 1 arc ou cercle
    DIAMETRE = "diametre"  # 1 arc ou cercle


@dataclass
class Cote:
    id: str
    genre: GenreCote
    entites: list[str]
    valeur: float  # mm, ou degrés pour un angle
    pilotee: bool = False  # True : cote « de référence », affichée entre parenthèses (COT-05)


class CoteImpossible(ValueError):
    """Les entités ou la valeur ne conviennent pas à cette cote (message pour l'utilisateur)."""


ORIGINE = "P0"  # origine du plan d'esquisse : point fixe, toujours présent, jamais enregistré


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
        self.relations: dict[str, Relation] = {}
        self.cotes: dict[str, Cote] = {}
        self._compteurs = dict.fromkeys([*_PREFIXES.values(), "R", "D"], 0)
        self._origine = Point(ORIGINE, 0.0, 0.0)

    # --- Accès ---

    def __getitem__(self, identifiant: str) -> Entite:
        if identifiant == ORIGINE:
            return self._origine
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

    # --- Relations (REL-01 à REL-05) ---

    def genre_entite(self, identifiant: str) -> str:
        """« point », « ligne » ou « courbe » (cercle ou arc)."""
        entite = self[identifiant]
        if isinstance(entite, Point):
            return "point"
        if isinstance(entite, Ligne):
            return "ligne"
        return "courbe"

    def ajouter_relation(self, genre: GenreRelation, *entites: str) -> str:
        """Ajoute une relation après avoir vérifié que les entités conviennent.

        L'ordre des entités n'a pas d'importance (un point est toujours rangé en
        premier). Une relation identique déjà présente n'est pas ajoutée deux
        fois : son identifiant est renvoyé.
        """
        if len(set(entites)) != len(entites):
            raise RelationImpossible("Choisissez des entités différentes.")
        genres = tuple(sorted(self.genre_entite(e) for e in entites))
        if genres not in _COMBINAISONS[genre]:
            raise RelationImpossible(_message_refus(genre))
        rangees = sorted(entites, key=lambda e: 0 if self.genre_entite(e) == "point" else 1)
        for relation in self.relations.values():
            if relation.genre == genre and sorted(relation.entites) == sorted(rangees):
                return relation.id
        self._compteurs["R"] += 1
        identifiant = f"R{self._compteurs['R']}"
        self.relations[identifiant] = Relation(identifiant, genre, rangees)
        return identifiant

    def relations_de(self, identifiant: str) -> list[str]:
        """Relations qui concernent une entité."""
        return [r.id for r in self.relations.values() if identifiant in r.entites]

    def supprimer_relation(self, identifiant: str) -> None:
        if identifiant not in self.relations:
            raise EntiteInconnue(identifiant)
        del self.relations[identifiant]

    def _retirer_relations_de(self, identifiant: str) -> list[str]:
        """Retire les relations et les cotes qui concernent une entité."""
        retirees = self.relations_de(identifiant)
        for relation in retirees:
            del self.relations[relation]
        cotes = self.cotes_de(identifiant)
        for cote in cotes:
            del self.cotes[cote]
        return retirees + cotes

    # --- Modification ---

    def basculer_construction(self, identifiant: str) -> None:
        """Passe une entité en construction ou l'en retire (ESQ-08)."""
        entite = self[identifiant]
        entite.construction = not entite.construction

    def deplacer_point(self, identifiant: str, x: float, y: float) -> None:
        if identifiant == ORIGINE:
            return  # l'origine ne bouge jamais
        p = self.point(identifiant)
        p.x, p.y = float(x), float(y)

    # --- Cotes (COT-01, COT-05) ---

    def ajouter_cote(
        self,
        genre: GenreCote,
        *entites: str,
        valeur: float | None = None,
        pilotee: bool = False,
    ) -> str:
        """Ajoute une cote ; sans valeur, elle prend la mesure actuelle (comme à la pose
        dans SolidWorks, avant que l'utilisateur ne tape la valeur voulue)."""
        if len(set(entites)) != len(entites):
            raise CoteImpossible("Choisissez des entités différentes.")
        genres = tuple(sorted(self.genre_entite(e) for e in entites))
        if genres not in _COMBINAISONS_COTES[genre]:
            raise CoteImpossible(_message_refus_cote(genre))
        rangees = sorted(entites, key=lambda e: 0 if self.genre_entite(e) == "point" else 1)
        self._compteurs["D"] += 1
        identifiant = f"D{self._compteurs['D']}"
        cote = Cote(identifiant, genre, rangees, 0.0, pilotee)
        from cao.esquisse.mesures import lignes_paralleles, mesurer_cote

        if genres == ("ligne", "ligne"):
            paralleles = lignes_paralleles(self, rangees[0], rangees[1])
            if genre == GenreCote.DISTANCE and not paralleles:
                self._compteurs["D"] -= 1
                raise CoteImpossible(
                    "Une distance entre deux lignes demande des lignes parallèles ; "
                    "pour deux lignes sécantes, cotez l'angle."
                )
            if genre == GenreCote.ANGLE and paralleles:
                self._compteurs["D"] -= 1
                raise CoteImpossible(
                    "Deux lignes parallèles n'ont pas d'angle : cotez la distance entre elles."
                )

        mesure = mesurer_cote(self, cote)
        cote.valeur = mesure if valeur is None else verifier_valeur(genre, valeur)
        self.cotes[identifiant] = cote
        return identifiant

    def modifier_cote(self, identifiant: str, valeur: float) -> None:
        """Nouvelle valeur d'une cote (la géométrie suit à la prochaine résolution)."""
        cote = self.cotes.get(identifiant)
        if cote is None:
            raise EntiteInconnue(identifiant)
        cote.valeur = verifier_valeur(cote.genre, valeur)

    def cotes_de(self, identifiant: str) -> list[str]:
        return [c.id for c in self.cotes.values() if identifiant in c.entites]

    def supprimer_cote(self, identifiant: str) -> None:
        if identifiant not in self.cotes:
            raise EntiteInconnue(identifiant)
        del self.cotes[identifiant]

    def supprimer(self, identifiant: str) -> list[str]:
        """Supprime une entité ; renvoie tout ce qui a été supprimé.

        Supprimer un point supprime les courbes qui s'en servent. Supprimer une
        courbe supprime ses points devenus inutiles (non partagés).
        """
        entite = self[identifiant]
        # Une relation sans son entité n'a plus de sens : elle part avec elle.
        supprimes: list[str] = self._retirer_relations_de(identifiant)
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
                retires += self._retirer_relations_de(identifiant)
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
            "relations": [
                {"id": r.id, "genre": r.genre.value, "entites": list(r.entites)}
                for r in self.relations.values()
            ],
            "cotes": [
                {
                    "id": c.id,
                    "genre": c.genre.value,
                    "entites": list(c.entites),
                    "valeur": c.valeur,
                    "pilotee": c.pilotee,
                }
                for c in self.cotes.values()
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
        for brut in donnees.get("relations", []):
            relation = Relation(brut["id"], GenreRelation(brut["genre"]), list(brut["entites"]))
            esquisse.relations[relation.id] = relation
            esquisse._compteurs["R"] = max(esquisse._compteurs["R"], int(relation.id[1:]))
        for brut in donnees.get("cotes", []):
            cote = Cote(
                brut["id"],
                GenreCote(brut["genre"]),
                list(brut["entites"]),
                float(brut["valeur"]),
                bool(brut.get("pilotee", False)),
            )
            esquisse.cotes[cote.id] = cote
            esquisse._compteurs["D"] = max(esquisse._compteurs["D"], int(cote.id[1:]))
        return esquisse


# Combinaisons d'entités acceptées par chaque relation (genres triés par ordre alphabétique).
_COMBINAISONS: dict[GenreRelation, set[tuple[str, ...]]] = {
    GenreRelation.HORIZONTALE: {("ligne",), ("point", "point")},
    GenreRelation.VERTICALE: {("ligne",), ("point", "point")},
    GenreRelation.COINCIDENTE: {("point", "point"), ("ligne", "point"), ("courbe", "point")},
    GenreRelation.POINT_MILIEU: {("ligne", "point")},
    GenreRelation.FIXE: {("point",)},
    GenreRelation.PARALLELE: {("ligne", "ligne")},
    GenreRelation.PERPENDICULAIRE: {("ligne", "ligne")},
    GenreRelation.COLINEAIRE: {("ligne", "ligne")},
    GenreRelation.TANGENTE: {("courbe", "ligne"), ("courbe", "courbe")},
    GenreRelation.CONCENTRIQUE: {("courbe", "courbe")},
    GenreRelation.EGALE: {("ligne", "ligne"), ("courbe", "courbe")},
}

_ATTENDU: dict[GenreRelation, str] = {
    GenreRelation.HORIZONTALE: "une ligne ou deux points",
    GenreRelation.VERTICALE: "une ligne ou deux points",
    GenreRelation.COINCIDENTE: "deux points, ou un point et une courbe",
    GenreRelation.POINT_MILIEU: "un point et une ligne",
    GenreRelation.FIXE: "un point",
    GenreRelation.PARALLELE: "deux lignes",
    GenreRelation.PERPENDICULAIRE: "deux lignes",
    GenreRelation.COLINEAIRE: "deux lignes",
    GenreRelation.TANGENTE: "une ligne et un arc ou cercle, ou deux arcs ou cercles",
    GenreRelation.CONCENTRIQUE: "deux arcs ou cercles",
    GenreRelation.EGALE: "deux lignes, ou deux arcs ou cercles",
}


def _message_refus(genre: GenreRelation) -> str:
    nom = genre.value.replace("_", " ")
    return f"La relation « {nom} » demande {_ATTENDU[genre]}."


_COMBINAISONS_COTES: dict[GenreCote, set[tuple[str, ...]]] = {
    GenreCote.LONGUEUR: {("ligne",), ("point", "point")},
    GenreCote.HORIZONTALE: {("ligne",), ("point", "point")},
    GenreCote.VERTICALE: {("ligne",), ("point", "point")},
    GenreCote.DISTANCE: {("ligne", "point"), ("ligne", "ligne")},
    GenreCote.ANGLE: {("ligne", "ligne")},
    GenreCote.RAYON: {("courbe",)},
    GenreCote.DIAMETRE: {("courbe",)},
}

_ATTENDU_COTES: dict[GenreCote, str] = {
    GenreCote.LONGUEUR: "une ligne ou deux points",
    GenreCote.HORIZONTALE: "une ligne ou deux points",
    GenreCote.VERTICALE: "une ligne ou deux points",
    GenreCote.DISTANCE: "un point et une ligne, ou deux lignes parallèles",
    GenreCote.ANGLE: "deux lignes",
    GenreCote.RAYON: "un arc ou un cercle",
    GenreCote.DIAMETRE: "un arc ou un cercle",
}


def _message_refus_cote(genre: GenreCote) -> str:
    return f"Une cote « {genre.value} » demande {_ATTENDU_COTES[genre]}."


def verifier_valeur(genre: GenreCote, valeur: float) -> float:
    """Valeur acceptable pour une cote ; CoteImpossible avec un message clair sinon."""
    valeur = float(valeur)
    if not math.isfinite(valeur):
        raise CoteImpossible("La valeur doit être un nombre.")
    if genre == GenreCote.ANGLE:
        if not 0 < valeur < 180:
            raise CoteImpossible("Un angle doit être compris entre 0 et 180°.")
    elif genre in (GenreCote.HORIZONTALE, GenreCote.VERTICALE, GenreCote.DISTANCE):
        if valeur < 0:
            raise CoteImpossible("Une distance ne peut pas être négative.")
    elif valeur <= TOLERANCE:
        raise CoteImpossible("La valeur doit être strictement positive.")
    return valeur
