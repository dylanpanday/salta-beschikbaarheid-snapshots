import requests
import pandas as pd
from datetime import date
import os

LABELS = {
    "BAN": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-BAN.csv",
    "BVO": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-BVO.csv",
    "CT": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-CT.csv",
    "ISBW": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-ISBW.csv",
    "MVP": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-MVP.csv",
    "NIBE-SVV": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-NIBE-SVV.csv",
    "NCOI": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-NCOI.csv",
    "ProEducation": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-ProEducation.csv",
    "Schoevers": "https://sag7dukf5l53jecp.blob.core.windows.net/course-csv-exports/products-Schoevers.csv",
}

today = date.today()
os.makedirs("snapshots", exist_ok=True)

rows = []

for merk, url in LABELS.items():
    df = pd.read_csv(url)
    df["Merk"] = merk
    df["SnapshotDatum"] = today

    # Startdatums uitklappen
    df["StartDates"] = df["StartDates"].astype(str)
    df = df.assign(Startdatum=df["StartDates"].str.split("|")).explode("Startdatum")
    df["Startdatum"] = pd.to_datetime(df["Startdatum"], format="%d-%m-%Y", errors="coerce")

    # Alleen toekomstige starts
    df = df[df["Startdatum"] >= pd.Timestamp(today)]

    # Vroegste start per opleiding
    df = df.sort_values("Startdatum").groupby(["Id", "Merk", "Name", "SnapshotDatum"]).first().reset_index()

    # Nabijheid categorie
    df["DagenTotStart"] = (df["Startdatum"] - pd.Timestamp(today)).dt.days
    df["NabijheidCategorie"] = pd.cut(
        df["DagenTotStart"],
        bins=[-1, 14, 30, 90, 99999],
        labels=["1. ≤ 14 dagen", "2. 15-30 dagen", "3. 31-90 dagen", "4. > 90 dagen"]
    )

    rows.append(df[["SnapshotDatum", "Merk", "Id", "Name", "Startdatum", "DagenTotStart", "NabijheidCategorie"]])

snapshot = pd.concat(rows)
filename = f"snapshots/snapshot_{today}.csv"
snapshot.to_csv(filename, index=False)
print(f"Opgeslagen: {filename} ({len(snapshot)} rijen)")
