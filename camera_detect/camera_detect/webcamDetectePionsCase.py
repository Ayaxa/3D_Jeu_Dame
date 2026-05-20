#! /usr/bin/python
import cv2 # pip install opencv-python
import os
import shutil
import time
import numpy as np

from videoStream import VideoStreamWidget
from detectePionCase import *

CAM_WIDTH = 640 
titre = "webcam : detection pions cases"
titre_video = "ma_video_detecte_pions_cases.avi"


print("-- initialisation de la camera")
#cam = VideoStreamWidget(0, titre, resize_width=CAM_WIDTH) # capture d'image par la webcam integré
cam = VideoStreamWidget(1, titre, resize_width=CAM_WIDTH) # capture d'image par la webcam USB
#cam = VideoStreamWidget('http://192.168.19.81:8081', titre, resize_width=CAM_WIDTH) # capture d'image par le reseau

if cam == None :
    print("-- ERREUR : la camera ne capte pas le flux video")
    exit(1)

time.sleep(1)

detectorDamier = DamierDetector(10)
detectorPions = DetectePionCase()

# repetoire pour sauvegarder les photos
os.makedirs("data", exist_ok=True)
print("-- On appuye sur 'espace' pour sauvegarder une photo")
print("-- On appuye sur 'r' pour activer / desactiver une video")


recording_active = False

while True:

    # image de la webcam
    frame = cam.get_resized_frame()

    if frame is None:
        print("-- failed to grab frame")
        break

    # Affichage d'un indicateur visuel si on enregistre
    if recording_active:
        cv2.circle(frame, (30, 60), 10, (0, 0, 255), -1) # Point rouge

    result = detectorDamier.detectGrid(frame)

    if result is None:
        print("-- damier NON detecte")
        out = frame
    else:
        print("-- damier detecte")
        grid, warped = result
        out = detectorDamier.draw_checkerboard_segments(warped.copy(), grid)

        matrix = detectorPions.detect(warped, grid)
        print(matrix)

        out = detectorPions.draw_result_overlay(
            frame=frame,
            warped=warped,
            grid=grid,
            matrix=matrix,
            size=150
        )



    #board = detectionPions.process(frame)    
    #if board is None:
    #    print("-- pas detecté ")
    #out = detectionPions.draw_image()

    cv2.imshow(titre, out)

    # touches 
    key = cv2.waitKey(1) & 0xFF
    if key == ord('r'): # Appuyer sur 'r' pour démarrer/arrêter
        if not recording_active:
            cam.start_recording(titre_video)
            recording_active = True
        else:
            cam.stop_recording()
            recording_active = False
    elif key == 32: # Espace pour photo
        img_name = f"data/webcam_{time.time()}.jpg"
        print(f"   sauvegarde image : {img_name} ")
        cv2.imwrite(img_name , out)
    elif key in (ord('q'), 27): # echap ou q
        if recording_active:
            cam.stop_recording()
        break

print("--- on quitte la prise de vue")

