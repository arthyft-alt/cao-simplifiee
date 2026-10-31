"""Pont entre l'esquisse et le solveur de contraintes python-solvespace (REL-01 à REL-05).

`resoudre(esquisse)` traduit points, courbes et relations en équations, les fait
résoudre, puis recopie les positions et rayons calculés dans l'esquisse.

Il renvoie aussi l'état de l'esquisse (ESQ-07) :
    sous-contrainte      il reste des degrés de liberté (affichée en bleu) ;
    totalement contrainte  plus rien ne peut bouger (en noir) ;
    sur-contrainte       relations en conflit (en rouge) : l'esquisse n'est pas
                         modifiée et les relations en cause sont désignées.

Particularités de python-solvespace prises en compte (essais du 2026-10-31) :
    - arcs et cercles demandent une normale 3D, créée dans le groupe fixe ;
    - « point sur un arc » n'existe pas : on impose centre→point = centre→début ;
    - la tangence ligne / cercle n'existe pas sans extrémité commune : on ajoute
      un point d'appui invisible, sur les deux courbes, avec le rayon
      perpendiculaire à la ligne (ou les deux rayons alignés pour deux cercles) ;
    - une entité refusée par le solveur ne lève pas d'erreur (simple message) :
      on vérifie donc après chaque relation qu'elle a bien été ajoutée.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from python_solvespace import ResultFlag, SolverSystem

from cao.esquisse.esquisse import (
    ORIGINE,
    Arc,
    Cercle,
    Cote,
    Esquisse,
    GenreCote,
    GenreRelation,
    Ligne,
    Point,
    Relation,
)
from cao.esquisse.geometrie import TOLERANCE, Point2D, distance
from cao.esquisse.mesures import angle_interieur, mesurer_cote


class EtatEsquisse(Enum):
    SOUS_CONTRAINTE = "sous-contrainte"
    TOTALEMENT_CONTRAINTE = "totalement contrainte"
    SUR_CONTRAINTE = "sur-contrainte"


@dataclass
class Resultat:
    etat: EtatEsquisse
    degres_de_liberte: int  # -1 si la résolution a échoué
    conflits: list[str] = field(default_factory=list)  # relations en cause
    message: str = ""

    @property
    def reussi(self) -> bool:
        return self.etat != EtatEsquisse.SUR_CONTRAINTE


class ErreurInterneSolveur(RuntimeError):
    """Le solveur a refusé une contrainte qui aurait dû être acceptée (défaut du logiciel)."""


class _Traduction:
    """Système d'équations construit à partir d'une esquisse."""

    def __init__(self, esquisse: Esquisse) -> None:
        self.esquisse = esquisse
        self.s = SolverSystem()
        self.plan = self.s.create_2d_base()
        self.normale = self.s.add_normal_3d(1.0, 0.0, 0.0, 0.0)  # groupe fixe
        origine = self.s.add_point_2d(0.0, 0.0, self.plan)  # groupe fixe : ne bouge jamais
        self.s.set_group(2)
        self.points: dict[str, Any] = {ORIGINE: origine}
        self.courbes: dict[str, Any] = {}
        self.rayons: dict[str, Any] = {}  # cercle -> entité « distance » du rayon
        self.proprietaire: dict[int, str] = {}  # numéro de contrainte -> relation

        for entite in esquisse.entites.values():
            if isinstance(entite, Point):
                self.points[entite.id] = self.s.add_point_2d(entite.x, entite.y, self.plan)
        for entite in esquisse.entites.values():
            if isinstance(entite, Ligne):
                self.courbes[entite.id] = self.s.add_line_2d(
                    self.points[entite.debut], self.points[entite.fin], self.plan
                )
            elif isinstance(entite, Cercle):
                rayon = self.s.add_distance(entite.rayon, self.plan)
                self.rayons[entite.id] = rayon
                self.courbes[entite.id] = self.s.add_circle(
                    self.normale, self.points[entite.centre], rayon, self.plan
                )
            elif isinstance(entite, Arc):
                self.courbes[entite.id] = self.s.add_arc(
                    self.normale,
                    self.points[entite.centre],
                    self.points[entite.debut],
                    self.points[entite.fin],
                    self.plan,
                )

    # --- Aides ---

    def _ligne_aide(self, a: Any, b: Any) -> Any:
        """Ligne invisible servant seulement au calcul."""
        return self.s.add_line_2d(a, b, self.plan)

    def _point_aide(self, position: Point2D) -> Any:
        return self.s.add_point_2d(position.x, position.y, self.plan)

    def _centre(self, courbe: str) -> str:
        entite = self.esquisse[courbe]
        assert isinstance(entite, Cercle | Arc)
        return entite.centre

    def _point_sur(self, point: Any, courbe: str) -> None:
        entite = self.esquisse[courbe]
        if isinstance(entite, Arc):
            centre = self.points[entite.centre]
            self.s.equal(
                self._ligne_aide(centre, point),
                self._ligne_aide(centre, self.points[entite.debut]),
                self.plan,
            )
        else:
            self.s.coincident(point, self.courbes[courbe], self.plan)

    def _extremites(self, courbe: str) -> set[str]:
        entite = self.esquisse[courbe]
        if isinstance(entite, Ligne | Arc):
            return {entite.debut, entite.fin}
        return set()

    # --- Relations ---

    def ajouter(self, element: Relation | Cote) -> None:
        """Ajoute une relation ou une cote pilotante, en notant ses numéros de contrainte."""
        avant = self.s.cons_len()
        if isinstance(element, Relation):
            self._traduire(element)
        else:
            self._traduire_cote(element)
        apres = self.s.cons_len()
        if apres == avant:
            raise ErreurInterneSolveur(f"{element.id} refusée par le solveur")
        for numero in range(avant + 1, apres + 1):
            self.proprietaire[numero] = element.id

    # --- Cotes (COT-01) ---

    def _deux_points(self, cote: Cote) -> tuple[str, str]:
        if len(cote.entites) == 1:
            ligne = self.esquisse[cote.entites[0]]
            assert isinstance(ligne, Ligne)
            return ligne.debut, ligne.fin
        return cote.entites[0], cote.entites[1]

    def _ecart_aligne(self, a: str, b: str, valeur: float, horizontal: bool) -> None:
        """Écart horizontal (ou vertical) entre deux points, par un point d'aide
        aligné horizontalement sur a et verticalement sur b (ou l'inverse)."""
        pa, pb = self.esquisse.position(a), self.esquisse.position(b)
        if valeur < TOLERANCE:
            aide = self._ligne_aide(self.points[a], self.points[b])
            (self.s.vertical if horizontal else self.s.horizontal)(aide, self.plan)
            return
        coin = Point2D(pb.x, pa.y) if horizontal else Point2D(pa.x, pb.y)
        if distance(coin, pa) < TOLERANCE:  # départ dégénéré : on écarte un peu le point d'aide
            coin = Point2D(pa.x + valeur, pa.y) if horizontal else Point2D(pa.x, pa.y + valeur)
        aide = self._point_aide(coin)
        cote_aide = self._ligne_aide(self.points[a], aide)
        rappel = self._ligne_aide(aide, self.points[b])
        if horizontal:
            self.s.horizontal(cote_aide, self.plan)
            self.s.vertical(rappel, self.plan)
        else:
            self.s.vertical(cote_aide, self.plan)
            self.s.horizontal(rappel, self.plan)
        self.s.distance(self.points[a], aide, valeur, self.plan)

    def _a_gauche(self, point: str, ligne: str) -> bool:
        """Le point est-il à gauche de la ligne, dans son sens de tracé ?"""
        entite = self.esquisse[ligne]
        assert isinstance(entite, Ligne)
        a, b = self.esquisse.position(entite.debut), self.esquisse.position(entite.fin)
        p = self.esquisse.position(point)
        return (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x) > 0

    def _traduire_cote(self, cote: Cote) -> None:
        s, plan, g, v = self.s, self.plan, cote.genre, cote.valeur
        if g == GenreCote.LONGUEUR:
            a, b = self._deux_points(cote)
            s.distance(self.points[a], self.points[b], v, plan)
        elif g in (GenreCote.HORIZONTALE, GenreCote.VERTICALE):
            a, b = self._deux_points(cote)
            self._ecart_aligne(a, b, v, horizontal=g == GenreCote.HORIZONTALE)
        elif g == GenreCote.DISTANCE:
            premiere, seconde = cote.entites
            if self.esquisse.genre_entite(premiere) == "point":
                point = premiere
            else:
                autre = self.esquisse[premiere]
                assert isinstance(autre, Ligne)
                point = autre.debut
            # Distance signée pour le solveur : positive = à droite du sens de tracé
            # (essai du 2026-10-31). On garde le point du côté où il a été dessiné.
            signe = -1.0 if self._a_gauche(point, seconde) else 1.0
            s.distance(self.points[point], self.courbes[seconde], signe * v, plan)
        elif g == GenreCote.ANGLE:
            l1, l2 = cote.entites
            _actuel, meme_sens = angle_interieur(self.esquisse, l1, l2)
            # Le solveur mesure l'angle entre les sens de tracé des lignes.
            s.angle(self.courbes[l1], self.courbes[l2], v if meme_sens else 180.0 - v, plan)
        else:
            diametre = 2 * v if g == GenreCote.RAYON else v
            s.diameter(self.courbes[cote.entites[0]], diametre)  # pas de plan pour cette cote

    def _traduire(self, relation: Relation) -> None:
        s, plan, g = self.s, self.plan, relation.genre
        ids = relation.entites
        if g == GenreRelation.HORIZONTALE:
            s.horizontal(self.courbes[ids[0]], plan)
        elif g == GenreRelation.VERTICALE:
            s.vertical(self.courbes[ids[0]], plan)
        elif g == GenreRelation.FIXE:
            s.dragged(self.points[ids[0]], plan)
        elif g == GenreRelation.COINCIDENTE:
            if self.esquisse.genre_entite(ids[1]) == "point":
                s.coincident(self.points[ids[0]], self.points[ids[1]], plan)
            else:
                self._point_sur(self.points[ids[0]], ids[1])
        elif g == GenreRelation.POINT_MILIEU:
            s.midpoint(self.points[ids[0]], self.courbes[ids[1]], plan)
        elif g == GenreRelation.PARALLELE:
            s.parallel(self.courbes[ids[0]], self.courbes[ids[1]], plan)
        elif g == GenreRelation.PERPENDICULAIRE:
            s.perpendicular(self.courbes[ids[0]], self.courbes[ids[1]], plan)
        elif g == GenreRelation.COLINEAIRE:
            s.parallel(self.courbes[ids[0]], self.courbes[ids[1]], plan)
            seconde = self.esquisse[ids[1]]
            assert isinstance(seconde, Ligne)
            s.coincident(self.points[seconde.debut], self.courbes[ids[0]], plan)
        elif g == GenreRelation.CONCENTRIQUE:
            s.coincident(self.points[self._centre(ids[0])], self.points[self._centre(ids[1])], plan)
        elif g == GenreRelation.EGALE:
            s.equal(self.courbes[ids[0]], self.courbes[ids[1]], plan)
        elif g == GenreRelation.TANGENTE:
            self._tangente(ids[0], ids[1])

    def _tangente(self, a: str, b: str) -> None:
        if self.esquisse.genre_entite(a) == "ligne":
            a, b = b, a  # a : la courbe ; b : la ligne ou la seconde courbe
        arcs_relies = (
            isinstance(self.esquisse[a], Arc)
            and self._extremites(a) & self._extremites(b)
            and (self.esquisse.genre_entite(b) == "ligne" or isinstance(self.esquisse[b], Arc))
        )
        if arcs_relies:
            # Cas natif du solveur : tangence à une extrémité commune.
            self.s.tangent(self.courbes[a], self.courbes[b], self.plan)
            return
        centre_a = self.esquisse.position(self._centre(a))
        rayon_a = self.esquisse.rayon(a)
        if self.esquisse.genre_entite(b) == "ligne":
            ligne = self.esquisse[b]
            assert isinstance(ligne, Ligne)
            pied = _projection(
                centre_a, self.esquisse.position(ligne.debut), self.esquisse.position(ligne.fin)
            )
            appui = self._point_aide(_vers(centre_a, pied, rayon_a))
            self._point_sur(appui, a)
            self.s.coincident(appui, self.courbes[b], self.plan)
            rayon_aide = self._ligne_aide(self.points[self._centre(a)], appui)
            self.s.perpendicular(rayon_aide, self.courbes[b], self.plan)
        else:
            centre_b = self.esquisse.position(self._centre(b))
            appui = self._point_aide(_vers(centre_a, centre_b, rayon_a))
            self._point_sur(appui, a)
            self._point_sur(appui, b)
            self.s.parallel(
                self._ligne_aide(self.points[self._centre(a)], appui),
                self._ligne_aide(self.points[self._centre(b)], appui),
                self.plan,
            )

    # --- Résultat ---

    def recopier(self) -> None:
        for identifiant, poignee in self.points.items():
            x, y = self.s.params(poignee.params)
            self.esquisse.deplacer_point(identifiant, x, y)
        for identifiant, rayon in self.rayons.items():
            cercle = self.esquisse[identifiant]
            assert isinstance(cercle, Cercle)
            cercle.rayon = abs(self.s.params(rayon.params)[0])


def _projection(p: Point2D, a: Point2D, b: Point2D) -> Point2D:
    """Pied de la perpendiculaire abaissée de p sur la droite (a, b)."""
    ab = b - a
    longueur2 = ab.x**2 + ab.y**2
    t = ((p.x - a.x) * ab.x + (p.y - a.y) * ab.y) / longueur2 if longueur2 else 0.0
    return a + ab.fois(t)


def _vers(depuis: Point2D, cible: Point2D, longueur: float) -> Point2D:
    """Point à `longueur` de `depuis`, en direction de `cible` (estimation de départ)."""
    d = distance(depuis, cible)
    if d < 1e-9:
        return Point2D(depuis.x + longueur, depuis.y)
    return depuis + (cible - depuis).fois(longueur / d)


def resoudre(esquisse: Esquisse) -> Resultat:
    """Résout l'esquisse en place ; ne la modifie pas si les relations sont en conflit."""
    traduction = _Traduction(esquisse)
    for relation in esquisse.relations.values():
        traduction.ajouter(relation)
    for cote in esquisse.cotes.values():
        if not cote.pilotee:  # une cote de référence ne fait que mesurer
            traduction.ajouter(cote)
    resultat = traduction.s.solve()
    if resultat == ResultFlag.OKAY:
        traduction.recopier()
        for cote in esquisse.cotes.values():
            if cote.pilotee:
                cote.valeur = mesurer_cote(esquisse, cote)
        ddl = traduction.s.dof()
        etat = EtatEsquisse.TOTALEMENT_CONTRAINTE if ddl == 0 else EtatEsquisse.SOUS_CONTRAINTE
        return Resultat(etat, ddl)
    conflits = sorted(
        {
            traduction.proprietaire[n]
            for n in traduction.s.failures()
            if n in traduction.proprietaire
        },
        key=lambda e: (e[0], int(e[1:])),  # relations R… puis cotes D…
    )
    # Le solveur répond « incohérent » ou « n'a pas convergé » selon les cas (deux lignes
    # parallèles ET perpendiculaires donnent le second) ; s'il désigne des relations, on les cite.
    if conflits:
        message = "Relations en conflit : " + ", ".join(conflits)
    elif resultat == ResultFlag.INCONSISTENT:
        message = "Relations en conflit."
    else:
        message = "Le calcul n'a pas abouti : essayez de retirer la dernière relation ajoutée."
    return Resultat(EtatEsquisse.SUR_CONTRAINTE, -1, conflits, message)


def angle_entre_lignes(esquisse: Esquisse, l1: str, l2: str) -> float:
    """Angle (degrés, 0 à 90) entre deux lignes : utile aux tests et à la cotation."""
    a, b = esquisse[l1], esquisse[l2]
    assert isinstance(a, Ligne) and isinstance(b, Ligne)
    da = esquisse.position(a.fin) - esquisse.position(a.debut)
    db = esquisse.position(b.fin) - esquisse.position(b.debut)
    cosinus = abs(da.x * db.x + da.y * db.y) / (da.norme() * db.norme())
    return math.degrees(math.acos(min(1.0, cosinus)))
