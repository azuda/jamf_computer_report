# register_task.ps1
# Registers the daily 10:00 report task (Windows equivalent of com.devicereport.daemon.plist).
# Run once from an elevated PowerShell prompt in the project folder:
#   powershell -ExecutionPolicy Bypass -File register_task.ps1

$Project = $PSScriptRoot

$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Project\run.ps1`"" `
  -WorkingDirectory $Project

$Trigger = New-ScheduledTaskTrigger -Daily -At 10:00

# StartWhenAvailable ≈ launchd RunAtLoad: catch up if the 10:00 run was missed
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "Jamf Inventory Report" -TaskPath "\Rundle\" `
  -Action $Action -Trigger $Trigger -Settings $Settings `
  -Description "Daily Jamf device report to Google Sheets" -Force

Write-Host "Task 'Jamf Inventory Report' registered under \Rundle\. Test it with:"
Write-Host "  Start-ScheduledTask -TaskName 'Jamf Inventory Report' -TaskPath \Rundle\"
