"""Panneau « Mesure » (IHM-12) : affiché à gauche à la place de l'arbre.

Il montre les mesures de la sélection en cours, mises à jour à chaque clic.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from cao.ihm import textes
from cao.noyau.mesure import Valeur, formater


class PanneauMesure(QWidget):
    fermer_demande = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(14, 4, 14, 14)
        disposition.setSpacing(10)

        consigne = QLabel(textes.MESURE_CONSIGNE)
        consigne.setObjectName("consigne_panneau")
        consigne.setWordWrap(True)
        disposition.addWidget(consigne)

        self.resultats = QLabel()
        self.resultats.setObjectName("resultats_mesure")
        self.resultats.setWordWrap(True)
        self.resultats.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        disposition.addWidget(self.resultats)
        disposition.addStretch()

        bas = QHBoxLayout()
        bas.addStretch()
        fermer = QPushButton(textes.MESURE_FERMER)
        fermer.setObjectName("bouton_secondaire")
        fermer.clicked.connect(self.fermer_demande.emit)
        bas.addWidget(fermer)
        disposition.addLayout(bas)
        self.afficher([], 0)

    def afficher(self, valeurs: list[Valeur], nombre_selectionnes: int) -> None:
        if valeurs:
            self.resultats.setText("\n".join(formater(v) for v in valeurs))
        elif nombre_selectionnes:
            self.resultats.setText(textes.MESURE_RIEN)
        else:
            self.resultats.setText("")

    def texte(self) -> str:
        return self.resultats.text()
