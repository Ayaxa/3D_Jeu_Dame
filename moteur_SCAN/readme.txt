
#####################
# installation / compilation SCAN (moteur de dames)
# https://github.com/rhalbersma/scan
sudo apt install git build-essential
git clone https://github.com/rhalbersma/scan.git
cd scan/src
make
# et le binaire se trouve dans : scan/src/scan


#####################
# installation draughts (wrapper python): 
# https://pypi.org/project/pydraughts/
pip install pydraughts
# pip install draughts
# pip install python-draughts







# voir les intallation 
pip list | grep dra
# uninstall
pip uninstall draughts -y
pip uninstall pydraughts -y
pip uninstall python-draughts -y



