"""
Windows Task Scheduler Setup — Colab Keepalive
================================================
Run this script ONCE to register the keepalive task in Windows Task Scheduler.
It will:
  1. Run every 5 minutes, all day (Colab free-tier sessions can disconnect
     after as little as 10-15 min idle, so this catches a disconnect well
     within that window)
  2. Restart if the keepalive script itself crashes

Usage:
  python scripts/setup_colab_task.py

Requires admin rights (run as administrator) or the scheduler will prompt for elevation.
"""

import subprocess
import sys
import os
from pathlib import Path

TASK_NAME   = "FTMO_Colab_Keepalive"
SCRIPT_PATH = str(Path(__file__).parent.parent / "colab" / "keepalive.py")
PYTHON_PATH = sys.executable   # uses the same Python that runs this script
LOG_DIR     = str(Path(__file__).parent.parent / "logs")

os.makedirs(LOG_DIR, exist_ok=True)

# Repetition interval — re-run continuously throughout the day
REPEAT_INTERVAL = "PT5M"

def create_task():
    print(f"Creating Task Scheduler task: {TASK_NAME}")
    print(f"Script:   {SCRIPT_PATH}")
    print(f"Python:   {PYTHON_PATH}")
    print(f"Interval: every 5 minutes")
    print()

    # Delete existing task if present
    subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True
    )

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTMO AI Trading — Colab keepalive. Checks and restarts Google Colab inference session every 5 minutes.</Description>
    <Author>FTMO_System</Author>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>{REPEAT_INTERVAL}</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON_PATH}</Command>
      <Arguments>"{SCRIPT_PATH}"</Arguments>
      <WorkingDirectory>{str(Path(SCRIPT_PATH).parent)}</WorkingDirectory>
    </Exec>
  </Actions>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>"""

    xml_path = str(Path(__file__).parent / "_colab_task_temp.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(task_xml)

    result = subprocess.run(
        ["schtasks", "/create", "/tn", TASK_NAME, "/xml", xml_path, "/f"],
        capture_output=True, text=True
    )

    os.remove(xml_path)

    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' created successfully.")
        print()
        print("Next steps:")
        print("  1. Confirm COLAB_NOTEBOOK_URL in colab/keepalive.py points to your notebook")
        print("  2. First run requires a one-time manual Google login:")
        print("       python colab/keepalive.py")
        print("     An Edge window will open in a dedicated automation profile —")
        print("     log into the Google account that owns the Colab notebook, then close it.")
    else:
        print(f"[FAIL] Task creation failed:\n{result.stderr}")
        print("Try running this script as Administrator.")
        sys.exit(1)


def verify_task():
    result = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("\nTask details:")
        print(result.stdout)
    else:
        print("Could not query task.")


if __name__ == "__main__":
    create_task()
    verify_task()
