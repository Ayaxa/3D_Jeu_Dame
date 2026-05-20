from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from cameraFPS import *
from scene3D import *
from queue import Queue
import threading
import time


class Echequier3D(ShowBase):

    def __init__(self):

        ShowBase.__init__(self)

        props = WindowProperties()
        props.setFullscreen(True)
        self.win.requestProperties(props)

        self.cameraController = FPSCamera(self)
        self.scene = Scene(self)

        self.grille = [[0 for _ in range(10)] for _ in range(10)]
        self.pions_par_coord = {}

        self.taskMgr.add(self.update, "update")
        self.command_queue = Queue()

    def add_command(self, func, *args, **kwargs):
        self.command_queue.put((func, args, kwargs))

    def update(self, task):

        dt = globalClock.getDt()
        self.cameraController.update(dt)
        self.scene.update(dt)

        while not self.command_queue.empty():
            func, args, kwargs = self.command_queue.get()
            func(*args, **kwargs)

        return task.cont

    # =========================================================
    # MATRICE → NORMALISATION UNIQUE (IMPORTANT)
    # =========================================================

    def charger_position(self, matrice):
        """
        matrice côté NOIR -> conversion côté BLANC
        rotation 180° appliquée ICI UNE SEULE FOIS
        """

        self.clear_pions()

        matrice = self.rotation_180(matrice)
        self.grille = [row[:] for row in matrice]

        for y in range(10):
            for x in range(10):

                val = matrice[y][x]

                if val == 0:
                    continue

                pos = self._case_to_world(x, 9-y)

                color = ROUGE if val == 1 else BLEU
                pion = self.add_pion(pos, color)
                self.pions_par_coord[(x, y)] = pion

    # =========================================================
    # COUPS (DOIT UTILISER MÊME REPERE QUE MATRICE TRANSFORMEE)
    # =========================================================

    def jouer_coups(self, liste_cases):

        if len(liste_cases) == 0:
            return

        coords = []

        for case in liste_cases:
            x, y = self._case_to_xy(case)

            # IMPORTANT : cohérence même repère que matrice
            #coords.append(self._case_to_world(x-1, y))
            coords.append(self._case_to_world(x, y))

        pos_init = (POS_BRAS_REPOS_X, POS_BRAS_REPOS_Y, POS_BRAS_REPOS_Z)

        coords.insert(0, pos_init)
        coords.append(pos_init)

        def animation():
            for i in range(len(coords) - 1):

                start = coords[i]
                end = coords[i + 1]

                if i == 0 or i == len(coords) - 2:
                    self.add_command(self.deplacer_vers, start, end, DUREE_ANIM)
                else:
                    case_depart = liste_cases[i - 1]
                    case_arrivee = liste_cases[i]

                    self.add_command(
                        self.deplacer_pion_case,
                        case_depart,
                        case_arrivee,
                        start,
                        end,
                        DUREE_ANIM
                    )
                time.sleep(DUREE_ANIM * 2)

                if i != 0 and i != len(coords) - 2:
                    self.add_command(
                        self.mettre_a_jour_grille,
                        case_depart,
                        case_arrivee
                    )

        threading.Thread(target=animation, daemon=True).start()

    def deplacer_pion_case(self, case_depart, case_arrivee,
                           start, end, duration=1.0):
        coord_depart = self._case_to_matrix_xy(case_depart)
        pion = self.pions_par_coord.get(coord_depart)

        if pion is None:
            print(f"Aucun pion sur la case {case_depart}")
            self.deplacer_vers(start, end, duration)
            return

        self.deplacer_vers(start, end, duration, pion)

    def mettre_a_jour_grille(self, case_depart, case_arrivee):
        coord_depart = self._case_to_matrix_xy(case_depart)
        coord_arrivee = self._case_to_matrix_xy(case_arrivee)

        x_depart, y_depart = coord_depart
        x_arrivee, y_arrivee = coord_arrivee

        valeur = self.grille[y_depart][x_depart]
        if valeur == 0:
            print(f"Impossible de mettre a jour : case {case_depart} vide")
            return

        self.grille[y_depart][x_depart] = 0
        self.grille[y_arrivee][x_arrivee] = valeur

        pion = self.pions_par_coord.pop(coord_depart, None)
        if pion is not None:
            self.pions_par_coord[coord_arrivee] = pion

        coord_capture = self._coord_capture(case_depart, case_arrivee)
        if coord_capture is not None:
            x_capture, y_capture = coord_capture
            self.grille[y_capture][x_capture] = 0

            pion_capture = self.pions_par_coord.pop(coord_capture, None)
            if pion_capture is not None:
                self.scene.remove_pion(pion_capture)

    def _coord_capture(self, case_depart, case_arrivee):
        x_depart, y_depart = self._case_to_xy(case_depart)
        x_arrivee, y_arrivee = self._case_to_xy(case_arrivee)

        dx = x_arrivee - x_depart
        dy = y_arrivee - y_depart

        if abs(dx) != 2 or abs(dy) != 2:
            return None

        x_capture = x_depart + dx // 2
        y_capture = y_depart + dy // 2

        return (x_capture, 9 - y_capture)

    # =========================================================
    # CASES
    # =========================================================

    def _case_to_xy(self, case):

        if case < 1 or case > 50:
            raise ValueError("case invalide")

        row = (case - 1) // 5
        col_in_row = (case - 1) % 5

        if row % 2 == 0:
            x = 2 + col_in_row * 2
        else:
            x = 1 + col_in_row * 2

        y = 9 - row   # <- IMPORTANT FIX (repère stable blanc)

        # NORMALISATION 0..9 ICI
        return (x - 1, y )

    def _case_to_matrix_xy(self, case):
        x, y = self._case_to_xy(case)
        return (x, 9 - y)

    # =========================================================
    # MONDE 3D (PROPRE, SANS FLIP X ICI)
    # =========================================================

    def _case_to_world(self, x, y):

        wx = x * CASE_WIDTH + CASE_WIDTH_2
        wy = y * CASE_WIDTH + CASE_WIDTH_2

        return (wx, wy, 0)

    # =========================================================
    # ROTATION MATRICE (OK)
    # =========================================================

    def rotation_180(self, matrice):
        return [row[::-1] for row in matrice[::-1]]

    def get_grille(self):
        return [row[:] for row in self.grille]

    # =========================================================
    # API SCENE
    # =========================================================

    def clear_pions(self):
        self.scene.clear_pions()
        self.pions_par_coord.clear()

    def add_pion(self, pos, color):
        return self.scene.add_pion(pos, color)

    def viser_point(self, x, y, z):
        self.scene.bras_viser_point(x, y, z)

    def _viser_task(self, task, x, y, z):
        self.viser_point(x, y, z)
        return task.done

    def bezier_quadratique(self, P0, P1, P2, t):
        x = (1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * P1[0] + t ** 2 * P2[0]
        y = (1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * P1[1] + t ** 2 * P2[1]
        z = (1 - t) ** 2 * P0[2] + 2 * (1 - t) * t * P1[2] + t ** 2 * P2[2]
        return x, y, z

    def deplacer_vers(self, start, end, duration=1.0, pion=None):

        start = (start[0], start[1], start[2] + PION_Z_MINI)
        end = (end[0], end[1], end[2] + PION_Z_MINI)

        mid = (
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2,
            (start[2] + end[2]) / 2 + PION_Z_MAXI
        )

        steps = 30
        dt = duration / steps

        def animation():
            for i in range(steps + 1):
                t = i / steps

                x, y, z = self.bezier_quadratique(start, mid, end, t)

                self.scene.base.taskMgr.add(
                    lambda task, x=x, y=y, z=z: self._deplacer_task(
                        task,
                        x,
                        y,
                        z,
                        pion
                    ),
                    f"move_arm_{i}"
                )

                time.sleep(dt)

        threading.Thread(target=animation, daemon=True).start()

    def _deplacer_task(self, task, x, y, z, pion=None):
        self.viser_point(x, y, z)

        if pion is not None:
            pion.set_position((x, y, z - PION_Z_MINI))

        return task.done


if __name__ == "__main__":
    print("USAGE : python main.py")
