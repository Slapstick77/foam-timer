#!/usr/bin/env python3

import os
import shutil
import logging
import json

## Configuration
LOG_FILE = '/home/pi/timer_project/backup_log.log'  # Update path if necessary
DB_FILE = '/home/pi/timer_project/logs.db'          # Path to the SQLite database
USB_LABEL = 'USB_BACKUP'                            # Label of your USB drive
BACKUP_FILENAME = 'logs_backup.db'                  # Name of the backup file on USB

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_usb_mount_point(label):
    """
    Searches for the USB drive by its label and returns its mount point.
    """
    try:
        mounts = os.popen("lsblk -o NAME,LABEL,MOUNTPOINT -J").read()
        mounts_json = json.loads(mounts)
        for device in mounts_json['blockdevices']:
            if 'children' in device:
                for child in device['children']:
                    if child.get('label') == label and child.get('mountpoint'):
                        return child.get('mountpoint')
    except json.JSONDecodeError:
        logging.error("Failed to parse lsblk output.")
    except Exception as e:
        logging.error(f"An error occurred while searching for the USB drive: {e}")
    return None

def copy_db():
    """
    Copies logs.db to the USB drive if mounted.
    """
    mount_point = get_usb_mount_point(USB_LABEL)
    if mount_point:
        destination = os.path.join(mount_point, BACKUP_FILENAME)
        try:
            shutil.copy2(DB_FILE, destination)
            logging.info(f"Successfully backed up logs.db to {destination}")
        except Exception as e:
            logging.error(f"Failed to copy logs.db: {e}")
    else:
        logging.warning(f"USB drive '{USB_LABEL}' not mounted. Skipping backup.")

def main():
    logging.info("Backup script started.")
    copy_db()
    logging.info("Backup script finished.")

if __name__ == '__main__':
    main()
