# Presidio PII Pseudonymizer dla języka polskiego

Narzędzie do wykrywania i pseudonimizacji danych osobowych (PII) w tekstach polskojęzycznych. Wykorzystuje [Microsoft Presidio](https://microsoft.github.io/presidio/) do wykrywania PII oraz [Faker](https://faker.readthedocs.io/) do generowania realistycznych, deterministycznych zamienników.

## 📋 Spis treści

- [Funkcjonalności](#-funkcjonalności)
- [Jak to działa](#-jak-to-działa)
- [Wymagania](#-wymagania)
- [Instalacja](#-instalacja)
- [Modele spaCy](#-modele-spacy)
- [Szybki start](#-szybki-start)
- [Konfiguracja](#-konfiguracja)
- [Obsługiwane typy PII](#-obsługiwane-typy-pii)
- [API](#-api)
- [Przykłady użycia](#-przykłady-użycia)
- [Pliki konfiguracyjne](#-pliki-konfiguracyjne)
- [Walidacja numerów](#-walidacja-numerów)
- [Rozwój](#-rozwój)

## ✨ Funkcjonalności

- **Wykrywanie PII** - automatyczne rozpoznawanie danych osobowych w tekście
- **Pseudonimizacja** - zamiana prawdziwych danych na realistyczne, fikcyjne odpowiedniki
- **Determinizm** - ta sama wartość wejściowa zawsze daje ten sam pseudonim (przy tym samym salt)
- **Poprawne numery** - generowane PESEL, NIP i REGON przechodzą walidację sum kontrolnych
- **Polski kontekst** - rozpoznawanie na podstawie polskich słów kontekstowych (np. "telefon", "pesel", "numer konta")
- **Zachowanie formatowania** - wielkość liter i format są zachowywane

## 🔍 Jak to działa

Rozwiązanie składa się z trzech głównych komponentów:

### 1. Wykrywanie PII (Presidio Analyzer)

```
Tekst wejściowy → [NLP Engine (spaCy)] → [Rozpoznawacze] → Lista encji PII
```

**Silnik NLP (spaCy)** przetwarza tekst i wykonuje:
- Tokenizację (podział na słowa)
- Lematyzację (sprowadzenie do formy podstawowej)
- **Named Entity Recognition (NER)** - rozpoznawanie nazwanych encji (osoby, organizacje, miejsca)

**Rozpoznawacze (Recognizers)** to moduły wykrywające konkretne typy PII:
- **SpacyRecognizer** - wykorzystuje etykiety NER z modelu spaCy (np. `persName` → `PERSON`)
- **Rozpoznawacze regex** - wykrywają wzorce jak PESEL, NIP, email na podstawie wyrażeń regularnych
- **Słowa kontekstowe** - zwiększają pewność wykrycia gdy w pobliżu znajdują się słowa jak "pesel", "telefon", "email"

### 2. Generowanie zamienników (Faker)

```
Encja PII → [Hash(salt + wartość)] → [Seed] → [Faker] → Pseudonim
```

Mechanizm zapewnia **determinizm** - ta sama wartość wejściowa zawsze daje ten sam pseudonim:

1. Obliczamy hash SHA-256 z kombinacji: `salt + oryginalna_wartość + typ_encji`
2. Fragment hasha używamy jako seed dla generatora Faker
3. Faker generuje realistyczną, fikcyjną wartość (imię, nazwę firmy, email itp.)

Dla numerów PESEL, NIP, REGON stosujemy własne generatory z **poprawnymi sumami kontrolnymi**.

### 3. Zastępowanie w tekście

```
Tekst + Lista encji → [Sortowanie malejąco po pozycji] → [Zamiana od końca] → Tekst zanonimizowany
```

Zamiany wykonujemy **od końca tekstu**, aby nie popsuć indeksów pozycji wcześniejszych encji.

### Schemat przepływu danych

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TEKST WEJŚCIOWY                             │
│  "Jan Kowalski, PESEL: 90010112345, email: jan@example.com"         │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      1. ANALIZA (Presidio)                          │
│  ┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐   │
│  │ spaCy NLP   │───▶│ SpacyRecognizer  │───▶│ PERSON: 0-12     │   │
│  │ (pl_core_   │    │ (NER: persName)  │    │ "Jan Kowalski"   │   │
│  │  news_lg)   │    └──────────────────┘    └──────────────────┘   │
│  └─────────────┘    ┌──────────────────┐    ┌──────────────────┐   │
│                     │ PeselRecognizer  │───▶│ PL_PESEL: 21-32  │   │
│                     │ (regex + kontekst│    │ "90010112345"    │   │
│                     └──────────────────┘    └──────────────────┘   │
│                     ┌──────────────────┐    ┌──────────────────┐   │
│                     │ EmailRecognizer  │───▶│ EMAIL: 41-57     │   │
│                     │ (regex)          │    │ "jan@example.com"│   │
│                     └──────────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   2. GENEROWANIE ZAMIENNIKÓW                        │
│                                                                     │
│  "Jan Kowalski" ──hash──▶ seed:1234 ──Faker──▶ "Tadeusz Elwart"    │
│  "90010112345"  ──hash──▶ seed:5678 ──PESEL──▶ "97050447064"       │
│  "jan@example.com" ─hash─▶ seed:9012 ─Faker─▶ "dorobekemil@..."    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    3. ZASTĘPOWANIE W TEKŚCIE                        │
│  (od końca, aby zachować indeksy)                                   │
│                                                                     │
│  "Tadeusz Elwart, PESEL: 97050447064, email: dorobekemil@..."      │
└─────────────────────────────────────────────────────────────────────┘
```

## 📦 Wymagania

- Python 3.10+
- spaCy z polskim modelem językowym

## 🚀 Instalacja

### 1. Zainstaluj zależności

```bash
pip install presidio-analyzer presidio-anonymizer faker spacy
```

### 2. Pobierz polski model spaCy

```bash
# Zalecany - duży model z najlepszą dokładnością NER
python -m spacy download pl_core_news_lg

# Alternatywnie - mniejsze modele
python -m spacy download pl_core_news_md  # średni
python -m spacy download pl_core_news_sm  # mały
```

### 3. Sklonuj repozytorium

```bash
git clone <repo-url>
cd presidio-BM
```

## 🧠 Modele spaCy

spaCy oferuje trzy modele dla języka polskiego, różniące się rozmiarem i dokładnością:

| Model | Rozmiar | Wektory | Dokładność NER | Użycie |
|-------|---------|---------|----------------|--------|
| `pl_core_news_sm` | ~15 MB | ❌ Brak | ~85% F1 | Szybkie prototypowanie, ograniczone zasoby |
| `pl_core_news_md` | ~50 MB | ✅ 20k kluczy | ~87% F1 | Balans między rozmiarem a dokładnością |
| `pl_core_news_lg` | ~550 MB | ✅ 500k kluczy | ~89% F1 | **Zalecany** - najlepsza jakość |

### Porównanie modeli

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOKŁADNOŚĆ vs ROZMIAR                        │
│                                                                 │
│  Dokładność │                                    ● pl_core_lg   │
│     NER     │                        ● pl_core_md               │
│             │            ● pl_core_sm                           │
│             │                                                   │
│             └───────────────────────────────────────────────────│
│                         Rozmiar modelu / Czas ładowania         │
└─────────────────────────────────────────────────────────────────┘
```

### Etykiety NER w polskich modelach

Polski model spaCy używa **specyficznych etykiet** różnych od standardowych:

| Etykieta spaCy (PL) | Opis | Mapowanie Presidio |
|---------------------|------|-------------------|
| `persName` | Imię i nazwisko osoby | `PERSON` |
| `orgName` | Nazwa organizacji/firmy | `ORGANIZATION` |
| `placeName` | Nazwa miejsca | `LOCATION` |
| `geogName` | Nazwa geograficzna | `LOCATION` |
| `date` | Data | `DATE_TIME` |
| `time` | Czas | `DATE_TIME` |

> ⚠️ **Ważne**: Standardowe modele angielskie używają etykiet jak `PERSON`, `ORG`, `GPE`. 
> Polski model używa `persName`, `orgName`, `placeName`. 
> Mapowanie jest skonfigurowane w pliku `languages-config.yml`.

### Zmiana modelu

Aby użyć innego modelu, edytuj `languages-config.yml`:

```yaml
models:
  - lang_code: pl
    model_name: pl_core_news_md  # zmień na sm, md lub lg
```

### Instalacja konkretnego modelu

```bash
# Sprawdź zainstalowane modele
python -m spacy info

# Zainstaluj konkretny model
python -m spacy download pl_core_news_lg

# Lub bezpośrednio przez pip (konkretna wersja)
pip install https://github.com/explosion/spacy-models/releases/download/pl_core_news_lg-3.8.0/pl_core_news_lg-3.8.0-py3-none-any.whl
```

### Wybór modelu - rekomendacje

| Scenariusz | Zalecany model |
|------------|----------------|
| Produkcja - wysoka jakość | `pl_core_news_lg` |
| Środowisko z ograniczoną pamięcią | `pl_core_news_md` |
| Szybkie testy / CI/CD | `pl_core_news_sm` |
| Przetwarzanie dużych wolumenów | `pl_core_news_md` (kompromis) |

## 🏁 Szybki start

### Użycie modułu `pseudonymizer.py` (zalecane)

```python
from pseudonymizer import Pseudonymizer

# Utwórz instancję
ps = Pseudonymizer(salt="moj-sekretny-klucz")

# Pseudonimizacja tekstu
text = "Jan Kowalski, PESEL: 90010112345, email: jan@example.com"
result = ps.pseudonymize(text)
print(result)
# Output: "Tadeusz Elwart, PESEL: 97050447064, email: dorobekemil@example.com"
```

### Użycie ze szczegółami

```python
result = ps.pseudonymize_with_details(text)

print(f"Oryginał: {result.original_text}")
print(f"Pseudonim: {result.pseudonymized_text}")
print(f"Znaleziono encji: {result.entities_found}")

for repl in result.replacements:
    print(f"  {repl.entity_type}: '{repl.original}' → '{repl.replacement}'")
```

### Użycie prostego skryptu `gen.py`

```python
from gen import pseudonymize

text = "Jan Kowalski z firmy Drutex, tel: +48 123 456 789"
print(pseudonymize(text))
```

### Uruchomienie demo

```bash
python pseudonymizer.py
```

## ⚙️ Konfiguracja

### Parametry Pseudonymizer

| Parametr | Typ | Domyślna wartość | Opis |
|----------|-----|------------------|------|
| `language` | `str` | `"pl"` | Kod języka do analizy |
| `salt` | `str` | `"<<<USTAW...>>>"` | Sól kryptograficzna dla determinizmu |
| `locale` | `str` | `"pl_PL"` | Locale dla generatora Faker |
| `nlp_config_path` | `Path\|str` | `languages-config.yml` | Ścieżka do konfiguracji NLP |
| `recognizers_config_path` | `Path\|str` | `recognizers-config.yml` | Ścieżka do konfiguracji rozpoznawaczy |

### Przykład z niestandardową konfiguracją

```python
ps = Pseudonymizer(
    salt="super-tajny-klucz-2024",
    locale="pl_PL",
    nlp_config_path="./config/my-nlp.yml",
    recognizers_config_path="./config/my-recognizers.yml"
)
```

## 📊 Obsługiwane typy PII

### Encje wykrywane przez NLP (spaCy)

| Typ | Opis | Przykład |
|-----|------|----------|
| `PERSON` | Imię i nazwisko | Jan Kowalski |
| `ORGANIZATION` | Nazwa firmy/organizacji | Drutex Sp.z.o.o. |
| `LOCATION` | Lokalizacja | Warszawa, Polska |
| `DATE_TIME` | Data i czas | 15 marca 2024 |

### Encje wykrywane przez regex (polskie formaty)

| Typ | Opis | Przykład | Walidacja |
|-----|------|----------|-----------|
| `PL_PESEL` | Numer PESEL | 90010112345 | ✅ Suma kontrolna |
| `PL_NIP` | Numer NIP | 123-456-78-90 | ✅ Suma kontrolna |
| `PL_REGON` | Numer REGON | 123456789 | ✅ Suma kontrolna |
| `PL_ID_CARD` | Dowód osobisty | ABC123456 | ❌ |
| `PL_PASSPORT` | Paszport | AB1234567 | ❌ |
| `PL_POSTAL_CODE` | Kod pocztowy | 00-001 | ❌ |
| `PL_PHONE` | Telefon komórkowy | +48 123 456 789 | ❌ |
| `PL_BANK_ACCOUNT` | Numer konta | 12 3456 7890... | ❌ |

### Encje predefiniowane Presidio

| Typ | Opis | Przykład |
|-----|------|----------|
| `EMAIL_ADDRESS` | Adres email | jan@example.com |
| `PHONE_NUMBER` | Numer telefonu | +48123456789 |
| `CREDIT_CARD` | Karta kredytowa | 4111111111111111 |
| `IBAN_CODE` | Numer IBAN | PL12345678901234567890123456 |
| `IP_ADDRESS` | Adres IP | 192.168.1.1 |
| `URL` | Adres URL | https://example.com |

## 📚 API

### Klasa `Pseudonymizer`

```python
class Pseudonymizer:
    def __init__(
        self,
        *,
        language: str = "pl",
        salt: str = DEFAULT_SALT,
        locale: str = "pl_PL",
        nlp_config_path: Path | str | None = None,
        recognizers_config_path: Path | str | None = None,
    ) -> None: ...

    def analyze(self, text: str) -> list[RecognizerResult]:
        """Analizuje tekst i zwraca wykryte encje PII."""

    def pseudonymize(self, text: str) -> str:
        """Pseudonimizuje tekst, zastępując wykryte PII."""

    def pseudonymize_with_details(self, text: str) -> PseudonymizationResult:
        """Pseudonimizuje tekst i zwraca szczegółowe informacje."""
```

### Klasa `PseudonymizationResult`

```python
@dataclass
class PseudonymizationResult:
    original_text: str
    pseudonymized_text: str
    replacements: list[Replacement]

    @property
    def entities_found(self) -> int: ...

    @property
    def entity_types(self) -> set[str]: ...
```

### Klasa `Replacement`

```python
@dataclass(frozen=True)
class Replacement:
    start: int
    end: int
    original: str
    replacement: str
    entity_type: str
    score: float
```

### Walidatory

```python
from pseudonymizer import PolishIdentifierValidator

validator = PolishIdentifierValidator()

validator.validate_pesel("90010112345")  # True/False
validator.validate_nip("123-456-78-90")  # True/False
validator.validate_regon("123456789")    # True/False
```

### Generatory

```python
from pseudonymizer import PolishIdentifierGenerator

generator = PolishIdentifierGenerator()

generator.generate_pesel(seed=12345)           # "76120183943"
generator.generate_nip(seed=12345)             # "604-534-96-27"
generator.generate_regon(seed=12345, length=9) # "604534961"
```

## 💡 Przykłady użycia

### Przetwarzanie wielu dokumentów

```python
from pseudonymizer import Pseudonymizer

ps = Pseudonymizer(salt="production-salt-2024")

documents = [
    "Klient Jan Kowalski, PESEL 90010112345",
    "Firma ABC Sp.z.o.o., NIP 123-456-78-90",
    "Kontakt: anna.nowak@firma.pl, tel. +48 600 700 800"
]

for doc in documents:
    result = ps.pseudonymize_with_details(doc)
    print(f"Encje: {result.entity_types}")
    print(f"Wynik: {result.pseudonymized_text}\n")
```

### Tylko analiza (bez pseudonimizacji)

```python
ps = Pseudonymizer()
entities = ps.analyze("Jan Kowalski, email: jan@example.com")

for entity in entities:
    print(f"{entity.entity_type}: pozycja {entity.start}-{entity.end}, score={entity.score}")
```

### Integracja z pandas

```python
import pandas as pd
from pseudonymizer import Pseudonymizer

ps = Pseudonymizer(salt="my-salt")

df = pd.DataFrame({
    "notatka": [
        "Klient Jan Kowalski, tel: 123456789",
        "Spotkanie z Anną Nowak z firmy XYZ"
    ]
})

df["notatka_anon"] = df["notatka"].apply(ps.pseudonymize)
```

## 📁 Pliki konfiguracyjne

### `languages-config.yml`

Konfiguracja silnika NLP (spaCy) z mapowaniem etykiet NER:

```yaml
nlp_engine_name: spacy

models:
  - lang_code: pl
    model_name: pl_core_news_lg

ner_model_configuration:
  default_score: 0.6
  model_to_presidio_entity_mapping:
    persName: PERSON      # Polski model używa persName
    orgName: ORGANIZATION
    placeName: LOCATION
    geogName: LOCATION

supported_languages:
  - pl
```

### `recognizers-config.yml`

Konfiguracja rozpoznawaczy z polskimi słowami kontekstowymi:

```yaml
global_regex_flags: 26
supported_languages:
  - pl

recognizers:
  # SpaCy NER (wymagane!)
  - name: SpacyRecognizer
    type: predefined
    supported_languages:
      - language: pl

  # Email z polskim kontekstem
  - name: EmailRecognizer
    type: predefined
    supported_languages:
      - language: pl
        context:
          - email
          - e-mail
          - poczta
          - kontakt

  # Własny rozpoznawacz PESEL
  - name: PolishPeselRecognizer
    type: custom
    supported_entity: PL_PESEL
    supported_languages:
      - language: pl
        context:
          - pesel
          - numer pesel
    patterns:
      - name: pesel_pattern
        regex: "\\b\\d{11}\\b"
        score: 0.5
```

## ✅ Walidacja numerów

Generowane numery PESEL, NIP i REGON są **poprawne** - przechodzą walidację sum kontrolnych:

### PESEL
- Format: 11 cyfr (RRMMDDXXXXY)
- Wagi: 1, 3, 7, 9, 1, 3, 7, 9, 1, 3
- Cyfra kontrolna: `(10 - suma % 10) % 10`

### NIP
- Format: 10 cyfr (XXX-XXX-XX-XX)
- Wagi: 6, 5, 7, 2, 3, 4, 5, 6, 7
- Cyfra kontrolna: `suma % 11` (musi być < 10)

### REGON
- Format: 9 lub 14 cyfr
- Wagi (9-cyfrowy): 8, 9, 2, 3, 4, 5, 6, 7
- Wagi (14-cyfrowy): 2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8

```python
from pseudonymizer import PolishIdentifierGenerator, PolishIdentifierValidator

gen = PolishIdentifierGenerator()
val = PolishIdentifierValidator()

pesel = gen.generate_pesel(seed=12345)
print(f"PESEL: {pesel}, valid: {val.validate_pesel(pesel)}")
# PESEL: 76120183943, valid: True
```

## 🔧 Rozwój

### Struktura projektu

```
presidio-BM/
├── pseudonymizer.py        # Główny moduł (zalecany)
├── gen.py                  # Prosty skrypt
├── languages-config.yml    # Konfiguracja NLP
├── recognizers-config.yml  # Konfiguracja rozpoznawaczy
└── README.md               # Dokumentacja
```

### Dodawanie nowych rozpoznawaczy

1. Edytuj `recognizers-config.yml`
2. Dodaj nowy recognizer:

```yaml
- name: MyCustomRecognizer
  type: custom
  supported_entity: MY_ENTITY
  supported_languages:
    - language: pl
      context:
        - słowo1
        - słowo2
  patterns:
    - name: my_pattern
      regex: "\\b[A-Z]{2}\\d{6}\\b"
      score: 0.7
```

3. Dodaj generator w `pseudonymizer.py`:

```python
# W metodzie _generate_replacement
"MY_ENTITY": lambda: fake.bothify("??######"),
```

### Uruchomienie testów

```bash
python pseudonymizer.py  # Demo z testami walidacji
python gen.py            # Prosty test
```

## 📄 Licencja

MIT License

## 🔗 Linki

- [Microsoft Presidio](https://microsoft.github.io/presidio/)
- [Presidio - Customizing NLP Models](https://microsoft.github.io/presidio/analyzer/customizing_nlp_models/)
- [Presidio - Recognizer Registry](https://microsoft.github.io/presidio/analyzer/recognizer_registry_provider/)
- [Faker Documentation](https://faker.readthedocs.io/)
- [spaCy Polish Models](https://spacy.io/models/pl)
