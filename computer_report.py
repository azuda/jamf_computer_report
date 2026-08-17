# computer_report.py

"""
- parses `response_computers.json`
- convert extension attribute report string to json
- cleanup columns for report
- write results to `data/computers.csv`
"""

import csv
import json
import re

from util import convert_datetime
from util import _get_name, _get_sn, _get_model, _get_user, _get_building, _get_department, _get_position, _get_purchase_price, _get_purchase_date

DATA_PATH = "data/response_computers.json"
try:
  with open(DATA_PATH) as f:
    DATA = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
  raise SystemExit(f"computer_report.py: could not load {DATA_PATH}: {e}")

# ==================================================================================

def convert_report(report_str):
  report_dict = {}
  lines = report_str.split("\n\n")
  for line in lines:
    kvp = line.split("\n")
    report_dict[kvp[0]] = kvp[1] if len(kvp) > 1 else None
  return report_dict

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

def clean_outputs(computer):
  report = computer.get("report_dict")

  # uptime
  try:
    hours = normalize_uptime(report["UPTIME"])
    report["UPTIME"] = hours
  except (KeyError, TypeError) as e:
    # missing UPTIME is normal (no report); an unparseable one is worth a log line
    if "UPTIME" in report:
      print(f"warn: could not parse uptime for {computer.get('name')}: {e}")
  if not report: # if no report found set uptime to -1
    report["UPTIME"] = -1

  # # filevault
  # try:
  #   fv = report["FILEVAULT"].split("]")[-1].strip()
  #   try:
  #     report["FILEVAULT"] = fv.split(" ")[3].strip()
  #   except IndexError:
  #     report["FILEVAULT"] = fv
  # except (KeyError, AttributeError) as e:
  #   if "FILEVAULT" in report:
  #     print(f"warn: could not parse filevault for {computer.get('name')}: {e}")

  # update by reference
  computer["report_dict"] = report
  return

# ==================================================================================

def _get_date(computer):
  report = computer.get("report_dict")
  # print(f"converting date for computer {computer.get("name")}")
  if report and report.get("DATE"):
    try:
      return convert_datetime(report["DATE"])
    except (ValueError, OverflowError):
      return report.get("DATE")
  # fallback to last checkin date
  try:
    return convert_datetime(computer["report_date_utc"])
  except (KeyError, TypeError, ValueError, OverflowError):
    try:
      return computer["report_date_utc"].split(".")[0]
    except (KeyError, AttributeError):
      return None

def _get_os(computer):
  report = computer.get("report_dict")
  return report.get("OS") if report else computer.get("os_version")

def _get_uptime(computer):
  report = computer.get("report_dict") if computer else None
  # assume parsed uptime is normalized (int hours) if present
  if report and report.get("UPTIME") is not None:
    return report.get("UPTIME")
  return None

# def _get_filevault(computer):
#   report = computer.get("report_dict")
#   return report.get("FILEVAULT") if report else None

# def _get_jamf_manage(computer):
#   report = computer.get("report_dict")
#   return report.get("JAMF_MANAGE") if report else None

def _get_cloudflare_status(computer):
  report = computer.get("report_dict")
  return report.get("CLOUDFLARE_STATUS") if report else None

def _get_cloudflare_org(computer):
  report = computer.get("report_dict")
  return report.get("CLOUDFLARE_ORG") if report else None

# add or modify columns here to be included in the final report
COLUMNS = [
  {"header": "LAST_CHECKIN", "func": _get_date},
  {"header": "NAME", "func": _get_name},
  {"header": "SN", "func": _get_sn},
  {"header": "OS", "func": _get_os},
  {"header": "MODEL", "func": _get_model},
  {"header": "USER", "func": _get_user},
  {"header": "BLDG", "func": _get_building},
  {"header": "DEPT", "func": _get_department},
  {"header": "POS", "func": _get_position},
  {"header": "PURCHASE_PRICE", "func": _get_purchase_price},
  {"header": "PURCHASE_DATE", "func": _get_purchase_date},
  {"header": "UPTIME", "func": _get_uptime},
  # {"header": "FILEVAULT", "func": _get_filevault},
  # {"header": "JAMF_MANAGE", "func": _get_jamf_manage},
  {"header": "CLOUDFLARE_STATUS", "func": _get_cloudflare_status},
  {"header": "CLOUDFLARE_ORG", "func": _get_cloudflare_org},
]

# ==================================================================================

def main():
  computers = DATA["computers"]

  # convert report string to dict and add to all computers
  for computer in computers:
    report_str = computer.get("report")
    if report_str:
      computer["report_dict"] = convert_report(report_str)
    else:
      computer["report_dict"] = {}
    clean_outputs(computer)

  # debug
  with open("debug/c_final.json", "w") as f:
    json.dump(computers, f, indent=2)

  # write entries to csv
  with open("data/computers.csv", "w", newline='') as f:
    writer = csv.writer(f)
    headers = [col["header"] for col in COLUMNS]
    writer.writerow(headers)
    for computer in computers:
      row = []
      for col in COLUMNS:
        try:
          val = col["func"](computer)
        except Exception as e:
          # last-resort guard: one bad record shouldn't kill the report, but log it
          print(f"warn: {col['header']} failed for {computer.get('name')}: {e}")
          val = None
        # normalize None -> empty cell, keep numeric and string values as-is
        row.append("" if val is None else val)
      writer.writerow(row)

  print("Done computer_report.py")

# ==================================================================================

if __name__ == "__main__":
  main()
