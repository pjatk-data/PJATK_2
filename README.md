# Projekt Edu - Instrukcja instalacji

Ten repozytorium zawiera materiały edukacyjne (notatniki Jupyter i skrypty) używające pakietów takich jak NumPy, Pandas, Faker i Microsoft Presidio.

## Szybka instalacja dla lokalnego środowiska (Windows, PowerShell)

1. Utwórz i aktywuj virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Zaktualizuj `pip` i zainstaluj zależności:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Dodatkowe kroki dla Presidio / spaCy (pobierz model PL):

```powershell
python -m spacy download pl_core_web_lg
```

> Uwaga: Instalacja `presidio_analyzer`/`presidio_anonymizer` oraz modelu spaCy może wymagać narzędzi kompilacyjnych i większej ilości pamięci.

### Uruchamianie notatników

- Otwórz Jupyter Notebook / JupyterLab i uruchom notatniki z katalogów `Dzien1`, `Dzien2` itd.

### Zawarte pakiety

Plik `requirements.txt` zawiera podstawowe zależności: `numpy`, `pandas`, `matplotlib`, `faker`, `presidio_analyzer`, `presidio_anonymizer`, `spacy`, `sqlalchemy`, `pyodbc`.

### Wskazówki

- Jeśli pracujesz w systemie innym niż Windows, aktywacja venv różni się (np. `source .venv/bin/activate`).
- Jeśli chcesz zamrozić wersje pakietów po udanej instalacji: `pip freeze > requirements.txt`.

## Użycie codespace

Jeśli chcesz uruchomić projekt w GitHub Codespaces, możesz skorzystać z wbudowanego środowiska, które automatycznie przygotuje kontener z Pythonem i zainstaluje zależności z `requirements.txt`. Po utworzeniu codespace:

1. Otwórz terminal w codespace.
2. Uruchom Jupyter Notebook / JupyterLab w codespace i otwórz notatniki z katalogów `Dzien1`, `Dzien2` itd.
