import pandas as pd
import json

def load_data(filepath: str) -> pd.DataFrame:
    """Wczytuje plik CSV z danymi produkcyjnymi."""
    df = pd.read_csv(filepath)
    return df

def get_summary(df: pd.DataFrame, n_rows: int = 50) -> dict:
    """
    Tworzy zwięzłe podsumowanie danych do wysłania do AI.
    AI nie przetworzy 10 000 wierszy – wysyłamy skrót + próbkę.
    """

    # Statystyki dla kolumn liczbowych
    numeric_stats = {}
    for col in df.select_dtypes(include='number').columns:
        numeric_stats[col] = {
            "srednia":  round(df[col].mean(), 3),
            "min":      round(df[col].min(), 3),
            "max":      round(df[col].max(), 3),
            "odch_std": round(df[col].std(), 3),
        }

    # Statystyki dla kolumn tekstowych / kategorycznych
    categorical_stats = {}
    for col in df.select_dtypes(include='object').columns:
        categorical_stats[col] = df[col].value_counts().head(5).to_dict()

    # Próbka danych (pierwszych n wierszy)
    sample = df.head(n_rows).to_dict(orient='records')

    summary = {
        "liczba_rekordow": len(df),
        "kolumny": df.columns.tolist(),
        "statystyki_liczbowe": numeric_stats,
        "statystyki_kategoryczne": categorical_stats,
        "probka_danych": sample,
    }

    return summary


def format_for_prompt(summary: dict) -> str:
    """Zamienia słownik podsumowania na czytelny tekst dla AI."""

    # Statystyki liczbowe
    stats_text = ""
    for col, s in summary["statystyki_liczbowe"].items():
        stats_text += (
            f"  • {col}: średnia={s['srednia']}, "
            f"min={s['min']}, max={s['max']}, "
            f"odch.std={s['odch_std']}\n"
        )

    # Statystyki kategoryczne
    cat_text = ""
    for col, vals in summary["statystyki_kategoryczne"].items():
        top = ", ".join([f"{k}: {v}" for k, v in vals.items()])
        cat_text += f"  • {col}: {top}\n"

    # Próbka jako JSON (tylko 10 pierwszych rekordów żeby nie przytłoczyć AI)
    sample_json = json.dumps(
        summary["probka_danych"][:10],
        indent=2,
        ensure_ascii=False,
        default=str
    )

    prompt_text = f"""
=== DANE PRODUKCYJNE DO ANALIZY ===

Liczba rekordów: {summary['liczba_rekordow']}
Kolumny: {', '.join(summary['kolumny'])}

STATYSTYKI LICZBOWE:
{stats_text}
STATYSTYKI KATEGORYCZNE:
{cat_text}
PRZYKŁADOWE REKORDY (pierwsze 10):
{sample_json}
"""
    return prompt_text