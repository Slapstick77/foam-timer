# foam-timer
Foam Press Timer
# Foam Timer

## Overview

The Foam Timer is a Python-based application designed to run on a Raspberry Pi. It provides a graphical user interface (GUI) with timer functionality, logging, and settings management. The application logs timer activities to a SQLite database and allows for automated backups and exports.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [GPIO Pin Configuration](#gpio-pin-configuration)
- [License](#license)

---

## Features

- Multiple timers with customizable durations and labels
- Idle timer with color-coded thresholds
- Logging of timer activities to a SQLite database
- Export logs to an Excel file (`logs.xlsx`)
- Backup of logs to a USB drive
- Settings screen for adjusting timers and thresholds
- Automatic startup of the application on system boot

---

## Requirements

### Hardware

- **Raspberry Pi** (any model with GPIO support)
- **Display** connected to the Raspberry Pi
- **Physical Buttons** connected to GPIO pins for timer control

### Software

- **Operating System**: Raspberry Pi OS (formerly Raspbian) or any Linux distribution compatible with Raspberry Pi
- **Python 3.6** or higher

### Python Libraries

- Listed in `requirements.txt` (installed via `pip`)
- Additional system packages installed via `apt`

---

## Installation

### 1. Clone the Repository

Open a terminal on your Raspberry Pi and run:

```bash
cd /home/pi/
git clone https://github.com/Slapstick77/foam-timer.git
2. Install System Packages
Update your package list:

bash
Copy code
sudo apt update
Install the necessary system packages:

bash
Copy code
sudo apt install python3 python3-pip python3-tk python3-rpi.gpio
Notes:

python3: The Python 3 interpreter.
python3-pip: The Python package manager for Python 3.
python3-tk: Provides the tkinter module for GUI applications.
python3-rpi.gpio: Provides the RPi.GPIO module for GPIO interaction.
3. Install Python Packages
Navigate to the project directory:

bash
Copy code
cd /home/pi/foam-timer/
Install the required Python packages using pip:

bash
Copy code
sudo pip3 install -r requirements.txt
Usage
Running the Application
You can run the application manually:

bash
Copy code
python3 /home/pi/foam-timer/main.py
The application will start in full-screen mode, displaying the main timer screen.

Navigating the Application
Start/Stop Timers: Use the physical buttons connected to the Raspberry Pi GPIO pins.
Access Log Screen: Press Alt + l on the keyboard.
Access Settings Screen: Press Alt + s on the keyboard.
Exporting Logs
Logs are exported to logs.xlsx automatically based on the export interval defined in the settings. You can also export logs manually from the log screen.

GPIO Pin Configuration
By default, the application uses the following GPIO pins for the buttons:

Timer 1: GPIO 17
Timer 2: GPIO 27
Timer 3: GPIO 22
Timer 4: GPIO 23
Ensure your buttons are connected to these pins and configured correctly.