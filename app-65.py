import os
import time
from urllib.parse import quote_plus
from datetime import date

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Companies House Company Monitor",
    page_icon="🏢",
    layout="wide",
)

SIC_LABELS = {
    "64303": "VC's",
    "64991": "PIC",
    "77400": "Image Rights / Royalties",
    "73199": "Image Rights / Royalties",
    "68100": "Property Dealing",
}
DEFAULT_SICS = list(SIC_LABELS)
BASE_URL = "https://api.company-information.service.gov.uk"


def get_api_key():
    try:
        secret_key = st.secrets.get("COMPANIES_HOUSE_API_KEY", "")
    except Exception:
        secret_key = ""
    return (secret_key or os.getenv("COMPANIES_HOUSE_API_KEY", "")).strip()


def request_json(path, api_key, params=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        auth=(api_key, ""),
        timeout=30,
        headers={"User-Agent": "CompaniesHouseCompanyMonitor/1.0"},
    )
    if response.status_code == 401:
        raise RuntimeError("Companies House rejected the API key.")
    if response.status_code == 429:
        raise RuntimeError("Companies House rate limit reached. Wait and try again.")
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, show_spinner=False)
def search_companies(api_key, start_date, end_date, sic_codes, max_results):
    results = []
    start_index = 0
    page_size = min(500, max_results)

    while len(results) < max_results:
        data = request_json(
            "/advanced-search/companies",
            api_key,
            {
                "incorporated_from": start_date,
                "incorporated_to": end_date,
                "sic_codes": ",".join(sic_codes),
                "size": page_size,
                "start_index": start_index,
            },
        )
        items = data.get("items", [])
        if not items:
            break
        results.extend(items)
        if len(items) < page_size:
            break
        start_index += page_size
        time.sleep(0.15)

    return results[:max_results]


@st.cache_data(ttl=300, show_spinner=False)
def get_company(company_number, api_key):
    return request_json(f"/company/{company_number}", api_key)


@st.cache_data(ttl=300, show_spinner=False)
def get_pscs(company_number, api_key):
    results = []
    start_index = 0

    while True:
        data = request_json(
            f"/company/{company_number}/persons-with-significant-control",
            api_key,
            {"items_per_page": 100, "start_index": start_index},
        )
        items = data.get("items", [])
        results.extend(items)
        total = data.get("total_results", len(results))
        if not items or len(results) >= total or len(items) < 100:
            break
        start_index += 100
        time.sleep(0.1)

    return results


def get_person_name(person):
    if person.get("name"):
        return " ".join(str(person["name"]).split())

    elements = person.get("name_elements", {})
    return " ".join(
        str(value).strip()
        for value in [
            elements.get("title"),
            elements.get("forename"),
            elements.get("middle_name"),
            elements.get("surname"),
        ]
        if value
    ).strip()


def get_birth_month_year(person):
    birth = person.get("date_of_birth") or {}
    month = birth.get("month")
    year = birth.get("year")
    if month and year:
        return f"{int(month):02d}/{year}"
    return ""


def google_link(name):
    return f"https://www.google.com/search?q={quote_plus(name)}" if name else ""


def make_results(items, api_key, include_corporate):
    rows = []
    progress = st.progress(0, text="Retrieving company details…")

    for position, search_item in enumerate(items, start=1):
        company_number = search_item.get("company_number", "")
        try:
            company = get_company(company_number, api_key)
            pscs = get_pscs(company_number, api_key)
        except requests.RequestException as error:
            st.warning(f"Could not retrieve {company_number}: {error}")
            continue

        individual_pscs = [
            psc for psc in pscs
            if psc.get("kind") == "individual-person-with-significant-control"
        ]
        corporate_pscs = [
            psc for psc in pscs
            if psc.get("kind") != "individual-person-with-significant-control"
        ]
        selected_pscs = individual_pscs + (corporate_pscs if include_corporate else [])
        sic_codes = company.get("sic_codes") or search_item.get("sic_codes", [])

        row = {
            "Company name": company.get("company_name") or search_item.get("title", ""),
            "Company number": company_number,
            "Incorporation date": company.get("date_of_creation") or search_item.get("date_of_creation", ""),
            "Company status": company.get("company_status", ""),
            "SIC codes": ", ".join(sic_codes),
            "Matched SIC titles": "; ".join(
                SIC_LABELS[code] for code in sic_codes if code in SIC_LABELS
            ),
            "Companies House link": f"https://find-and-update.company-information.service.gov.uk/company/{company_number}",
        }

        for psc_number, psc in enumerate(selected_pscs, start=1):
            name = get_person_name(psc)
            prefix = f"Shareholder / PSC {psc_number}"
            row[f"{prefix} name"] = name
            row[f"{prefix} type"] = (
                "Individual"
                if psc.get("kind") == "individual-person-with-significant-control"
                else "Corporate / legal entity"
            )
            row[f"{prefix} month/year of birth"] = get_birth_month_year(psc)
            row[f"{prefix} Google search"] = google_link(name)
            row[f"{prefix} nature of control"] = "; ".join(
                psc.get("natures_of_control", [])
            )

        rows.append(row)
        progress.progress(position / max(len(items), 1), text=f"Retrieved {position} of {len(items)} companies")
        time.sleep(0.05)

    progress.empty()
    return pd.DataFrame(rows)


def csv_data(frame):
    return frame.to_csv(index=False).encode("utf-8-sig")


st.title("🏢 Companies House Company Monitor")
st.caption("Individual PSCs are a prospecting proxy and are not verified HNW individuals.")

with st.sidebar:
    st.header("Search settings")
    api_key = get_api_key()

    if not api_key:
        st.error("Add COMPANIES_HOUSE_API_KEY to .env or Streamlit secrets.")

    today = date.today()
    start_date = st.date_input("Incorporated from", value=today, max_value=today)
    end_date = st.date_input("Incorporated to", value=today, min_value=start_date, max_value=today)
    selected_sics = st.multiselect(
        "SIC codes",
        options=DEFAULT_SICS,
        default=DEFAULT_SICS,
        format_func=lambda code: f"{code} — {SIC_LABELS[code]}",
    )
    max_results = st.number_input(
        "Maximum companies per run",
        min_value=1,
        max_value=5000,
        value=500,
        step=50,
    )
    include_corporate = st.checkbox(
        "Include corporate/legal-entity PSCs",
        value=False,
    )
    run_search = st.button("Run search", type="primary", use_container_width=True)
    refresh_search = st.button("Refresh results", use_container_width=True)

if run_search or refresh_search:
    if not api_key:
        st.stop()
    if not selected_sics:
        st.error("Select at least one SIC code.")
        st.stop()
    if start_date > end_date:
        st.error("The start date must be on or before the end date.")
        st.stop()

    with st.spinner("Searching Companies House…"):
        try:
            companies = search_companies(
                api_key,
                start_date.isoformat(),
                end_date.isoformat(),
                selected_sics,
                int(max_results),
            )
            results = make_results(companies, api_key, include_corporate)
            st.session_state["results"] = results
            st.session_state["run_meta"] = {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "company_count": len(results),
            }
        except Exception as error:
            st.error(str(error))

results = st.session_state.get("results")
if results is not None:
    meta = st.session_state.get("run_meta", {})
    st.success(
        f"Found {meta.get('company_count', len(results))} companies "
        f"from {meta.get('start')} to {meta.get('end')}."
    )
    st.download_button(
        "Download CSV",
        data=csv_data(results),
        file_name=f"companies_house_{meta.get('start')}_{meta.get('end')}.csv",
        mime="text/csv",
    )
    st.dataframe(results, use_container_width=True, hide_index=True)
else:
    st.info("Choose a date range and SIC codes, then click Run search.")
