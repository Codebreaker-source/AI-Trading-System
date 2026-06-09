"""
Windows Task Scheduler Setup — Colab Keepalive
================================================
Run this script ONCE to register the keepalive task in Windows Task Scheduler.
It will:
  1. Run at 07:45 UTC daily (before London open)
  2. Re-run every 4 hours during trading hours (07:45, 11:45, 15:45, 19:45 UTC)
  3. Restart if the keepalive script itself crashes

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

# Run times (UTC) — adjust if your timezone offsets change
# 07:45, 11:45, 15:45, 19:45 UTC covers London open through NY close
RUN_TIMES_UTC = ["07:45", "11:45", "15:45", "19:45"]

def create_task():
    print(f"Creating Task Scheduler task: {TASK_NAME}")
    print(f"Script:  {SCRIPT_PATH}")
    print(f"Python:  {PYTHON_PATH}")
    print(f"Times:   {', '.join(RUN_TIMES_UTC)} UTC")
    print()

    # Delete existing task if present
    subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True
    )

    # Build the XML task definition
    # Using XML gives us full control over triggers, conditions, and settings
    triggers_xml = "\n".join([
        f"""
        <CalendarTrigger>
          <StartBoundary>2026-01-01T{t}:00</StartBoundary>
          <Enabled>true</Enabled>
          <ScheduleByDay>
            <DaysInterval>1</DaysInterval>
          </ScheduleByDay>
        </CalendarTrigger>""".strip()
        for t in RUN_TIMES_UTC
    ])

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTMO AI Trading — Colab keepalive. Checks and restarts Google Colab inference session.</Description>
    <Author>FTMO_System</Author>
  </RegistrationInfo>
  <Triggers>
    {triggers_xml}
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
        print(f"✓ Task '{TASK_NAME}' created successfully.")
        print()
        print("Next steps:")
        print("  1. Upload colab/trading_inference.ipynb to Google Drive")
        print("  2. Open it in Google Colab and copy the notebook URL")
        print("  3. Set COLAB_NOTEBOOK_URL in colab/keepalive.py (or as env var)")
        print("  4. Run 'pip install playwright && playwright install chromium'")
        print("  5. Test manually: python colab/keepalive.py")
    else:
        print(f"✗ Task creation failed:\n{result.stderr}")
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
