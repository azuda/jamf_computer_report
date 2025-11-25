#!/bin/sh

# THIS SCRIPT IS TO BE RUN VIA JAMF POLICY

# define base dir
REPORT_BASE_DIR="/Users/rundleadmin/Library/Application Support/rundle_device_report"

# create report dir if it doesnt exist
while ! [ -d "${REPORT_BASE_DIR}" ]; do
	echo "Creating report dir..."
	mkdir -p "${REPORT_BASE_DIR}"
done

# path to report file
DEVICE_NAME=$(hostname)
SERIAL_NO=$(ioreg -l | awk -F'"' '/IOPlatformSerialNumber/ {print $4}')
# REPORT_FILE="${REPORT_BASE_DIR}/device_report_${DEVICE_NAME}_$(date +%Y%m%d_%H%M%S).txt"
REPORT_FILE="${REPORT_BASE_DIR}/device_report"


# start writing report
# echo "--- RUNDLE DEVICE REPORT ---" > "${REPORT_FILE}"
# echo "" >> "${REPORT_FILE}"

echo "DATE" > "${REPORT_FILE}"
echo $(date) >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

# hostname
echo "NAME" >> "${REPORT_FILE}"
hostname >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

# serial no
echo "SN" >> "${REPORT_FILE}"
ioreg -l | awk -F'"' '/IOPlatformSerialNumber/ {print $4}' >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

# os
echo "OS" >> "${REPORT_FILE}"
sw_vers -productVersion >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

# logged in user
echo "LOGGED_IN_USER" >> "${REPORT_FILE}"
/bin/ls -l /dev/console | /usr/bin/awk '{ print $3 }' >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

# uptime
echo "UPTIME" >> "${REPORT_FILE}"
system_profiler SPSoftwareDataType -detailLevel mini | grep "Time since boot" >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

# secureTokenStatus
echo "FILEVAULT" >> "${REPORT_FILE}"
sysadminctl -secureTokenStatus rundleadmin >> "${REPORT_FILE}" 2>&1
echo "" >> "${REPORT_FILE}"

# jamf manage
echo "JAMF_MANAGE" >> "${REPORT_FILE}"
sudo pkill -f /usr/local/jamf/bin/jamf
sudo /usr/local/bin/jamf manage >> "${REPORT_FILE}" 2>&1
echo "" >> "${REPORT_FILE}"

# cloudflare warp status
if command -v warp-cli &> /dev/null; then
	echo "CLOUDFLARE_STATUS" >> "${REPORT_FILE}"
	warp-cli status >> "${REPORT_FILE}" 2>&1
else
	echo "CLOUDFLARE_STATUS" >> "${REPORT_FILE}"
	echo "warp-cli not found or not in PATH." >> "${REPORT_FILE}"
fi
echo "" >> "${REPORT_FILE}"

# cloudflare organization
if command -v warp-cli &> /dev/null; then
	echo "CLOUDFLARE_ORG" >> "${REPORT_FILE}"
	warp-cli registration organization >> "${REPORT_FILE}" 2>&1
else
	echo "CLOUDFLARE_ORG" >> "${REPORT_FILE}"
	echo "warp-cli not found or not in PATH." >> "${REPORT_FILE}"
fi
# echo "" >> "${REPORT_FILE}"

# echo "--- END ---" >> "${REPORT_FILE}"

echo "Device report generated and saved to: ${REPORT_FILE}"

exit 0
