from detecteDamier import *
from detecteCercle import *


class PionsDetector:

    def __init__(self, nb_cases=10):
        self.nb_cases = nb_cases

        self.damier = DamierDetector(nb_cases)
        #self.circle_detector = FastCircleDetector(40, 45, 40)
        self.circle_detector = FastCircleDetector(min_diam=40, max_diam=48, min_dist=40)

        self.grid = None
        self.warped = None

        # Définition des constantes (Format BGR pour OpenCV ou RGB selon votre usage)
        # Ici nous restons en RGB standard
        self.BGR_ROUGE = np.array([0, 0, 255], dtype=np.float32)
        self.BGR_VERT  = np.array([0, 255, 0], dtype=np.float32)
        self.BGR_BLEU  = np.array([255, 0, 0], dtype=np.float32)
        self.BGR_BLANC = np.array([255, 255, 255], dtype=np.float32)
        self.BGR_NOIR  = np.array([0, 0, 0], dtype=np.float32)
        self.BGR_GRIS  = np.array([128, 128, 128], dtype=np.float32)

        self.equipeCouleurBlanc = np.array(self.BGR_VERT, dtype=np.float32)
        self.equipeCouleurNoir = np.array(self.BGR_ROUGE, dtype=np.float32) 

        self.seuil_couleur = 200  # seuil de tolérance (50 strict et 100 tolérant)

        self.PION_VIDE = 0 
        self.PION_NOIR = self.PION_VIDE + 1 
        self.PION_BLANC = self.PION_NOIR + 1  

        self.hsv_blanc = self._bgr_to_hsv(self.equipeCouleurBlanc)
        self.hsv_noir  = self._bgr_to_hsv(self.equipeCouleurNoir)

        self.tol_h = 15     # tolérance sur la teinte
        self.tol_s = 80     # tolérance saturation
        self.tol_v = 80     # tolérance luminosité


    def _hue_distance(self, h1, h2):
        d = abs(int(h1) - int(h2))
        return min(d, 180 - d)

    def _bgr_to_hsv(self, bgr):
        bgr_uint8 = np.uint8([[bgr]])
        hsv = cv2.cvtColor(bgr_uint8, cv2.COLOR_BGR2HSV)[0][0]
        return hsv



    def process(self, frame):

        self.frame = frame.copy()
        result = self.damier.detectGrid(frame)

        if result is None:
            return None

        grid, warped = result
        self.warped = warped.copy()

        # --- détection des cercles ---
        circles = self.circle_detector.detect(warped)

        if circles is not None:
            circles = np.uint16(np.around(circles))[0]
            #print("-- cercles OK ", len(circles))
        else:
            #print("-- pas de cercles")
            circles = []

        # --- création matrice 10x10 ---
        board = np.zeros((self.nb_cases, self.nb_cases), dtype=int)

        h, w = warped.shape[:2]
        cell_w = w / self.nb_cases
        cell_h = h / self.nb_cases

        # --- mapping cercles -> cases ---
        for (x, y, r) in circles:

            #print("CERCLE ", x, y, r)
            col = int(x // cell_w)
            row = int(y // cell_h)

            if 0 <= row < self.nb_cases and 0 <= col < self.nb_cases:

                # damier : bas gauche = noir
                # conversion repère image -> repère damier
                board_row = self.nb_cases - 1 - row
                board_col = col

                # case noire 
                if (board_row + board_col) % 2 == 0:

                    #print("    --detect ")
                    # board[board_row, board_col] = 1
                    mean_color = self._mean_color_in_circle(warped, x, y, r)
                    team = self._classify_color(mean_color)
                    board[board_row, board_col] = team

        self.grid = board

        return board



    def _mean_color_in_circle(self, img, x, y, r):
    
        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (x, y), int(r * 0.6), 255, -1)  # rayon réduit (évite bord)
        mean_color = cv2.mean(img, mask=mask)[:3]  # BGR
        return np.array(mean_color, dtype=np.float32)


    def _classify_color(self, color_bgr):
    
        # --- conversion en HSV ---
        color_bgr_uint8 = np.uint8([[color_bgr]])
        hsv = cv2.cvtColor(color_bgr_uint8, cv2.COLOR_BGR2HSV)[0][0]
    
        h, s, v = hsv
    
        # --- filtre bruit (gris / sombre) ---
        if s < 50 or v < 50:
            print("-- color du pion NON DETECT ")
            return self.PION_VIDE
    
        # --- couleurs de référence ---
        h_blanc, s_blanc, v_blanc = self.hsv_blanc
        h_noir,  s_noir,  v_noir  = self.hsv_noir
    
        # --- distances ---
        dist_h_blanc = self._hue_distance(h, h_blanc)
        dist_h_noir  = self._hue_distance(h, h_noir)
    
        dist_s_blanc = abs(int(s) - int(s_blanc))
        dist_s_noir  = abs(int(s) - int(s_noir))
    
        dist_v_blanc = abs(int(v) - int(v_blanc))
        dist_v_noir  = abs(int(v) - int(v_noir))
    
        # score global (pondéré)
        score_blanc = dist_h_blanc * 2 + dist_s_blanc + dist_v_blanc
        score_noir  = dist_h_noir  * 2 + dist_s_noir  + dist_v_noir
    
        # --- décision ---
        if score_noir < score_blanc and dist_h_noir < self.tol_h:
            return self.PION_NOIR
    
        if score_blanc < score_noir and dist_h_blanc < self.tol_h:
            return self.PION_BLANC
    
        print(" -- detect pion vide")
        return self.PION_VIDE




    def _classify_color2(self, color):
    
        dist_noir = np.linalg.norm(color - self.equipeCouleurNoir)
        dist_blanc = np.linalg.norm(color - self.equipeCouleurBlanc)
        #print("classifi", color, dist_noir, dist_blanc)
    
        if dist_noir < dist_blanc and dist_noir < self.seuil_couleur:
            return self.PION_NOIR  # équipe noire
    
        if dist_blanc < dist_noir and dist_blanc < self.seuil_couleur:
            return self.PION_BLANC  # équipe blanche
    
        return self.PION_VIDE  # pion inconnu / vide



    def _classify_color3(self, color_bgr):
    
        # convertir en HSV
        color_bgr_uint8 = np.uint8([[color_bgr]])
        hsv = cv2.cvtColor(color_bgr_uint8, cv2.COLOR_BGR2HSV)[0][0]
    
        h, s, v = hsv
    
        # --- seuils ---
        seuil_saturation = 60   # ignore gris / blanc / noir
        seuil_value_min = 50    # ignore très sombre
    
        if s < seuil_saturation or v < seuil_value_min:
            return self.PION_VIDE
    
        # --- plages de teinte (à ajuster si besoin) ---
        # rouge = autour de 0 ET 179
        rouge1_min, rouge1_max = 0, 10
        rouge2_min, rouge2_max = 170, 179
    
        # vert
        vert_min, vert_max = 40, 85
    
        # --- classification ---
        if (rouge1_min <= h <= rouge1_max) or (rouge2_min <= h <= rouge2_max):
            return self.PION_NOIR  # ton équipe rouge
    
        if vert_min <= h <= vert_max:
            return self.PION_BLANC  # ton équipe verte
    
        return self.PION_VIDE





    def draw_board_overlay(self):
    
        if self.warped is None or self.grid is None:
            return None
    
        img = self.warped.copy()
        h, w = img.shape[:2]
        cell_w = w // self.nb_cases
        cell_h = h // self.nb_cases
    
        for r in range(self.nb_cases):
            for c in range(self.nb_cases):
                if self.grid[r, c] == self.PION_NOIR or self.grid[r, c] == self.PION_BLANC : # noir en bas a gauche (les points sur les noirs)
                    x = int(c * cell_w + cell_w / 2)
                    y = int((self.nb_cases - 1 - r) * cell_h + cell_h / 2)
                    # cv2.circle(img, (x, y), 10, (0, 0, 255), -1)
                    if self.grid[r, c] == self.PION_BLANC:
                        cv2.circle(img, (x, y), 10, (255, 255, 255), -1)
                    elif self.grid[r, c] == self.PION_NOIR:
                        cv2.circle(img, (x, y), 10, (0, 0, 0), -1)
                    else:
                        continue
    
        return img

    def draw_board_pions(self, imageSize=100):
        nb = self.nb_cases
    
        # image vide (blanche)
        img = np.ones((imageSize, imageSize, 3), dtype=np.uint8) * 255
    
        cell_w = imageSize // nb
        cell_h = imageSize // nb
    
        for r in range(nb):
            for c in range(nb):
                # --- Couleur de la case ---
                # bas gauche = gris => (nb-1-r + c) pair
                if ( (nb - 1 - r) + c ) % 2 == 1:
                    color_case = (128, 128, 128)  # gris
                else:
                    color_case = (255, 255, 255)  # blanc
    
                # coordonnées du carré
                x1 = c * cell_w
                y1 = (nb - 1 - r) * cell_h
                x2 = x1 + cell_w
                y2 = y1 + cell_h
    
                # dessiner la case
                cv2.rectangle(img, (x1, y1), (x2, y2), color_case, -1)
    
                # --- Dessin du pion ---
                if self.grid[r, c] == self.PION_BLANC:
                    cx = x1 + cell_w // 2
                    cy = y1 + cell_h // 2
                    cv2.circle(img, (cx, cy), min(cell_w, cell_h)//3, (255, 255, 255), -1)
    
                elif self.grid[r, c] == self.PION_NOIR:
                    cx = x1 + cell_w // 2
                    cy = y1 + cell_h // 2
                    cv2.circle(img, (cx, cy), min(cell_w, cell_h)//3, (0, 0, 0), -1)
    
        return img



    def draw_image(self):
    
        if self.warped is None or self.grid is None:
            return self.frame

        img_fond = self.frame
        img_logo = self.draw_board_pions()
        
        redim=100
        logo_redimensionne = cv2.resize(img_logo, (redim, redim))
        
        h_fond, w_fond = img_fond.shape[:2]
        
        # On veut placer l'image de 50x50 tout en bas à droite
        # On définit la zone de destination (ROI)
        y1, y2 = h_fond - redim, h_fond
        x1, x2 = w_fond - redim, w_fond
        
        # Incruster l'image
        img_fond[y1:y2, x1:x2] = logo_redimensionne

        return img_fond
       





if __name__ == '__main__':

    #imageName = "data/damierPerspective1.jpg" # non
    imageName = "data/damierPerspective2.jpg" # non
    #imageName = "data/damierPerspective3.jpg" # non
    #imageName = "data/image_damier_pions.jpg" # ok
    #imageName = "data/image_damier_pions2.jpg" # ok
    #imageName = "data/webcam_damier_perspective.jpg" # ok
    
    img = cv2.imread(imageName)

    detectionPions = PionsDetector(10)
    board = detectionPions.process(img)
    
    if board is None:
        print("-- pas detecté ")
    else:
        inversee = np.flipud(board)
        print(inversee)
    
    #out = detectionPions.draw_board_overlay()
    out = detectionPions.draw_image()

    #cv2.imshow('Fenetre Numero 1', img)
    cv2.imshow('detection pion damier', out)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


