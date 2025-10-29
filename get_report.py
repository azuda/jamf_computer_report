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
    print(f"Success: got extension attributes for computer {computer_id}")
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

def main():
  # init jamf api access token
  access_token, expires_in = get_token()
  token_expiration_epoch = int(time.time()) + expires_in

  with open("data/response_computers.json") as f:
    computers = json.load(f)["computers"]

  raw = []
  report = []
  count = 50

  for computer in computers:
    # count -= 1
    # if count <= 0:
    #   break

    response, access_token, token_expiration_epoch = get_extension_attributes(computer["id"], access_token, token_expiration_epoch)
    line = report_to_json(parse_response(response))
    raw.append(copy.deepcopy(line))
    if line:
      try:
        line["DATE"] = convert_time(line["DATE"])
      except:
        print(f"BAD REPORT: {line}")
        line["DATE"] = convert_time(line["--- RUNDLE DEVICE REPORT ---"])

      # clean command outputs and add to final report
      report.append(clean_outputs(line))
    else:
      print(f"BAD LINE: {line}")
      try:
        computer_date = convert_time(computer["report_date_utc"])
      except:
        computer_date = computer["report_date_utc"].split(".")[0]
      report.append({"DATE": computer_date, "NAME": computer["name"], "SN": computer["serial_number"], "OS": None, "LOGGED_IN_USER": computer["username"], "UPTIME": None, "FILEVAULT": None, "JAMF_MANAGE": None, "CLOUDFLARE_STATUS": None, "CLOUDFLARE_ORG": None})

  # kill jamf api access token
  invalidate_token(access_token)

  # write raw
  with open("data/raw.json", "w") as f:
    json.dump(raw, f)

  # write final report to csv
  with open("data/output.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(["DATE", "NAME", "SN", "OS", "LOGGED_IN_USER", "UPTIME", "FILEVAULT", "JAMF_MANAGE", "CLOUDFLARE_STATUS", "CLOUDFLARE_ORG"])
    for row in report:
      writer.writerow(row.values())

  print("Done")

# ==================================================================================

if __name__ == "__main__":
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  main()
