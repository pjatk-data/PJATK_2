
Jesteście zespołem developerskim budującym **aplikację „CityHub”** – platformę łączącą lokalne sklepy i usługi z klientami. Aplikacja ma moduły:

*   **Użytkownicy** (klienci i sprzedawcy),
*   **Sklepy** (z kategoriami, godzinami otwarcia, geolokalizacją),
*   **Produkty** (z ceną, kodem kreskowym, dostępnością),
*   **Zamówienia** (statusy, płatności, koszyk, historia),
*   **Logi sesji** (user agent, IP, czas, urządzenie).

Zespół QA potrzebuje **wiarygodnych, różnorodnych danych testowych**, które zasymulują realne scenariusze: różne kraje, formaty adresów, błędne dane, sezonowe skoki zamówień, różne typy płatności. Dane mają pokrywać przypadki brzegowe i umożliwiać testy integracyjne.

***

## 🎯 Zadanie do wykonania

**Cel:** Wygeneruj zestaw danych testowych (np. 5–10 tys. rekordów) korzystając z providerów Faker zgodnie z poniższą specyfikacją. Zadbaj o spójność relacji, realizm oraz obecność kontrolowanych „anomalii”.

### 1) Zaprojektuj schemat danych (minimalny zakres)

**Użytkownik (`User`)**

*   `user_id` (UUID)
*   `role` (enum: `customer` / `seller`)
*   `profile`: imię, nazwisko, email, telefon (`person`, `profile`, `phone_number`, `internet`)
*   `address`: ulica, miasto, region, kraj, kod, współrzędne (`address`, `geo`)
*   `preferences`: język, kanał powiadomień (email/SMS/push)

**Sklep (`Shop`)**

*   `shop_id` (UUID), `owner_user_id`
*   `name`, `company_info` (`company`)
*   `category` (np. `grocery`, `electronics`, `books`, `services`)
*   `location`: adres + `lat/lon` (`address`, `geo`)
*   `hours`: harmonogram (pn–nd, przedziały czasowe)
*   `rating` (0–5, rozkład normalny z odchyleniem)

**Produkt (`Product`)**

*   `product_id` (UUID), `shop_id`
*   `name`, `description` (`lorem`)
*   `price` (waluty różne, `currency`)
*   `barcode` (`barcode`)
*   `stock` (0–500, z rozkładem pareto dla „long tail”)

**Zamówienie (`Order`)**

*   `order_id`, `customer_user_id`, `shop_id`
*   pozycje (lista `product_id`, `qty`, `unit_price`)
*   `status` (enum: `created`, `paid`, `shipped`, `delivered`, `cancelled`, `returned`)
*   `payment`: typ (`card`, `cash`, `wallet`), szczegóły karty (`credit_card`) – tylko do środowiska dev!
*   `timestamps`: `created_at`, `updated_at` (`date_time`)
*   `shipping_address` (może różnić się od `User.address`)

**Log sesji (`SessionLog`)**

*   `session_id`, `user_id`, `timestamp` (`date_time`)
*   `ip`, `user_agent`, `device` (`internet`, `user_agent`)
*   `action` (np. `login`, `view_product`, `add_to_cart`, `checkout`, `logout`)

### 2) Reguły realizmu i spójności

*   Relacje: `Shop.owner_user_id` musi wskazywać na `User.role = seller`. Produkty są powiązane z istniejącymi sklepami. Zamówienia łączą klientów, sklepy i produkty.
*   **Dystrybucje wartości**:
    *   `rating` \~ normalna (μ≈4.1, σ≈0.6, obcięta do \[1,5]).
    *   `stock` \~ pareto (dużo niskich stanów, kilka wysokich).
    *   `price` zależy od `category` (np. electronics > books).
    *   Godziny szczytu zamówień: 18:00–22:00 (większy wolumen).
*   **Geografia**: uwiarygodnij adresy z różnych krajów (różne formaty kodów pocztowych; np. PL, DE, FR, UK, US), z poprawnymi `lat/lon`. Dodaj kilka nietypowych opisów adresów (np. „zielony dom na rogu”) jako pole dodatkowe `address_note`.
*   **Dane wrażliwe**: karty tylko w środowisku dev; nie używaj prawdziwych danych, zawsze generuj przez Faker.

### 3) Kontrolowane anomalie (do testów walidacji)

*   \~2% adresów z **brakującym kodem pocztowym**.
*   \~1% zamówień ze stanem `paid` **bez** `payment_details` (test spójności).
*   \~3% produktów z **ceną = 0** (test promocji / błędów cenowych).
*   \~5% logów sesji z **nietypowym user agentem** (np. boty, stare przeglądarki).
*   \~1% zamówień z **sprzecznymi timestampami** (`updated_at < created_at`).

### 4) Formaty wyjściowe

*   Zapisz dane jako:
    *   `users.jsonl`, `shops.jsonl`, `products.jsonl`, `orders.jsonl`, `sessions.jsonl` (JSON Lines),
    *   oraz zagregowany `dataset_summary.md` (liczności, rozkłady, wskaźniki anomalii).

### 5) Kryteria zaliczenia

*   **Spójność referencyjna** (brak wiszących kluczy).
*   **Realizm formatów** (telefony, kody, maile, user agent).
*   **Różnorodność** (kraje, kategorie, waluty).
*   **Anomalie** w zadanych odsetkach.
*   **Replikowalność** (ustawiony `random_seed`, skrypt uruchamialny).
*   **Krótki raport** (`dataset_summary.md`) z metrykami i przykładowymi rekordami.

***

## 📦 Przykładowy szkic danych (JSON)

```json
{
  "User": {
    "user_id": "c3c7c0a4-7c3f-4a8b-9e3a-1f2b9b1e2a11",
    "role": "customer",
    "profile": { "first_name": "Anna", "last_name": "Kowalska", "email": "anna.kowalska@example.com", "phone": "+48 600 123 456" },
    "address": { "street": "ul. Marszałkowska 10", "city": "Warszawa", "postal_code": "00-001", "country": "PL", "lat": 52.2297, "lon": 21.0122 },
    "preferences": { "language": "pl", "notifications": "email" }
  },
  "Shop": {
    "shop_id": "8f1d3b6a-0b1a-4c06-9d4e-9a56c0f92b33",
    "owner_user_id": "e5b2e51c-9d45-4b0e-9a25-0f3f20c8a7d2",
    "name": "TechNova",
    "company_info": { "name": "TechNova Sp. z o.o.", "vat": "PL1234567890" },
    "category": "electronics",
    "location": { "address": "al. Jerozolimskie 100, Warszawa", "lat": 52.229, "lon": 21.011 },
    "hours": { "mon_fri": "09:00-19:00", "sat": "10:00-16:00", "sun": "closed" },
    "rating": 4.5
  },
  "Product": {
    "product_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    "shop_id": "8f1d3b6a-0b1a-4c06-9d4e-9a56c0f92b33",
    "name": "Smartfon X",
    "description": "Nowoczesny smartfon z 128GB pamięci i ekranem OLED.",
    "price": { "amount": 2499.00, "currency": "PLN" },
    "barcode": "5901234123457",
    "stock": 42
  },
  "Order": {
    "order_id": "77aa22bb-33cc-44dd-55ee-66ff77889900",
    "customer_user_id": "c3c7c0a4-7c3f-4a8b-9e3a-1f2b9b1e2a11",
    "shop_id": "8f1d3b6a-0b1a-4c06-9d4e-9a56c0f92b33",
    "items": [
      { "product_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab", "qty": 1, "unit_price": 2499.00 }
    ],
    "status": "paid",
    "payment": { "type": "card", "card_masked": "4111 **** **** 1111" },
    "timestamps": { "created_at": "2025-12-12T18:43:10Z", "updated_at": "2025-12-12T18:45:03Z" },
    "shipping_address": { "street": "ul. Prosta 51", "city": "Warszawa", "postal_code": "00-838", "country": "PL" }
  },
  "SessionLog": {
    "session_id": "sess_01H9KJ3T04",
    "user_id": "c3c7c0a4-7c3f-4a8b-9e3a-1f2b9b1e2a11",
    "timestamp": "2025-12-12T18:44:00Z",
    "ip": "83.1.24.200",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "device": "desktop",
    "action": "checkout"
  }
}
```

***

## 🧪 Podpowiedź: co wykorzystać z Faker

*   `faker.providers.person`, `profile`, `job` – osoby, profile, zawody.
*   `address`, `geo` – adresy, współrzędne.
*   `company`, `credit_card`, `currency` – firmy, płatności, waluty.
*   `phone_number`, `internet` (email, domain, IP) – kontakt, sieć.
*   `date_time` – czas operacji, sesje, zamówienia.
*   `barcode` – kody produktów.
*   `user_agent` – identyfikacja przeglądarki/urządzeń.
*   `lorem`, `file` – opisy, nazwy plików (np. zdjęcia produktów).

***

## 🔍 Rozszerzenia (opcjonalnie)

*   Dodaj **fraudy** (np. wiele zamówień z tego samego IP, sprzeczne adresy, dziwne geolokacje).
*   Zaimplementuj **walidatory** (np. testy Pydantic/JSON Schema).
*   Wygeneruj **metryki** i wykresy (histogram cen, rozkład ratingów, mapa ciepła godzin).
*   Zasymuluj **sezonowość** (np. Black Friday, święta – wzrost zamówień).
*   Dodaj **lokalizacje** (napisy w różnych językach dla produktów).

