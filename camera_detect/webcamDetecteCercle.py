#! /usr/bin/python
import cv2 # pip install opencv-python
import os
import shutil
import time
import numpy as np

from videoStream import VideoStreamWidget
from detecteCercle import *

CAM_WIDTH = 640 
titre = "webcam : detection cercle"
titre_video = "ma_video_detecte_cercle.avi"


print("-- initialisation de la camera")
#cam = VideoStreamWidget(0, titre, resize_width=CAM_WIDTH) # capture d'image par la webcam integré
cam = VideoStreamWidget(1, titre, resize_width=CAM_WIDTH) # capture d'image par la webcam USB
#cam = VideoStreamWidget('http://192.168.19.30:8081', titre, resize_width=CAM_WIDTH) # capture d'image par le reseau 

if cam == None :
    print("-- ERREUR : la camera ne capte pas le flux video")
    exit(1)

time.sleep(1)

detector = FastCircleDetector(min_diam=15, max_diam=36)

# repetoire pour sauvegarder les photos
os.makedirs("data", exist_ok=True)
print("-- On appuye sur 'espace' pour sauvegarder une photo")
print("-- On appuye sur 'r' pour activer / desactiver une video")


recording_active = False






tracker = CircleClusterTracker(
    delta_center=10,
    delta_r=8,
    min_probability=0.6,
    max_frames=30
)

while True:
    frame = cam.get_resized_frame()
    if frame is None:
        print("-- failed to grab frame")
        break

    # ---- Détection brute ----
    circles = detector.detect(frame)

    raw_circles = []
    if circles is not None:
        circles = np.uint16(np.around(circles))
        raw_circles = [(x, y, r) for x, y, r in circles[0]]

    # ---- Tracking / clustering ----
    confirmed = tracker.update(raw_circles)

    # ---- Affichage ----
    out = frame.copy()

    # Cercles détectés (bruts)
    for (x, y, r) in raw_circles:
        cv2.circle(out, (x, y), r, (0, 255, 0), 1)

    # Cercles validés (clusters)
    for (x, y, r) in confirmed:
        cv2.circle(out, (x, y), r, (0, 0, 255), 3)
        cv2.circle(out, (x, y), 2, (255, 0, 0), 3)

    # Debug texte
    cv2.putText(out, f"Raw: {len(raw_circles)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

    cv2.putText(out, f"Confirmed: {len(confirmed)}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

    cv2.imshow("Detection + Cluster", out)

    # Quitter avec 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break








#while True:
#
#    # image de la webcam
#    frame = cam.get_resized_frame()
#
#    if frame is None:
#        print("-- failed to grab frame")
#        break
#
#    # Affichage d'un indicateur visuel si on enregistre
#    if recording_active:
#        cv2.circle(frame, (30, 60), 10, (0, 0, 255), -1) # Point rouge
#
#    circles = detector.detect(frame)
#    out = detector.drawCircles(frame, circles)
#
#    cv2.imshow(titre, out)
#
#    # touches 
#    key = cv2.waitKey(1) & 0xFF
#    if key == ord('r'): # Appuyer sur 'r' pour démarrer/arrêter
#        if not recording_active:
#            cam.start_recording(titre_video)
#            recording_active = True
#        else:
#            cam.stop_recording()
#            recording_active = False
#    elif key == 32: # Espace pour photo
#        img_name = f"data/webcam_{time.time()}.jpg"
#        print(f"   sauvegarde image : {img_name} ")
#        cv2.imwrite(img_name , out)
#    elif key in (ord('q'), 27): # echap ou q
#        if recording_active:
#            cam.stop_recording()
#        break

print("--- on quitte la prise de vue")

