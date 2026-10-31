"""Plans d'esquisse : passage des coordonnées de l'esquisse (u, v) à l'espace (X, Y, Z).

Convention d'axes de SolidWorks : Y vertical. Chaque plan est vu de face quand
on entre dans l'esquisse, avec u vers la droite de l'écran et v vers le haut :
    face   : plan XY, vu depuis +Z : u = X,  v = Y
    dessus : plan XZ, vu depuis +Y : u = X,  v = -Z
    droite : plan YZ, vu depuis +X : u = -Z, v = Y
Aucune dépendance (ni Qt ni OpenCascade).
"""

from dataclasses import dataclass

Vecteur = tuple[float, float, float]


@dataclass(frozen=True)
class PlanEsquisse:
    nom: str  # « face », « dessus », « droite »
    libelle: str  # texte affiché (« Plan de face »)
    origine: Vecteur
    axe_u: Vecteur  # direction de u dans l'espace (droite de l'écran)
    axe_v: Vecteur  # direction de v dans l'espace (haut de l'écran)

    @property
    def normale(self) -> Vecteur:
        """Direction vers l'observateur (u × v)."""
        (ux, uy, uz), (vx, vy, vz) = self.axe_u, self.axe_v
        return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)

    def vers_espace(self, u: float, v: float) -> Vecteur:
        o, a, b = self.origine, self.axe_u, self.axe_v
        return (
            o[0] + u * a[0] + v * b[0],
            o[1] + u * a[1] + v * b[1],
            o[2] + u * a[2] + v * b[2],
        )

    def vers_plan(self, point: Vecteur) -> tuple[float, float]:
        """Coordonnées (u, v) de la projection d'un point de l'espace sur le plan."""
        d = (point[0] - self.origine[0], point[1] - self.origine[1], point[2] - self.origine[2])
        a, b = self.axe_u, self.axe_v
        return (
            d[0] * a[0] + d[1] * a[1] + d[2] * a[2],
            d[0] * b[0] + d[1] * b[1] + d[2] * b[2],
        )


PLANS: dict[str, PlanEsquisse] = {
    "face": PlanEsquisse("face", "Plan de face", (0, 0, 0), (1, 0, 0), (0, 1, 0)),
    "dessus": PlanEsquisse("dessus", "Plan de dessus", (0, 0, 0), (1, 0, 0), (0, 0, -1)),
    "droite": PlanEsquisse("droite", "Plan de droite", (0, 0, 0), (0, 0, -1), (0, 1, 0)),
}


def plan_par_libelle(libelle: str) -> PlanEsquisse | None:
    return next((p for p in PLANS.values() if p.libelle == libelle), None)
