
---

## **`AUTOSTART_INSTRUCTIONS.md`**

Here's the `AUTOSTART_INSTRUCTIONS.md` file with your repository path, also in a code block:

```markdown
# Autostart Instructions

This guide provides step-by-step instructions to configure the Foam Timer application to start automatically when the Raspberry Pi boots.

---

## Table of Contents

- [Creating a Systemd Service](#creating-a-systemd-service)
- [Enabling the Service](#enabling-the-service)
- [Managing the Service](#managing-the-service)
- [Troubleshooting](#troubleshooting)

---

## Creating a Systemd Service

1. **Create the Service File**

   Open a terminal and create a new service file:

   ```bash
   sudo nano /etc/systemd/system/foam_timer.service
Add the Following Content

Paste the following configuration into the file:

ini
Copy code
[Unit]
Description=Foam Timer Application
After=graphical.target

[Service]
Type=simple
Restart=always
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/usr/bin/python3 /home/pi/foam-timer/main.py
WorkingDirectory=/home/pi/foam-timer/
StandardOutput=inherit
StandardError=inherit

[Install]
WantedBy=graphical.target
Notes:

Replace pi with your username if different.
Ensure the paths to python3 and main.py are correct.
The Environment variables are set to allow GUI applications to run as a service.
Save and Exit

Press Ctrl + O to save.
Press Enter to confirm the filename.
Press Ctrl + X to exit the editor.
Enabling the Service
Reload Systemd Daemon

bash
Copy code
sudo systemctl daemon-reload
Enable the Service to Start on Boot

bash
Copy code
sudo systemctl enable foam_timer.service
Start the Service Immediately

bash
Copy code
sudo systemctl start foam_timer.service
Managing the Service
Check Service Status
To check if the service is running:

bash
Copy code
sudo systemctl status foam_timer.service
Restart the Service
If you make changes to main.py and need to restart the service:

bash
Copy code
sudo systemctl restart foam_timer.service
Stop the Service
To stop the service:

bash
Copy code
sudo systemctl stop foam_timer.service
Troubleshooting
Service Fails to Start

Check the status for error messages:

bash
Copy code
sudo systemctl status foam_timer.service
Review logs:

bash
Copy code
journalctl -u foam_timer.service
Permission Issues

Ensure the main.py script has the appropriate permissions:

bash
Copy code
chmod +x /home/pi/foam-timer/main.py
Display Issues

If the GUI does not display when running as a service, ensure that the DISPLAY and XAUTHORITY environment variables are correctly set in the service file.
Notes
User Sessions: Running GUI applications as a systemd service can be complex due to user session management. Ensure that the service runs under the correct user and environment.

Alternative Autostart Methods: If you encounter issues with systemd, consider using other autostart methods like cron @reboot, or adding the script to the LXDE autostart file if you're using the Raspberry Pi desktop environment.

Support
If you need further assistance, please refer to the project's README.md or contact the maintainer