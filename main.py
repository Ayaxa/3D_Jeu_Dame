from echequier3D import *

monEchequier3D = Echequier3D()


matrice_position_noir= [
    [0,0,0,0,0,0,0,0,0,0],
    [0,1,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,1,0,0,0,0,0],
    [0,0,0,0,0,1,0,0,0,0],
    [0,0,0,0,2,0,0,0,0,0],
    [0,0,0,0,0,2,0,0,0,0],
    [0,0,2,0,2,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0]
]



#matrice_position_noir= [
#    [0,0,0,0,0,0,0,0,0,0],
#    [0,0,0,0,0,0,0,0,0,0],
#    [0,0,0,0,0,1,0,0,0,0],
#    [0,0,0,0,1,0,0,0,0,0],
#    [0,0,0,0,0,1,0,0,0,0],
#    [0,0,0,0,2,0,0,0,0,0],
#    [0,0,0,0,0,2,0,0,0,0],
#    [0,0,2,0,2,0,0,0,0,0],
#    [0,0,0,0,0,0,0,0,0,0],
#    [0,0,0,0,0,0,0,0,0,0]
#]





# =========================================================
# COUPS A JOUER
# =========================================================

listeCoups = [23, 32, 41]

# =========================================================
# EXECUTION
# =========================================================

def scenario():


    matrice_position_blanc = monEchequier3D.rotation_180(matrice_position_noir)

    # charger position
    monEchequier3D.add_command(
        monEchequier3D.charger_position,
        matrice_position_blanc
    )

    # attendre un peu
    import time
    time.sleep(2)

    # jouer les coups
    monEchequier3D.jouer_coups(listeCoups)


import threading
t = threading.Thread(target=scenario, daemon=True)
t.start()

monEchequier3D.run()

