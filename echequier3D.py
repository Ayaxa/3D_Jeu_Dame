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
        self.pions_par_xy = {}
        self.pions_perdus = []

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

                xy = (x, 9-y)
                pos = self._case_to_world(*xy)

                color = BLEU if val == 1 else VERT
                pion = self.add_pion(pos, color)
                self.pions_par_xy[xy] = pion

    # =========================================================
    # COUPS (DOIT UTILISER MÊME REPERE QUE MATRICE TRANSFORMEE)
    # =========================================================

    def jouer_coups(self, liste_cases):

        if len(liste_cases) < 2:
            return

        chemin_xy = [self._case_to_xy(case) for case in liste_cases]
        pieces_mangees_xy = self._pieces_mangees_sur_chemin(chemin_xy)
        coords = [self._case_to_world(x, y) for x, y in chemin_xy]

        pos_init = (POS_BRAS_REPOS_X, POS_BRAS_REPOS_Y, POS_BRAS_REPOS_Z)
        pion_joue = self.pions_par_xy.get(chemin_xy[0])

        def animation():
            position_bras = pos_init

            if pion_joue is None:
                chemin_bras = [pos_init] + coords + [pos_init]

                for i in range(len(chemin_bras) - 1):
                    self._animer_trajectoire(
                        chemin_bras[i],
                        chemin_bras[i + 1],
                        DUREE_ANIM
                    )

                return

            self.pions_par_xy.pop(chemin_xy[0], None)
            self._animer_trajectoire(position_bras, coords[0], DUREE_ANIM)
            position_bras = coords[0]

            for i in range(len(coords) - 1):
                self._animer_trajectoire(
                    coords[i],
                    coords[i + 1],
                    DUREE_ANIM,
                    pion=pion_joue
                )
                position_bras = coords[i + 1]

            self.pions_par_xy[chemin_xy[-1]] = pion_joue

            for piece_xy in pieces_mangees_xy:
                position_bras = self._animer_piece_perdue(piece_xy, position_bras)

            self._animer_trajectoire(position_bras, pos_init, DUREE_ANIM)

        threading.Thread(target=animation, daemon=True).start()

    def piece_perdu(self, cases):
        pieces_xy = self._normaliser_cases_perdues(cases)
        if not pieces_xy:
            return

        pos_init = (POS_BRAS_REPOS_X, POS_BRAS_REPOS_Y, POS_BRAS_REPOS_Z)

        def animation():
            position_bras = pos_init

            for piece_xy in pieces_xy:
                position_bras = self._animer_piece_perdue(piece_xy, position_bras)

            self._animer_trajectoire(position_bras, pos_init, DUREE_ANIM)

        threading.Thread(target=animation, daemon=True).start()

    def _normaliser_cases_perdues(self, cases):
        if cases is None:
            return []

        if isinstance(cases, int):
            return [self._case_to_xy(cases)]

        if self._est_coord_xy(cases):
            return [tuple(cases)]

        pieces_xy = []

        for case in cases:
            if isinstance(case, int):
                pieces_xy.append(self._case_to_xy(case))
            elif self._est_coord_xy(case):
                pieces_xy.append(tuple(case))

        return pieces_xy

    def _est_coord_xy(self, valeur):
        return (
            isinstance(valeur, (tuple, list))
            and len(valeur) == 2
            and all(isinstance(coord, (int, float)) for coord in valeur)
        )

    def _pieces_mangees_sur_chemin(self, chemin_xy):
        pieces_mangees = []

        for depart, arrivee in zip(chemin_xy, chemin_xy[1:]):
            dx = arrivee[0] - depart[0]
            dy = arrivee[1] - depart[1]

            if dx == 0 or dy == 0 or abs(dx) != abs(dy):
                continue

            pas_x = 1 if dx > 0 else -1
            pas_y = 1 if dy > 0 else -1
            x = depart[0] + pas_x
            y = depart[1] + pas_y

            while (x, y) != arrivee:
                if (x, y) in self.pions_par_xy:
                    pieces_mangees.append((x, y))
                x += pas_x
                y += pas_y

        return pieces_mangees

    def _animer_piece_perdue(self, piece_xy, position_bras):
        pion = self.pions_par_xy.pop(piece_xy, None)

        if pion is None:
            return position_bras

        depart = self._case_to_world(*piece_xy)
        arrivee = self._position_piece_perdue()

        self._animer_trajectoire(position_bras, depart, DUREE_ANIM)
        self._animer_trajectoire(depart, arrivee, DUREE_ANIM, pion=pion)

        self.pions_perdus.append(pion)
        return arrivee

    def _position_piece_perdue(self):
        index = len(self.pions_perdus)
        ligne = index % PIECES_PERDUES_PAR_COLONNE
        colonne = index // PIECES_PERDUES_PAR_COLONNE

        x = PIECES_PERDUES_X - colonne * PIECES_PERDUES_SPACING
        y = PIECES_PERDUES_Y + ligne * PIECES_PERDUES_SPACING

        return (x, y, 0)

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
        self.pions_par_xy.clear()
        self.pions_perdus.clear()
        self.scene.clear_pions()

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

    def deplacer_vers(self, start, end, duration=1.0):
        threading.Thread(
            target=self._animer_trajectoire,
            args=(start, end, duration),
            daemon=True
        ).start()

    def _animer_trajectoire(self, start, end, duration=1.0, pion=None):

        start = (start[0], start[1], start[2] + PION_Z_MINI)
        end = (end[0], end[1], end[2] + PION_Z_MINI)

        mid = (
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2,
            (start[2] + end[2]) / 2 + PION_Z_MAXI
        )

        steps = 30
        dt = duration / steps

        for i in range(steps + 1):
            t = i / steps

            x, y, z = self.bezier_quadratique(start, mid, end, t)

            if pion is None:
                self.add_command(self.viser_point, x, y, z)
            else:
                z_pion = max(0, z - PION_Z_MINI)
                self.add_command(self._placer_bras_et_pion, pion, x, y, z, z_pion)

            time.sleep(dt)

    def _placer_bras_et_pion(self, pion, x, y, z_bras, z_pion):
        self.viser_point(x, y, z_bras)
        pion.set_position((x, y, z_pion))


if __name__ == "__main__":
    print("USAGE : python main.py")
