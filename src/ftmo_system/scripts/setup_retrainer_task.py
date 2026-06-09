"""
Windows Task Scheduler Setup — Daily Model Retrainer
=====================================================
Run this script ONCE (as Administrator) to register the daily retraining task.

What it schedules
-----------------
  Script  : training/daily_retrainer.py
  Trigger : Daily at 00:00 UTC  (02:00 local if UTC+2, adjust RUN_TIME_UTC below)
  Action  : python daily_retrainer.py  (reads ftmo_config.json automatically)
  After   : Retrained models are committed and pushed to GitHub automatically,
            so Colab picks them up on the next session start.

Usage
-----
  python scripts/setup_retrainer_task.py          # register / update task
  python scripts/setup_retrainer_task.py --delete  # remove task
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

TASK_NAME   = "FTMO_Daily_Retrainer"
SCRIPT_PATH = str(Path(__file__).parent.parent / "training" / "daily_retrainer.py")
PYTHON_PATH = sys.executable
LOG_DIR     = str(Path(__file__).parent.parent / "logs")

# ── Schedule: every Sunday at 08:00 local time ───────────────────────────
RUN_TIME_LOCAL = "08:00"
RUN_DAY        = "Sunday"


def create_task():
    print(f"Creating Task Scheduler task : {TASK_NAME}")
    print(f"Script                       : {SCRIPT_PATH}")
    print(f"Python                       : {PYTHON_PATH}")
    print(f"Schedule                     : Every {RUN_DAY} at {RUN_TIME_LOCAL}")
    print()

    os.makedirs(LOG_DIR, exist_ok=True)

    # Delete existing task if present (ignore errors)
    subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                   capture_output=True)

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTMO AI Trading — weekly model retraining (XGBoost + LightGBM + CatBoost + Transformer). Runs every Sunday at 08:00. Pushes updated models to GitHub on completion.</Description>
    <Author>FTMO_System</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-04T{RUN_TIME_LOCAL}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
          <{RUN_DAY}/>
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT10M</Interval>
      <Count>2</Count>
    </RestartOnFailure>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
    </IdleSettings>
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

    xml_path = str(Path(__file__).parent / "_retrainer_task_temp.xml")
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
        print(f"The retrainer will run every {RUN_DAY} at {RUN_TIME_LOCAL}.")
        print("It trains all 4 model types and auto-pushes updated models to GitHub.")
        print()
        print("To run immediately for testing:")
        print(f"  schtasks /run /tn {TASK_NAME}")
        print()
        print("To check last run status:")
        print(f"  schtasks /query /tn {TASK_NAME} /fo LIST")
        print()
        print(f"Log output: {LOG_DIR}\\retrainer.log  (created on first run)")
    else:
        print(f"✗ Task creation failed:\n{result.stderr}")
        print("Try running this script as Administrator.")
        sys.exit(1)


def delete_task():
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"✓ Task '{TASK_NAME}' deleted.")
    else:
        print(f"Task not found or could not be deleted:\n{result.stderr}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage FTMO daily retrainer task")
    parser.add_argument("--delete", action="store_true", help="Remove the scheduled task")
    args = parser.parse_args()

    if args.delete:
        delete_task()
    else:
        create_task()
