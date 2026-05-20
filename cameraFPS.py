from panda3d.core import WindowProperties, Vec3
from direct.showbase.DirectObject import DirectObject
from define import *

class FPSCamera(DirectObject):
    def __init__(self, base):
        self.base = base
        self.camera = base.camera

        # Sensibilité souris
        self.sensitivity = 0.01

        # Vitesse déplacement
        self.speed = 5*CASE_WIDTH

        # Rotation
        self.camera.setPos(10*CASE_WIDTH, -20*CASE_WIDTH, 15*CASE_WIDTH)
        self.camera.lookAt(5*CASE_WIDTH, 9*CASE_WIDTH, 2*CASE_WIDTH)
        hpr = self.camera.getHpr()
        self.heading = hpr.x
        self.pitch = hpr.y
        #self.camera.setPos(-5, -10, 5)
        #self.heading = -46
        #self.pitch = -14
        #self.camera.setHpr(self.heading, self.pitch, 0)


        # Désactiver souris Panda3D
        base.disableMouse()

        # Capturer souris
        props = WindowProperties()
        props.setCursorHidden(True)
        # props.setMouseMode(WindowProperties.M_relative)
        base.win.requestProperties(props)

        self.centered = False

        self.last_x = 0
        self.last_y = 0

        if base.mouseWatcherNode.hasMouse():
            mouse = base.mouseWatcherNode.getMouse()
            self.last_x = mouse.getX()
            self.last_y = mouse.getY()

        self.ignore_mouse = True

        # États clavier
        self.keys = {"z":0, "s":0, "q":0, "d":0}

        for key in self.keys:
            self.accept(key, self.set_key, [key, 1])
            self.accept(key+"-up", self.set_key, [key, 0])

    def set_key(self, key, value):
        self.keys[key] = value

    def update(self, dt):

        if not self.centered:
            center_x = self.base.win.getXSize() // 2
            center_y = self.base.win.getYSize() // 2
        
            self.base.win.movePointer(0, center_x, center_y)
            self.centered = True
        
            return  # on ne lit PAS la souris ici



        if self.base.mouseWatcherNode.hasMouse():
            md = self.base.win.getPointer(0)
        
            center_x = self.base.win.getXSize() // 2
            center_y = self.base.win.getYSize() // 2
        
            dx = md.getX() - center_x
            dy = md.getY() - center_y

            if abs(dx) > 200 or abs(dy) > 200:
                return

            if self.ignore_mouse:
                self.ignore_mouse = False
                self.base.win.movePointer(0, center_x, center_y)
                return

            # rotation
            self.heading -= dx * self.sensitivity
            self.pitch -= dy * self.sensitivity   # ✅ inversé ici
        
            self.pitch = max(-90, min(90, self.pitch))
        
            self.camera.setHpr(self.heading, self.pitch, 0)
        
            # 🔥 indispensable pour FPS
            self.base.win.movePointer(0, center_x, center_y)


        # --- CLAVIER (déplacement) ---
        direction = Vec3(0, 0, 0)

        if self.keys["z"]:
            direction.y += 1
        if self.keys["s"]:
            direction.y -= 1
        if self.keys["q"]:
            direction.x -= 1
        if self.keys["d"]:
            direction.x += 1

        if direction.length() > 0:
            direction.normalize()

            # Déplacement relatif à la caméra
            self.camera.setPos(
                self.camera,
                direction * self.speed * dt
            )

