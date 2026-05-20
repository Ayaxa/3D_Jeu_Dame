from objet3D import *


class Scene:

    def __init__(self, base):
        self.base = base
        self.render = base.render

        # Liste d'objets (optionnel mais utile)
        self.objects = []

        self.pions = []

        self.init_scene()

    def init_scene(self):
        # --- CUBE rotatif
        #cube = self.base.loader.loadModel("models/misc/rgbCube")
        #cube.reparentTo(self.render)
        #cube.setPos(5, 5, 2)
        #self.objects.append({
        #    "node": cube,
        #    "type": "rotating_cube",
        #    "speed": 60
        #})

        ## plateau + texture
        self.plateau = Plateau(self.base, self.render)

        ## bras articulé  
        self.bras = BrasArticule(self.base, self.render)

        ## la webcam et son socle
        self.webcam = Webcam(self.base, self.render)

        ## pions
        #self.add_pion((0, 5, 0), (1, 0, 0, 1))
        #self.add_pion((1, 5, 0), (0, 0, 1, 1))

    def add_pion(self, position, couleur):
        pion = Pion(self.base, position, couleur)
        self.pions.append(pion)
        return pion

    def remove_pion(self, pion):
        if pion in self.pions:
            self.pions.remove(pion)
        pion.destroy()

    def clear_pions(self):
        for pion in self.pions :
            pion.destroy()
        self.pions.clear()

    def rotateBras(self, angle0, angle1, angle2) :
        self.bras.rotation( angle0, angle1, angle2)

    def bras_viser_point(self, x, y, z) :
        self.bras.viser_point( x, y, z)

    def update(self, dt):
        for obj in self.objects:
            if obj["type"] == "rotating_cube":
                node = obj["node"]
                node.setH(node.getH() + obj["speed"] * dt)
