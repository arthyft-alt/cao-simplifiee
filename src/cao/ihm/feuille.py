"""Zone graphique de la mise en plan : une feuille de dessin vue d'en haut.

Pour l'instant (étape 1.2), une feuille A4 paysage vierge avec son cadre et
l'emplacement du cartouche. Les vues, cotes et le vrai cartouche arrivent au lot 5.
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from cao.ihm.theme import COULEURS

FORMAT_A4_PAYSAGE_MM = (297.0, 210.0)
MARGE_CADRE_MM = 10.0
CARTOUCHE_MM = (180.0, 40.0)  # largeur, hauteur (emplacement indicatif)


class FeuilleDessin(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("feuille_dessin")
        self.format_mm = FORMAT_A4_PAYSAGE_MM

    def rectangle_feuille(self) -> QRectF:
        """Feuille centrée dans la zone, à la plus grande échelle qui tient."""
        largeur_mm, hauteur_mm = self.format_mm
        marge = 32.0
        echelle = min(
            (self.width() - 2 * marge) / largeur_mm, (self.height() - 2 * marge) / hauteur_mm
        )
        echelle = max(echelle, 0.1)
        largeur, hauteur = largeur_mm * echelle, hauteur_mm * echelle
        return QRectF((self.width() - largeur) / 2, (self.height() - hauteur) / 2, largeur, hauteur)

    def paintEvent(self, _evenement: QPaintEvent) -> None:
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.fillRect(self.rect(), QColor(COULEURS["fond"]))

        feuille = self.rectangle_feuille()
        echelle = feuille.width() / self.format_mm[0]

        # Ombre douce puis feuille blanche.
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(QColor(0, 0, 0, 28))
        peintre.drawRect(feuille.translated(3, 4))
        peintre.setBrush(QColor("#ffffff"))
        peintre.drawRect(feuille)

        # Cadre intérieur et emplacement du cartouche (en bas à droite).
        marge = MARGE_CADRE_MM * echelle
        cadre = feuille.adjusted(marge, marge, -marge, -marge)
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.setPen(QPen(QColor("#2b2b2b"), 1.4))
        peintre.drawRect(cadre)
        largeur_c, hauteur_c = (v * echelle for v in CARTOUCHE_MM)
        cartouche = QRectF(
            cadre.right() - largeur_c, cadre.bottom() - hauteur_c, largeur_c, hauteur_c
        )
        peintre.setPen(QPen(QColor("#2b2b2b"), 1.0))
        peintre.drawRect(cartouche)
        peintre.end()
