#!/bin/sh

FILE_PATH="/Users/rundleadmin/Library/Application Support/rundle_device_report/device_report"

if [ -f "$FILE_PATH" ]; then
	echo "<result>$(cat "$FILE_PATH" 2>&1)</result>"
else
	echo "<result>null</result>"
fi
