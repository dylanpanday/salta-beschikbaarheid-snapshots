name: Dagelijkse beschikbaarheid snapshot

on:
  schedule:
    - cron: '0 5 * * *'
  workflow_dispatch:

jobs:
  snapshot:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Python instellen
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Dependencies installeren
        run: pip install pandas requests

      - name: Snapshot draaien
        run: python snapshot.py

      - name: Snapshot committen
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add snapshots/
          git diff --staged --quiet || git commit -m "Snapshot $(date +%Y-%m-%d)"
          git push
