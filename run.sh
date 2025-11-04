#!/bin/sh

PROJECT="$PWD"
VENV="$PROJECT/.venv/bin/python3"

echo "Script start @ $(date)"

$VENV query_jamf.py
$VENV get_report.py
$VENV upload.py

echo -e "\nScript end @ $(date)"
