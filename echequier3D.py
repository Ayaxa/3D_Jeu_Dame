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

        for y in range(10):
            for x in range(10):

                val = matrice[y][x]

                if val == 0:
                    continue

                pos = self._case_to_world(x, 9-y)

                color = ROUGE if val == 1 else BLEU
                self.add_pion(pos, color)

    # =========================================================
    # COUPS (DOIT UTILISER MÊME REPERE QUE MATRICE TRANSFORMEE)
    # =========================================================

    def jouer_coups(self, liste_cases):

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

                self.add_command(self.deplacer_vers, start, end, DUREE_ANIM)
                time.sleep(DUREE_ANIM * 2)

        threading.Thread(target=animation, daemon=True).start()

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

    # =========================================================
    # API SCENE
    # =========================================================

    def clear_pions(self):
        self.scene.clear_pions()

    def add_pion(self, pos, color):
        self.scene.add_pion(pos, color)

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

    def deplacer_vers(self, start, end, duration=1.0):

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
                    lambda task, x=x, y=y, z=z: self._viser_task(task, x, y, z),
                    f"move_arm_{i}"
                )

                time.sleep(dt)

        threading.Thread(target=animation, daemon=True).start()


if __name__ == "__main__":
    print("USAGE : python main.py")
