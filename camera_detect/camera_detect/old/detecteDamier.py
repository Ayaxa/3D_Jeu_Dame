import cv2
import numpy as np
import os


class DamierDetector:

    def __init__(self, nb_cases_x, nb_cases_y):
        self.nb_cases_x = nb_cases_x
        self.nb_cases_y = nb_cases_y
        self.pattern_size = (nb_cases_x - 1, nb_cases_y - 1)

        self.corners = None
        self.found = False




    def detectGrid(self, img):

        self.img = img.copy()

        # 1. détection initiale
        if not self._detectCorner(self.img):
            self.img_warped = None
            return None

        # 2. warp
        warped = self._get_warped_board(self.img)

        if warped is None:
            self.img_warped = None
            return None

        # après warp
        gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        
        # coin bas gauche (normalement noir)
        patch = gray[-20:, :20]
        mean_val = np.mean(patch)
        
        # si blanc → flip vertical
        if mean_val > 128:
            warped = cv2.flip(warped, 0)

        self.img_warped = warped.copy()
        # cv2.imwrite("data/warped.jpg", warped)

        # 3. redétection sur image corrigée
        if not self._detectCorner(self.img_warped):
            return None

        # 4. calcul grille finale
        grid = self.compute_full_grid()

        return grid, warped


    def _normalize_corners(self):
        """
        Garantit :
        - coins[0,0] = haut gauche
        - coins[0,-1] = haut droite
        - coins[-1,0] = bas gauche
        """
    
        c = self.corners
    
        # vecteurs moyens
        step_x = np.mean(c[:, 1:] - c[:, :-1], axis=(0, 1))
        step_y = np.mean(c[1:, :] - c[:-1, :], axis=(0, 1))
    
        # flip horizontal si nécessaire
        if step_x[0] < 0:
            c = np.flip(c, axis=1)
    
        # flip vertical si nécessaire
        if step_y[1] < 0:
            c = np.flip(c, axis=0)
    
        self.corners = c





    def _detectCorner2(self, img):

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


        flags = cv2.CALIB_CB_EXHAUSTIVE + cv2.CALIB_CB_ACCURACY + cv2.CALIB_CB_NORMALIZE_IMAGE

        ret, corners = cv2.findChessboardCorners(gray, self.pattern_size, None)
        #ret, corners = cv2.findChessboardCornersSB(gray, self.pattern_size, None)

        if ret:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

            self.corners = corners.reshape(self.pattern_size[1], self.pattern_size[0], 2)
            self._normalize_corners()
            self.found = True
        else:
            self.found = False

        return self.found


    def _detectCorner(self, img):
    
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
        # ==============================
        # 1. tentative SB (robuste mais exigeant)
        # ==============================
        gray_sb = cv2.equalizeHist(gray)
        gray_sb = cv2.GaussianBlur(gray_sb, (5, 5), 0)
    
        flags = (cv2.CALIB_CB_EXHAUSTIVE |
                 cv2.CALIB_CB_ACCURACY |
                 cv2.CALIB_CB_NORMALIZE_IMAGE)
    
        ret, corners = cv2.findChessboardCornersSB(gray_sb, self.pattern_size, flags)
    
        # ==============================
        # 2. fallback classique (plus tolérant)
        # ==============================
        if not ret:
            flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
            ret, corners = cv2.findChessboardCorners(gray, self.pattern_size, flags)
    
            if ret:
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    
        # ==============================
        # 3. validation
        # ==============================
        if ret:
            self.corners = corners.reshape(self.pattern_size[1], self.pattern_size[0], 2)
            self._normalize_corners()
            self.found = True
        else:
            self.found = False
    
        return self.found




    def compute_full_grid(self):

        if not self.found or self.corners is None:
            return None

        rows, cols = self.pattern_size[1], self.pattern_size[0]
        corners = self.corners

        step_x = np.mean(corners[:, 1:] - corners[:, :-1], axis=(0, 1))
        step_y = np.mean(corners[1:, :] - corners[:-1, :], axis=(0, 1))

        grid = np.zeros((rows + 2, cols + 2, 2), dtype=np.float32)

        for r in range(rows + 2):
            for c in range(cols + 2):

                rr = np.clip(r - 1, 0, rows - 1)
                cc = np.clip(c - 1, 0, cols - 1)

                base = corners[rr, cc]

                dx = (c - 1 - cc)
                dy = (r - 1 - rr)

                grid[r, c] = base + dx * step_x + dy * step_y

        return grid.astype(int)





    def draw_checkerboard_segments(self, img, grid):

        out=img.copy()

        if grid is None:
            return out

        rows, cols = grid.shape[0] - 1, grid.shape[1] - 1

        for r in range(rows + 1):
            for c in range(cols):
                cv2.line(out, tuple(grid[r, c]), tuple(grid[r, c + 1]), (0, 0, 255), 2)

        for c in range(cols + 1):
            for r in range(rows):
                cv2.line(out, tuple(grid[r, c]), tuple(grid[r + 1, c]), (0, 0, 255), 2)

        return out




    def _get_warped_board(self, img, output_size=500):

        if not self.found or self.corners is None:
            return None

        rows, cols = self.pattern_size[1], self.pattern_size[0]
        corners = self.corners

        step_x = np.mean(corners[:, 1:] - corners[:, :-1], axis=(0, 1))
        step_y = np.mean(corners[1:, :] - corners[:-1, :], axis=(0, 1))


        tl = corners[0, 0]
        tr = corners[0, -1]
        bl = corners[-1, 0]
        br = corners[-1, -1]
        
        # correction orientation AVANT extrapolation
        v1 = tr - tl
        v2 = bl - tl
        cross = v1[0]*v2[1] - v1[1]*v2[0]
        
        if cross < 0:
            tr, bl = bl, tr
        
        # recalcul step APRÈS correction (important !)
        step_x = (tr - tl) / (cols - 1)
        step_y = (bl - tl) / (rows - 1)
        

        
        # correction miroir gauche/droite
        if step_x[0] < 0:
            tr, tl = tl, tr
            br, bl = bl, br
        
            # recalcul après swap
            step_x = (tr - tl) / (cols - 1)
            step_y = (bl - tl) / (rows - 1)

        # correction miroir haut/bas
        if step_y[1] < 0:
            tl, bl = bl, tl
            tr, br = br, tr
        
            step_x = (tr - tl) / (cols - 1)
            step_y = (bl - tl) / (rows - 1)

        # extrapolation correcte
        tl_ext = tl - step_x - step_y
        tr_ext = tr + step_x - step_y
        bl_ext = bl - step_x + step_y
        br_ext = br + step_x + step_y
        
        src = np.array([tl_ext, tr_ext, br_ext, bl_ext], dtype=np.float32)


        dst = np.array([
            [0, 0],
            [output_size, 0],
            [output_size, output_size],
            [0, output_size]
        ], dtype=np.float32)

        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(img, M, (output_size, output_size))

        return warped




    def drawImage(self):
    
        if not self.found or self.corners is None:
            return self.img.copy()

        # 1. Charger les images
        # img_fond: 640x480 | img_logo: 500x500
        img_fond = self.img.copy()
        img_logo = self.img_warped.copy()
        
        redim=100
        # 2. Redimensionner la deuxième image en 50x50
        logo_redimensionne = cv2.resize(img_logo, (redim, redim))
        
        # 3. Définir les coordonnées du coin en bas à droite
        # Hauteur (h) et Largeur (w) du fond
        h_fond, w_fond = img_fond.shape[:2]
        
        # On veut placer l'image de 50x50 tout en bas à droite
        # On définit la zone de destination (ROI)
        y1, y2 = h_fond - redim, h_fond
        x1, x2 = w_fond - redim, w_fond
        
        # 4. Incruster l'image
        # On remplace la zone cible par le logo
        img_fond[y1:y2, x1:x2] = logo_redimensionne

        return img_fond
        



if __name__ == '__main__':

    os.makedirs("data", exist_ok=True)
    #imageName = "data/damierPerspective1.jpg" # non
    #imageName = "data/damierPerspective2.jpg" # non
    #imageName = "data/damierPerspective3.jpg" # non
    #imageName = "data/damierPerspectiveSansPion.jpg" # ok
    #imageName = "data/damierPerspectiveSansPion2.jpg" # ok
    #imageName = "data/image_damier.jpg" # inversé
    #imageName = "data/image_damier_pions.jpg" # inversé
    #imageName = "data/image_damier_pions2.jpg" # ok
    imageName = "data/webcam_damier_perspective.jpg" # non
    img = cv2.imread(imageName)

    if img is None:
        print("-- erreur lecture image")
        exit(1)

    detector = DamierDetector(10, 10)
    result = detector.detectGrid(img)

    if result is None:
        print("-- damier NON detecte")
        out = img
    else:
        grid, warped = result
        print("-- damier detecte")
        out = detector.draw_checkerboard_segments(warped.copy(), grid)

    img_fond = detector.drawImage()

    imgSave = "data/detecteDamier.jpg"
    cv2.imwrite(imgSave, img_fond)
    print("--", imgSave)

    cv2.imshow('image origine', img)
    cv2.imshow('image quadrillage', out)
    cv2.imshow('Fenetre Numero 3', img_fond)

    cv2.waitKey(0)
    cv2.destroyAllWindows()


