"""
scan_predictor.py
=================
Interface entre une matrice 10x10 et le moteur de dames SCAN.

Ce module permet de :
    - Convertir une matrice 10x10 en FEN (format compris par pydraughts/SCAN)
    - Interroger le moteur SCAN pour obtenir le meilleur coup
    - Appliquer ce coup sur la matrice (déplacement + suppression des prises)
    - Afficher la matrice de façon lisible

Convention de la matrice :
    0 = case vide
    1 = pion du joueur 1  (blancs, démarrent en bas,  rangées 6-9)
    2 = pion du joueur 2  (noirs,  démarrent en haut, rangées 0-3)

Numérotation des cases jouables (cases sombres uniquement, 1 à 50) :
    Rangée 0 (haut), colonnes impaires  → cases  1 à  5
    Rangée 1,        colonnes paires    → cases  6 à 10
    ...
    Rangée 9 (bas),  colonnes paires    → cases 46 à 50

    Formule : case = rangée * 5 + colonne // 2 + 1
              case jouable si (rangée + colonne) % 2 == 1

Dépendances :
    pip install pydraughts

Utilisation rapide :
    from scan_predictor import analyser_position

     Cela nous renvoie :

     return {
        "scan_de"      : scan.de,
        "scan_vers"    : scan.vers,
        "scan_prises"  : scan.prises,
        "scan_chemin"  : scan.chemin,
        "alea_de"      : alea.de,
        "alea_vers"    : alea.vers,
        "alea_prises"  : alea.prises,
        "alea_chemin"  : alea.chemin,
        "coups_legaux" : coups_legaux,
        "matrice_avant": copy.deepcopy(matrice),
    }
"""

import os
import copy
import time
import random
import warnings
import dataclasses
from typing import List

# Supprime les ResourceWarning de pydraughts (bug interne de la lib)
warnings.filterwarnings("ignore", category=ResourceWarning)

from draughts.engine import HubEngine, Limit
from draughts import Board


# ---------------------------------------------------------------------------
# Constantes représentant le contenu d'une case dans la matrice
# ---------------------------------------------------------------------------
VIDE    = 0   # case vide
JOUEUR1 = 1   # pion du joueur 1 (blancs dans SCAN)
JOUEUR2 = 2   # pion du joueur 2 (noirs  dans SCAN)


# ---------------------------------------------------------------------------
# Structure de données pour le résultat d'un coup
# ---------------------------------------------------------------------------
@dataclasses.dataclass
class ResultatCoup:
    """
    Contient toutes les informations sur le coup prédit par SCAN.

    Attributs :
        coup_brut : coup tel que retourné par pydraughts (liste ou chaîne)
        de        : numéro de case de départ (1-50)
        vers      : numéro de case d'arrivée (1-50)
        prises    : liste des cases des pièces capturées (vide si coup tranquille)
        chemin    : liste de toutes les cases parcourues (de inclus)
    """
    coup_brut: object       # ex. [33, 29] ou "33-29"
    de:        int          # case de départ
    vers:      int          # case d'arrivée
    prises:    List[int]    # cases des pièces capturées
    chemin:    List[int]    # parcours complet du pion


# ---------------------------------------------------------------------------
# Fonctions de conversion entre matrice et numérotation SCAN
# ---------------------------------------------------------------------------

def _case(rangee: int, col: int) -> int:
    """
    Convertit des coordonnées (rangée, colonne) en numéro de case SCAN (1-50).

    Seules les cases sombres sont jouables : (rangée + colonne) % 2 == 1.
    Ne pas appeler sur une case claire.

    Args:
        rangee : ligne de la matrice (0 = haut, 9 = bas)
        col    : colonne de la matrice (0 à 9)

    Returns:
        Numéro de case entre 1 et 50.
    """
    return rangee * 5 + col // 2 + 1


def case_vers_coords(case: int) -> tuple:
    """
    Convertit un numéro de case SCAN (1-50) en coordonnées (rangée, colonne)
    dans la matrice 10x10.

    Args:
        case : numéro de case entre 1 et 50

    Returns:
        Tuple (rangée, colonne).
    """
    rangee = (case - 1) // 5
    offset = (case - 1) % 5
    # Les rangées paires ont leurs cases sombres sur les colonnes impaires
    # Les rangées impaires ont leurs cases sombres sur les colonnes paires
    if rangee % 2 == 0:
        col = offset * 2 + 1
    else:
        col = offset * 2
    return rangee, col


# ---------------------------------------------------------------------------
# Conversion matrice → FEN
# ---------------------------------------------------------------------------

def matrix_vers_fen(matrice, joueur_actif: int = 1) -> str:
    """
    Convertit une matrice 10x10 en chaîne FEN compatible pydraughts/SCAN.

    Parcourt toutes les cases sombres de la matrice, collecte les cases
    occupées par chaque joueur, et formate la chaîne FEN.

    Args:
        matrice      : liste 10x10 (ou tableau numpy 10x10)
                       valeurs : 0 = vide, 1 = joueur 1, 2 = joueur 2
        joueur_actif : 1 → c'est au joueur 1 de jouer (blancs = "W")
                       2 → c'est au joueur 2 de jouer (noirs  = "B")

    Returns:
        Chaîne FEN, ex. "W:W31,32,33:B1,2,3"
    """
    j1_cases = []   # cases occupées par le joueur 1 (blancs dans SCAN)
    j2_cases = []   # cases occupées par le joueur 2 (noirs  dans SCAN)

    for r in range(10):
        for c in range(10):
            # On ignore les cases claires (non jouables aux dames)
            if (r + c) % 2 == 0:
                continue

            sq  = _case(r, c)
            val = int(matrice[r][c])

            if val == JOUEUR1:
                j1_cases.append(str(sq))
            elif val == JOUEUR2:
                j2_cases.append(str(sq))

    # "W" = blancs (joueur 1) jouent, "B" = noirs (joueur 2) jouent
    cote = "W" if joueur_actif == 1 else "B"
    return f"{cote}:W{','.join(j1_cases)}:B{','.join(j2_cases)}"


# ---------------------------------------------------------------------------
# Analyse du coup retourné par pydraughts
# ---------------------------------------------------------------------------

def _analyser_coup(coup_brut) -> tuple:
    """
    Analyse le coup retourné par pydraughts pour en extraire les cases clés.

    pydraughts peut retourner le coup sous deux formes :
      - Liste  : [33, 29]        → déplacement tranquille
      - Chaîne : "33-29"         → déplacement tranquille
      - Chaîne : "28x17x6"       → prise(s) (format Hub SCAN)

    Les prises réelles sont récupérées séparément via move.captures
    (géré dans predire_coup), donc ici on retourne prises=[] par défaut.

    Args:
        coup_brut : coup sous forme de liste ou de chaîne

    Returns:
        Tuple (de, vers, prises_hub, chemin)
    """
    # Cas liste : pydraughts retourne directement le parcours [case_depart, case_arrivee]
    if isinstance(coup_brut, (list, tuple)):
        chemin = [int(c) for c in coup_brut]
        return chemin[0], chemin[-1], [], chemin

    # Cas chaîne tranquille : "33-29"
    if "-" in coup_brut:
        parties = coup_brut.split("-")
        de, vers = int(parties[0]), int(parties[1])
        return de, vers, [], [de, vers]

    # Cas chaîne avec prise(s) : "28x17x6"
    # Format Hub : depart x arrivee x prise1 x prise2 ...
    parties = [int(p) for p in coup_brut.split("x")]
    de     = parties[0]
    vers   = parties[1]
    prises = parties[2:]
    return de, vers, prises, parties


# ---------------------------------------------------------------------------
# Moteur SCAN persistant
# ---------------------------------------------------------------------------

SCAN_PATH = "./scan_linux"

# Instance unique du moteur, partagée entre tous les appels
_engine: HubEngine = None


def _obtenir_moteur() -> HubEngine:
    """
    Retourne le moteur SCAN en cours d'exécution.
    Le démarre une seule fois à la première utilisation (singleton).
    """
    global _engine
    if _engine is None:
        _engine = HubEngine([SCAN_PATH, "hub"])
        _engine.init()
    return _engine


def fermer_moteur() -> None:
    """
    Arrête proprement le moteur SCAN.
    À appeler en fin de programme si besoin.
    """
    global _engine
    if _engine is not None:
        _engine.quit()
        _engine = None


# ---------------------------------------------------------------------------
# Fonction principale : interrogation de SCAN
# ---------------------------------------------------------------------------

def predire_coup(matrice, joueur_actif: int = 1) -> tuple:
    """
    Interroge le moteur SCAN (persistant) et retourne le meilleur coup
    ainsi que les coups légaux.

    Le moteur SCAN reste actif entre les appels — pas de redémarrage.

    Args:
        matrice      : matrice 10x10 (0=vide, 1=joueur1, 2=joueur2)
        joueur_actif : 1 ou 2 — joueur qui doit jouer

    Returns:
        Tuple (ResultatCoup, moves, coups_legaux) :
            ResultatCoup  — meilleur coup SCAN
            moves         — liste d'objets Move (réutilisable pour coup aléatoire)
            coups_legaux  — liste de chaînes représentant les coups possibles
    """
    fen    = matrix_vers_fen(matrice, joueur_actif)
    board  = Board(variant="standard", fen=fen)
    engine = _obtenir_moteur()

    resultat   = engine.play(board, Limit(time=1), ponder=False)  # modifié (était 10) : temps de réflexion en secondes → 1s au lieu de 10s, réponse bien plus rapide
    coup_brut  = resultat.move.steps_move
    prises_lib = list(resultat.move.captures or [])
    de, vers, prises_hub, chemin = _analyser_coup(coup_brut)
    prises_finales = prises_lib if prises_lib else prises_hub

    meilleur_coup = ResultatCoup(
        coup_brut=coup_brut,
        de=de,
        vers=vers,
        prises=prises_finales,
        chemin=chemin,
    )

    # Coups légaux calculés une seule fois, partagés avec le coup aléatoire
    moves        = list(board.legal_moves())
    coups_legaux = [str(m) for m in moves]

    return meilleur_coup, moves, coups_legaux


def predire_coup_aleatoire(moves: list) -> ResultatCoup:
    """
    Choisit aléatoirement un coup parmi une liste de Move déjà calculée.

    Ne recrée pas de Board, ne relance pas SCAN — très rapide.

    Args:
        moves : liste d'objets Move retournée par predire_coup()

    Returns:
        ResultatCoup du coup tiré au hasard.
    """
    if not moves:
        raise ValueError("Aucun coup légal disponible pour cette position.")

    move_choisi = random.choice(moves)
    coup_brut   = move_choisi.steps_move
    prises_lib  = list(move_choisi.captures or [])
    de, vers, prises_hub, chemin = _analyser_coup(coup_brut)
    prises_finales = prises_lib if prises_lib else prises_hub

    return ResultatCoup(
        coup_brut=coup_brut,
        de=de,
        vers=vers,
        prises=prises_finales,
        chemin=chemin,
    )


# ---------------------------------------------------------------------------
# Application du coup sur la matrice
# ---------------------------------------------------------------------------

def appliquer_coup(matrice, resultat: ResultatCoup) -> list:
    """
    Applique un coup sur la matrice et retourne la nouvelle matrice.

    La matrice originale n'est pas modifiée (copie profonde).

    Actions effectuées :
        - Déplace la pièce de la case de départ vers la case d'arrivée
        - Supprime les pièces adverses capturées

    Args:
        matrice  : matrice 10x10 avant le coup
        resultat : ResultatCoup retourné par predire_coup()

    Returns:
        Nouvelle matrice 10x10 après le coup.
    """
    nouvelle = copy.deepcopy(matrice)

    # Coordonnées de départ et d'arrivée dans la matrice
    r_de,   c_de   = case_vers_coords(resultat.de)
    r_vers, c_vers = case_vers_coords(resultat.vers)

    # Déplace la pièce
    nouvelle[r_vers][c_vers] = nouvelle[r_de][c_de]
    nouvelle[r_de][c_de]     = VIDE

    # Supprime chaque pièce capturée
    for case_prise in resultat.prises:
        r_p, c_p = case_vers_coords(case_prise)
        nouvelle[r_p][c_p] = VIDE

    return nouvelle


# ---------------------------------------------------------------------------
# Affichage de la matrice
# ---------------------------------------------------------------------------

def afficher_matrice(matrice, titre: str = "") -> None:
    """
    Affiche la matrice 10x10 de façon lisible dans le terminal.

    Légende :
        .  = case vide
        1  = pion du joueur 1
        2  = pion du joueur 2

    Args:
        matrice : matrice 10x10 à afficher
        titre   : titre affiché au-dessus (optionnel)
    """
    if titre:
        print(f"\n=== {titre} ===")
    symboles = {VIDE: ".", JOUEUR1: "1", JOUEUR2: "2"}
    # En-tête des colonnes
    print("  " + " ".join(str(c) for c in range(10)))
    for r, rangee in enumerate(matrice):
        ligne = " ".join(symboles.get(v, "?") for v in rangee)
        print(f"{r} {ligne}")


def analyser_position(matrice, joueur_actif: int = 1) -> dict:
    """
    Interroge SCAN et tire un coup aléatoire, puis retourne les deux dans un dictionnaire.

    Args:
        matrice      : matrice 10x10 (0 = vide, 1 = joueur 1, 2 = joueur 2)
        joueur_actif : 1 ou 2 — joueur qui doit jouer

    Returns:
        Dictionnaire avec :
            "scan_de"      : int        — case de départ du meilleur coup SCAN (1-50)
            "scan_vers"    : int        — case d'arrivée du meilleur coup SCAN (1-50)
            "scan_prises"  : List[int]  — cases capturées par SCAN ([] si aucune)
            "scan_chemin"  : List[int]  — toutes les cases parcourues par SCAN
            "alea_de"      : int        — case de départ du coup aléatoire (1-50)
            "alea_vers"    : int        — case d'arrivée du coup aléatoire (1-50)
            "alea_prises"  : List[int]  — cases capturées par le coup aléatoire
            "alea_chemin"  : List[int]  — toutes les cases parcourues (aléatoire)
            "coups_legaux" : List[str]  — tous les coups possibles (non triés)
            "matrice_avant": List[List] — matrice avant le coup
    """
    scan, moves, coups_legaux = predire_coup(matrice, joueur_actif=joueur_actif)
    alea                      = predire_coup_aleatoire(moves)

    return {
        "scan_de"      : scan.de,
        "scan_vers"    : scan.vers,
        "scan_prises"  : scan.prises,
        "scan_chemin"  : scan.chemin,
        "alea_de"      : alea.de,
        "alea_vers"    : alea.vers,
        "alea_prises"  : alea.prises,
        "alea_chemin"  : alea.chemin,
        "coups_legaux" : coups_legaux,
        "matrice_avant": copy.deepcopy(matrice),
    }


def tester_position(matrice, joueur_actif: int, description: str) -> None:
    """
    Teste une position donnée : affiche la matrice initiale, le meilleur coup
    SCAN, le coup aléatoire et les coups légaux disponibles.

    Args:
        matrice      : matrice 10x10 représentant la position
        joueur_actif : 1 ou 2 — joueur qui doit jouer
        description  : texte décrivant le scénario testé
    """
    print("\n" + "=" * 55)
    print(f" SCENARIO : {description}")
    print(f" Joueur {joueur_actif} doit jouer")
    print("=" * 55)

    afficher_matrice(matrice, "Position initiale")

    print("\nInterrogation de SCAN + tirage aléatoire...")
    t_debut = time.time()
    info = analyser_position(matrice, joueur_actif)
    t_fin = time.time()
    print(f"Temps d'exécution : {t_fin - t_debut:.3f} s")

    # --- Meilleur coup SCAN ---
    print(f"\n--- Meilleur coup (SCAN) ---")
    chemin_str = " → ".join(str(c) for c in info["scan_chemin"])
    print(f"  Chemin : {chemin_str}")
    print(f"  De     : {info['scan_de']}")
    print(f"  Vers   : {info['scan_vers']}")
    if info["scan_prises"]:
        nb = len(info["scan_prises"])
        print(f"  Prises : {info['scan_prises']}  ({nb} pièce{'s' if nb > 1 else ''} capturée{'s' if nb > 1 else ''})")
    else:
        print(f"  Prises : aucune")

    # --- Coup aléatoire ---
    print(f"\n--- Coup aléatoire ---")
    chemin_str = " → ".join(str(c) for c in info["alea_chemin"])
    print(f"  Chemin : {chemin_str}")
    print(f"  De     : {info['alea_de']}")
    print(f"  Vers   : {info['alea_vers']}")
    if info["alea_prises"]:
        nb = len(info["alea_prises"])
        print(f"  Prises : {info['alea_prises']}  ({nb} pièce{'s' if nb > 1 else ''} capturée{'s' if nb > 1 else ''})")
    else:
        print(f"  Prises : aucune")

    # --- Coups légaux ---
    print(f"\n--- Coups légaux ({len(info['coups_legaux'])} disponibles, non triés) ---")
    for coup in info["coups_legaux"]:
        print(f"  {coup}")


# ---------------------------------------------------------------------------
# Programme principal — exemple d'un coup unique
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    # Position de départ internationale
    matrice = [[0] * 10 for _ in range(10)]
    for r in range(4):
        for c in range(10):
            if (r + c) % 2 == 1:
                matrice[r][c] = JOUEUR2
    for r in range(6, 10):
        for c in range(10):
            if (r + c) % 2 == 1:
                matrice[r][c] = JOUEUR1

    # Prédit et affiche un seul coup
    tester_position(matrice, joueur_actif=1, description="Position de départ")
