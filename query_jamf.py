# query_jamf.py

from jamf_credential import JAMF_URL, get_token, invalidate_token, check_token_expiration
import requests
import urllib3
import time
import os
import json

"""
- gets basic info about all computers in jamf
- writes results to `data/response_computers.json`
"""

# ==================================================================================

def get_computers_basic(access_token, token_expiration_epoch):
  access_token, token_expiration_epoch = check_token_expiration(access_token, token_expiration_epoch)

  # GET basic info all computers
  url = f"{JAMF_URL}/JSSResource/computers/subset/basic"
  headers = {
    "accept": "application/json",
    "authorization": f"Bearer {access_token}"
  }
  response = requests.get(url, headers=headers, verify=False)
  return response, access_token, token_expiration_epoch

def get_computers_userandlocation(access_token, token_expiration_epoch):
  access_token, token_expiration_epoch = check_token_expiration(access_token, token_expiration_epoch)

  # GET userAndLocation all computers
  url = f"{JAMF_URL}/api/v2/computers-inventory?section=USER_AND_LOCATION&page=0&page-size=2000&sort=id%3Aasc"
  headers = {
    "accept": "application/json",
    "authorization": f"Bearer {access_token}"
  }
  response = requests.get(url, headers=headers, verify=False)

  return response, access_token, token_expiration_epoch

# ==================================================================================

def main():
  # create access token
  access_token, expires_in = get_token()
  token_expiration_epoch = int(time.time()) + expires_in
  print(f"Token valid for {expires_in} seconds")

  # print jamf pro version
  version_url = f"{JAMF_URL}/api/v1/jamf-pro-version"
  headers = {"Authorization": f"Bearer {access_token}"}
  version = requests.get(version_url, headers=headers, verify=False)
  print("Jamf Pro version:", version.json()["version"])

  # # get basic info for all computers
  # computers_url = f"{JAMF_URL}/JSSResource/computers/subset/basic"
  # headers = {
  #   "accept": "application/json",
  #   "authorization": f"Bearer {access_token}"
  # }
  # response = requests.get(computers_url, headers=headers, verify=False)
  # response_json = response.json()
  # total = 0
  # for computer in response_json.get("computers", []):
  #   total += 1
  # response_json["total"] = total
  # response_json["max_id"] = max([c["id"] for c in response_json.get("computers", [])]) if total > 0 else 0

  # get basic info for all computers
  computers, access_token, token_expiration_epoch  = get_computers_basic(access_token, token_expiration_epoch)

  # get userAndLocation for all computers
  computers_users, access_token, token_expiration_epoch  = get_computers_userandlocation(access_token, token_expiration_epoch)

  # add userAndLocation data to computers
  computers_json = {}
  computers_json["computers"] = computers.json().get("computers", [])
  computers_users_json = computers_users.json().get("results", [])
  total = 0
  for c in computers_json["computers"]:
    total += 1
    c["realname"], c["email"], c["position"] = None, None, None
    for cu in computers_users_json:
      if c["id"] == int(cu["id"]):
        cu_data = cu["userAndLocation"]
        c["realname"] = cu_data["realname"]
        c["email"] = cu_data["email"]
        c["position"] = cu_data["position"]
        break

  computers_json["total"] = total
  computers_json["max_id"] = max([c["id"] for c in computers_json.get("computers", [])]) if total > 0 else 0

  # write to file
  if not os.path.exists("data"):
      os.makedirs("data")
  with open("data/response_computers.json", "w") as f:
    f.write(json.dumps(computers_json, indent=2))
  print("--- Jamf computers saved to ./data/response_computers.json ---")

  # kill access token
  invalidate_token(access_token)
  print("Done query_jamf.py\n")

# ==================================================================================

if __name__ == "__main__":
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  main()
