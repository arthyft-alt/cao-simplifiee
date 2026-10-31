"""Mode esquisse d'une fenêtre de pièce (ESQ-01, ESQ-02, ESQ-03, ESQ-07, GEO-01 à 04).

Le contrôleur reçoit les clics de la vue 3D, les convertit en coordonnées du
plan d'esquisse, accroche les points proches, transmet le clic à l'outil actif,
et exécute les tracés sous forme de commandes annulables (Ctrl+Z). Après chaque
modification, l'esquisse est résolue et redessinée avec la couleur de son état.

Sans vue 3D (tests automatiques), tout fonctionne sauf l'affichage : les tests
appellent directement `clic_plan` avec des coordonnées du plan.
"""

from collections.abc import Callable
from typing import Protocol

from PySide6.QtCore import QObject, Qt, Signal

from cao.document.document import Document
from cao.esquisse.aimants import Aimantation, aimanter
from cao.esquisse.esquisse import ORIGINE, Esquisse, RelationImpossible
from cao.esquisse.geometrie import GeometrieImpossible, Point2D, distance
from cao.esquisse.outils import OUTILS, Clic, Outil
from cao.esquisse.plans import PLANS
from cao.esquisse.solveur import EtatEsquisse, Resultat, resoudre
from cao.ihm import textes
from cao.noyau import esquisse_3d
from cao.noyau.affichage import VueStandard, centrer_sur_origine, orienter
from cao.noyau.esquisse_3d import AffichageEsquisse, Teinte
from cao.piece.piece import CommandeAjouterEsquisse, CommandeEsquisse, Piece

ACCROCHE_PIXELS = 10  # un clic à moins de 10 pixels d'un point s'y accroche
VUE_DU_PLAN = {"face": VueStandard.FACE, "dessus": VueStandard.DESSUS, "droite": VueStandard.DROITE}
TEINTE_ETAT = {
    EtatEsquisse.SOUS_CONTRAINTE: Teinte.SOUS_CONTRAINTE,
    EtatEsquisse.TOTALEMENT_CONTRAINTE: Teinte.TOTALEMENT_CONTRAINTE,
    EtatEsquisse.SUR_CONTRAINTE: Teinte.SUR_CONTRAINTE,
}


class VueOcc(Protocol):
    """Ce dont le mode esquisse a besoin de la vue 3D (Vue3D le fournit)."""

    @property
    def prete(self) -> bool: ...
    @property
    def contexte(self) -> object: ...
    @property
    def vue_occ(self) -> object: ...


class ModeEsquisse(QObject):
    actif_change = Signal(bool)
    etat_change = Signal(str)  # texte de la pastille d'état
    consigne = Signal(str)  # aide affichée dans la barre d'état
    message = Signal(str)  # erreur ou information ponctuelle
    esquisses_changees = Signal()  # pour mettre à jour l'arbre

    def __init__(self, document: Document, vue: VueOcc | None = None) -> None:
        super().__init__()
        assert isinstance(document.modele, Piece)
        self.document = document
        self.piece: Piece = document.modele
        self.vue = vue
        self.esquisse: Esquisse | None = None
        self.outil: Outil | None = None
        self.resultat: Resultat | None = None
        self.affichages: dict[int, AffichageEsquisse] = {}  # id(esquisse) -> objets affichés
        self.affichage_apercu = AffichageEsquisse()
        self.affichage_aimant = AffichageEsquisse()
        document.historique.abonner(self._historique_change)

    # --- État ---

    @property
    def actif(self) -> bool:
        return self.esquisse is not None

    def _affichable(self) -> bool:
        return self.vue is not None and self.vue.prete

    # --- Entrer / quitter (ESQ-01, ESQ-02, ESQ-03) ---

    def entrer(self, plan: str | None = None, esquisse: Esquisse | None = None) -> Esquisse:
        """Crée une esquisse sur un plan, ou rouvre une esquisse existante."""
        if self.actif:
            self.quitter()
        if esquisse is None:
            assert plan in PLANS
            esquisse = Esquisse(self.piece.nom_esquisse_suivant(), plan)
            self.document.historique.executer(CommandeAjouterEsquisse(self.piece, esquisse))
        self.esquisse = esquisse
        self.outil = None
        self.resultat = resoudre(esquisse)
        if self._affichable():
            orienter(self.vue.vue_occ, VUE_DU_PLAN[esquisse.plan])  # type: ignore[union-attr,arg-type]
            if not any(e.courbes() for e in self.piece.esquisses):
                centrer_sur_origine(self.vue.vue_occ)  # type: ignore[union-attr,arg-type]
        self.redessiner()
        self.actif_change.emit(True)
        self._publier_etat()
        self.consigne.emit(textes.CONSIGNE_SANS_OUTIL)
        return esquisse

    def quitter(self) -> None:
        if not self.actif:
            return
        self.outil = None
        self._effacer_apercu()
        self.esquisse = None
        self.resultat = None
        self.redessiner()
        self.actif_change.emit(False)
        self.etat_change.emit(textes.ETAT_PAS_D_ESQUISSE)
        self.consigne.emit("")

    # --- Outils ---

    def choisir_outil(self, nom: str) -> None:
        self.outil = OUTILS[nom]()
        self._effacer_apercu()
        self._publier_consigne()

    def _publier_consigne(self) -> None:
        if self.outil is None:
            self.consigne.emit(textes.CONSIGNE_SANS_OUTIL)
            return
        etapes = textes.CONSIGNES_OUTILS[self.outil.nom]
        self.consigne.emit(etapes[min(self.outil.etape, len(etapes) - 1)])

    def aimanter(self, position: Point2D, tolerance: float) -> Aimantation:
        """Position corrigée par les aimants : points, horizontale/verticale, repère."""
        assert self.esquisse is not None
        depart = self.outil.point_de_depart() if self.outil is not None else None
        return aimanter(self.esquisse, position, tolerance, depart)

    def accroche(self, position: Point2D, tolerance: float) -> str | None:
        """Point existant (ou origine) le plus proche, s'il est à moins de `tolerance` mm."""
        if self.esquisse is None:
            return None
        candidats = [p.id for p in self.esquisse.points()] + [ORIGINE]
        meilleur = min(candidats, key=lambda i: distance(self.esquisse.position(i), position))  # type: ignore[union-attr]
        return (
            meilleur if distance(self.esquisse.position(meilleur), position) <= tolerance else None
        )

    def clic_plan(self, position: Point2D, tolerance: float = 0.5) -> None:
        """Clic sur le plan d'esquisse (coordonnées en mm)."""
        if self.esquisse is None or self.outil is None:
            return
        aimant = self.aimanter(position, tolerance)
        modification = self.outil.clic(
            Clic(aimant.position, aimant.accroche, aimant.sur_axe, aimant.orientation)
        )
        erreur = None
        if modification is not None:
            erreur = self._executer(textes.libelle_trace(self.outil.nom), modification, self.outil)
        self._publier_consigne()
        if erreur is not None:  # après la consigne, sinon elle effacerait aussitôt le message
            self.message.emit(erreur)

    def _executer(
        self, libelle: str, modification: Callable[[Esquisse], object], outil: Outil | None = None
    ) -> str | None:
        """Exécute une modification annulable ; renvoie le message d'erreur éventuel."""
        assert self.esquisse is not None

        def puis_resoudre(esquisse: Esquisse) -> object:
            resultat = modification(esquisse)
            self.resultat = resoudre(esquisse)
            return resultat

        commande = CommandeEsquisse(self.esquisse, libelle, puis_resoudre)
        try:
            self.document.historique.executer(commande)
        except (GeometrieImpossible, RelationImpossible) as erreur:
            if outil is not None:
                outil.abandonner()
            return str(erreur)
        if outil is not None:
            outil.applique(self.esquisse, commande.resultat)
        return None

    def supprimer(self, identifiants: list[str]) -> None:
        """Supprime des entités de l'esquisse (touche Suppr), en une seule étape annulable."""
        if self.esquisse is None:
            return
        a_supprimer = [i for i in identifiants if i != ORIGINE]
        if not a_supprimer:
            return

        def modification(esquisse: Esquisse) -> None:
            for identifiant in a_supprimer:
                if identifiant in esquisse.entites:
                    esquisse.supprimer(identifiant)

        erreur = self._executer(textes.SUPPRIMER_ENTITES, modification)
        if erreur is not None:
            self.message.emit(erreur)

    def echap(self) -> bool:
        """Échap : abandonne le tracé en cours, puis l'outil, puis quitte l'esquisse."""
        if not self.actif:
            return False
        if self.outil is not None and self.outil.en_cours:
            self.outil.abandonner()
            self._effacer_apercu()
        elif self.outil is not None:
            self.outil = None
            self._effacer_apercu()
        else:
            self.quitter()
            return True
        self._publier_consigne()
        return True

    def terminer_trace(self) -> None:
        """Double-clic ou clic droit : termine une suite de lignes."""
        if self.outil is not None:
            self.outil.terminer()
            self._effacer_apercu()
            self._publier_consigne()

    # --- Événements de la vue 3D (pixels réels) ---

    def _vers_plan(self, x: int, y: int) -> Point2D | None:
        if self.esquisse is None or not self._affichable():
            return None
        return esquisse_3d.point_sur_plan(self.vue.vue_occ, x, y, PLANS[self.esquisse.plan])  # type: ignore[union-attr,arg-type]

    def clic_ecran(self, x: int, y: int) -> bool:
        """Clic gauche dans la vue ; True si le mode esquisse l'a utilisé."""
        if self.outil is None:
            return False  # pas d'outil : le clic sert à sélectionner
        position = self._vers_plan(x, y)
        if position is not None:
            tolerance = ACCROCHE_PIXELS * esquisse_3d.taille_pixel(self.vue.vue_occ)  # type: ignore[union-attr,arg-type]
            self.clic_plan(position, tolerance)
        return True

    def mouvement_ecran(self, x: int, y: int) -> None:
        """Survol : montre les aimants actifs et l'aperçu du tracé en cours."""
        if self.outil is None:
            return
        position = self._vers_plan(x, y)
        if position is None or self.esquisse is None:
            return
        tolerance = ACCROCHE_PIXELS * esquisse_3d.taille_pixel(self.vue.vue_occ)  # type: ignore[union-attr,arg-type]
        aimant = self.aimanter(position, tolerance)
        position = aimant.position
        self.affichage_aimant = esquisse_3d.afficher_aimant(
            self.vue.contexte,  # type: ignore[union-attr,arg-type]
            PLANS[self.esquisse.plan],
            aimant,
            self.affichage_aimant,
        )
        if not self.outil.en_cours:
            return
        self.affichage_apercu = esquisse_3d.afficher_apercu(
            self.vue.contexte,  # type: ignore[union-attr,arg-type]
            PLANS[self.esquisse.plan],
            self.outil.apercu(position),
            self.affichage_apercu,
        )

    def touche(self, cle: int) -> bool:
        if not self.actif:
            return False
        if cle == Qt.Key.Key_Escape:
            return self.echap()
        return False

    def entites_selectionnees(self, formes: list[object]) -> list[str]:
        """Identifiants des entités de l'esquisse active correspondant à des formes cliquées."""
        if self.esquisse is None:
            return []
        affichage = self.affichages.get(id(self.esquisse))
        if affichage is None:
            return []
        ids = [affichage.entite_de(f) for f in formes]  # type: ignore[arg-type]
        return [i for i in ids if i is not None]

    # --- Affichage ---

    def _effacer_apercu(self) -> None:
        if self._affichable():
            self.affichage_apercu.retirer(self.vue.contexte)  # type: ignore[union-attr,arg-type]
            self.affichage_aimant.retirer(self.vue.contexte)  # type: ignore[union-attr,arg-type]
            self.vue.contexte.UpdateCurrentViewer()  # type: ignore[union-attr]

    def redessiner(self) -> None:
        """Affiche toutes les esquisses : l'ouverte en couleur d'état, les autres en gris."""
        if not self._affichable():
            return
        contexte = self.vue.contexte  # type: ignore[union-attr]
        presentes = {id(e) for e in self.piece.esquisses}
        for cle in [c for c in self.affichages if c not in presentes]:
            self.affichages.pop(cle).retirer(contexte)  # type: ignore[arg-type]
        for esquisse in self.piece.esquisses:
            active = esquisse is self.esquisse
            if active and self.resultat is not None:
                teinte = TEINTE_ETAT[self.resultat.etat]
            else:
                teinte = Teinte.INACTIVE
            self.affichages[id(esquisse)] = esquisse_3d.afficher_esquisse(
                contexte,  # type: ignore[arg-type]
                esquisse,
                teinte,
                avec_points=active,
                affichage=self.affichages.get(id(esquisse)),
            )

    def _publier_etat(self) -> None:
        if self.esquisse is None or self.resultat is None:
            return
        if not self.esquisse.courbes():
            self.etat_change.emit(textes.esquisse_vide(self.esquisse.nom))
            return
        texte = textes.etat_esquisse(
            self.esquisse.nom, self.resultat.etat.value, max(self.resultat.degres_de_liberte, 0)
        )
        if self.resultat.conflits:
            texte += " — " + self.resultat.message
        self.etat_change.emit(texte)

    def _historique_change(self) -> None:
        """Après une modification, une annulation ou un rétablissement."""
        if self.esquisse is not None and self.esquisse not in self.piece.esquisses:
            self.quitter()  # l'esquisse ouverte a été annulée (Ctrl+Z sur sa création)
        if self.esquisse is not None:
            self.resultat = resoudre(self.esquisse)
            self._publier_etat()
        self.redessiner()
        self.esquisses_changees.emit()
