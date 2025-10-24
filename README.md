# Fake Sources Tester Pro (GitHub Actions ready)

IMPORTANT LEGAL: Folosește doar pe servere/site-uri pe care le deții sau ai permisiune clară. Nu folosi pentru abuz, DDoS sau ocolirea protecțiilor fără acord.

## Ce face
- Trimite cereri către un URL țintă folosind profiluri diferite (User-Agent / Referer / IP prin proxy).
- Arată progres live, coduri HTTP, blocări (403 etc.), latență, histogramă.
- Export CSV și raport HTML.
- Rulează cu interfață grafică PySimpleGUI.

---

## Cum rulezi local (fără .exe)
1. Instalează Python 3.11 (sau 3.10).
2. În folderul proiectului:
   ```bat
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python main_gui_pro.py
   ```

---

## Cum construiești singur .exe pe Windows (local)
1. Deschide Command Prompt în acest folder.
2. Rulează:
   ```bat
   build_win.bat
   ```
3. Executabilul final va apărea în `dist\FakeSourcesTesterPro.exe`.

---

## Cum obții .exe automat cu GitHub Actions
1. Creează un repository pe GitHub.
2. Pune TOATE fișierele din acest folder în repo (inclusiv `.github/workflows/build-windows.yml`).
3. Fă commit & push pe `main` sau `master`.
4. Intră în tab-ul “Actions” din GitHub, rulează workflow-ul `Build Windows EXE` dacă nu a pornit singur.
5. La final, artefactul `FakeSourcesTesterPro-windows-exe` conține `FakeSourcesTesterPro.exe` gata de descărcat.

---

## Fișiere importante
- `core.py` — logica de test + raport HTML.
- `main_gui_pro.py` — interfața grafică.
- `requirements.txt` — dependențe Python.
- `build_win.bat` — build local .exe pe Windows.
- `.github/workflows/build-windows.yml` — workflow GitHub Actions care îți produce automat .exe pe un runner Windows.
