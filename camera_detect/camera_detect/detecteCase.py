import cv2 # pip install opencv-python
import math
import numpy as np



class DetecteCase:

    def __init__(self, taille_grille=10):
        self.taille_grille = taille_grille


    def detecter(self, image_damier):
        h, w = image_damier.shape[:2]
        case_h = h // self.taille_grille
        case_w = w // self.taille_grille

        matrice = np.zeros((self.taille_grille, self.taille_grille), dtype=int)

        for row in range(self.taille_grille):
            for col in range(self.taille_grille):

                # 🟫 On ignore les cases blanches
                if not self._est_case_noire(row, col):
                    continue

                y1 = row * case_h
                y2 = (row + 1) * case_h
                x1 = col * case_w
                x2 = (col + 1) * case_w

                case_img = image_damier[y1:y2, x1:x2]

                valeur = self._analyser_case(case_img)
                matrice[row, col] = valeur

        return matrice


    def _analyser_case(self, case_img):
        # On réduit le bruit
        case_img = cv2.GaussianBlur(case_img, (5, 5), 0)

        # On convertit en HSV
        hsv = cv2.cvtColor(case_img, cv2.COLOR_BGR2HSV)

        # Moyenne couleur
        mean_color = np.mean(hsv.reshape(-1, 3), axis=0)

        return self._classify_color(mean_color)


    def _extraire_zone_centrale(self, case_img):
        h, w = case_img.shape[:2]

        margin = int(min(h, w) * 0.25)

        return case_img[
            margin:h-margin,
            margin:w-margin
        ]

    def _est_case_noire(self, row, col):
        return (row + col) % 2 == 1

    def _classify_color(self, hsv):
        h, s, v = hsv

        # Rouge
        if (h < 10 or h > 170) and s > 100:
            return 1

        # Vert
        if 40 < h < 90 and s > 100:
            return 2

        return 0



if __name__ == '__main__':

    # teste la detection de cercles
    imageName = "data/damierPerspective1.jpg" # non
    #imageName = "data/damierPerspective2.jpg" # non
    #imageName = "data/damierPerspective3.jpg" # non
    #imageName = "data/image_damier_pions.jpg" # ok
    #imageName = "data/image_damier_pions2.jpg" # ok
    #imageName = "data/webcam_damier_perspective.jpg" # non
    #imageName = "data/warped.jpg"
    img = cv2.imread(imageName)

    if img is None:
        print("-- erreur lecture image")
        exit(1)

    
    damier = detecteDamier.detecter(img)
    
    detecteur = DetecteCase()
    matrice = detecteur.detecter(damier)
    
    print(matrice)


