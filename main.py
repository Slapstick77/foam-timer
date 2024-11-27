import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import pandas as pd
import json
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
import time
import sys
import os
import sqlite3  # For database support

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and PyInstaller """
    try:
        # When running in a PyInstaller bundle, _MEIPASS is set
        base_path = sys._MEIPASS
    except AttributeError:
        # In development mode, use the current directory
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# === Configuration ===

# File paths for storing persistent data
SETTINGS_FILE = resource_path("settings.json")
LOGS_DB = resource_path("logs.db")  # Using SQLite database

# GPIO Pin Definitions
BUTTON_PINS = {
    1: 17,  # Timer 1
    2: 27,  # Timer 2
    3: 22,  # Timer 3
    4: 23   # Timer 4
}

# Debounce time in seconds
DEBOUNCE_TIME = 0.3  # 300 milliseconds

# Password for clearing logs
CLEAR_LOGS_PASSWORD = "your_password_here"  # Replace with a secure password

# === Global Variables ===

# Timer durations (in seconds) and texts
TIMER_DURATIONS = [5 * 60, 10 * 60, 15 * 60, 20 * 60]  # 5, 10, 15, 20 minutes
TIMER_TEXTS = ["First Timer", "Second Timer", "Third Timer", "Fourth Timer"]

active_timer = None
remaining_time = 0
running = False
current_screen = "idle"

# Idle Timer Color Thresholds (in seconds)
IDLE_YELLOW_DURATION = 5 * 60  # 5 minutes
IDLE_RED_DURATION = 10 * 60    # 10 minutes

# Variables for tracking times
timer_start_time = None
timer_stop_time = None
idle_timer_running = False
idle_start_time = None

# === Export Interval Variables ===
EXPORT_INTERVAL_HOURS = 1  # Default export interval hours
EXPORT_INTERVAL_MINUTES = 0  # Default export interval minutes
export_after_id = None  # To store the after callback ID

# Variables for debouncing
last_press_time = {timer: 0 for timer in BUTTON_PINS.keys()}  # Track last press times

# === GPIO Setup ===

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for pin in BUTTON_PINS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)  # No internal pull-downs

def cleanup_gpio():
    GPIO.cleanup()

# === Settings Management ===

def load_settings():
    global TIMER_DURATIONS, TIMER_TEXTS, IDLE_YELLOW_DURATION, IDLE_RED_DURATION
    global EXPORT_INTERVAL_HOURS, EXPORT_INTERVAL_MINUTES
    try:
        with open(SETTINGS_FILE, "r") as file:
            data = json.load(file)
            TIMER_DURATIONS = data.get("durations", TIMER_DURATIONS)
            TIMER_TEXTS = data.get("texts", TIMER_TEXTS)
            IDLE_YELLOW_DURATION = data.get("idle_yellow_duration", IDLE_YELLOW_DURATION)
            IDLE_RED_DURATION = data.get("idle_red_duration", IDLE_RED_DURATION)
            EXPORT_INTERVAL_HOURS = data.get("export_interval_hours", EXPORT_INTERVAL_HOURS)
            EXPORT_INTERVAL_MINUTES = data.get("export_interval_minutes", EXPORT_INTERVAL_MINUTES)
    except (FileNotFoundError, json.JSONDecodeError):
        save_settings()  # Create settings file with defaults

def save_settings():
    data = {
        "durations": TIMER_DURATIONS,
        "texts": TIMER_TEXTS,
        "idle_yellow_duration": IDLE_YELLOW_DURATION,
        "idle_red_duration": IDLE_RED_DURATION,
        "export_interval_hours": EXPORT_INTERVAL_HOURS,
        "export_interval_minutes": EXPORT_INTERVAL_MINUTES
    }
    with open(SETTINGS_FILE, "w") as file:
        json.dump(data, file)

# === Database Initialization ===

def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(LOGS_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            start_time TEXT,
            stop_time TEXT,
            duration TEXT
        )
    ''')
    conn.commit()
    conn.close()

# === Timer Functions ===

def start_timer(timer_list_index):
    global active_timer, remaining_time, running, timer_start_time
    if not running:
        if idle_timer_running:
            stop_idle_timer()
        active_timer = timer_list_index
        remaining_time = TIMER_DURATIONS[timer_list_index]
        running = True
        timer_start_time = datetime.now()
        timer_text_label.config(text=TIMER_TEXTS[timer_list_index])
        idle_timer_label.config(text="")
        update_timer()

def stop_timer():
    global active_timer, remaining_time, running, timer_stop_time
    if active_timer is not None:
        timer_stop_time = datetime.now()
        log_state_change(TIMER_TEXTS[active_timer], timer_start_time, timer_stop_time)
        active_timer = None
        remaining_time = 0
        running = False
        timer_label.config(text="00:00")
        timer_text_label.config(text="")
        start_idle_timer()

def update_timer():
    global remaining_time, running
    if running and remaining_time > 0:
        minutes, seconds = divmod(remaining_time, 60)
        timer_label.config(text=f"{int(minutes):02}:{int(seconds):02}")
        remaining_time -= 1
        root.after(1000, update_timer)
    elif running and remaining_time <= 0:
        stop_timer()

# === Idle Timer Functions ===

def start_idle_timer():
    global idle_timer_running, idle_start_time
    if not idle_timer_running:
        idle_timer_running = True
        idle_start_time = datetime.now()
        timer_text_label.config(text="Idle")
        update_idle_timer()

def stop_idle_timer():
    global idle_timer_running, idle_start_time
    if idle_timer_running:
        idle_stop_time = datetime.now()
        log_state_change("Idle", idle_start_time, idle_stop_time)
        idle_timer_running = False
        idle_start_time = None
        idle_timer_label.config(text="")
        timer_text_label.config(text="")

def update_idle_timer():
    global idle_timer_running
    if idle_timer_running:
        now = datetime.now()
        elapsed = now - idle_start_time
        elapsed_seconds = elapsed.total_seconds()
        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        idle_timer_label.config(text=f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}")
        # Change color based on thresholds
        if elapsed_seconds < IDLE_YELLOW_DURATION:
            idle_timer_label.config(fg="green")
        elif elapsed_seconds < IDLE_RED_DURATION:
            idle_timer_label.config(fg="yellow")
        else:
            idle_timer_label.config(fg="red")
        root.after(1000, update_idle_timer)

# === Logging Functions ===

def log_state_change(name, start_time, stop_time):
    """Log state changes to the database."""
    duration = (stop_time - start_time).total_seconds()
    duration_str = str(timedelta(seconds=int(duration)))
    conn = sqlite3.connect(LOGS_DB)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (name, start_time, stop_time, duration)
        VALUES (?, ?, ?, ?)
    ''', (
        name,
        start_time.strftime("%Y-%m-%d %H:%M:%S"),
        stop_time.strftime("%Y-%m-%d %H:%M:%S"),
        duration_str
    ))
    conn.commit()
    conn.close()

def clear_logs():
    """Clear logs from the database."""
    password = simpledialog.askstring("Password Required", "Enter the password:", show='*')
    if password == CLEAR_LOGS_PASSWORD:
        conn = sqlite3.connect(LOGS_DB)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM logs')
        conn.commit()
        conn.close()
        refresh_log_view()
        messagebox.showinfo("Success", "Logs cleared successfully.")
    else:
        messagebox.showerror("Error", "Incorrect password.")

def export_logs():
    """Export logs from the database to logs.xlsx."""
    conn = sqlite3.connect(LOGS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT name, start_time, stop_time, duration FROM logs')
    rows = cursor.fetchall()
    conn.close()
    if rows:
        df = pd.DataFrame(rows, columns=["Name", "Start Time", "Stop Time", "Duration"])
        try:
            df.to_excel("logs.xlsx", index=False)
            print("Logs exported to logs.xlsx.")  # Optional: Console logging for confirmation
        except Exception as e:
            print(f"Failed to export logs: {e}")  # Optional: Console logging for errors
    else:
        print("No logs to export.")  # Optional: Console logging for warnings

def refresh_log_view():
    """Refresh the log view by fetching logs from the database."""
    for item in log_tree.get_children():
        log_tree.delete(item)
    conn = sqlite3.connect(LOGS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT name, start_time, stop_time, duration FROM logs')
    rows = cursor.fetchall()
    conn.close()
    for row in rows:
        log_tree.insert("", "end", values=row)

# === Scheduling Export Logs ===

def perform_export_logs():
    """Perform the export logs action and reschedule."""
    export_logs()
    schedule_export_logs()  # Schedule the next export

def schedule_export_logs():
    global export_after_id
    interval_seconds = EXPORT_INTERVAL_HOURS * 3600 + EXPORT_INTERVAL_MINUTES * 60
    if interval_seconds > 0:
        interval_ms = interval_seconds * 1000
        export_after_id = root.after(interval_ms, perform_export_logs)

def reschedule_export_logs():
    global export_after_id
    if export_after_id is not None:
        root.after_cancel(export_after_id)
        export_after_id = None
    schedule_export_logs()

# === Screen Navigation ===

def show_main_screen():
    global current_screen
    current_screen = "idle"
    log_frame.pack_forget()
    settings_frame.pack_forget()
    timer_frame.pack(fill="both", expand=True)
    timer_text_label.config(text="Idle")
    start_idle_timer()
    schedule_export_logs()  # Ensure export is scheduled when returning to main screen

def show_settings_screen():
    global current_screen
    current_screen = "settings"
    timer_frame.pack_forget()
    log_frame.pack_forget()
    # Update the settings entries with current settings
    for i, (min_entry, sec_entry) in enumerate(timer_entries):
        minutes, seconds = divmod(TIMER_DURATIONS[i], 60)
        min_entry.delete(0, tk.END)
        min_entry.insert(0, str(int(minutes)))
        sec_entry.delete(0, tk.END)
        sec_entry.insert(0, str(int(seconds)))
        text_entries[i].delete(0, tk.END)
        text_entries[i].insert(0, TIMER_TEXTS[i])
    # Update idle timer color thresholds
    idle_yellow_entry.delete(0, tk.END)
    idle_yellow_entry.insert(0, str(int(IDLE_YELLOW_DURATION // 60)))
    idle_red_entry.delete(0, tk.END)
    idle_red_entry.insert(0, str(int(IDLE_RED_DURATION // 60)))
    # Update export interval entries
    export_hours_entry.delete(0, tk.END)
    export_hours_entry.insert(0, str(int(EXPORT_INTERVAL_HOURS)))
    export_minutes_entry.delete(0, tk.END)
    export_minutes_entry.insert(0, str(int(EXPORT_INTERVAL_MINUTES)))
    settings_frame.pack(fill="both", expand=True)
    stop_idle_timer()
    if export_after_id is not None:
        root.after_cancel(export_after_id)  # Pause export while in settings
    # Set focus to the first Entry widget
    if timer_entries:
        timer_entries[0][0].focus_set()

def show_log_page():
    global current_screen
    current_screen = "logs"
    timer_frame.pack_forget()
    settings_frame.pack_forget()
    log_frame.pack(fill="both", expand=True)
    stop_idle_timer()
    refresh_log_view()

# === Key Press Handlers ===

def handle_alt_l(event):
    print("Alt-l pressed")  # Debugging statement
    if current_screen == "idle":
        show_log_page()
        return "break"

def handle_alt_s(event):
    print("Alt-s pressed")  # Debugging statement
    if current_screen == "idle":
        show_settings_screen()
        return "break"

# === Settings Update Function ===

def update_settings():
    global TIMER_DURATIONS, TIMER_TEXTS, IDLE_YELLOW_DURATION, IDLE_RED_DURATION
    global EXPORT_INTERVAL_HOURS, EXPORT_INTERVAL_MINUTES
    try:
        for i in range(4):
            minutes = int(timer_entries[i][0].get())
            seconds = int(timer_entries[i][1].get())
            if minutes < 0 or seconds < 0 or seconds >= 60:
                raise ValueError
            TIMER_DURATIONS[i] = minutes * 60 + seconds
            TIMER_TEXTS[i] = text_entries[i].get()
        # Read idle timer color thresholds
        yellow_minutes = int(idle_yellow_entry.get())
        red_minutes = int(idle_red_entry.get())
        if yellow_minutes < 0 or red_minutes < 0:
            raise ValueError
        IDLE_YELLOW_DURATION = yellow_minutes * 60
        IDLE_RED_DURATION = red_minutes * 60
        # Read export interval settings
        export_hours = int(export_hours_entry.get())
        export_minutes = int(export_minutes_entry.get())
        if export_hours < 0 or export_minutes < 0 or export_minutes >= 60:
            raise ValueError
        EXPORT_INTERVAL_HOURS = export_hours
        EXPORT_INTERVAL_MINUTES = export_minutes
        save_settings()
        reschedule_export_logs()  # Reschedule export with new settings
        show_main_screen()
    except ValueError:
        messagebox.showerror("Error", "Invalid input. Please enter valid positive numbers.")

# === GPIO Button Callback ===

def button_callback(timer_index):
    # Map button index (1-4) to list index (0-3)
    timer_list_index = timer_index - 1
    
    # Ensure the index is within the valid range
    if timer_list_index < 0 or timer_list_index >= len(TIMER_DURATIONS):
        print(f"Invalid timer index: {timer_index}")
        return
    
    current_time = time.time()
    if current_time - last_press_time[timer_index] >= DEBOUNCE_TIME:
        print(f"Button {timer_index} pressed")  # Debugging statement
        if running and active_timer == timer_list_index:
            stop_timer()
        else:
            start_timer(timer_list_index)
        last_press_time[timer_index] = current_time
    else:
        print(f"Button {timer_index} press ignored due to debounce.")  # Debugging statement
        pass

# === GPIO Event Detection Setup ===

def setup_event_detection():
    for timer_index, pin in BUTTON_PINS.items():
        GPIO.add_event_detect(
            pin,
            GPIO.RISING,  # Detect rising edge (LOW -> HIGH)
            callback=lambda channel, idx=timer_index: button_callback(idx),
            bouncetime=int(DEBOUNCE_TIME * 1000)  # Convert to milliseconds
        )

# === Application Exit Handler ===

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        if running:
            stop_timer()
        elif idle_timer_running:
            stop_idle_timer()
        if export_after_id is not None:
            root.after_cancel(export_after_id)
        cleanup_gpio()
        root.destroy()

# === Initialize the GUI ===

def initialize_gui():
    global root, timer_frame, timer_label, timer_text_label, idle_timer_label
    global log_frame, log_tree, log_buttons
    global settings_frame, timer_entries, text_entries
    global idle_yellow_entry, idle_red_entry
    global export_hours_entry, export_minutes_entry  # Added
    global buttons_frame

    root = tk.Tk()
    root.title("Timer Application")
    root.geometry("1920x1080")
    root.attributes("-fullscreen", True)
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Bind keys for navigation only
    root.bind('<Alt-l>', handle_alt_l)
    root.bind('<Alt-s>', handle_alt_s)

    # Main timer screen
    timer_frame = tk.Frame(root, bg="black")
    central_frame = tk.Frame(timer_frame, bg="black")
    central_frame.pack(expand=True)
    timer_label = tk.Label(central_frame, text="00:00", font=("Helvetica", 500, "bold"), fg="white", bg="black")
    timer_label.pack()
    timer_text_label = tk.Label(central_frame, text="", font=("Helvetica", 60), fg="gray", bg="black")
    timer_text_label.pack(pady=(20, 20))
    idle_timer_label = tk.Label(timer_frame, text="", font=("Helvetica", 40), fg="green", bg="black")
    idle_timer_label.pack(side="bottom", pady=20)

    # Log screen
    log_frame = tk.Frame(root, bg="white")
    log_tree = ttk.Treeview(log_frame, columns=("Name", "Start Time", "Stop Time", "Duration"), show="headings")
    log_tree.heading("Name", text="Name")
    log_tree.heading("Start Time", text="Start Time")
    log_tree.heading("Stop Time", text="Stop Time")
    log_tree.heading("Duration", text="Duration")
    log_tree.column("Name", width=200, anchor='center')
    log_tree.column("Start Time", width=200, anchor='center')
    log_tree.column("Stop Time", width=200, anchor='center')
    log_tree.column("Duration", width=150, anchor='center')
    log_tree.pack(fill="both", expand=True, padx=20, pady=20)

    log_buttons = tk.Frame(log_frame, bg="white")
    log_buttons.pack(fill="x", pady=10, padx=20)
    clear_logs_button = tk.Button(log_buttons, text="Clear Logs", command=clear_logs, font=("Helvetica", 16))
    clear_logs_button.pack(side="left", padx=10, pady=5)
    export_logs_button = tk.Button(log_buttons, text="Export Logs", command=export_logs, font=("Helvetica", 16))
    export_logs_button.pack(side="left", padx=10, pady=5)
    back_log_button = tk.Button(log_buttons, text="Back", command=show_main_screen, font=("Helvetica", 16))
    back_log_button.pack(side="right", padx=10, pady=5)

    # Settings screen
    settings_frame = tk.Frame(root, bg="white")
    timer_entries, text_entries = [], []
    for i, duration in enumerate(TIMER_DURATIONS):
        frame = tk.Frame(settings_frame, bg="white")
        frame.pack(pady=5, anchor='w', padx=20)
        label = tk.Label(frame, text=f"Timer {i + 1}:", font=("Helvetica", 16), bg="white")
        label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        minutes, seconds = divmod(duration, 60)
        min_label = tk.Label(frame, text="Min:", font=("Helvetica", 16), bg="white")
        min_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        min_entry = tk.Entry(frame, font=("Helvetica", 16), width=5)
        min_entry.insert(0, str(int(minutes)))
        min_entry.grid(row=0, column=2, padx=5, pady=5)
        sec_label = tk.Label(frame, text="Sec:", font=("Helvetica", 16), bg="white")
        sec_label.grid(row=0, column=3, padx=5, pady=5, sticky='w')
        sec_entry = tk.Entry(frame, font=("Helvetica", 16), width=5)
        sec_entry.insert(0, str(int(seconds)))
        sec_entry.grid(row=0, column=4, padx=5, pady=5)
        timer_entries.append((min_entry, sec_entry))
        text_label = tk.Label(frame, text="Text:", font=("Helvetica", 16), bg="white")
        text_label.grid(row=0, column=5, padx=5, pady=5, sticky='w')
        text_entry = tk.Entry(frame, font=("Helvetica", 16), width=25)
        text_entry.insert(0, TIMER_TEXTS[i])
        text_entry.grid(row=0, column=6, padx=5, pady=5)
        text_entries.append(text_entry)

    idle_settings_frame = tk.Frame(settings_frame, bg="white")
    idle_settings_frame.pack(pady=10, anchor='w', padx=20)
    idle_label = tk.Label(idle_settings_frame, text="Idle Timer Color Change Durations:", font=("Helvetica", 16), bg="white")
    idle_label.grid(row=0, column=0, columnspan=2, pady=(10, 5), sticky='w')
    idle_yellow_label = tk.Label(idle_settings_frame, text="Yellow Threshold (minutes):", font=("Helvetica", 16), bg="white")
    idle_yellow_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
    idle_yellow_entry = tk.Entry(idle_settings_frame, font=("Helvetica", 16), width=5)
    idle_yellow_entry.insert(0, str(int(IDLE_YELLOW_DURATION // 60)))
    idle_yellow_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
    idle_red_label = tk.Label(idle_settings_frame, text="Red Threshold (minutes):", font=("Helvetica", 16), bg="white")
    idle_red_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
    idle_red_entry = tk.Entry(idle_settings_frame, font=("Helvetica", 16), width=5)
    idle_red_entry.insert(0, str(int(IDLE_RED_DURATION // 60)))
    idle_red_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')

    # === Export Interval Settings ===
    export_settings_frame = tk.Frame(settings_frame, bg="white")
    export_settings_frame.pack(pady=10, anchor='w', padx=20)
    export_label = tk.Label(export_settings_frame, text="Export Logs Interval:", font=("Helvetica", 16), bg="white")
    export_label.grid(row=0, column=0, columnspan=2, pady=(10, 5), sticky='w')
    export_hours_label = tk.Label(export_settings_frame, text="Hours:", font=("Helvetica", 16), bg="white")
    export_hours_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
    export_hours_entry = tk.Entry(export_settings_frame, font=("Helvetica", 16), width=5)
    export_hours_entry.insert(0, str(int(EXPORT_INTERVAL_HOURS)))
    export_hours_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
    export_minutes_label = tk.Label(export_settings_frame, text="Minutes:", font=("Helvetica", 16), bg="white")
    export_minutes_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
    export_minutes_entry = tk.Entry(export_settings_frame, font=("Helvetica", 16), width=5)
    export_minutes_entry.insert(0, str(int(EXPORT_INTERVAL_MINUTES)))
    export_minutes_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')

    buttons_frame = tk.Frame(settings_frame, bg="white")
    buttons_frame.pack(pady=20, padx=20, anchor='w')
    save_button = tk.Button(buttons_frame, text="Save", command=update_settings, font=("Helvetica", 16), bg="#555555", fg="white", width=12)
    save_button.grid(row=0, column=0, padx=10, pady=5)
    back_button = tk.Button(buttons_frame, text="Back", command=show_main_screen, font=("Helvetica", 16), bg="#555555", fg="white", width=12)
    back_button.grid(row=0, column=1, padx=10, pady=5)

    # Pack all frames but hide them initially
    timer_frame.pack(fill="both", expand=True)
    log_frame.pack_forget()
    settings_frame.pack_forget()

    # Initialize labels
    timer_text_label.config(text="Idle")

# === Main Application ===

if __name__ == "__main__":
    try:
        setup_gpio()
        setup_event_detection()
        load_settings()
        init_db()  # Initialize the database
        initialize_gui()
        show_main_screen()
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        cleanup_gpio()
