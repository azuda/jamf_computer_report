from jamf_credential import JAMF_URL, get_token, invalidate_token
import requests
import urllib3
import os

# ==================================================================================

def main():
  # create access token
  access_token, expires_in = get_token()
  print(f"Token valid for {expires_in} seconds")

  # print jamf pro version
  version_url = f"{JAMF_URL}/api/v1/jamf-pro-version"
  headers = {"Authorization": f"Bearer {access_token}"}
  version = requests.get(version_url, headers=headers, verify=False)
  print("Jamf Pro version:", version.json()["version"])

  # get basic info for all computers
  computers_url = f"{JAMF_URL}/JSSResource/computers/subset/basic"
  headers = {
    "accept": "application/json",
    "authorization": f"Bearer {access_token}"
  }
  response = requests.get(computers_url, headers=headers, verify=False)

  # write to file
  if not os.path.exists("data"):
      os.makedirs("data")
  with open("data/response_computers.json", "w") as f:
    f.write(response.text)
  print("--- Jamf computers saved to ./data/response_computers.json ---")

  # kill access token
  invalidate_token(access_token)
  print("Done query_jamf.py\n")

# ==================================================================================

if __name__ == "__main__":
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  main()
