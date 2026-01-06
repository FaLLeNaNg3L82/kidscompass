@echo off
setlocal

REM --- zum Projekt-Root wechseln ---
cd /d D:\Programmieren\kidscompass

REM --- venv aktivieren ---
call .venv\Scripts\activate.bat

REM --- optional: sicherstellen, dass Abhängigkeiten da sind ---
REM python -m pip install -r requirements.txt

REM --- App starten (empfohlen als Modul, wenn installiert) ---
python -m kidscompass.ui

REM --- falls das nicht geht, nimm stattdessen (Pfad ggf. anpassen) ---
REM python .\src\kidscompass\ui.py

endlocal
