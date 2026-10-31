"""Pilotage de la vue 3D d'OpenCascade : orientations, cube de vue, zoom, modes de rendu.

Ce module ne dépend pas de Qt : il reçoit la vue (V3d_View) et le contexte
d'affichage (AIS_InteractiveContext) créés par l'interface, et agit dessus.

Convention d'axes : comme SolidWorks, l'axe **Y est vertical** (vers le haut).
    Plan de face = plan XY (vue de face : on regarde depuis +Z) ;
    Plan de dessus = plan XZ (vue de dessus : on regarde depuis +Y) ;
    Plan de droite = plan YZ (vue de droite : on regarde depuis +X).
"""

import math
from enum import Enum

from OCC.Core.AIS import (
    AIS_InteractiveContext,
    AIS_ListOfInteractive,
    AIS_Shaded,
    AIS_Shape,
    AIS_ViewCube,
    AIS_ViewCubeOwner,
    AIS_WireFrame,
)
from OCC.Core.Aspect import Aspect_TOL_SOLID, Aspect_TOTP_RIGHT_UPPER
from OCC.Core.gp import gp_Dir, gp_Vec
from OCC.Core.Graphic3d import (
    Graphic3d_MaterialAspect,
    Graphic3d_NameOfMaterial_Satin,
    Graphic3d_TMF_TriedronPers,
    Graphic3d_TransformPers,
    Graphic3d_Vec2i,
)
from OCC.Core.Prs3d import (
    Prs3d_IsoAspect,
    Prs3d_LineAspect,
    Prs3d_TypeOfHighlight_Dynamic,
    Prs3d_TypeOfHighlight_LocalDynamic,
    Prs3d_TypeOfHighlight_LocalSelected,
    Prs3d_TypeOfHighlight_Selected,
)
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.V3d import (
    V3d_TypeOfOrientation,
    V3d_TypeOfOrientation_Yup_AxoRight,
    V3d_TypeOfOrientation_Yup_Back,
    V3d_TypeOfOrientation_Yup_Bottom,
    V3d_TypeOfOrientation_Yup_Front,
    V3d_TypeOfOrientation_Yup_Left,
    V3d_TypeOfOrientation_Yup_Right,
    V3d_TypeOfOrientation_Yup_Top,
    V3d_View,
    V3d_Viewer,
    V3d_Xneg,
    V3d_Xpos,
    V3d_Yneg,
    V3d_Ypos,
    V3d_Zneg,
    V3d_Zpos,
)


class VueStandard(Enum):
    FACE = "face"
    ARRIERE = "arriere"
    GAUCHE = "gauche"
    DROITE = "droite"
    DESSUS = "dessus"
    DESSOUS = "dessous"
    ISOMETRIQUE = "isometrique"


ORIENTATIONS: dict[VueStandard, V3d_TypeOfOrientation] = {
    VueStandard.FACE: V3d_TypeOfOrientation_Yup_Front,
    VueStandard.ARRIERE: V3d_TypeOfOrientation_Yup_Back,
    VueStandard.GAUCHE: V3d_TypeOfOrientation_Yup_Left,
    VueStandard.DROITE: V3d_TypeOfOrientation_Yup_Right,
    VueStandard.DESSUS: V3d_TypeOfOrientation_Yup_Top,
    VueStandard.DESSOUS: V3d_TypeOfOrientation_Yup_Bottom,
    VueStandard.ISOMETRIQUE: V3d_TypeOfOrientation_Yup_AxoRight,
}

# Noms des faces du cube de vue, en convention Y vers le haut.
ETIQUETTES_CUBE: dict[V3d_TypeOfOrientation, str] = {
    V3d_Zpos: "Face",
    V3d_Zneg: "Arrière",
    V3d_Xpos: "Droite",
    V3d_Xneg: "Gauche",
    V3d_Ypos: "Dessus",
    V3d_Yneg: "Dessous",
}


class ModeRendu(Enum):
    OMBRE_ARETES = "ombre_aretes"  # faces ombrées + arêtes noires (par défaut, comme SolidWorks)
    OMBRE = "ombre"  # faces ombrées seules
    FILAIRE = "filaire"  # toutes les arêtes, sans faces
    LIGNES_CACHEES = "lignes_cachees"  # arêtes vues seulement (lignes cachées supprimées)


PAS_ROTATION_CLAVIER = math.radians(15)  # flèches du clavier : 15°, comme SolidWorks
TAILLE_CUBE_PX = 70
MARGE_CUBE_PX = 80


# Apparence par défaut des pièces (la matière choisie par l'utilisateur viendra au lot 3).
COULEUR_PIECE = (0.60, 0.65, 0.73)  # gris bleuté
COULEUR_TRAITS = (0.11, 0.14, 0.19)  # gris très foncé, presque noir
EPAISSEUR_TRAITS = 1.4
COULEUR_SURVOL = (0.40, 0.65, 1.00)  # bleu clair
COULEUR_SELECTION = (0.15, 0.39, 0.92)  # bleu franc
INTENSITE_AMBIANTE = 0.55
# Direction du phare dans le repère de la caméra (essais du 2026-10-31 : dessus clair,
# face moyenne, côté droit sombre en vue isométrique).
DIRECTION_PHARE = (0.45, -0.55, -1.0)


def _couleur(rvb: tuple[float, float, float]) -> Quantity_Color:
    return Quantity_Color(rvb[0], rvb[1], rvb[2], Quantity_TOC_RGB)


def configurer_apparence(contexte: AIS_InteractiveContext) -> None:
    """Couleurs et traits par défaut : pièce gris bleuté satiné, arêtes foncées.

    Remplace les réglages d'origine d'OpenCascade (laiton, traits jaunes,
    lignes d'isoparamétriques grises), peu lisibles sur un fond clair.
    """
    dessin = contexte.DefaultDrawer()
    matiere = Graphic3d_MaterialAspect(Graphic3d_NameOfMaterial_Satin)
    matiere.SetColor(_couleur(COULEUR_PIECE))
    dessin.ShadingAspect().SetMaterial(matiere)
    dessin.ShadingAspect().SetColor(_couleur(COULEUR_PIECE))
    trait = _couleur(COULEUR_TRAITS)
    for regler in (
        dessin.SetFaceBoundaryAspect,
        dessin.SetFreeBoundaryAspect,
        dessin.SetUnFreeBoundaryAspect,
        dessin.SetWireAspect,
        dessin.SetLineAspect,
        dessin.SetSeenLineAspect,
    ):
        regler(Prs3d_LineAspect(trait, Aspect_TOL_SOLID, EPAISSEUR_TRAITS))
    # Pas de lignes « isoparamétriques » (traits internes aux faces courbes).
    dessin.SetUIsoAspect(Prs3d_IsoAspect(trait, Aspect_TOL_SOLID, 1.0, 0))
    dessin.SetVIsoAspect(Prs3d_IsoAspect(trait, Aspect_TOL_SOLID, 1.0, 0))
    # Surbrillance (IHM-04) : bleu clair au survol, bleu franc pour la sélection.
    # Les faces sont remplies de couleur (mode ombré), en semi-transparence.
    styles = [
        (Prs3d_TypeOfHighlight_Dynamic, COULEUR_SURVOL, 0.5),
        (Prs3d_TypeOfHighlight_LocalDynamic, COULEUR_SURVOL, 0.5),
        (Prs3d_TypeOfHighlight_Selected, COULEUR_SELECTION, 0.35),
        (Prs3d_TypeOfHighlight_LocalSelected, COULEUR_SELECTION, 0.35),
    ]
    for type_surbrillance, couleur, transparence in styles:
        style = contexte.HighlightStyle(type_surbrillance)
        style.SetColor(_couleur(couleur))
        style.SetDisplayMode(AIS_Shaded)
        style.SetTransparency(transparence)


def configurer_eclairage(visualiseur: V3d_Viewer) -> None:
    """Règle les deux lumières d'origine du visualiseur (phare + ambiante).

    Le phare suit la caméra ; on l'incline pour qu'il éclaire surtout le dessus
    des pièces : chaque face a ainsi une
    teinte différente, quelle que soit la vue. La lumière ambiante est
    adoucie pour que les faces vues de face ne saturent pas en blanc.

    pythonocc ne sait pas parcourir la liste des lumières (et la vider la vide
    réellement) : on n'atteint que la première (phare) et la dernière (ambiante).
    """
    lumieres = visualiseur.ActiveLights()
    if lumieres.Size() != 2:
        return  # configuration inattendue : on garde l'éclairage d'origine
    phare, ambiante = lumieres.First(), lumieres.Last()
    phare.SetDirection(gp_Dir(*DIRECTION_PHARE))
    ambiante.SetIntensity(INTENSITE_AMBIANTE)


def afficher_forme(contexte: AIS_InteractiveContext, forme: TopoDS_Shape) -> AIS_Shape:
    """Affiche une forme avec l'apparence du logiciel (matière et traits par défaut)."""
    presentation = AIS_Shape(forme)
    contexte.Display(presentation, True)
    activer_selection(contexte, presentation, FiltreSelection.TOUT)
    return presentation


def orienter(vue: V3d_View, vue_standard: VueStandard, ajuster: bool = True) -> None:
    """Oriente la caméra sur une vue standard (IHM-02)."""
    vue.SetProj(ORIENTATIONS[vue_standard], True)
    if ajuster:
        vue.FitAll(0.1, True)
    vue.Redraw()


def creer_cube_de_vue() -> AIS_ViewCube:
    """Cube de vue cliquable affiché en haut à droite (IHM-02)."""
    cube = AIS_ViewCube()
    cube.SetYup(True)
    for orientation, texte in ETIQUETTES_CUBE.items():
        cube.SetBoxSideLabel(orientation, texte)
    cube.SetSize(TAILLE_CUBE_PX)
    cube.SetFontHeight(15)
    cube.SetBoxColor(Quantity_Color(0.89, 0.93, 0.99, Quantity_TOC_RGB))
    cube.SetTextColor(Quantity_Color(0.12, 0.31, 0.60, Quantity_TOC_RGB))
    cube.SetTransformPersistence(
        Graphic3d_TransformPers(
            Graphic3d_TMF_TriedronPers,
            Aspect_TOTP_RIGHT_UPPER,
            Graphic3d_Vec2i(MARGE_CUBE_PX, MARGE_CUBE_PX),
        )
    )
    return cube


def clic_sur_cube(contexte: AIS_InteractiveContext, vue: V3d_View, x: int, y: int) -> bool:
    """Si le clic (x, y) tombe sur le cube de vue, oriente la caméra et renvoie True.

    Une face donne une vue standard, une arête ou un coin une vue intermédiaire.
    """
    contexte.MoveTo(x, y, vue, False)
    if not contexte.HasDetected():
        return False
    detecte = contexte.DetectedOwner()
    # On vérifie la nature de l'objet avant de le convertir : pythonocc lève une
    # erreur (au lieu de renvoyer None) si l'objet cliqué n'est pas le cube.
    if detecte is None or not detecte.IsKind("AIS_ViewCubeOwner"):
        return False
    proprietaire = AIS_ViewCubeOwner.DownCast(detecte)
    vue.SetProj(proprietaire.MainOrientation(), True)
    vue.FitAll(0.1, True)
    vue.Redraw()
    return True


def zoomer_au_point(vue: V3d_View, x: int, y: int, facteur: float) -> None:
    """Zoom centré sur le point (x, y) de l'écran : ce point reste sous le curseur (IHM-01)."""
    # ConvertWithProj renvoie (X, Y, Z, dX, dY, dZ) : le point 3D sous le pixel et la visée.
    avant = vue.ConvertWithProj(x, y)
    vue.SetZoom(facteur, True)
    apres = vue.ConvertWithProj(x, y)
    decalage = gp_Vec(apres[0] - avant[0], apres[1] - avant[1], apres[2] - avant[2])
    camera = vue.Camera()
    camera.SetCenter(camera.Center().Translated(decalage.Reversed()))
    camera.SetEye(camera.Eye().Translated(decalage.Reversed()))
    vue.Redraw()


def tourner(vue: V3d_View, horizontal: float, vertical: float) -> None:
    """Rotation de la vue (radians) autour des axes de l'écran (flèches du clavier)."""
    vue.Rotate(vertical, horizontal, 0.0, True)
    vue.Redraw()


def appliquer_mode_rendu(contexte: AIS_InteractiveContext, vue: V3d_View, mode: ModeRendu) -> None:
    """Change le mode de rendu de toutes les formes affichées (IHM-03)."""
    dessin = contexte.DefaultDrawer()
    dessin.SetFaceBoundaryDraw(mode == ModeRendu.OMBRE_ARETES)
    vue.SetComputedMode(mode == ModeRendu.LIGNES_CACHEES)
    ombre = mode in (ModeRendu.OMBRE_ARETES, ModeRendu.OMBRE)
    contexte.SetDisplayMode(AIS_Shaded if ombre else AIS_WireFrame, False)
    # Les formes déjà affichées doivent être recalculées pour montrer ou cacher leurs arêtes.
    objets = AIS_ListOfInteractive()
    contexte.DisplayedObjects(objets)
    for objet in objets:
        contexte.Redisplay(objet, False)
    contexte.UpdateCurrentViewer()


class FiltreSelection(Enum):
    """Ce que le clic peut sélectionner (filtre de sélection, IHM-04)."""

    TOUT = "tout"
    FACES = "faces"
    ARETES = "aretes"
    SOMMETS = "sommets"


GENRES_FILTRE = {
    FiltreSelection.TOUT: (TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX),
    FiltreSelection.FACES: (TopAbs_FACE,),
    FiltreSelection.ARETES: (TopAbs_EDGE,),
    FiltreSelection.SOMMETS: (TopAbs_VERTEX,),
}


def activer_selection(
    contexte: AIS_InteractiveContext, presentation: AIS_Shape, filtre: FiltreSelection
) -> None:
    """Rend sélectionnables les faces, arêtes et/ou sommets d'une forme affichée."""
    contexte.Deactivate(presentation)
    for genre in GENRES_FILTRE[filtre]:
        contexte.Activate(presentation, AIS_Shape.SelectionMode(genre), False)


def appliquer_filtre(contexte: AIS_InteractiveContext, filtre: FiltreSelection) -> None:
    """Applique le filtre à toutes les formes affichées (le cube de vue n'est pas touché)."""
    contexte.ClearSelected(False)
    objets = AIS_ListOfInteractive()
    contexte.DisplayedObjects(objets)
    for objet in objets:
        if objet.IsKind("AIS_Shape"):
            activer_selection(contexte, AIS_Shape.DownCast(objet), filtre)
    contexte.UpdateCurrentViewer()


def formes_selectionnees(contexte: AIS_InteractiveContext) -> list[TopoDS_Shape]:
    """Faces, arêtes et sommets actuellement sélectionnés."""
    formes = []
    contexte.InitSelected()
    while contexte.MoreSelected():
        if contexte.HasSelectedShape():
            formes.append(contexte.SelectedShape())
        contexte.NextSelected()
    return formes


def orienter_normale(vue: V3d_View, normale: gp_Dir) -> None:
    """Regarde une face plane de face, depuis l'extérieur de la matière (IHM-02)."""
    vue.SetProj(normale.X(), normale.Y(), normale.Z())
    # Haut de l'écran : l'axe Y, sauf si l'on regarde le long de Y (on prend alors -Z).
    haut = (0.0, 0.0, -1.0) if abs(normale.Y()) > 0.99 else (0.0, 1.0, 0.0)
    vue.SetUp(*haut)
    vue.FitAll(0.1, True)
    vue.Redraw()
