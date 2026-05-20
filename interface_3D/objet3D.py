from panda3d.core import *
from panda3d.core import CardMaker
from define import *

import math

class BrasArticule:

    def __init__(self, base, render):
        self.base = base
        self.render= render

        cube = self.base.loader.loadModel("models/misc/rgbCube")

        self.pivot0 = self.render.attachNewNode("pivot0")
        self.pivot0.setPos( POS_BRAS_INIT_X, POS_BRAS_INIT_Y, POS_BRAS_INIT_Z)

        self.pied = cube.copyTo(self.pivot0)
        self.pied.setScale(CASE_WIDTH*2, CASE_WIDTH*2, CASE_WIDTH_2)
        self.pied.setPos(0, 0, 0)

        # axe fixe pour garder le bon repère
        self.pivot1_axis = self.pivot0.attachNewNode("pivot1_axis")

        # pivot de rotation bras1
        self.pivot1 = self.pivot1_axis.attachNewNode("pivot1")

        self.bras1 = cube.copyTo(self.pivot1)
        self.bras1.setScale(BRAS_LENGTH, BRAS_WIDTH, BRAS_WIDTH)
        self.bras1.setPos(BRAS_LENGTH_2, 0, 0)

        # pivot2 positionné en bout du bras1
        self.pivot2_axis = self.pivot1.attachNewNode("pivot2_axis")
        self.pivot2_axis.setPos(BRAS_LENGTH, 0, 0)

        self.pivot2 = self.pivot2_axis.attachNewNode("pivot2")

        self.bras2 = cube.copyTo(self.pivot2)
        self.bras2.setScale(BRAS_LENGTH, BRAS_WIDTH, BRAS_WIDTH)
        self.bras2.setPos(BRAS_LENGTH_2 , 0, 0)

        self.pivot0.setColor(NOIR)
        self.pivot1.setColor(NOIR)
        self.pivot2.setColor(NOIR)
        self.bras1.setColor(VERT)
        self.bras2.setColor(BLEU)

        self.viser_point(
            POS_BRAS_REPOS_X,
            POS_BRAS_REPOS_Y,
            POS_BRAS_REPOS_Z)

    def rotation(self, angle0, angle1, angle2):

        self.pivot0.setH( angle0)
        self.pivot1.setP( angle1)
        self.pivot2.setP( angle2)


    def viser_point(self, x_case, y_case, z_case):

        #print("--------------------")
        #print("point :",  x_case, y_case, z_case)
    
        # centre de la case
        target_x = x_case
        target_y = y_case
        target_z = z_case 
    
        # position du pivot0
        base_pos = self.pivot0.getPos(self.render)
    
        dx = target_x - base_pos.x
        dy = target_y - base_pos.y
        dz = target_z - base_pos.z
        #print("dx dy dz:", dx, dy, dz)
    
        # rotation pivot0 (orientation horizontale)
        angle0 = math.degrees(math.atan2(dy, dx))
        self.pivot0.setH(angle0)
        #print("angle0 :", angle0)
    
        # distance horizontale
        dist_xy = math.sqrt(dx*dx + dy*dy)
    
        # IK dans le plan (distance = horizontal, hauteur = z)
        x = dist_xy
        z = dz
    
        # clamp pour éviter erreurs acos
        OM = math.sqrt(x*x + z*z)
        max_reach = 2 * BRAS_LENGTH
    
        if OM > max_reach:
            x *= max_reach / OM
            z *= max_reach / OM
            OM = math.sqrt(x*x + z*z)
        #print("x et z", x, z)

        if OM < 0.0001:
            return

        alphaDelta = - math.atan(z/x)
    
        alpha1 = - math.acos(x/(2*BRAS_LENGTH))
        self.pivot1.setR(math.degrees(alpha1 + alphaDelta))

        alpha2 = - alpha1 * 2
        self.pivot2.setR(math.degrees(alpha2))



class Pion:

    model = None  # cylindre 3D partagé

    def __init__(self, base, position=(0, 0, 0), couleur=ROUGE):
        self.base = base

        # Chargement du modèle
        if Pion.model is None:
            Pion.model = base.loader.loadModel("data/pion.glb")

        self.node = Pion.model.copyTo(base.render)

        # Scale / orientation
        self.node.setScale(0.3*CASE_WIDTH, 0.08*CASE_WIDTH, 0.3*CASE_WIDTH)
        self.node.setHpr(0, -90, 0)

        # Couleur
        self.set_color(couleur)

        # Position initiale
        self.set_position(position)

    # --- Position ---
    def set_position(self, position):
        x, y, z = position
        self.node.setPos(x, y, z)

    def get_position(self):
        return self.node.getPos()

    # --- Couleur ---
    def set_color(self, couleur):
        self.node.setColor(*couleur)

    # --- Suppression ---
    def destroy(self):
        self.node.removeNode()



class Plateau:

    def __init__(self, base, render):
        self.base = base
        self.render= render

        cm = CardMaker("board")
        cm.setFrame(-5*CASE_WIDTH, 5*CASE_WIDTH, -5*CASE_WIDTH, 5*CASE_WIDTH)
        
        self.board = self.render.attachNewNode(cm.generate())
        self.board.setPos(5*CASE_WIDTH, 5*CASE_WIDTH, 0)
        self.board.setHpr(0, -90, 0)
        
        tex = self.base.loader.loadTexture("data/checker2.png")
        self.board.setTexture(tex)



class Webcam:

    def __init__(self, base, render):
        self.base = base
        self.render= render

        cube = self.base.loader.loadModel("models/misc/rgbCube")
        sphere = self.base.loader.loadModel("models/misc/sphere")

        self.socle = self.render.attachNewNode("socle")
        self.socle.setPos( WEBCAM_POS_X, WEBCAM_POS_Y, 0)
        #self.socle.set_color(ROUGE)

        self.pied = cube.copyTo(self.socle)
        self.pied.setScale(CASE_WIDTH*2, CASE_WIDTH*2, CASE_WIDTH_2)
        self.pied.setPos(0, 0, 0)

        self.tige = cube.copyTo(self.socle)
        self.tige.setScale( CASE_WIDTH_2, CASE_WIDTH_2, WEBCAM_TIGE_LENGTH)
        self.tige.setPos(0, 0, WEBCAM_TIGE_LENGTH_2)

        self.tige_top = self.tige.attachNewNode("tige_top")
        self.tige_top.setPos(0, 0, WEBCAM_TIGE_LENGTH)

        self.webcam = sphere.copyTo(self.socle)
        self.webcam.setScale( CASE_WIDTH)
        self.webcam.setPos(0, -CASE_WIDTH, WEBCAM_POS_Z)



class AxesDebug :

    def __init__(self, base, render):
        self.base = base
        self.render= render

        self.axis = self.base.loader.loadModel("models/misc/xyzAxis")
        self.axis.reparentTo(self.render)
        self.axis.setPos(0, 0, -0.1)


if __name__ == "__main__":

    print("execute plutot :")
    print("python main.py")

