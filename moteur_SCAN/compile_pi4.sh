#!/bin/bash
# Compile SCAN pour Raspberry Pi 4 (ARM64 / aarch64)
# À exécuter directement sur le Pi dans le dossier moteurDames/scan/src/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/scan/src"
OUT="$SCRIPT_DIR/scan_linux"

echo "=== Compilation de SCAN pour Raspberry Pi 4 ==="
echo "Sources : $SRC_DIR"

# Vérifie que g++ est disponible
if ! command -v g++ &>/dev/null; then
    echo "Installation de g++…"
    sudo apt-get update && sudo apt-get install -y g++
fi

cd "$SRC_DIR"

# Récupère tous les fichiers source .cpp
SOURCES=$(ls *.cpp 2>/dev/null)
if [ -z "$SOURCES" ]; then
    echo "Erreur : aucun fichier .cpp dans $SRC_DIR"
    exit 1
fi

echo "Fichiers sources : $SOURCES"

# Compilation optimisée pour Cortex-A72 (CPU du Pi 4)
g++ -std=c++14 \
    -O3 \
    -march=armv8-a+crc \
    -mcpu=cortex-a72 \
    -pthread \
    -o "$OUT" \
    $SOURCES

echo ""
echo "Binaire compilé : $OUT"
echo ""
echo "Installation de pydraughts (si nécessaire) :"
echo "  pip3 install pydraughts"
echo ""
echo "Test :"
echo "  python3 scan_predictor.py"
