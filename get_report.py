# get_report.py

from jamf_credential import JAMF_URL, get_token, invalidate_token
import requests
import urllib3
import time
import json
import csv
from dateutil import parser
import re
import copy

"""
- parses response_computers.json
- extracts `Rundle Device Report` extension attribute from each computer
- cleans up column data for report
- writes results to data/output.csv
"""

TESTING = False
LIMIT = 100

with open("data/response_computers.json") as f:
  DATA = json.load(f)

# ==================================================================================

def get_extension_attributes(computer_id, access_token, token_expiration_epoch):
  # renew token if expiration < 15 secs
  current_epoch = int(time.time())
  if current_epoch > token_expiration_epoch - 15:
    access_token, expires_in = get_token()
    token_expiration_epoch = current_epoch + expires_in
    print(f"Token valid for {expires_in} seconds")

  url = f"{JAMF_URL}/JSSResource/computers/id/{computer_id}/subset/extension_attributes"
  headers = {
    "accept": "application/json",
    "authorization": f"Bearer {access_token}"
  }

  # GET computer extension attributes
  try:
    response = requests.get(url, headers=headers, verify=False)
  except:
    return None, access_token, token_expiration_epoch
  # print(response.text)

  # resolve response
  if response and response.status_code == 200:
    print(f"Success: got extension attributes for computer {computer_id} / {DATA['max_id']}")
    return response.json(), access_token, token_expiration_epoch
  else:
    print(f"Fail: status {response.status_code}: {response.text}")

  return None, access_token, token_expiration_epoch

def parse_response(response: dict) -> str:
  # extract extension_attributes from response object
  try:
    extension_attributes = response.get("computer", {}).get("extension_attributes", [])
  except:
    print("Can't parse response - extension_attributes missing")
    return None

  # extract report string from extension_attributes
  for attr in extension_attributes:
    if attr["name"] == "Rundle Device Report":
      report = attr["value"]
      return report
  return None

def report_to_json(report):
  # convert report string to json
  report_json = {}
  if report:
    items = report.strip().split("\n\n")
    for item in items:
      lines = item.split("\n")
      if len(lines) == 2:
        key = lines[0].strip()
        value = lines[1].strip()
        report_json[key] = value
  else:
    return None

  return report_json

def normalize_uptime(uptime_str: str) -> int:
  # uptime str format: `Time since boot: x day(s), y hour(s), z minute(s)`
  uptime_int = 0
  # extract days
  match_days = re.search(r'(\d+)\s+day', uptime_str)
  if match_days:
    uptime_int += int(match_days.group(1)) * 24
  # extract hours
  match_hours = re.search(r'(\d+)\s+hour', uptime_str)
  if match_hours:
    uptime_int += int(match_hours.group(1))
  # extract hours if format matches when uptime < 24 hours
  match_less = re.search(r'\d+:\d+', uptime_str)
  if match_less:
    uptime_int += int(match_less.group(0).split(":")[0])
  return uptime_int
  # match = re.search(r'((\d+)\s+days?,\s+)?((\d+)\s+hours?,\s+)?((\d+)\s+minutes?)?', uptime_str)
  # if match:
  #   days = int(match.group(1)) if match.group(1) else 0
  #   hours = int(match.group(2)) if match.group(2) else 0
  #   minutes = int(match.group(3)) if match.group(3) else 0
  #   return days * 24 + hours + minutes // 60
  # else:
  #   print(f"BAD_NORMALIZE {uptime_str}")
  # return uptime_str.split("up")[1].strip()

def clean_outputs(device_report):
  # uptime
  try:
    hours = normalize_uptime(device_report["UPTIME"])
    # print(hours)
    device_report["UPTIME"] = hours
  except:
    pass

  # filevault
  try:
    fv_val = device_report["FILEVAULT"]
    device_report["FILEVAULT"] = device_report["FILEVAULT"].split("token is")[-1].strip()
  except:
    pass

  return device_report

def convert_time(timestamp):
  dt = parser.parse(timestamp)
  return dt.strftime("%Y-%m-%d %H:%M:%S")

# ==================================================================================

def _get_date(parsed, computer):
  if parsed and parsed.get("DATE"):
    try:
      return convert_time(parsed["DATE"])
    except:
      try:
        return convert_time(parsed.get("--- RUNDLE DEVICE REPORT ---"))
      except:
        return parsed.get("DATE")
  # fallback to last checkin date
  try:
    return convert_time(computer["report_date_utc"])
  except:
    try:
      return computer["report_date_utc"].split(".")[0]
    except:
      return None

def _get_name(parsed, computer):
  return (parsed.get("NAME") if parsed else None) or computer.get("name")

def _get_sn(parsed, computer):
  return (parsed.get("SN") if parsed else None) or computer.get("serial_number")

def _get_os(parsed, computer):
  return parsed.get("OS") if parsed else None

def _get_logged_in_user(parsed, computer):
  return (parsed.get("LOGGED_IN_USER") if parsed else None) or computer.get("username")

def _get_uptime(parsed, computer):
  # assume parsed uptime is normalized (int hours) if present
  if parsed and parsed.get("UPTIME") is not None:
    return parsed.get("UPTIME")
  return None

def _get_filevault(parsed, computer):
  if parsed and parsed.get("FILEVAULT") is not None:
    return parsed.get("FILEVAULT")
  return None

def _get_jamf_manage(parsed, computer):
  return parsed.get("JAMF_MANAGE") if parsed else None

def _get_cloudflare_status(parsed, computer):
  return parsed.get("CLOUDFLARE_STATUS") if parsed else None

def _get_cloudflare_org(parsed, computer):
  return parsed.get("CLOUDFLARE_ORG") if parsed else None

def _get_department(parsed, computer):
  full = (parsed.get("DEPT") if parsed else None) or computer.get("department")
  if re.search(r'(?i)\bStudent\b', full):
    return "Student"
  elif re.search(r'(?i)\b(?:Staff|Teacher|Admin|Childcare)\b', full):
    return "Staff"
  else:
    return full

def _get_position(parsed, computer):
  full = (parsed.get("EGY") if parsed else None) or computer.get("position")
  if not full:
    return None
  m = re.search(r'(EGY)(\d{4})', full, re.IGNORECASE)
  if m:
    return int(m.group(2))
  return full

# add or modify columns here to be included in the final report
COLUMNS = [
  {"header": "DATE", "func": _get_date},
  {"header": "NAME", "func": _get_name},
  {"header": "SN", "func": _get_sn},
  {"header": "OS", "func": _get_os},
  {"header": "LOGGED_IN_USER", "func": _get_logged_in_user},
  {"header": "DEPT", "func": _get_department},
  {"header": "EGY", "func": _get_position},
  {"header": "UPTIME", "func": _get_uptime},
  {"header": "FILEVAULT", "func": _get_filevault},
  {"header": "JAMF_MANAGE", "func": _get_jamf_manage},
  {"header": "CLOUDFLARE_STATUS", "func": _get_cloudflare_status},
  {"header": "CLOUDFLARE_ORG", "func": _get_cloudflare_org},
]

# ==================================================================================

def main():
  # init jamf api access token
  access_token, expires_in = get_token()
  token_expiration_epoch = int(time.time()) + expires_in

  computers = DATA["computers"]

  raw = []
  entries = []
  count = LIMIT

  for computer in computers:
    if TESTING:
      count -= 1
      if count <= 0:
        break

    response, access_token, token_expiration_epoch = get_extension_attributes(computer["id"], access_token, token_expiration_epoch)
    line = report_to_json(parse_response(response))
    raw.append(copy.deepcopy(line))

    if line:
      try:
        line["DATE"] = convert_time(line["DATE"])
      except:
        print(f"BAD REPORT: {line}")
      # clean command outputs and add to entries
      cleaned = clean_outputs(line)
      entries.append({"parsed": cleaned, "computer": computer})
    else:
      print(f"BAD LINE: {line}")
      entries.append({"parsed": None, "computer": computer})


  # kill jamf api access token
  invalidate_token(access_token)

  # write raw
  with open("data/raw.json", "w") as f:
    json.dump(raw, f)

  # write entries to csv
  with open("data/output.csv", "w", newline='') as f:
    writer = csv.writer(f)
    headers = [col["header"] for col in COLUMNS]
    writer.writerow(headers)
    for entry in entries:
      parsed = entry["parsed"]
      computer = entry["computer"]
      row = []
      for col in COLUMNS:
        try:
          val = col["func"](parsed, computer)
        except Exception:
          val = None
        # normalize None -> empty cell, keep numeric and string values as-is
        row.append("" if val is None else val)
      writer.writerow(row)

  print("Done")

# ==================================================================================

if __name__ == "__main__":
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  main()
