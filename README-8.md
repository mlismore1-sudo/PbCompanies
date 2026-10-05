# Companies House Company Monitor

A Streamlit app for monitoring newly incorporated UK companies matching selected SIC codes. It retrieves company details and Persons with Significant Control (PSC) records from Companies House, adds Google search links for individual PSCs, and exports results as CSV.

## Important limitation
Companies House does not publish a definitive high-net-worth flag. This app uses individual PSCs as a prospecting proxy. It does not prove that a person is HNW, and PSC data is not necessarily a complete shareholder register.

## Supported SIC codes

| SIC code | Label |
|---|---|
| 64303 | VC's |
| 64991 | PIC |
| 77400 | Image Rights / Royalties |
| 73199 | Image Rights / Royalties |
| 68100 | Property Dealing |

## Features

- Choose an incorporation start and end date before searching.
- Search one or more of the configured SIC codes.
- Retrieve Companies House company details.
- Retrieve individual PSC records and optionally corporate/legal-entity PSCs.
- Create separate columns for PSC 1, PSC 2, PSC 3, and so on.
- Show month and year of birth where supplied by Companies House.
- Add Google search links for each individual PSC.
- Download the result as a CSV file.
- Refresh the same query during the day to identify newly available records.
- Cache API responses briefly to reduce unnecessary duplicate requests.

## Requirements

- A GitHub account.
- A Streamlit Community Cloud account.
- A Companies House API key.

## Local setup

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd companies-house-hnw-monitor
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Add your API key to `.env`:

```env
COMPANIES_HOUSE_API_KEY=your_api_key_here
```

Run locally:

```bash
streamlit run app.py
```

## Streamlit Community Cloud deployment

1. Push all files in this repository to GitHub.
2. Open Streamlit Community Cloud.
3. Create a new app from the GitHub repository.
4. Select `app.py` as the main file.
5. Open the app's Advanced settings and add this secret:

```toml
COMPANIES_HOUSE_API_KEY = "your_api_key_here"
```

6. Deploy the app.

No Render account or Render configuration is required.

## Daily workflow

Set the date range and SIC codes, then click **Run search**. To repeat the same search later in the day, click **Refresh results**. Companies House data may not appear immediately after incorporation, so repeating the search is expected.

The maximum number of companies per run defaults to 500. Increase it only when necessary and remain mindful of Companies House API rate limits.

## Data protection

PSC information is personal data. Use the output lawfully and securely for an appropriate business purpose. Do not publish downloaded files or infer wealth, suitability, or other sensitive characteristics without appropriate checks.
