# query_jamf.py

"""
- get info on all computers + mobile devices via jamf api
- sort + combine relevant info to dicts
- write result dicts to `data/response_computers.json` and `data/response_devices.json`
"""

import jamf_client
from jamf_client import jamf_session, jamf_get
import json
import os

# ==================================================================================

def get_all_pages(endpoint, token, session, page_size=2000):
  # accumulate every page of a paginated /api/v2 endpoint so the report
  # doesn't silently truncate once inventory grows past one page
  results = []
  page = 0
  while True:
    response = jamf_get(f"{endpoint}&page={page}&page-size={page_size}", token, session)
    body = response.json()
    page_results = body.get("results", [])
    results.extend(page_results)
    if len(results) >= body.get("totalCount", 0) or not page_results:
      break
    page += 1
  return {"totalCount": body.get("totalCount", 0), "results": results}

def combine_computers(computers_response, computers_users, computers_purchasing, computers_extension_attributes):
  computers_json = {}
  computers_json["computers"] = computers_response.json().get("computers", [])
  users_by_id = {int(cu["id"]): cu["userAndLocation"] for cu in computers_users["results"]}
  purchasing_by_id = {int(cp["id"]): cp["purchasing"] for cp in computers_purchasing["results"]}
  ea_by_id = {int(cea["id"]): cea["extensionAttributes"] for cea in computers_extension_attributes["results"]}

  for c in computers_json["computers"]:
    c["realname"], c["email"], c["position"], c["purchase_price"], c["purchase_date"], c["report"] = None, None, None, None, None, None
    cu_data = users_by_id.get(c["id"])
    if cu_data:
      c["realname"] = cu_data["realname"]
      c["email"] = cu_data["email"]
      c["position"] = cu_data["position"]
    cp_data = purchasing_by_id.get(c["id"])
    if cp_data:
      c["purchase_price"] = cp_data["purchasePrice"]
      c["purchase_date"] = cp_data["poDate"]
    cea_data = ea_by_id.get(c["id"])
    if cea_data:
      report = next((attr["values"] for attr in cea_data if attr["name"] == "Rundle Device Report"), None)
      c["report"] = report[0] if report else None

  computers_json["total"] = len(computers_json["computers"])
  computers_json["max_id"] = max((c["id"] for c in computers_json["computers"]), default=0)
  return computers_json

def combine_devices(devices_response, devices_users, devices_general, devices_purchasing):
  devices_json = {}
  devices_json["devices"] = devices_response.json().get("mobile_devices", [])
  general_by_id = {int(dg["mobileDeviceId"]): dg["general"] for dg in devices_general["results"]}
  users_by_id = {int(du["mobileDeviceId"]): du["userAndLocation"] for du in devices_users["results"]}
  purchasing_by_id = {int(dp["mobileDeviceId"]): dp["purchasing"] for dp in devices_purchasing["results"]}

  for d in devices_json["devices"]:
    d["date"], d["os"], d["realname"], d["email"], d["position"], d["department"], d["purchase_price"], d["purchase_date"] = None, None, None, None, None, None, None, None
    dg_data = general_by_id.get(d["id"])
    if dg_data:
      d["date"] = dg_data["lastInventoryUpdateDate"]
      d["os"] = dg_data["osVersion"]
    du_data = users_by_id.get(d["id"])
    if du_data:
      d["realname"] = du_data["realName"]
      d["email"] = du_data["emailAddress"]
      d["position"] = du_data["position"]
      d["department"] = du_data["department"]
      d["building"] = du_data["building"]
    dp_data = purchasing_by_id.get(d["id"])
    if dp_data:
      d["purchase_price"] = dp_data["purchasePrice"]
      d["purchase_date"] = dp_data["poDate"]

  devices_json["total"] = len(devices_json["devices"])
  devices_json["max_id"] = max((d["id"] for d in devices_json["devices"]), default=0)
  return devices_json

# ==================================================================================

def main():
  jamf_client.init()

  with jamf_session() as (token, session):
    # print jamf pro version
    version = jamf_get("/api/v1/jamf-pro-version", token, session)
    print("Jamf Pro version:", version.json()["version"])

    # get info for all computers
    # https://developer.jamf.com/jamf-pro/reference/findcomputersbasic
    # https://developer.jamf.com/jamf-pro/reference/get_v2-computers-inventory
    computers = jamf_get("/JSSResource/computers/subset/basic", token, session)
    computers_users = get_all_pages("/api/v2/computers-inventory?section=USER_AND_LOCATION&sort=id%3Aasc", token, session)
    computers_purchasing = get_all_pages("/api/v2/computers-inventory?section=PURCHASING&sort=id%3Aasc", token, session)
    computers_extension_attributes = get_all_pages("/api/v2/computers-inventory?section=EXTENSION_ATTRIBUTES&sort=id%3Aasc", token, session)
    computers_json = combine_computers(computers, computers_users, computers_purchasing, computers_extension_attributes)

    # get info for all mobile devices
    # https://developer.jamf.com/jamf-pro/reference/findmobiledevices
    # https://developer.jamf.com/jamf-pro/reference/get_v2-mobile-devices-detail
    devices = jamf_get("/JSSResource/mobiledevices", token, session)
    devices_users = get_all_pages("/api/v2/mobile-devices/detail?section=USER_AND_LOCATION&sort=deviceId%3Aasc", token, session)
    devices_general = get_all_pages("/api/v2/mobile-devices/detail?section=GENERAL&sort=deviceId%3Aasc", token, session)
    devices_purchasing = get_all_pages("/api/v2/mobile-devices/detail?section=PURCHASING&sort=deviceId%3Aasc", token, session)
    devices_json = combine_devices(devices, devices_users, devices_general, devices_purchasing)

  # raw api responses for debug
  if not os.path.exists("debug"):
    os.makedirs("debug")
  with open("debug/c.json", "w") as f:
    f.write(json.dumps(computers.json(), indent=2))
  with open("debug/cu.json", "w") as f:
    f.write(json.dumps(computers_users, indent=2))
  with open("debug/cp.json", "w") as f:
    f.write(json.dumps(computers_purchasing, indent=2))
  with open("debug/cea.json", "w") as f:
    f.write(json.dumps(computers_extension_attributes, indent=2))
  with open("debug/d.json", "w") as f:
    f.write(json.dumps(devices.json(), indent=2))
  with open("debug/du.json", "w") as f:
    f.write(json.dumps(devices_users, indent=2))
  with open("debug/dg.json", "w") as f:
    f.write(json.dumps(devices_general, indent=2))
  with open("debug/dp.json", "w") as f:
    f.write(json.dumps(devices_purchasing, indent=2))

  # write to file
  if not os.path.exists("data"):
    os.makedirs("data")
  with open("data/response_computers.json", "w") as f:
    f.write(json.dumps(computers_json, indent=2))
  print("--- Jamf computers saved to ./data/response_computers.json ---")
  with open("data/response_devices.json", "w") as f:
    f.write(json.dumps(devices_json, indent=2))
  print("--- Jamf devices saved to ./data/response_devices.json ---")

  print("\nDone query_jamf.py")

# ==================================================================================

if __name__ == "__main__":
  main()
