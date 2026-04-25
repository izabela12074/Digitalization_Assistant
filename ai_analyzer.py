import os
import json
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """Jesteś ekspertem ds. digitalizacji procesów produkcyjnych (Lean Manufacturing, TPM).
Analizujesz dane i zwracasz WYŁĄCZNIE krótki JSON. Bądź zwięzły – maksymalnie 2 problemy i 2 rekomendacje.

Format (czysty JSON, bez ```):
{
  "podsumowanie": "max 2 zdania",
  "ocena_ryzyka": "Wysokie / Średnie / Niskie",
  "uzasadnienie_ryzyka": "1 zdanie",
  "problemy": [
    {"nazwa": "max 4 słowa", "opis": "1 zdanie z liczbami", "waga": "Wysoka / Średnia / Niska", "affected_kpi": "nazwa KPI"}
  ],
  "przyczyny_korzeniowe": [
    {"problem": "nazwa", "analiza_5why": "Dlaczego 1 → Dlaczego 2 → Przyczyna"}
  ],
  "rekomendacje": [
    {"akcja": "1 zdanie", "priorytet": "Natychmiastowy / Krótkoterminowy / Długoterminowy", "lean_tool": "nazwa", "oczekiwany_efekt": "1 zdanie", "odpowiedzialny": "rola"}
  ],
  "kpi_do_monitorowania": [
    {"nazwa": "KPI", "cel": "wartość", "czestotliwosc": "dzienna / tygodniowa"}
  ]
}"""


def clean_and_parse(raw: str) -> dict:
    """Czyści odpowiedź AI i parsuje JSON – obsługuje urwane odpowiedzi."""

    # Usuń bloki ```json```
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()

    # Spróbuj sparsować normalnie
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Jeśli JSON jest urwany – spróbuj go domknąć
    # Zlicz otwarte nawiasy klamrowe i kwadratowe
    open_braces   = raw.count('{') - raw.count('}')
    open_brackets = raw.count('[') - raw.count(']')

    # Zamknij otwarte struktury
    raw += ']' * max(0, open_brackets)
    raw += '}' * max(0, open_braces)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Ostatnia deska ratunku – wyciągnij to co się da regex
    result = {
        "podsumowanie": "Analiza częściowa – odpowiedź AI została skrócona.",
        "ocena_ryzyka": "Średnie",
        "uzasadnienie_ryzyka": "Brak pełnych danych do oceny.",
        "problemy": [],
        "przyczyny_korzeniowe": [],
        "rekomendacje": [],
        "kpi_do_monitorowania": []
    }

    # Wyciągnij podsumowanie jeśli jest
    match = re.search(r'"podsumowanie"\s*:\s*"([^"]+)"', raw)
    if match:
        result["podsumowanie"] = match.group(1)

    match = re.search(r'"ocena_ryzyka"\s*:\s*"([^"]+)"', raw)
    if match:
        result["ocena_ryzyka"] = match.group(1)

    return result


def analyze(data_text: str, user_question: str = "") -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    user_content = f"""Przeanalizuj dane produkcyjne. Odpowiedz TYLKO krótkim JSON.

{data_text}
"""
    if user_question.strip():
        user_content += f"\nPytanie: {user_question}\n"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}]
    )

    raw_text = message.content[0].text
    return clean_and_parse(raw_text)


def test_connection() -> bool:
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Odpowiedz tylko słowem: OK"}]
        )
        print(f"Odpowiedź Claude: {message.content[0].text.strip()}")
        return True
    except Exception as e:
        print(f"Błąd połączenia: {e}")
        return False


if __name__ == "__main__":
    print("Testuję połączenie z Claude API...")
    if test_connection():
        print("✅ Połączenie działa!")
    else:
        print("❌ Problem z połączeniem.")