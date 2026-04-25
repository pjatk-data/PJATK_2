"""
Moduł do pseudonimizacji danych osobowych (PII) w tekstach polskojęzycznych.

Wykorzystuje bibliotekę Presidio do wykrywania PII oraz Faker do generowania
realistycznych, deterministycznych zamienników.

Przykład użycia:
    >>> from pseudonymizer import Pseudonymizer
    >>> ps = Pseudonymizer()
    >>> ps.pseudonymize("Jan Kowalski, PESEL: 90010112345")
    'Tadeusz Elwart, PESEL: 97050447064'
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from faker import Faker
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

if TYPE_CHECKING:
    from collections.abc import Sequence

# =============================================================================
# Stałe konfiguracyjne
# =============================================================================

DEFAULT_LANGUAGE = "pl"
DEFAULT_LOCALE = "pl_PL"
DEFAULT_SALT = "<<<USTAW_TUTAJ_SWÓJ_SEKRETNY_SALT>>>"

# Ścieżki do plików konfiguracyjnych (względem tego modułu)
_MODULE_DIR = Path(__file__).parent
DEFAULT_NLP_CONFIG = _MODULE_DIR / "languages-config.yml"
DEFAULT_RECOGNIZERS_CONFIG = _MODULE_DIR / "recognizers-config.yml"

# Typy encji, dla których zachowujemy wielkość liter
CASE_SENSITIVE_ENTITIES = frozenset({"PERSON", "ORGANIZATION", "LOCATION"})

# Wagi do walidacji polskich numerów identyfikacyjnych
PESEL_WEIGHTS = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)
REGON_9_WEIGHTS = (8, 9, 2, 3, 4, 5, 6, 7)
REGON_14_WEIGHTS = (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8)


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass(frozen=True)
class Replacement:
    """Reprezentuje pojedynczą zamianę w tekście."""

    start: int
    end: int
    original: str
    replacement: str
    entity_type: str
    score: float


@dataclass
class PseudonymizationResult:
    """Wynik pseudonimizacji z metadanymi."""

    original_text: str
    pseudonymized_text: str
    replacements: list[Replacement] = field(default_factory=list)

    @property
    def entities_found(self) -> int:
        """Liczba znalezionych encji PII."""
        return len(self.replacements)

    @property
    def entity_types(self) -> set[str]:
        """Zbiór typów wykrytych encji."""
        return {r.entity_type for r in self.replacements}


# =============================================================================
# Generatory poprawnych numerów identyfikacyjnych
# =============================================================================


class PolishIdentifierGenerator:
    """Generator poprawnych polskich numerów identyfikacyjnych."""

    @staticmethod
    def generate_pesel(seed: int) -> str:
        """
        Generuje poprawny numer PESEL z prawidłową sumą kontrolną.

        Args:
            seed: Ziarno dla generatora liczb losowych (zapewnia determinizm).

        Returns:
            11-cyfrowy numer PESEL.
        """
        rng = random.Random(seed)

        # Data urodzenia (lata 1950-1999)
        year = rng.randint(50, 99)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)

        # Numer seryjny i płeć
        serial = rng.randint(0, 999)
        gender = rng.randint(0, 9)

        pesel_10 = f"{year:02d}{month:02d}{day:02d}{serial:03d}{gender}"

        # Suma kontrolna
        checksum = sum(int(pesel_10[i]) * PESEL_WEIGHTS[i] for i in range(10))
        control_digit = (10 - (checksum % 10)) % 10

        return pesel_10 + str(control_digit)

    @staticmethod
    def generate_nip(seed: int, formatted: bool = True) -> str:
        """
        Generuje poprawny numer NIP z prawidłową sumą kontrolną.

        Args:
            seed: Ziarno dla generatora liczb losowych.
            formatted: Czy formatować jako XXX-XXX-XX-XX.

        Returns:
            10-cyfrowy numer NIP.
        """
        rng = random.Random(seed)
        nip_9 = [rng.randint(0, 9) for _ in range(9)]

        # Suma kontrolna
        checksum = sum(nip_9[i] * NIP_WEIGHTS[i] for i in range(9))
        control_digit = checksum % 11

        # NIP nieprawidłowy gdy suma = 10, trzeba skorygować
        if control_digit == 10:
            nip_9[8] = (nip_9[8] + 1) % 10
            checksum = sum(nip_9[i] * NIP_WEIGHTS[i] for i in range(9))
            control_digit = checksum % 11
            if control_digit == 10:
                control_digit = 0

        nip_str = "".join(map(str, nip_9 + [control_digit]))

        if formatted:
            return f"{nip_str[:3]}-{nip_str[3:6]}-{nip_str[6:8]}-{nip_str[8:10]}"
        return nip_str

    @staticmethod
    def generate_regon(seed: int, length: int = 9) -> str:
        """
        Generuje poprawny numer REGON z prawidłową sumą kontrolną.

        Args:
            seed: Ziarno dla generatora liczb losowych.
            length: Długość REGON (9 lub 14).

        Returns:
            Numer REGON o zadanej długości.

        Raises:
            ValueError: Gdy length nie jest 9 ani 14.
        """
        if length not in (9, 14):
            raise ValueError(f"REGON musi mieć 9 lub 14 cyfr, podano: {length}")

        rng = random.Random(seed)
        weights = REGON_9_WEIGHTS if length == 9 else REGON_14_WEIGHTS
        digits_count = length - 1

        digits = [rng.randint(0, 9) for _ in range(digits_count)]
        checksum = sum(digits[i] * weights[i] for i in range(digits_count))
        control_digit = checksum % 11

        if control_digit == 10:
            control_digit = 0

        return "".join(map(str, digits)) + str(control_digit)


# =============================================================================
# Walidatory
# =============================================================================


class PolishIdentifierValidator:
    """Walidator polskich numerów identyfikacyjnych."""

    @staticmethod
    def validate_pesel(pesel: str) -> bool:
        """Sprawdza poprawność sumy kontrolnej PESEL."""
        pesel_clean = pesel.replace(" ", "").replace("-", "")
        if len(pesel_clean) != 11 or not pesel_clean.isdigit():
            return False

        checksum = sum(int(pesel_clean[i]) * PESEL_WEIGHTS[i] for i in range(10))
        control = (10 - (checksum % 10)) % 10
        return control == int(pesel_clean[10])

    @staticmethod
    def validate_nip(nip: str) -> bool:
        """Sprawdza poprawność sumy kontrolnej NIP."""
        nip_clean = nip.replace("-", "").replace(" ", "")
        if len(nip_clean) != 10 or not nip_clean.isdigit():
            return False

        checksum = sum(int(nip_clean[i]) * NIP_WEIGHTS[i] for i in range(9))
        control = checksum % 11
        return control != 10 and control == int(nip_clean[9])

    @staticmethod
    def validate_regon(regon: str) -> bool:
        """Sprawdza poprawność sumy kontrolnej REGON (9 lub 14 cyfr)."""
        regon_clean = regon.replace(" ", "").replace("-", "")
        if not regon_clean.isdigit():
            return False

        if len(regon_clean) == 9:
            weights = REGON_9_WEIGHTS
        elif len(regon_clean) == 14:
            weights = REGON_14_WEIGHTS
        else:
            return False

        checksum = sum(int(regon_clean[i]) * weights[i] for i in range(len(weights)))
        control = checksum % 11
        if control == 10:
            control = 0
        return control == int(regon_clean[-1])


# =============================================================================
# Główna klasa pseudonimizatora
# =============================================================================


class Pseudonymizer:
    """
    Pseudonimizator danych osobowych (PII) dla tekstów polskojęzycznych.

    Wykorzystuje Presidio do wykrywania PII oraz Faker do generowania
    realistycznych zamienników. Generowanie jest deterministyczne -
    ta sama wartość wejściowa zawsze da ten sam pseudonim.

    Attributes:
        language: Kod języka (domyślnie "pl").
        salt: Sól kryptograficzna dla determinizmu.
        locale: Locale dla Faker (domyślnie "pl_PL").

    Example:
        >>> ps = Pseudonymizer(salt="moj-sekret")
        >>> result = ps.pseudonymize_with_details("Jan Kowalski, tel: +48 123 456 789")
        >>> print(result.pseudonymized_text)
        >>> print(f"Znaleziono {result.entities_found} encji")
    """

    def __init__(
        self,
        *,
        language: str = DEFAULT_LANGUAGE,
        salt: str = DEFAULT_SALT,
        locale: str = DEFAULT_LOCALE,
        nlp_config_path: Path | str | None = None,
        recognizers_config_path: Path | str | None = None,
    ) -> None:
        """
        Inicjalizuje pseudonimizator.

        Args:
            language: Kod języka do analizy.
            salt: Sól kryptograficzna zapewniająca determinizm.
            locale: Locale dla generatora Faker.
            nlp_config_path: Ścieżka do konfiguracji NLP (YAML).
            recognizers_config_path: Ścieżka do konfiguracji rozpoznawaczy (YAML).
        """
        self.language = language
        self.salt = salt
        self.locale = locale

        # Konfiguracja ścieżek
        nlp_config = Path(nlp_config_path) if nlp_config_path else DEFAULT_NLP_CONFIG
        recognizers_config = (
            Path(recognizers_config_path)
            if recognizers_config_path
            else DEFAULT_RECOGNIZERS_CONFIG
        )

        # Inicjalizacja silnika NLP
        nlp_provider = NlpEngineProvider(conf_file=str(nlp_config))
        nlp_engine = nlp_provider.create_engine()

        # Inicjalizacja rejestru rozpoznawaczy
        registry_provider = RecognizerRegistryProvider(
            conf_file=str(recognizers_config)
        )
        registry = registry_provider.create_recognizer_registry()

        # Inicjalizacja analizatora
        self._analyzer = AnalyzerEngine(
            registry=registry,
            nlp_engine=nlp_engine,
            supported_languages=[language],
        )

        # Generator identyfikatorów
        self._id_generator = PolishIdentifierGenerator()

    def _compute_seed(self, value: str, entity_type: str) -> int:
        """Oblicza deterministyczny seed na podstawie wartości i typu."""
        data = f"{self.salt}{value.lower()}{entity_type}"
        hash_hex = hashlib.sha256(data.encode("utf-8")).hexdigest()
        return int(hash_hex[:16], 16)

    def _create_faker(self, seed: int) -> Faker:
        """Tworzy seedowaną instancję Faker."""
        fake = Faker(self.locale)
        fake.seed_instance(seed)
        return fake

    def _generate_replacement(self, original: str, entity_type: str) -> str:
        """Generuje zamiennik dla danej wartości i typu encji."""
        seed = self._compute_seed(original, entity_type)
        fake = self._create_faker(seed)

        generators: dict[str, callable] = {
            "PERSON": fake.name,
            "ORGANIZATION": fake.company,
            "EMAIL_ADDRESS": fake.email,
            "PHONE_NUMBER": fake.phone_number,
            "PL_PHONE": fake.phone_number,
            "PL_PESEL": lambda: self._id_generator.generate_pesel(seed),
            "PL_NIP": lambda: self._id_generator.generate_nip(seed),
            "PL_REGON": lambda: self._id_generator.generate_regon(
                seed, 14 if len(original.replace(" ", "").replace("-", "")) > 9 else 9
            ),
            "PL_ID_CARD": lambda: fake.bothify("???######").upper(),
            "PL_PASSPORT": lambda: fake.bothify("??#######").upper(),
            "PL_POSTAL_CODE": lambda: fake.numerify("##-###"),
            "PL_BANK_ACCOUNT": lambda: fake.numerify(
                "## #### #### #### #### #### ####"
            ),
            "IBAN_CODE": fake.iban,
            "CREDIT_CARD": fake.credit_card_number,
            "IP_ADDRESS": fake.ipv4,
            "URL": fake.url,
            "DATE_TIME": fake.date,
            "LOCATION": fake.city,
        }

        generator = generators.get(entity_type)
        if generator:
            return generator()

        # Domyślnie: maskowanie gwiazdkami
        return "*" * len(original)

    @staticmethod
    def _match_casing(source: str, replacement: str) -> str:
        """Dopasowuje wielkość liter zamiennika do oryginału."""
        if source.isupper():
            return replacement.upper()

        words = source.split()
        if words and all(
            w[0].isupper() and w[1:].islower() for w in words if len(w) > 1
        ):
            return " ".join(w.capitalize() if w else w for w in replacement.split())

        return replacement

    @staticmethod
    def _filter_overlapping(
        results: Sequence[RecognizerResult],
    ) -> list[RecognizerResult]:
        """Filtruje nakładające się encje, zostawiając te z najwyższym score."""
        if not results:
            return []

        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
        filtered: list[RecognizerResult] = []

        for result in sorted_results:
            is_overlapping = any(
                not (result.end <= accepted.start or result.start >= accepted.end)
                for accepted in filtered
            )
            if not is_overlapping:
                filtered.append(result)

        return filtered

    def analyze(self, text: str) -> list[RecognizerResult]:
        """
        Analizuje tekst i zwraca wykryte encje PII.

        Args:
            text: Tekst do analizy.

        Returns:
            Lista wykrytych encji (bez nakładających się).
        """
        results = self._analyzer.analyze(text=text, language=self.language)
        return self._filter_overlapping(results)

    def pseudonymize(self, text: str) -> str:
        """
        Pseudonimizuje tekst, zastępując wykryte PII.

        Args:
            text: Tekst do pseudonimizacji.

        Returns:
            Tekst z zamienionymi danymi osobowymi.
        """
        return self.pseudonymize_with_details(text).pseudonymized_text

    def pseudonymize_with_details(self, text: str) -> PseudonymizationResult:
        """
        Pseudonimizuje tekst i zwraca szczegółowe informacje.

        Args:
            text: Tekst do pseudonimizacji.

        Returns:
            Obiekt PseudonymizationResult z tekstem i metadanymi.
        """
        results = self.analyze(text)
        replacements: list[Replacement] = []
        mapping: dict[tuple[str, str], str] = {}

        # Przygotuj zamienniki
        for result in results:
            original = text[result.start : result.end]
            key = (original.strip().lower(), result.entity_type)

            if key not in mapping:
                replacement_text = self._generate_replacement(
                    original, result.entity_type
                )
                if result.entity_type in CASE_SENSITIVE_ENTITIES:
                    replacement_text = self._match_casing(original, replacement_text)
                mapping[key] = replacement_text

            replacements.append(
                Replacement(
                    start=result.start,
                    end=result.end,
                    original=original,
                    replacement=mapping[key],
                    entity_type=result.entity_type,
                    score=result.score,
                )
            )

        # Zastosuj zamiany (od końca, by zachować indeksy)
        new_text = text
        for repl in sorted(replacements, key=lambda r: r.start, reverse=True):
            new_text = new_text[: repl.start] + repl.replacement + new_text[repl.end :]

        return PseudonymizationResult(
            original_text=text,
            pseudonymized_text=new_text,
            replacements=replacements,
        )


# =============================================================================
# CLI / Demo
# =============================================================================


def main() -> None:
    """Funkcja demonstracyjna."""
    print("=" * 70)
    print("PSEUDONIMIZATOR PII - DEMO")
    print("=" * 70)

    pseudonymizer = Pseudonymizer()
    validator = PolishIdentifierValidator()

    # Test 1: Imiona i nazwy firm
    print("\n[1] Test pseudonimizacji osób i firm")
    print("-" * 50)

    sample = (
        "Jan Kowalski spotkał ANNĘ NOWAK i Jana Kowalskiego w siedzibie banku. "
        "Następnie Jan KOWALSKI udał się na spotkanie. "
        "Obecni byli także Piotr Zięba i Maria Wiśniewska z firmy Drutex Sp.z.o.o."
    )

    result = pseudonymizer.pseudonymize_with_details(sample)
    print(f"ORYGINAŁ:    {result.original_text}")
    print(f"PSEUDONIM:   {result.pseudonymized_text}")
    print(f"Encje ({result.entities_found}): {result.entity_types}")

    # Test 2: Różne typy PII
    print("\n[2] Test różnych typów PII")
    print("-" * 50)

    test_text = (
        "Nazywam się Jan Kowalski. "
        "Mój e-mail to jan.kowalski@example.com, telefon: +48 123 456 789. "
        "PESEL: 90010112345, NIP: 123-456-78-90. "
        "Numer konta: 12 3456 7890 1234 5678 9012 3456."
    )

    result = pseudonymizer.pseudonymize_with_details(test_text)
    print(f"ORYGINAŁ:\n  {result.original_text}\n")
    print("WYKRYTE ENCJE:")
    for repl in sorted(result.replacements, key=lambda r: r.start):
        print(
            f"  • {repl.entity_type}: '{repl.original}' → '{repl.replacement}' (score={repl.score:.2f})"
        )
    print(f"\nPSEUDONIM:\n  {result.pseudonymized_text}")

    # Test 3: Walidacja generowanych numerów
    print("\n[3] Test walidacji PESEL i NIP")
    print("-" * 50)

    generator = PolishIdentifierGenerator()

    for seed in [12345, 67890, 11111]:
        pesel = generator.generate_pesel(seed)
        nip = generator.generate_nip(seed)
        regon = generator.generate_regon(seed)

        print(f"Seed {seed}:")
        print(f"  PESEL: {pesel} → {'✓' if validator.validate_pesel(pesel) else '✗'}")
        print(f"  NIP:   {nip} → {'✓' if validator.validate_nip(nip) else '✗'}")
        print(f"  REGON: {regon} → {'✓' if validator.validate_regon(regon) else '✗'}")

    print("\n" + "=" * 70)
    print("DEMO ZAKOŃCZONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
