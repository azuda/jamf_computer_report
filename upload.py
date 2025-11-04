# upload.py
# https://gist.github.com/nahidsaikat/61ecfe9e333bd55fec287e1e04dfbafd#file-csv_to_google_sheet-py

import urllib3
import gspread
from oauth2client.service_account import ServiceAccountCredentials

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

credentials = ServiceAccountCredentials.from_json_keyfile_name("client_secret.json", scope)
client = gspread.authorize(credentials)

spreadsheet = client.open("[csv2sheet] Rundle Computer Report")

with open("data/output.csv", "r") as f:
  content = f.read()
  client.import_csv(spreadsheet.id, data=content)
