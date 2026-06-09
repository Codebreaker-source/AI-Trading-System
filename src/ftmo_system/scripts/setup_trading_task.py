"""
Windows Task Scheduler Setup — Live Trading System
===================================================
Run this script ONCE (as Administrator) to register the trading system task.

What it schedules
-----------------
  Script  : run_system.py
  Trigger : Daily at 07:30 (before London open at 08:00)
  Restart : Up to 3 times if it crashes (5 min between attempts)

Usage
-----
  python scripts/setup_trading_task.py          # register / update task
  python scripts/setup_trading_task.py --delete  # remove task
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

TASK_NAME   = "FTMO_Trading_System"
SCRIPT_PATH = str(Path(__file__).parent.parent / "run_system.py")
PYTHON_PATH = sys.executable
WORK_DIR    = str(Path(__file__).parent.parent)
LOG_DIR     = str(Path(__file__).parent.parent / "logs")
RUN_TIME    = "07:30"


def create_task():
    print(f"Creating Task Scheduler task : {TASK_NAME}")
    print(f"Script                       : {SCRIPT_PATH}")
    print(f"Python                       : {PYTHON_PATH}")
    print(f"Schedule                     : Daily at {RUN_TIME}")
    print()

    os.makedirs(LOG_DIR, exist_ok=True)

    subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                   capture_output=True)

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTMO AI Trading System — starts live_trading_system.py daily before London open.</Description>
    <Author>FTMO_System</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T{RUN_TIME}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT20H</ExecutionTimeLimit>
    <Priority>5</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
    </IdleSettings>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON_PATH}</Command>
      <Arguments>"{SCRIPT_PATH}"</Arguments>
      <WorkingDirectory>{WORK_DIR}</WorkingDirectory>
    </Exec>
  </Actions>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>"""

    xml_path = str(Path(__file__).parent / "_trading_task_temp.xml")
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
        print(f"Trading system will start automatically every day at {RUN_TIME}.")
        print("Restarts up to 3 times if it crashes (5 min between attempts).")
        print()
        print("To start immediately:")
        print(f"  schtasks /run /tn {TASK_NAME}")
        print()
        print("To check status:")
        print(f"  schtasks /query /tn {TASK_NAME} /fo LIST")
    else:
        print(f"[FAIL] Task creation failed:\n{result.stderr}")
        print("Try running this script as Administrator.")
        sys.exit(1)


def delete_task():
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' deleted.")
    else:
        print(f"Task not found or could not be deleted:\n{result.stderr}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true", help="Remove the scheduled task")
    args = parser.parse_args()

    if args.delete:
        delete_task()
    else:
        create_task()
