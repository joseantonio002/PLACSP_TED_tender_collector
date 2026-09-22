import json
import requests


url = "https://api.ted.europa.eu/v3/notices/search"

payload = {
    "query": (
        "buyer-country=ESP "
        "AND publication-date>=20260901 "
        "SORT BY publication-date DESC"
    ),
    "fields": [
        "publication-number",
        "publication-date",
        "notice-title",
        "notice-type",
        "procedure-identifier",
        "buyer-name",
        "buyer-country",
        "classification-cpv",
    ],
    "page": 1,
    "limit": 1,
    "scope": "ALL",
    "checkQuerySyntax": False,
    "paginationMode": "PAGE_NUMBER",
}

response = requests.post(
    url,
    json=payload,
    timeout=30,
)

response.raise_for_status()

data = response.json()

print(json.dumps(data, indent=2, ensure_ascii=False))