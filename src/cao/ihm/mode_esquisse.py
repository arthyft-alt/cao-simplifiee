"""Mode esquisse d'une fenêtre de pièce (ESQ-01, ESQ-02, ESQ-03, ESQ-07, GEO-01 à 04).

Le contrôleur reçoit les clics de la vue 3D, les convertit en coordonnées du
plan d'esquisse, accroche les points proches, transmet le clic à l'outil actif,
et exécute les tracés sous forme de commandes annulables (Ctrl+Z). Après chaque
modification, l'esquisse est résolue et redessinée avec la couleur de son état.

Sans vue 3D (tests automatiques), tout fonctionne sauf l'affichage : les tests
appellent directement `clic_plan` avec des coordonnées du plan.
"""

from collections.abc import Callable
from typing import Any, Protocol

from PySide6.QtCore import QObject, Qt, Signal

from cao.document.document import Document
from cao.document.unites import SaisieInvalide
from cao.esquisse.aimants import Aimantation, aimanter
from cao.esquisse.cotation import deduire_cote, deport_pour
from cao.esquisse.esquisse import (
    ORIGINE,
    Cote,
    CoteImpossible,
    Esquisse,
    GenreCote,
    RelationImpossible,
    verifier_valeur,
)
from cao.esquisse.geometrie import GeometrieImpossible, Point2D, distance
from cao.esquisse.mesures import mesurer_cote
from cao.esquisse.outils import OUTILS, Clic, Outil
from cao.esquisse.plans import PLANS
from cao.esquisse.proximite import entite_proche
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
        self.cotation = False  # outil « Cote » actif (cotation intelligente, 2.6)
        self.selection_cote: list[str] = []
        self.survol: str | None = None  # entité sous la souris (mise en évidence)
        self.apercu_cote: Cote | None = None  # cote qui suit la souris avant d'être placée
        self._dernier_curseur: Point2D | None = None
        self._tolerance = 0.5  # mm ; recalculée selon le zoom (10 pixels)
        # Fenêtre de saisie d'une valeur (titre, valeur proposée) -> texte tapé ou None.
        # Fournie par la fenêtre ; remplacée dans les tests.
        self.demander_valeur: Callable[[str, str], str | None] = lambda _t, _v: None
        self.resultat: Resultat | None = None
        self.affichages: dict[int, AffichageEsquisse] = {}  # id(esquisse) -> objets affichés
        self.affichage_apercu = AffichageEsquisse()
        self.affichage_aimant = AffichageEsquisse()
        self.affichage_surbrillance = AffichageEsquisse()
        self.affichage_apercu_cote = AffichageEsquisse()
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
        self._vider_cotation()
        self.cotation = False
        self._effacer_apercu()
        self.esquisse = None
        self.resultat = None
        self.redessiner()
        self.actif_change.emit(False)
        self.etat_change.emit(textes.ETAT_PAS_D_ESQUISSE)
        self.consigne.emit("")

    # --- Outils ---

    def choisir_outil(self, nom: str) -> None:
        self._vider_cotation()
        self.cotation = nom == "cote"
        self.outil = None if self.cotation else OUTILS[nom]()
        self._effacer_apercu()
        self._publier_consigne()

    def _publier_consigne(self) -> None:
        if self.cotation:
            etapes = textes.CONSIGNES_COTE
            self.consigne.emit(etapes[min(len(self.selection_cote), len(etapes) - 1)])
            return
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
        if self.cotation:
            if self.selection_cote:
                self._vider_cotation()
            else:
                self._vider_cotation()
                self.cotation = False
            self._publier_consigne()
            return True
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
        if self.cotation:
            position = self._vers_plan(x, y)
            if position is not None:
                self._tolerance = ACCROCHE_PIXELS * esquisse_3d.taille_pixel(self.vue.vue_occ)  # type: ignore[union-attr,arg-type]
                self.clic_cote(position)
            return True
        if self.outil is None:
            return False  # pas d'outil : le clic sert à sélectionner
        position = self._vers_plan(x, y)
        if position is not None:
            tolerance = ACCROCHE_PIXELS * esquisse_3d.taille_pixel(self.vue.vue_occ)  # type: ignore[union-attr,arg-type]
            self.clic_plan(position, tolerance)
        return True

    def mouvement_ecran(self, x: int, y: int) -> None:
        """Survol : montre les aimants actifs et l'aperçu du tracé en cours."""
        if self.cotation:
            position = self._vers_plan(x, y)
            if position is not None:
                self._tolerance = ACCROCHE_PIXELS * esquisse_3d.taille_pixel(self.vue.vue_occ)  # type: ignore[union-attr,arg-type]
                self.mouvement_cote(position)
            return
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

    def double_clic_ecran(self, x: int, y: int) -> None:
        """Double-clic : termine une suite de lignes, ou modifie la cote visée (COT-02)."""
        if self.outil is not None and self.outil.en_cours:
            self.terminer_trace()
            return
        cote = self._cote_sous(x, y)
        if cote is not None:
            self.modifier_cote(cote)

    # --- Cotation intelligente (COT-01, COT-02, COT-05) ---

    def texte_cote(self, cote: Cote) -> str:
        """Texte affiché sur la cote : « 80,00 mm », « Ø 20,00 mm », « R 5,00 mm », « 30,00° »,
        entre parenthèses pour une cote pilotée (de référence)."""
        unites = self.document.unites
        if cote.genre == GenreCote.ANGLE:
            texte = unites.formater_angle(cote.valeur)
        else:
            texte = unites.formater_longueur(cote.valeur)
            if cote.genre == GenreCote.DIAMETRE:
                texte = "Ø " + texte
            elif cote.genre == GenreCote.RAYON:
                texte = "R " + texte
        return f"({texte})" if cote.pilotee else texte

    def clic_cote(self, position: Point2D, tolerance: float | None = None) -> None:
        """Clic avec l'outil Cote : sur une entité, elle est sélectionnée ; dans le vide,
        la cote en cours est placée à cet endroit (comme dans SolidWorks)."""
        if self.esquisse is None:
            return
        if tolerance is not None:
            self._tolerance = tolerance
        entite = entite_proche(self.esquisse, position, self._tolerance)
        if entite is not None:
            self.clic_entite_cote(entite)
            self.mouvement_cote(position)
        else:
            self.placer_cote(position)

    def mouvement_cote(self, position: Point2D, tolerance: float | None = None) -> None:
        """Souris qui bouge avec l'outil Cote : mise en évidence de l'entité survolée,
        et cote d'aperçu qui suit la souris dès qu'une entité est sélectionnée."""
        if self.esquisse is None:
            return
        if tolerance is not None:
            self._tolerance = tolerance
        self._dernier_curseur = position
        self.survol = entite_proche(self.esquisse, position, self._tolerance)
        self.apercu_cote = None
        if self.selection_cote:
            try:
                genre, entites = deduire_cote(self.esquisse, self.selection_cote, position)
                apercu = Cote("apercu", genre, entites, 0.0)
                apercu.valeur = mesurer_cote(self.esquisse, apercu)
                apercu.deport = deport_pour(self.esquisse, genre, entites, position)
                self.apercu_cote = apercu
            except (CoteImpossible, ValueError):
                self.apercu_cote = None
        self._afficher_cotation()

    def clic_entite_cote(self, identifiant: str) -> None:
        """Ajoute (ou retire) une entité de la sélection à coter."""
        if identifiant in self.selection_cote:
            self.selection_cote.remove(identifiant)
        else:
            self.selection_cote = [*self.selection_cote, identifiant][-2:]
        self._publier_consigne()
        self._afficher_cotation()

    def _vider_cotation(self) -> None:
        self.selection_cote = []
        self.survol = None
        self.apercu_cote = None
        self._afficher_cotation()

    def _afficher_cotation(self) -> None:
        """Entités sélectionnées en bleu, entité survolée en orange, cote d'aperçu."""
        if not self._affichable() or self.esquisse is None:
            return
        assert self.vue is not None
        contexte: Any = self.vue.contexte
        teintes = [(i, Teinte.SELECTION) for i in self.selection_cote]
        if self.survol is not None and self.survol not in self.selection_cote:
            teintes.append((self.survol, Teinte.SURVOL))
        self.affichage_surbrillance = esquisse_3d.afficher_surbrillance(
            contexte,
            self.esquisse,
            teintes,
            self.affichage_surbrillance,
        )
        texte = self.texte_cote(self.apercu_cote) if self.apercu_cote is not None else ""
        self.affichage_apercu_cote = esquisse_3d.afficher_apercu_cote(
            contexte,
            self.esquisse,
            self.apercu_cote,
            texte,
            self.affichage_apercu_cote,
        )

    def placer_cote(self, curseur: Point2D | None = None) -> str | None:
        """Clic dans le vide : pose la cote déduite de la sélection, puis demande sa valeur."""
        if self.esquisse is None:
            return None
        selection = self.selection_cote
        self._vider_cotation()
        try:
            genre, entites = deduire_cote(self.esquisse, selection, curseur)
        except CoteImpossible as erreur:
            self._publier_consigne()
            self.message.emit(str(erreur))
            return None
        devenue_pilotee = False

        def poser(esquisse: Esquisse) -> str:
            nonlocal devenue_pilotee
            identifiant = esquisse.ajouter_cote(genre, *entites)
            if curseur is not None:  # la cote passe là où l'on a cliqué
                esquisse.cotes[identifiant].deport = deport_pour(esquisse, genre, entites, curseur)
            self.resultat = resoudre(esquisse)
            if not self.resultat.reussi:
                # L'esquisse était déjà contrainte : la cote devient « de référence » (COT-05).
                esquisse.cotes[identifiant].pilotee = devenue_pilotee = True
                self.resultat = resoudre(esquisse)
            return identifiant

        commande = CommandeEsquisse(self.esquisse, textes.LIBELLE_COTE, poser)
        try:
            self.document.historique.executer(commande)
        except CoteImpossible as erreur:
            self._publier_consigne()
            self.message.emit(str(erreur))
            return None
        identifiant = str(commande.resultat)
        self._publier_consigne()
        if devenue_pilotee:
            self.message.emit(textes.COTE_DEVENUE_PILOTEE)
        else:
            self.modifier_cote(identifiant)
        return identifiant

    def modifier_cote(self, identifiant: str) -> None:
        """Demande une nouvelle valeur ; la géométrie suit à la validation (COT-01, COT-02)."""
        if self.esquisse is None or identifiant not in self.esquisse.cotes:
            return
        cote = self.esquisse.cotes[identifiant]
        if cote.pilotee:
            self.message.emit(textes.COTE_PILOTEE_NON_MODIFIABLE)
            return
        unites = self.document.unites
        angle = cote.genre == GenreCote.ANGLE
        proposee = (
            textes.nombre_saisie(cote.valeur)
            if angle
            else unites.valeur_saisie_longueur(cote.valeur)
        )
        titre = textes.titre_saisie_cote(self.texte_cote(cote), unites.longueur.value, angle)
        texte = self.demander_valeur(titre, proposee)
        if texte is None:
            return
        try:
            valeur = unites.lire_angle(texte) if angle else unites.lire_longueur(texte)
            if cote.genre in (GenreCote.RAYON, GenreCote.DIAMETRE, GenreCote.LONGUEUR):
                verifier_valeur(cote.genre, valeur)
        except (SaisieInvalide, CoteImpossible) as erreur:
            self.message.emit(str(erreur))
            return

        def changer(esquisse: Esquisse) -> None:
            esquisse.modifier_cote(identifiant, valeur)
            self.resultat = resoudre(esquisse)
            if not self.resultat.reussi:
                raise CoteImpossible(textes.VALEUR_IMPOSSIBLE)

        commande = CommandeEsquisse(self.esquisse, textes.LIBELLE_MODIFIER_COTE, changer)
        try:
            self.document.historique.executer(commande)
        except CoteImpossible as erreur:
            self.resultat = resoudre(self.esquisse)
            self.message.emit(str(erreur))

    def _detecte(self, x: int, y: int) -> Any:
        """Contexte d'affichage après détection sous le curseur (pixels réels), ou None."""
        if not self._affichable():
            return None
        assert self.vue is not None
        contexte: Any = self.vue.contexte
        contexte.MoveTo(x, y, self.vue.vue_occ, False)
        return contexte if contexte.HasDetected() else None

    def _entite_sous(self, x: int, y: int) -> str | None:
        """Entité de l'esquisse active sous le curseur (points, origine, courbes)."""
        contexte = self._detecte(x, y)
        if contexte is None or self.esquisse is None:
            return None
        affichage = self.affichages.get(id(self.esquisse))
        if affichage is None or not contexte.HasDetectedShape():
            return None
        return affichage.entite_de(contexte.DetectedShape())

    def _cote_sous(self, x: int, y: int) -> str | None:
        """Cote de l'esquisse active sous le curseur."""
        contexte = self._detecte(x, y)
        if contexte is None or self.esquisse is None:
            return None
        affichage = self.affichages.get(id(self.esquisse))
        if affichage is None:
            return None
        return affichage.cote_detectee(contexte)

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
                texte_cote=self.texte_cote if active else None,
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
