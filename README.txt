Airbnb RC Generator - navod k pouziti
======================================

OBSAH SLOZKY:
  generate_airbnb_rc.py   - hlavni skript (logika)
  airbnb_rc_gui.py        - graficke okenko (doporuceno)
  spustit.bat             - pro Windows - spusti okenko dvojklikem

POZADAVKY:
  - Python 3.8 nebo novejsi
  - Stazeni: https://python.org/downloads
  - DULEZITE: pri instalaci zatrhnout "Add Python to PATH"

JAK POUZIT (GUI - nejjednodussi):
  1. Dvojklik na spustit.bat
  2. Kliknete "Vybrat..." a vyberte CSV soubor z Airbnb
  3. Zadejte prvni cislo dokladu (napr. 10)
  4. Kliknete "Stahnout z CNB" pro automaticky kurz
     NEBO zadejte kurz rucne (napr. 25.15)
  5. Kliknete "Generovat XML"
  6. XML soubor se vytvori ve stejne slozce jako CSV

JAK POUZIT (prikazova radka):
  python generate_airbnb_rc.py faktury.csv 10
  python generate_airbnb_rc.py faktury.csv 10 25.15

VYTVORENI .EXE (bez nutnosti Pythonu):
  pip install pyinstaller
  pyinstaller --onefile --windowed airbnb_rc_gui.py
  -> vysledek je v slozce dist/airbnb_rc_gui.exe
