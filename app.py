import streamlit as st
import pandas as pd
from data_processor import load_data, get_summary, format_for_prompt
from ai_analyzer import analyze

# ── Konfiguracja strony ──
st.set_page_config(
    page_title="Process Digitalization Assistant",
    page_icon="🏭",
    layout="wide"
)

# ── Style ──
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: white; padding: 16px; border-radius: 8px; border-left: 4px solid #1F4E79; }
    .risk-high { background: #fee2e2; border-radius: 8px; padding: 12px; border-left: 4px solid #dc2626; }
    .risk-mid  { background: #fef9c3; border-radius: 8px; padding: 12px; border-left: 4px solid #ca8a04; }
    .risk-low  { background: #dcfce7; border-radius: 8px; padding: 12px; border-left: 4px solid #16a34a; }
</style>
""", unsafe_allow_html=True)

# ── Nagłówek ──
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("# 🏭")
with col_title:
    st.title("Process Digitalization Assistant")
    st.caption("Automatyczna analiza danych produkcyjnych z rekomendacjami Lean/TPM | powered by Claude AI")

st.divider()

# ── Sidebar ──
with st.sidebar:
    st.header("⚙️ Ustawienia analizy")
    n_rows = st.slider("Liczba rekordów do analizy", 20, 200, 50,
                       help="Więcej rekordów = dokładniejsza analiza, ale wolniejsza odpowiedź AI")
    st.divider()
    user_question = st.text_area(
        "💬 Dodatkowe pytanie (opcjonalne)",
        placeholder="Np. Które parametry najbardziej wpływają na DefectStatus?",
        height=100
    )
    st.divider()
    st.markdown("**ℹ️ Jak działa aplikacja:**")
    st.markdown("""
    1. Wgraj dane CSV
    2. Kliknij **Analizuj**
    3. AI identyfikuje problemy metodą **5Why**
    4. Otrzymujesz rekomendacje **Lean/TPM**
    """)

# ── Upload danych ──
st.subheader("📁 Wczytaj dane produkcyjne")

uploaded_file = st.file_uploader(
    "Przeciągnij plik CSV lub kliknij Browse",
    type=['csv'],
    help="Obsługiwane formaty: CSV. Przykładowy dataset: kaggle.com/datasets/rabieelkharoua/predicting-manufacturing-defects-dataset"
)

# ── Główna logika ──
if uploaded_file:
    df = load_data(uploaded_file)

    # Podgląd danych
    with st.expander("📊 Podgląd wczytanych danych", expanded=False):
        st.dataframe(df.head(20), use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Rekordów", f"{len(df):,}")
        c2.metric("Kolumn", len(df.columns))
        c3.metric("Brakujące wartości", int(df.isnull().sum().sum()))

    st.divider()

    # Przycisk analizy
    if st.button("🔍 Analizuj z AI", type="primary", use_container_width=True):
        with st.spinner("🤖 Claude analizuje dane produkcyjne... (10–20 sekund)"):
            try:
                summary  = get_summary(df, n_rows)
                data_text = format_for_prompt(summary)
                result   = analyze(data_text, user_question)

                st.success("✅ Analiza zakończona!")
                st.divider()

                # ── PODSUMOWANIE + RYZYKO ──
                st.subheader("📋 Podsumowanie")
                st.info(result.get("podsumowanie", "—"))

                risk = result.get("ocena_ryzyka", "Średnie")
                uzasadnienie = result.get("uzasadnienie_ryzyka", "")
                if "Wysokie" in risk:
                    st.markdown(f'<div class="risk-high">⚠️ <strong>Ocena ryzyka: {risk}</strong><br>{uzasadnienie}</div>', unsafe_allow_html=True)
                elif "Średnie" in risk:
                    st.markdown(f'<div class="risk-mid">⚡ <strong>Ocena ryzyka: {risk}</strong><br>{uzasadnienie}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="risk-low">✅ <strong>Ocena ryzyka: {risk}</strong><br>{uzasadnienie}</div>', unsafe_allow_html=True)

                st.divider()

                # ── PROBLEMY + REKOMENDACJE obok siebie ──
                col_prob, col_rek = st.columns(2)

                with col_prob:
                    st.subheader("🔴 Zidentyfikowane problemy")
                    for p in result.get("problemy", []):
                        icon = "🔴" if p["waga"] == "Wysoka" else "🟡" if p["waga"] == "Średnia" else "🟢"
                        with st.expander(f"{icon} {p['nazwa']} — {p['waga']}"):
                            st.write(p["opis"])
                            st.caption(f"📊 KPI: {p.get('affected_kpi', '—')}")

                with col_rek:
                    st.subheader("✅ Rekomendacje działań")
                    for r in result.get("rekomendacje", []):
                        icon = "🚨" if r["priorytet"] == "Natychmiastowy" else "📅" if r["priorytet"] == "Krótkoterminowy" else "🔭"
                        with st.expander(f"{icon} {r['akcja'][:60]}... — {r['priorytet']}"):
                            st.markdown(f"**🔧 Narzędzie Lean/TPM:** {r.get('lean_tool', '—')}")
                            st.markdown(f"**📈 Oczekiwany efekt:** {r.get('oczekiwany_efekt', '—')}")
                            st.markdown(f"**👤 Odpowiedzialny:** {r.get('odpowiedzialny', '—')}")

                st.divider()

                # ── PRZYCZYNY KORZENIOWE ──
                st.subheader("🌿 Analiza przyczyn korzeniowych (metoda 5Why)")
                for pk in result.get("przyczyny_korzeniowe", []):
                    with st.expander(f"🔎 {pk['problem']}"):
                        steps = pk["analiza_5why"].split("→")
                        for i, step in enumerate(steps, 1):
                            if step.strip():
                                st.markdown(f"**Dlaczego {i}:** {step.strip()}")

                st.divider()

                # ── KPI DO MONITOROWANIA ──
                st.subheader("📈 KPI do monitorowania w Power BI")
                kpis = result.get("kpi_do_monitorowania", [])
                if kpis:
                    cols = st.columns(min(len(kpis), 3))
                    for i, kpi in enumerate(kpis):
                        with cols[i % 3]:
                            st.metric(
                                label=kpi.get("nazwa", "—"),
                                value=kpi.get("cel", "—"),
                                delta=kpi.get("czestotliwosc", "")
                            )

            except Exception as e:
                st.error(f"❌ Błąd podczas analizy: {e}")
                st.info("Sprawdź czy klucz API w pliku .env jest poprawny.")

else:
    # Stan początkowy – instrukcja
    st.info("👆 Wgraj plik CSV z danymi produkcyjnymi aby rozpocząć analizę.")

    with st.expander("📌 Przykładowe kolumny obsługiwane przez aplikację"):
        st.markdown("""
        | Kolumna | Opis |
        |---|---|
        | `DefectRate` | Wskaźnik defektów (%) |
        | `DowntimePercentage` | % przestojów |
        | `QualityScore` | Ogólny wynik jakości |
        | `MaintenanceHours` | Godziny przeglądów |
        | `WorkerProductivity` | Produktywność pracowników |
        | `SafetyIncidents` | Liczba incydentów BHP |
        | `EnergyConsumption` | Zużycie energii |
        | `DefectStatus` | Status defektu (0/1) |
        """)