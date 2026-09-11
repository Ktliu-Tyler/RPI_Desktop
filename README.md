# NTU Racing Raspberry Pi Deployment Record

A snapshot of the Raspberry Pi-side software layout used for vehicle CAN services and web monitoring. Its purpose is to collect the startup scripts, service definitions, server components, and linked monitoring code that make up the deployed working environment.

## What this repository records

- Initialization of two CAN interfaces.
- A logging startup script that invokes the linked monitoring project.
- A CAN web server and client arrangement.
- Five systemd service definitions, including older and GPS/RTK-related service configurations.
- Python environment dependency snapshots for Raspberry Pi and Windows-related work.

## Organization

| Path | Role |
| --- | --- |
| [scripts](scripts) | Startup scripts connecting services to applications |
| [services](services) | systemd unit definitions |
| [CAN_web](CAN_web) | CAN client, decoder, and web-server code |
| [.gitmodules](.gitmodules) | Declares the `GUI-dev` submodule |
| `GUI-dev` | Linked snapshot of [rpi_can_monitor](https://github.com/Ktliu-Tyler/rpi_can_monitor) |
| [requirements.txt](requirements.txt) | Broad Raspberry Pi environment snapshot |
| [requirements-win.txt](requirements-win.txt) | Smaller Windows-oriented dependency list |

## How it fits together

The service files point to shell scripts, and those scripts select application directories and Python interpreters. The included CAN initialization script configures both interfaces at 1 Mbit/s. The logging script references `canlogging-v4.py` in the submodule, while the web-server script starts `CAN_web/CanServer.py`.

## Personal infrastructure record

This repository preserves a machine-specific deployment arrangement rather than a portable installer. Paths under `/home/pi/Desktop/RPI_Desktop`, interpreter choices, service users, and referenced applications describe that environment. Some service definitions refer to components outside the checked-in tree, and included virtual environments are historical artifacts.

The original deployment illustration is retained below. Together with [rpi_can_monitor](https://github.com/Ktliu-Tyler/rpi_can_monitor), this record shows how application experiments were connected to operating-system services on the vehicle computer.

## Original project notes

The original documentation is retained below as a personal development record, including its original language, credits, illustrations, and historical instructions. Dates, paths, and environment details describe the original work.

<details>
<summary>Read the original documentation</summary>


# This description haven't been done yet !!
## RPI_desktop (A deployed sturcture of rpi)
This code is mainly for our main structure of NTUracing raspberry pi
It include 5 deployed dservice in the directory "services", which is link to the corresponding scripts in the directory "scripts"
<img width="749" height="443" alt="image" src="https://github.com/user-attachments/assets/e5c03d1b-5f00-4879-be54-4dfe95ebcbb7" />

</details>
