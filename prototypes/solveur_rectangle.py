"""Prototype 0.4 — résoudre un rectangle contraint avec python-solvespace.

Script jetable : il vérifie que le solveur calcule une esquisse à partir de
relations géométriques et de cotes, comme le fera le mode Esquisse.

On trace « à main levée » un quadrilatère approximatif, puis on impose :
    - le coin bas gauche fixé à l'origine ;
    - les côtés bas et haut horizontaux, les côtés gauche et droit verticaux ;
    - une cote de largeur 80 mm et une cote de hauteur 30 mm.
Le solveur doit replacer les points exactement et annoncer 0 degré de liberté
(esquisse « totalement contrainte », affichée en noir dans SolidWorks).

Lancement (environnement cao actif) :
    python prototypes/solveur_rectangle.py
"""

from python_solvespace import ResultFlag, SolverSystem

LARGEUR = 80.0  # mm
HAUTEUR = 30.0  # mm


def resoudre(avec_cote_hauteur: bool = True) -> tuple[ResultFlag, int, list]:
    """Construit et résout le rectangle ; renvoie (résultat, degrés de liberté, points)."""
    systeme = SolverSystem()
    plan = systeme.create_2d_base()  # plan d'esquisse (groupe 1)
    systeme.set_group(2)  # les entités de l'esquisse vont dans le groupe 2

    # Tracé approximatif, volontairement faux (comme un tracé à la souris).
    p_bas_gauche = systeme.add_point_2d(0.0, 0.0, plan)
    p_bas_droit = systeme.add_point_2d(70.0, 3.0, plan)
    p_haut_droit = systeme.add_point_2d(75.0, 25.0, plan)
    p_haut_gauche = systeme.add_point_2d(-4.0, 22.0, plan)

    # Les lignes partagent leurs points : le contour est fermé par construction.
    bas = systeme.add_line_2d(p_bas_gauche, p_bas_droit, plan)
    droite = systeme.add_line_2d(p_bas_droit, p_haut_droit, plan)
    haut = systeme.add_line_2d(p_haut_droit, p_haut_gauche, plan)
    gauche = systeme.add_line_2d(p_haut_gauche, p_bas_gauche, plan)

    # Relations géométriques.
    systeme.dragged(p_bas_gauche, plan)  # point fixe
    systeme.horizontal(bas, plan)
    systeme.horizontal(haut, plan)
    systeme.vertical(droite, plan)
    systeme.vertical(gauche, plan)

    # Cotes.
    systeme.distance(p_bas_gauche, p_bas_droit, LARGEUR, plan)
    if avec_cote_hauteur:
        systeme.distance(p_bas_droit, p_haut_droit, HAUTEUR, plan)

    resultat = systeme.solve()
    points = [
        systeme.params(p.params) for p in (p_bas_gauche, p_bas_droit, p_haut_droit, p_haut_gauche)
    ]
    return resultat, systeme.dof(), points


def main() -> None:
    attendus = [(0.0, 0.0), (LARGEUR, 0.0), (LARGEUR, HAUTEUR), (0.0, HAUTEUR)]
    noms = ["bas gauche", "bas droit", "haut droit", "haut gauche"]

    print("Cas 1 : rectangle totalement contraint")
    resultat, ddl, points = resoudre()
    print(f"  Résultat du solveur : {resultat.name}, degrés de liberté : {ddl}")
    erreur_max = 0.0
    for nom, (x, y), (xa, ya) in zip(noms, points, attendus, strict=True):
        print(f"  {nom:<12} : x = {x:8.4f}  y = {y:8.4f}   (attendu {xa:g} ; {ya:g})")
        erreur_max = max(erreur_max, abs(x - xa), abs(y - ya))

    print("Cas 2 : sans la cote de hauteur (sous-contraint)")
    resultat2, ddl2, _ = resoudre(avec_cote_hauteur=False)
    print(f"  Résultat du solveur : {resultat2.name}, degrés de liberté : {ddl2}")

    if resultat != ResultFlag.OKAY or ddl != 0 or erreur_max > 1e-6:
        raise SystemExit("ÉCHEC : le rectangle n'est pas résolu exactement")
    if resultat2 != ResultFlag.OKAY or ddl2 != 1:
        raise SystemExit("ÉCHEC : le cas sous-contraint devrait laisser 1 degré de liberté")
    print(f"OK : coordonnées exactes (écart max {erreur_max:.1e} mm), degrés de liberté justes")


if __name__ == "__main__":
    main()
