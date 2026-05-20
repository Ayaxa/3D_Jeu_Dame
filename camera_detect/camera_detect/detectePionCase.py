import cv2
import os
import numpy as np

from detectePions import *


class DetectePionCase:

    PION_VIDE = 0
    PION_VERT = 1
    PION_ROUGE = 2

    def __init__(self):
        # seuils HSV (à ajuster selon ton éclairage)
        self.tol_h = 15

        # références HSV (à calibrer une fois)
        self.hsv_vert = np.array([60, 150, 150])
        self.hsv_rouge = np.array([0, 150, 150])

    # ===============================
    # FONCTION PRINCIPALE
    # ===============================
    def detect(self, img_warped, grid):

        rows = grid.shape[0] - 1
        cols = grid.shape[1] - 1

        result = np.zeros((rows, cols), dtype=np.uint8)

        for r in range(rows):
            for c in range(cols):

                # damier : case noire seulement
                if (r + c) % 2 == 0:
                    continue

                roi = self._extract_cell(img_warped, grid, r, c)

                if roi is None or roi.size == 0:
                    continue

                color = self._mean_color(roi)

                label = self._classify_color(color)

                result[r, c] = label

        return result

    # ===============================
    # EXTRACTION CASE
    # ===============================
    def _extract_cell(self, img, grid, r, c, margin=0.2):

        p1 = grid[r, c]
        p2 = grid[r, c + 1]
        p3 = grid[r + 1, c + 1]
        p4 = grid[r + 1, c]

        x_min = int(min(p1[0], p2[0], p3[0], p4[0]))
        x_max = int(max(p1[0], p2[0], p3[0], p4[0]))
        y_min = int(min(p1[1], p2[1], p3[1], p4[1]))
        y_max = int(max(p1[1], p2[1], p3[1], p4[1]))

        # marge interne (important !)
        dx = int((x_max - x_min) * margin)
        dy = int((y_max - y_min) * margin)

        x_min += dx
        x_max -= dx
        y_min += dy
        y_max -= dy

        return img[y_min:y_max, x_min:x_max]

    # ===============================
    # COULEUR MOYENNE ROBUSTE
    # ===============================
    def _mean_color(self, roi):

        # flou pour lisser bruit
        roi_blur = cv2.GaussianBlur(roi, (5, 5), 0)

        # moyenne BGR
        mean = np.mean(roi_blur.reshape(-1, 3), axis=0)

        return mean.astype(np.uint8)

    # ===============================
    # CLASSIFICATION HSV
    # ===============================
    def _classify_color(self, color_bgr):

        color = np.uint8([[color_bgr]])
        hsv = cv2.cvtColor(color, cv2.COLOR_BGR2HSV)[0][0]

        h, s, v = hsv

        # filtre bruit
        if s < 60 or v < 60:
            return self.PION_VIDE

        # distances de teinte
        dist_vert = self._hue_distance(h, self.hsv_vert[0])
        dist_rouge = min(
            self._hue_distance(h, self.hsv_rouge[0]),
            self._hue_distance(h, 180)  # rouge wrap HSV
        )

        if dist_vert < self.tol_h:
            return self.PION_VERT

        if dist_rouge < self.tol_h:
            return self.PION_ROUGE

        return self.PION_VIDE

    # ===============================
    # DISTANCE CIRCULAIRE HUE
    # ===============================
    def _hue_distance(self, h1, h2):
        d = abs(int(h1) - int(h2))
        return min(d, 180 - d)




    def draw_result_overlay(self, frame, warped, grid, matrix, size=150):
    
        if warped is None or grid is None or matrix is None:
            return frame
    
        overlay = warped.copy()
    
        rows, cols = matrix.shape
    
        for r in range(rows):
            for c in range(cols):
    
                val = matrix[r, c]
    
                if val == self.PION_VIDE:
                    continue
    
                # centre de la case
                p1 = grid[r, c]
                p2 = grid[r, c + 1]
                p3 = grid[r + 1, c + 1]
                p4 = grid[r + 1, c]
    
                cx = int((p1[0] + p2[0] + p3[0] + p4[0]) / 4)
                cy = int((p1[1] + p2[1] + p3[1] + p4[1]) / 4)
    
                # rayon basé sur taille case
                w = np.linalg.norm(p1 - p2)
                h = np.linalg.norm(p1 - p4)
                radius = int(min(w, h) * 0.3)
    
                # couleur
                if val == self.PION_VERT:
                    color = (0, 255, 0)
                elif val == self.PION_ROUGE:
                    color = (0, 0, 255)
                else:
                    continue
    
                # dessin
                cv2.circle(overlay, (cx, cy), radius, color, 2)
    
        # ===============================
        # INCRUSTATION DANS IMAGE ORIGINE
        # ===============================
        img_out = frame.copy()
    
        overlay_resized = cv2.resize(overlay, (size, size))
    
        h, w = img_out.shape[:2]
    
        y1, y2 = h - size, h
        x1, x2 = w - size, w
    
        img_out[y1:y2, x1:x2] = overlay_resized
    
        return img_out






if __name__ == '__main__':

    os.makedirs("data", exist_ok=True)

    #imageName = "data/damierPerspective1.jpg" # non
    #imageName = "data/damierPerspective2.jpg" # non
    #imageName = "data/damierPerspective3.jpg" # non
    #imageName = "data/damierPerspectiveSansPion.jpg" # ok
    #imageName = "data/damierPerspectiveSansPion2.jpg" # ok
    #imageName = "data/image_damier.jpg" # ok
    #imageName = "data/image_damier_pions.jpg" # ok
    #imageName = "data/image_damier_pions2.jpg" # ok
    #imageName = "data/webcam_damier_perspective.jpg" # non
    #imageName = "data/webcam_damier_pions.jpg" # non
    imageName = "data/webcam_damier_pions2.jpg" # non
    img = cv2.imread(imageName)

    if img is None:
        print("-- erreur lecture image")
        exit(1)

    # detection du damier
    detectorDamier = DamierDetector(10)
    result = detectorDamier.detectGrid(img)

    if result is None:
        print("-- damier NON detecte")
        out = img
    else:
        print("-- damier detecte")
        grid, warped = result
        out = detectorDamier.draw_checkerboard_segments(warped.copy(), grid)

        detectorPions = DetectePionCase()
        matrix = detectorPions.detect(warped, grid)
        print(matrix)

