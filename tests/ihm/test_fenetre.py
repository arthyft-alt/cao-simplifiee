"""Tests de l'étape 1.2 : fenêtre d'un document (cahier des charges §2.2, DOC-01).

Révisions du 2026-10-31 à la demande de Simon :
    - barre du haut amincie : Fichier et recherche sur la ligne des onglets,
      outils sur une seule ligne (icône + nom côte à côte), sans légendes ;
    - interface modernisée, ruban adapté à la taille de l'écran ; les outils pas
      encore programmés restent cliquables et affichent un message ;
    - pièce, assemblage et mise en plan sont trois documents distincts, chacun
      dans sa propre fenêtre avec son propre ruban (comme SolidWorks).
"""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt

from cao.fichiers.types_documents import TypeDocument
from cao.ihm import textes
from cao.ihm.fenetre import FenetreDocument
from cao.ihm.feuille import FeuilleDessin
from cao.ihm.ruban import MODES


@pytest.fixture
def fenetre(application_qt: object) -> Iterator[FenetreDocument]:
    f = FenetreDocument(TypeDocument.PIECE, "Pièce1", avec_vue3d=False)
    f.show()
    yield f
    f.close()


def creer(type_document: TypeDocument, nom: str) -> FenetreDocument:
    return FenetreDocument(type_document, nom, avec_vue3d=False)


# --- Fenêtre de pièce ---


def test_titre_contient_document_type_et_application(fenetre: FenetreDocument) -> None:
    titre = fenetre.windowTitle()
    assert "Pièce1" in titre
    assert "(Pièce)" in titre
    assert "CAO simplifiée" in titre


def test_etat_enregistrement_dans_le_titre(fenetre: FenetreDocument) -> None:
    # Le marqueur [*] affiche une étoile quand le document est modifié.
    assert "[*]" in fenetre.windowTitle()
    fenetre.setWindowModified(True)
    assert fenetre.isWindowModified()


def test_onglets_ruban_piece(fenetre: FenetreDocument) -> None:
    assert fenetre.ruban.noms_onglets() == ["Esquisse", "Fonctions", "Évaluer", "Affichage"]


def test_chaque_outil_a_icone_et_info_bulle(fenetre: FenetreDocument) -> None:
    for page in fenetre.ruban.pages:
        assert page.groupes, "onglet vide"
        for groupe in page.groupes:
            for bouton in groupe.boutons:
                action = bouton.defaultAction()
                assert not action.icon().isNull()
                assert action.toolTip()


def test_outil_non_programme_affiche_un_message(fenetre: FenetreDocument) -> None:
    bouton = fenetre.ruban.pages[0].groupes[1].boutons[0]  # « Ligne »
    bouton.defaultAction().trigger()
    assert fenetre.statusBar().currentMessage() == textes.message_bientot("Ligne")


def test_arbre_piece_contient_plans_et_origine(fenetre: FenetreDocument) -> None:
    arbre = fenetre.panneau_gauche.arbre
    assert arbre.racine.text(0) == "Pièce1"
    assert arbre.noms_elements() == ["Plan de face", "Plan de dessus", "Plan de droite", "Origine"]


def test_panneau_proprietes_remplace_arbre(fenetre: FenetreDocument) -> None:
    gauche = fenetre.panneau_gauche
    assert gauche.montre_arbre()
    gauche.montrer_proprietes()
    assert not gauche.montre_arbre()
    gauche.montrer_arbre()
    assert gauche.montre_arbre()


def test_barre_affichage_vues_standard(fenetre: FenetreDocument) -> None:
    assert fenetre.barre_affichage is not None
    noms = [a.text() for a in fenetre.barre_affichage.actions_vues()]
    assert noms == ["Isométrique", "Face", "Dessus", "Droite", "Ajuster"]


def test_barre_etat_piece(fenetre: FenetreDocument) -> None:
    textes_pastilles = [p.text() for p in fenetre.pastilles]
    assert textes_pastilles == textes.ETAT_PAR_TYPE[TypeDocument.PIECE]
    assert fenetre.statusBar().currentMessage() == textes.ASTUCE_PAR_TYPE[TypeDocument.PIECE]


def test_menu_fichier_sur_la_ligne_des_onglets(fenetre: FenetreDocument) -> None:
    # Pas de barre de menus séparée : le bouton Fichier est dans le coin du ruban.
    assert fenetre.ruban.cornerWidget(Qt.Corner.TopLeftCorner) is fenetre.bouton_fichier
    assert fenetre.bouton_fichier.menu() is fenetre.menu_fichier
    assert fenetre.action_nouveau.isEnabled()
    assert fenetre.action_fermer.isEnabled()
    assert fenetre.action_quitter.isEnabled()


def test_raccourcis_actifs_sans_ouvrir_le_menu(fenetre: FenetreDocument) -> None:
    assert fenetre.action_nouveau in fenetre.actions()
    assert fenetre.action_quitter in fenetre.actions()


def test_barre_du_haut_fine(fenetre: FenetreDocument) -> None:
    # Demande de Simon : la barre du haut ne doit pas manger l'écran.
    fenetre.resize(1600, 900)
    assert fenetre.ruban.height() <= 90


def test_tient_sur_ecran_1366x768(fenetre: FenetreDocument) -> None:
    taille_mini = fenetre.minimumSize()
    assert taille_mini.width() <= 1366
    assert taille_mini.height() <= 768


# --- Adaptation à l'écran ---


def test_ruban_compact_sur_petite_largeur(fenetre: FenetreDocument) -> None:
    assert fenetre.ruban.adapter(300) == "compact"


def test_ruban_grand_sur_grande_largeur(fenetre: FenetreDocument) -> None:
    assert fenetre.ruban.adapter(3000) == "grand"


def test_ruban_suit_la_largeur_de_la_fenetre(fenetre: FenetreDocument) -> None:
    fenetre.resize(2400, 900)
    grand = fenetre.ruban.mode.taille_icone
    fenetre.resize(900, 700)
    assert fenetre.ruban.mode.taille_icone <= grand
    assert fenetre.ruban.mode in MODES


def test_petit_ecran_sans_grandes_icones(fenetre: FenetreDocument) -> None:
    fenetre.ruban.regler_pour_petit_ecran(True)
    assert fenetre.ruban.adapter(3000) == "moyen"
    fenetre.ruban.regler_pour_petit_ecran(False)
    assert fenetre.ruban.adapter(3000) == "grand"


def test_ruban_pas_plus_haut_en_compact(fenetre: FenetreDocument) -> None:
    fenetre.ruban.adapter(3000)
    hauteur_grand = fenetre.ruban.height()
    fenetre.ruban.adapter(300)
    assert fenetre.ruban.height() <= hauteur_grand


# --- Assemblage et mise en plan : interfaces distinctes ---


def test_assemblage_a_son_propre_ruban_et_arbre(application_qt: object) -> None:
    f = creer(TypeDocument.ASSEMBLAGE, "Assemblage1")
    assert f.ruban.noms_onglets() == ["Assemblage", "Évaluer", "Affichage"]
    assert "Esquisse" not in f.ruban.noms_onglets()
    assert f.panneau_gauche.arbre.noms_elements()[-1] == textes.ARBRE_CONTRAINTES
    assert f.barre_affichage is not None
    assert "(Assemblage)" in f.windowTitle()


def test_mise_en_plan_a_une_feuille_et_pas_de_vue_3d(application_qt: object) -> None:
    f = creer(TypeDocument.MISE_EN_PLAN, "Plan1")
    assert f.ruban.noms_onglets() == ["Disposition des vues", "Annotation", "Esquisse"]
    assert isinstance(f.zone_graphique, FeuilleDessin)
    assert f.barre_affichage is None
    assert f.panneau_gauche.arbre.noms_elements() == [textes.ARBRE_FEUILLE]
    assert "(Mise en plan)" in f.windowTitle()


def test_outils_de_fonctions_absents_hors_piece(application_qt: object) -> None:
    for type_document in (TypeDocument.ASSEMBLAGE, TypeDocument.MISE_EN_PLAN):
        f = creer(type_document, "Doc1")
        noms_outils = {
            b.property("nom_outil") for p in f.ruban.pages for g in p.groupes for b in g.boutons
        }
        assert "Bossage extrudé" not in noms_outils
