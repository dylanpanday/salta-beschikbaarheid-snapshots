import pandas as pd
from datetime import date
from google.cloud import bigquery
from google.oauth2 import service_account
import os
import json
import tempfile
import sys
import traceback

LABELS = {
    "BAN": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-ban.csv",
    "BVO": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-bvo.csv",
    "Computrain": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-computrain.csv",
    "ISBW": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-isbw.csv",
    "MVP": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-mvp.csv",
    "NCOI": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-ncoi.csv",
    "NIBE-SVV": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-nibe-svv.csv",
    "Pro Education": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-proeducation.csv",
    "Schoevers": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-schoevers.csv",
}

PROJECT_ID = "moonlit-pursuit-265709"
DATASET_ID = "salta_beschikbaarheid"
TABLE_ID = "startmomenten_snapshots"

today = date.today()
rows = []

print(f"Start snapshot voor {today}", flush=True)

for merk, url in LABELS.items():
    print(f"Laden: {merk}", flush=True)
    df = pd.read_csv(url)
    df["Merk"] = merk
    df["SnapshotDatum"] = today

    df["StartDates"] = df["StartDates"].astype(str)
    df = df.assign(Startdatum=df["StartDates"].str.split("|")).explode("Startdatum")
    df["Startdatum"] = pd.to_datetime(df["Startdatum"], format="%d-%m-%Y", errors="coerce")

    df = df[df["Startdatum"] >= pd.Timestamp(today)]

    df = df.sort_values("Startdatum").groupby(["Id", "Merk", "Name", "SnapshotDatum"]).first().reset_index()

    df["DagenTotStart"] = (df["Startdatum"] - pd.Timestamp(today)).dt.days
    df["NabijheidCategorie"] = pd.cut(
        df["DagenTotStart"],
        bins=[-1, 14, 30, 90, 99999],
        labels=["1. <= 14 dagen", "2. 15-30 dagen", "3. 31-90 dagen", "4. > 90 dagen"]
    )

    rows.append(df[["SnapshotDatum", "Merk", "Id", "Name", "Startdatum", "DagenTotStart", "NabijheidCategorie"]])
    print(f"{merk}: {len(df)} rijen", flush=True)

snapshot = pd.concat(rows)
snapshot["SnapshotDatum"] = snapshot["SnapshotDatum"].astype(str)
snapshot["Startdatum"] = snapshot["Startdatum"].astype(str)
snapshot["NabijheidCategorie"] = snapshot["NabijheidCategorie"].astype(str)
snapshot["DagenTotStart"] = snapshot["DagenTotStart"].astype(int)

print(f"Totaal: {len(snapshot)} rijen", flush=True)

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
        write_disposition="WRITE_APPEND",
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

    job = client.load_table_from_dataframe(snapshot, table_ref, job_config=job_config)
    job.result()

    print(f"Geschreven naar BigQuery: {len(snapshot)} rijen voor {today}", flush=True)

except Exception as e:
    print(f"FOUT: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
