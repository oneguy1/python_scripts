import time
import random
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from multiprocessing import Process, Manager


# --- BOT ENGINE ---
def launch_attendee(meet_url, name, status_dict, question=None, min_wait=10):
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    try:
        status_dict[name] = "Joining..."
        driver.get(meet_url)
        wait = WebDriverWait(driver, 30)

        # 1. Handle the "Recording Consent" popup
        try:
            recording_xpath = "//span[contains(text(), 'Join now') or contains(text(), 'הצטרפות כעת') or contains(text(), 'Got it')]"
            # Shorter wait (5s) because if it's not there, we want to move on quickly
            consent_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, recording_xpath))
            )
            consent_btn.click()
            time.sleep(2)  # Give the page a moment to clear the overlay
        except:
            pass  # No recording notice found, moving on...
        # --------------------------------

        # Join Logic (The bot can now see the name input)
        name_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='text' or @placeholder='Your name' or @placeholder='השם שלך']")))

        # Use clear() before typing just in case
        name_input.clear()
        name_input.send_keys(name)

        join_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(text(), 'Ask to join') or contains(text(), 'בקשת הצטרפות')]")))
        join_btn.click()

        status_dict[name] = "Active"

        # Randomized Q&A Logic
        if question:
            # Wait for the base time + a random 1-4 minute "human" jitter
            total_wait_seconds = (min_wait * 60) + random.randint(10, 240)
            time.sleep(total_wait_seconds)

            try:
                status_dict[name] = "Posting Q..."
                # Open Activities -> Q&A
                wait.until(EC.element_to_be_clickable((By.XPATH,
                                                       "//button[contains(@aria-label, 'Activities') or contains(@aria-label, 'פעילויות')]"))).click()
                wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(), 'Q&A') or contains(text(), 'שאלות ותשובות')]"))).click()
                wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(text(), 'Ask a question') or contains(text(), 'לשאול שאלה')]"))).click()

                # Type Question
                text_area = wait.until(EC.presence_of_element_located((By.TAG_NAME, "textarea")))
                text_area.send_keys(question)
                driver.find_element(By.XPATH, "//span[contains(text(), 'Post') or contains(text(), 'פרסום')]").click()

                status_dict[name] = "Question Posted ✅"
            except:
                status_dict[name] = "Q&A Hidden/Closed"

        while True: time.sleep(1)
    except Exception:
        status_dict[name] = "Disconnected"
    finally:
        driver.quit()


# --- GUI CLASS ---
class WebinarBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Stealth Webinar Bot Dash")
        self.root.geometry("600x750")

        self.manager = Manager()
        self.status_dict = self.manager.dict()
        self.processes = []
        self.is_running = False

        # Input Frame
        frm = tk.Frame(root, padx=20, pady=10)
        frm.pack(fill="x")

        # Row 0: URL
        tk.Label(frm, text="Meet URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = tk.Entry(frm, width=45)
        self.url_entry.grid(row=0, column=1, pady=5)

        # Row 1: Bot Count & Time
        tk.Label(frm, text="Bot Count:").grid(row=1, column=0, sticky="w")
        self.count_entry = tk.Entry(frm, width=10)
        self.count_entry.insert(0, "20")
        self.count_entry.grid(row=1, column=1, sticky="w")

        tk.Label(frm, text="Start (HH:MM):").grid(row=2, column=0, sticky="w")
        self.time_entry = tk.Entry(frm, width=10)
        self.time_entry.insert(0, "18:00")
        self.time_entry.grid(row=2, column=1, sticky="w")

        # Row 2: Duration
        tk.Label(frm, text="Duration (Min):").grid(row=3, column=0, sticky="w")
        self.dur_entry = tk.Entry(frm, width=10)
        self.dur_entry.insert(0, "60")
        self.dur_entry.grid(row=3, column=1, sticky="w")

        # Questions Area
        tk.Label(root, text="Seeded Questions (one per line):").pack()
        self.q_text = tk.Text(root, height=5, width=60)
        self.q_text.insert("1.0",
                           "Great presentation! Can you elaborate on the roadmap?\nIs this feature available for Business Standard users?")
        self.q_text.pack(pady=5)

        # Control Buttons
        btn_frm = tk.Frame(root)
        btn_frm.pack(pady=10)
        self.start_btn = tk.Button(btn_frm, text="Schedule & Start", command=self.start_thread, bg="#2ecc71",
                                   fg="white", width=18, font=("Arial", 10, "bold"))
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = tk.Button(btn_frm, text="EMERGENCY STOP", command=self.kill_all, bg="#e74c3c", fg="white",
                                  width=18, font=("Arial", 10, "bold"))
        self.stop_btn.pack(side="left", padx=5)

        # Live Status
        self.status_label = tk.Label(root, text="SYSTEM IDLE", font=("Courier", 14, "bold"), fg="#34495e")
        self.status_label.pack(pady=10)

        # Table
        self.tree = ttk.Treeview(root, columns=("Name", "Status"), show='headings')
        self.tree.heading("Name", text="Attendee Name");
        self.tree.heading("Status", text="Status")
        self.tree.column("Name", width=250);
        self.tree.column("Status", width=250)
        self.tree.pack(pady=10, fill='both', expand=True, padx=20)

    def kill_all(self):
        self.is_running = False
        for p in self.processes: p.terminate()
        os.system("pkill -f chrome")
        messagebox.showwarning("System Reset", "All bot processes terminated instantly.")

    def update_ui_loop(self):
        self.tree.delete(*self.tree.get_children())
        for name, status in sorted(self.status_dict.items()):
            self.tree.insert("", "end", values=(name, status))
        if self.is_running: self.root.after(2000, self.update_ui_loop)

    def start_thread(self):
        self.is_running = True
        threading.Thread(target=self.main_logic, daemon=True).start()
        self.update_ui_loop()

    def main_logic(self):
        url = self.url_entry.get()
        count = int(self.count_entry.get())
        target_time = self.time_entry.get()
        duration = int(self.dur_entry.get())
        questions = [q for q in self.q_text.get("1.0", "end-1c").split("\n") if q.strip()]

        while datetime.now().strftime("%H:%M") != target_time:
            if not self.is_running: return
            self.status_label.config(text=f"WAITING FOR {target_time}...")
            time.sleep(5)

        # --- BOT Names ---
        self.status_label.config(text="🚀 DEPLOYING BOTS...")
        names = ["James W.", "Maria G.", "Robert C.", "Sarah S.", "David M.", "Linda T.", "Kevin A.", "Elena R.",
                 "Tom H.", "Kim P","Norm M"]

        end_time = datetime.now() + timedelta(minutes=duration)

        for i in range(count):
            if not self.is_running: break
            name = names[i % len(names)] + (f" {i}" if i >= len(names) else "")

            # Logic: Assign questions to the first few bots with staggered start minutes
            q_to_ask = questions[i] if i < len(questions) else None
            start_minute = 10 + (i * 3)  # Starts at 10m, 13m, 16m...

            p = Process(target=launch_attendee, args=(url, name, self.status_dict, q_to_ask, start_minute))
            p.start()
            self.processes.append(p)
            time.sleep(random.randint(6, 12))  # Anti-detection stagger

        while datetime.now() < end_time and self.is_running:
            rem = (end_time - datetime.now())
            self.status_label.config(text=f"LIVE: {rem.seconds // 60}m {rem.seconds % 60}s left")
            time.sleep(1)

        self.kill_all()


if __name__ == "__main__":
    root = tk.Tk()
    app = WebinarBotGUI(root)
    root.mainloop()