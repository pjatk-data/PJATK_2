# Creative Nutrition Planner

Creative Nutrition Planner to prosta aplikacja webowa zbudowana w Streamlit, która pomaga komponować posiłek z wybranych składników i szacuje ich łączną kaloryczność. Aplikacja wyświetla tabelę przykładowych produktów, pozwala wybrać składniki z panelu bocznego, a następnie może wygenerować kreatywny przepis z użyciem modelu OpenAI lub Azure OpenAI.

## Co potrafi aplikacja

- pokazuje przykładową tabelę składników odżywczych,
- umożliwia wybór składników z panelu bocznego,
- oblicza łączną liczbę kalorii dla zaznaczonych produktów,
- generuje przepis na podstawie wybranych składników,
- wspiera OpenAI oraz Azure OpenAI przez zmienne środowiskowe.

## Wymagania

- Python 3.10 lub nowszy,
- zainstalowane zależności z pliku `requirements.txt`,
- opcjonalnie klucz API do OpenAI lub Azure OpenAI.

## Jak uruchomić

1. Przejdź do katalogu aplikacji:

```bash
cd Dzien2/10.BuildingAIapps/NutritionApp
```

2. Utwórz i aktywuj środowisko wirtualne, jeśli jeszcze go nie masz:

```bash
python -m venv .venv
\.venv\Scripts\Activate.ps1
```

3. Zainstaluj zależności:

```bash
pip install -r requirements.txt
```

4. Utwórz plik `.env` w tym samym katalogu i dodaj wymagane zmienne, jeśli chcesz korzystać z generowania przepisów:

```env
OPENAI_API_KEY=twoj_klucz
# albo dla Azure OpenAI:
AZURE_OPENAI_API_KEY=twoj_klucz
AZURE_OPENAI_ENDPOINT=https://twoj-zasob.openai.azure.com/
AZURE_OPENAI_COMPLETION_MODEL=nazwa-wdrozenialub-modelu
```

5. Uruchom aplikację:

```bash
streamlit run app.py
```

Po uruchomieniu aplikacja otworzy się w przeglądarce. Jeżeli nie ustawisz klucza API, część odpowiedzialna za generowanie przepisu pokaże komunikat informujący o braku konfiguracji.

## Uwagi

- Jeśli używasz Azure OpenAI, adres `AZURE_OPENAI_ENDPOINT` powinien wskazywać na zasób w formacie `https://nazwa-zasobu.openai.azure.com/`.
- Model można ustawić przez `AZURE_OPENAI_COMPLETION_MODEL` albo `OPENAI_MODEL`.