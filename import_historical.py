import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os
import json
import tempfile
import sys
import traceback
import requests
import re

REPO = "dylanpanday/salta-beschikbaarheid-snapshots"
PROJECT_ID = "moonlit-pursuit-265709"
DATASET_ID = "salta_beschikbaarheid"
TABLE_ID = "startmomenten_snapshots"

print("Ophalen lijst met snapshot bestanden...", flush=True)

response = requests.get(f"https://api.github.com/repos/{REPO}/contents/snapshots")
files = response.json()
csv_files = [f for f in files if f["name"].endswith(".csv")]
print(f"{len(csv_files)} bestanden gevonden", flush=True)

rows = []
for f in csv_files:
    match = re.search(r"snapshot_(\d{4}-\d{2}-\d{2})\.csv", f["name"])
    if not match:
        print(f"Overgeslagen (geen datum in naam): {f['name']}", flush=True)
        continue

    datum = match.group(1)
    url = f["download_url"]
    print(f"Laden: {f['name']} -> datum {datum}", flush=True)

    df = pd.read_csv(url)
    df["SnapshotDatum"] = datum
    rows.append(df)

if not rows:
    print("Geen bestanden gevonden", flush=True)
    sys.exit(0)

alle_data = pd.concat(rows)
alle_data["SnapshotDatum"] = alle_data["SnapshotDatum"].astype(str)
alle_data["Startdatum"] = alle_data["Startdatum"].astype(str)
alle_data["NabijheidCategorie"] = alle_data["NabijheidCategorie"].astype(str)
alle_data["DagenTotStart"] = alle_data["DagenTotStart"].astype(int)

print(f"Totaal: {len(alle_data)} rijen over {len(rows)} snapshots", flush=True)

try:
    key_json = os.environ["GBQ_SERVICE_ACCOUNT_KEY"]
    key_dict = json.loads(key_json)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(key_dict, f)
        key_path = f.name

    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=PROJECT_ID, credentials=credentials)

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=[
            bigquery.SchemaField("SnapshotDatum", "DATE"),
            bigquery.SchemaField("Merk", "STRING"),
            bigquery.SchemaField("Id", "STRING"),
            bigquery.SchemaField("Name", "STRING"),
            bigquery.SchemaField("Startdatum", "DATE"),
            bigquery.SchemaField("DagenTotStart", "INTEGER"),
            bigquery.SchemaField("NabijheidCategorie", "STRING"),
        ]
    )

    job = client.load_table_from_dataframe(alle_data, table_ref, job_config=job_config)
    job.result()

    print(f"Klaar -- {len(alle_data)} rijen geschreven naar BigQuery", flush=True)

except Exception as e:
    print(f"FOUT: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
