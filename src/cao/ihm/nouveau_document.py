"""Fenêtre « Nouveau document » : choisir Pièce, Assemblage ou Mise en plan.

Comme la fenêtre « Nouveau document SOLIDWORKS » : trois grandes cartes,
un clic sur une carte crée le document correspondant.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cao.fichiers.types_documents import INFOS, TypeDocument
from cao.ihm import textes
from cao.ihm.arbre import ICONE_DOCUMENT
from cao.ihm.icones import icone


class CarteDocument(QPushButton):
    """Grande carte cliquable : icône, nom du type, phrase d'explication."""

    def __init__(self, type_document: TypeDocument, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.type_document = type_document
        info = INFOS[type_document]
        self.setObjectName("carte_document")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(QSize(200, 220))
        self.setToolTip(info.description)

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(18, 22, 18, 18)
        disposition.setSpacing(10)
        image = QLabel()
        image.setPixmap(icone(ICONE_DOCUMENT[type_document]).pixmap(64, 64))
        image.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        titre = QLabel(info.libelle)
        titre.setObjectName("carte_titre")
        titre.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        description = QLabel(info.description)
        description.setObjectName("carte_description")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        for etiquette in (image, titre, description):
            # Le clic doit atteindre le bouton, pas les étiquettes posées dessus.
            etiquette.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            disposition.addWidget(etiquette)
        disposition.addStretch()


class DialogueNouveauDocument(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dialogue_nouveau")
        self.setWindowTitle(f"{textes.NOUVEAU_TITRE} — {textes.APPLICATION}")
        self.setWindowIcon(icone("piece"))
        self.choix: TypeDocument | None = None

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(28, 24, 28, 22)
        disposition.setSpacing(18)
        consigne = QLabel(textes.NOUVEAU_CONSIGNE)
        consigne.setObjectName("consigne_nouveau")
        disposition.addWidget(consigne)

        ligne = QHBoxLayout()
        ligne.setSpacing(16)
        self.cartes: list[CarteDocument] = []
        for type_document in TypeDocument:
            carte = CarteDocument(type_document)
            carte.clicked.connect(lambda _=False, t=type_document: self.choisir(t))
            self.cartes.append(carte)
            ligne.addWidget(carte)
        disposition.addLayout(ligne)

        bas = QHBoxLayout()
        bas.addStretch()
        annuler = QPushButton(textes.NOUVEAU_ANNULER)
        annuler.setObjectName("bouton_secondaire")
        annuler.clicked.connect(self.reject)
        bas.addWidget(annuler)
        disposition.addLayout(bas)

    def choisir(self, type_document: TypeDocument) -> None:
        self.choix = type_document
        self.accept()
