"""Prototype 0.5 — vue de face par l'algorithme HLR d'OpenCascade, dessinée dans Qt.

Script jetable : il vérifie qu'on sait produire une vue de mise en plan
à partir du modèle 3D, avec des traits différents pour les arêtes vues
et les arêtes cachées.

HLR = « Hidden Line Removal », suppression des lignes cachées : l'algorithme
projette le solide sur un plan et classe chaque arête en vue ou cachée.

Pièce : la plaque percée du prototype 0.3 (100 x 50 x 20 mm, trou Ø10).
En vue de face, le trou est caché : il doit apparaître en traits interrompus.

Lancement (environnement cao actif) :
    python prototypes/vue_hlr.py
Option --test : la fenêtre se ferme seule après 3 secondes.
"""

import sys
from itertools import pairwise

from extrusion_step import percer, plaque_extrudee
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.GeomAbs import GeomAbs_Line
from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCC.Core.HLRAlgo import HLRAlgo_Projector
from OCC.Core.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Shape, topods
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

Polyligne = list[tuple[float, float]]


def polylignes(compose: TopoDS_Shape) -> list[Polyligne]:
    """Transforme chaque arête projetée en liste de points 2D (x, y) en mm."""
    resultat: list[Polyligne] = []
    if compose is None or compose.IsNull():
        return resultat
    explorateur = TopExp_Explorer(compose, TopAbs_EDGE)
    while explorateur.More():
        courbe = BRepAdaptor_Curve(topods.Edge(explorateur.Current()))
        debut, fin = courbe.FirstParameter(), courbe.LastParameter()
        nb = 1 if courbe.GetType() == GeomAbs_Line else 40  # droite : 2 points suffisent
        points = []
        for i in range(nb + 1):
            p = courbe.Value(debut + (fin - debut) * i / nb)
            points.append((p.X(), p.Y()))
        resultat.append(points)
        explorateur.Next()
    return resultat


def vue_de_face(piece: TopoDS_Shape) -> tuple[list[Polyligne], list[Polyligne]]:
    """Projette la pièce vue de face (observateur côté -Y, Z vers le haut).

    Renvoie (arêtes vues, arêtes cachées). Dans le plan projeté :
    x = axe X du modèle, y = axe Z du modèle.
    """
    # Repère de projection : direction vers l'observateur, puis axe x de la vue.
    repere = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, -1, 0), gp_Dir(1, 0, 0))
    algo = HLRBRep_Algo()
    algo.Add(piece)
    algo.Projector(HLRAlgo_Projector(repere))
    algo.Update()
    algo.Hide()

    formes = HLRBRep_HLRToShape(algo)
    # VCompound : arêtes vives vues ; OutLine : contours apparents (cylindres).
    vues = polylignes(formes.VCompound()) + polylignes(formes.OutLineVCompound())
    cachees = polylignes(formes.HCompound()) + polylignes(formes.OutLineHCompound())
    return vues, cachees


class FeuilleDePlan(QWidget):
    """Dessine les traits de la vue, mis à l'échelle de la fenêtre."""

    MARGE = 40  # pixels

    def __init__(self, vues: list[Polyligne], cachees: list[Polyligne]):
        super().__init__()
        self.vues = vues
        self.cachees = cachees
        self.setWindowTitle("Prototype 0.5 — vue de face (HLR)")
        self.resize(900, 400)
        self.setStyleSheet("background: white;")

    def paintEvent(self, _evenement):
        tous = [p for ligne in self.vues + self.cachees for p in ligne]
        xmin, xmax = min(p[0] for p in tous), max(p[0] for p in tous)
        ymin, ymax = min(p[1] for p in tous), max(p[1] for p in tous)
        largeur_utile = self.width() - 2 * self.MARGE
        hauteur_utile = self.height() - 2 * self.MARGE
        echelle = min(largeur_utile / (xmax - xmin), hauteur_utile / (ymax - ymin))
        # Centrage du dessin dans la fenêtre.
        dx = self.MARGE + (largeur_utile - (xmax - xmin) * echelle) / 2
        dy = self.MARGE + (hauteur_utile - (ymax - ymin) * echelle) / 2

        def ecran(x: float, y: float) -> QPointF:
            # L'axe y de l'écran descend : on le retourne.
            return QPointF(dx + (x - xmin) * echelle, dy + (ymax - y) * echelle)

        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Traits normalisés : vu = continu fort, caché = interrompu fin.
        trait_vu = QPen(Qt.GlobalColor.black, 2.5, Qt.PenStyle.SolidLine)
        trait_cache = QPen(Qt.GlobalColor.black, 1.0, Qt.PenStyle.DashLine)
        for stylo, lignes in ((trait_cache, self.cachees), (trait_vu, self.vues)):
            peintre.setPen(stylo)
            for ligne in lignes:
                for a, b in pairwise(ligne):
                    peintre.drawLine(ecran(*a), ecran(*b))
        peintre.end()


def main() -> None:
    piece = percer(plaque_extrudee())
    vues, cachees = vue_de_face(piece)
    print(f"Arêtes vues : {len(vues)}, arêtes cachées : {len(cachees)}")

    # Contrôle : parmi les arêtes cachées verticales, celles qu'aucune arête vue
    # ne recouvre doivent être les bords du trou, x = 45 et x = 55.
    # (Les arêtes de la face arrière, x = 0 et x = 100, sont cachées derrière
    # celles de devant : sur le plan, le trait vu l'emporte.)
    def x_verticales(lignes: list[Polyligne]) -> set[float]:
        return {
            round(ligne[0][0], 3)
            for ligne in lignes
            if all(abs(p[0] - ligne[0][0]) < 1e-6 for p in ligne)
        }

    x_caches = sorted(x_verticales(cachees) - x_verticales(vues))
    print(f"Arêtes cachées verticales non recouvertes, abscisses : {x_caches}")
    if x_caches != [45.0, 55.0]:
        raise SystemExit("ÉCHEC : les arêtes cachées ne sont pas celles du trou")
    print("OK : le trou apparaît en arêtes cachées à x = 45 et x = 55 mm")

    app = QApplication(sys.argv)
    feuille = FeuilleDePlan(vues, cachees)
    feuille.show()
    if "--test" in sys.argv:
        QTimer.singleShot(3000, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
