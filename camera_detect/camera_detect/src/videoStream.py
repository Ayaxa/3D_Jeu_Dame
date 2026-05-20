from threading import Thread
import cv2
import time

class VideoStreamWidget(object):
    def __init__(self, src=0, titre='IP Camera Video Streaming',
                 resize_width=None, resize_height=None):

        self.capture = cv2.VideoCapture(src)
        #self.capture = cv2.VideoCapture(0) # camera interne
        #self.capture = cv2.VideoCapture(1) # camera USB
        #self.capture = cv2.VideoCapture("http://192.168.1.100:8081") # flux internet
        self.titre = titre

        self.resize_width = resize_width
        self.resize_height = resize_height

        self.status = False
        self.frame = None
        
        # --- Nouveaux attributs pour la vidéo ---
        self.video_writer = None
        self.recording = False

        # FPS live
        self.last_time = time.time()
        self.fps_value = 0

        # Thread de capture
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()


    def update(self):
        while True:
            if self.capture.isOpened():
                (self.status, frame) = self.capture.read()
                if self.status:
                    self.frame = frame
                    # Si on enregistre, on écrit la frame brute (ou redimensionnée selon ton choix)
                    if self.recording and self.video_writer is not None:
                        # On écrit la frame actuelle dans le fichier
                        self.video_writer.write(self.frame)
            time.sleep(0.01) # Petite pause pour libérer le CPU

    def start_recording(self, filename="output.avi", fps=20.0):
        """Initialise l'écriture vidéo"""
        if not self.status or self.frame is None:
            print("Erreur: Impossible de démarrer l'enregistrement, aucun flux.")
            return

        # Récupérer les dimensions réelles du flux (important !)
        h, w = self.frame.shape[:2]
        
        # Définition du Codec (XVID est très standard pour .avi)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(filename, fourcc, fps, (w, h))
        self.recording = True
        print(f"--- Enregistrement démarré : {filename} ({w}x{h} @ {fps}fps)")

    def stop_recording(self):
        """Arrête l'enregistrement et libère le fichier"""
        self.recording = False
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            print("--- Enregistrement terminé et sauvegardé.")



    def compute_fps(self):
        """Calcule un FPS lissé"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        if dt > 0:
            fps = 1.0 / dt
            # on lisse légèrement pour éviter les variations brutales
            self.fps_value = (self.fps_value * 0.9) + (fps * 0.1)

        return self.fps_value


    def get_resized_frame(self):
        if not self.status or self.frame is None:
            return None

        return self.maintain_aspect_ratio_resize(
            self.frame,
            width=self.resize_width,
            height=self.resize_height
        )


    def show_frame(self, fps=True):
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27, 32):
            self.capture.release()
            cv2.destroyAllWindows()
            exit(0)

        if not self.status:
            return

        frame_to_show = self.get_resized_frame()

        # FPS ?
        if fps:
            fps_now = self.compute_fps()
            text = f"{fps_now:.1f} FPS"
            cv2.putText(frame_to_show, text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow(self.titre, frame_to_show)


    def maintain_aspect_ratio_resize(self, image, width=None, height=None, inter=cv2.INTER_AREA):
        if width is None and height is None:
            return image

        (h, w) = image.shape[:2]

        if width is not None:
            r = width / float(w)
            dim = (width, int(h * r))
        else:
            r = height / float(h)
            dim = (int(w * r), height)

        return cv2.resize(image, dim, interpolation=inter)



if __name__ == '__main__':
    #stream_link = 'http://192.168.19.30:8081' # la video est celle du reseau
    #stream_link = 0 # la video est celle de la webcam integrée
    stream_link = 1 # la video est celle de la webcam USB

    print("init ...")
    print("touche 'q' ou 'esc' ou 'space' pour quitter")

    video_stream_widget = VideoStreamWidget(
        stream_link,
        resize_width=800
    )

    while True:
        video_stream_widget.show_frame(fps=True)


