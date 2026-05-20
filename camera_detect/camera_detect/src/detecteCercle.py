import cv2 # pip install opencv-python
import math
import numpy as np

class FastCircleDetector:
    def __init__(self, min_diam=24, max_diam=36, min_dist=35):
    #def __init__(self, min_diam=40, max_diam=48, min_dist=40):
        self.min_r = min_diam // 2
        self.max_r = max_diam // 2
        self.min_dist = min_dist

        # Optimisation : objets réutilisés
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        self.kernel_sharp = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])

        # Variables pour lisser les valeurs (éviter oscillation)
        self.prev_param1 = 90
        self.prev_param2 = 20

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # --- Analyse rapide ---
        mean_brightness = gray.mean()
        contrast = gray.std()
        edge_strength = cv2.Canny(gray, 50, 150).mean()

        # ---- Ajustement automatique ----

        # 1) Amélioration contraste seulement si nécessaire
        if mean_brightness > 150 or contrast < 35:
            gray = self.clahe.apply(gray)
            gray = cv2.filter2D(gray, -1, self.kernel_sharp)

        # 2) Gaussian blur universel
        gray = cv2.GaussianBlur(gray, (7, 7), 2)

        # 3) Param1 : dépend du contraste
        param1 = int(40 + contrast * 0.8)
        param1 = np.clip(param1, 60, 140)

        # lissage
        param1 = int((self.prev_param1 * 0.7) + (param1 * 0.3))
        self.prev_param1 = param1

        # 4) Param2 : dépend de la force des bords
        if edge_strength < 6:
            param2 = 15
        elif edge_strength < 12:
            param2 = 20
        else:
            param2 = 28

        #param2=12

        print("-- param1", param1, "-- param2", param2)

        # lissage
        param2 = int((self.prev_param2 * 0.7) + (param2 * 0.3))
        self.prev_param2 = param2

        # ---- Détection des cercles ----
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=self.min_dist,
            param1=param1,
            param2=param2,
            minRadius=self.min_r,
            maxRadius=self.max_r
        )

        return circles


    def drawCircles(self, frame, circles):
        out = frame.copy()
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for x, y, r in circles[0]:
                cv2.circle(out, (x, y), r, (0,255,0), 2)
                cv2.circle(out, (x, y), 2, (0,0,255), 3)

        return out 





class CircleCluster:
    def __init__(self, x, y, r, max_frames):
        self.x = float(x)
        self.y = float(y)
        self.r = float(r)
        self.count = 1               # Nombre de fois détecté
        self.total = 1               # Nombre de frames passés
        self.max_frames = max_frames

    def matches(self, x, y, r, delta_center, delta_r):
        return abs(self.x - x) <= delta_center and \
               abs(self.y - y) <= delta_center and \
               abs(self.r - r) <= delta_r

    def update(self, x, y, r):
        alpha = 0.25                # lissage exponentiel
        self.x = (1 - alpha) * self.x + alpha * x
        self.y = (1 - alpha) * self.y + alpha * y
        self.r = (1 - alpha) * self.r + alpha * r

        self.count += 1
        self.total += 1

    def no_detection(self):
        self.total += 1

    def probability(self):
        return self.count / self.total

    def is_dead(self):
        return self.total > self.max_frames and self.count == 0

    def get_circle(self):
        return (int(self.x), int(self.y), int(self.r))


class CircleClusterTracker:
    def __init__(self,
                 delta_center=8,
                 delta_r=6,
                 min_probability=0.7,
                 max_frames=100):

        self.delta_center = delta_center
        self.delta_r = delta_r
        self.min_probability = min_probability
        self.max_frames = max_frames

        self.clusters = []

    def update(self, circles):
        """
        circles = [(x, y, r), ...]
        """

        if circles is None:
            circles = []

        # Marquer que pour tous les clusters, un frame est passé
        for c in self.clusters:
            c.no_detection()

        # Tentative d'associer chaque cercle à un cluster existant
        for (x, y, r) in circles:
            matched = False
            for cluster in self.clusters:
                if cluster.matches(x, y, r, self.delta_center, self.delta_r):
                    cluster.update(x, y, r)
                    matched = True
                    break

            if not matched:
                # création d'un nouveau cluster
                self.clusters.append(CircleCluster(x, y, r, self.max_frames))

        # Supprimer les clusters trop vieux ou jamais validés
        self.clusters = [
            c for c in self.clusters
            if not (c.total > self.max_frames and c.probability() < self.min_probability)
        ]

        # Renvoyer les cercles confirmés
        return self.get_confirmed_circles()

    def get_confirmed_circles(self):
        return [
            c.get_circle()
            for c in self.clusters
            if c.probability() >= self.min_probability
        ]




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

    detector = FastCircleDetector(min_diam=30, max_diam=48, min_dist=40)
    circles = detector.detect(img)
    out = detector.drawCircles(img, circles)

    imgSave = "data/detecteCercleWarped.jpg"
    cv2.imwrite(imgSave, out)
    print("--", imgSave)

    cv2.imshow('Fenetre Numero 1', img)
    cv2.imshow('Fenetre Numero 2', out)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

