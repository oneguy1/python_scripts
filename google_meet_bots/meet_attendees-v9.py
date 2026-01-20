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
        status_dict[name] = "Connecting..."
        driver.get(meet_url)
        wait = WebDriverWait(driver, 30)

        # 1. HANDLE RECORDING CONSENT (The "Join now" wall)
        try:
            recording_xpath = "//span[contains(text(), 'Join now') or contains(text(), 'הצטרפות כעת') or contains(text(), 'Got it')]"
            consent_btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, recording_xpath)))
            consent_btn.click()
            time.sleep(2)
        except:
            pass  # No recording notice, proceed

        # 2. JOIN LOGIC
        status_dict[name] = "Entering Name..."
        name_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='text' or @placeholder='Your name' or @placeholder='השם שלך']")))
        name_input.clear()
        for char in name:
            name_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

        join_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(text(), 'Ask to join') or contains(text(), 'בקשת הצטרפות')]")))
        join_btn.click()

        status_dict[name] = "Active ✅"

        # 3. RANDOMIZED Q&A
        if question:
            total_wait = (min_wait * 60) + random.randint(10, 180)
            time.sleep(total_wait)
            try:
                status_dict[name] = "Posting Q..."
                wait.until(EC.element_to_be_clickable((By.XPATH,
                                                       "//button[contains(@aria-label, 'Activities') or contains(@aria-label, 'פעילויות')]"))).click()
                wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(), 'Q&A') or contains(text(), 'שאלות ותשובות')]"))).click()
                wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(text(), 'Ask a question') or contains(text(), 'לשאול שאלה')]"))).click()
                text_area = wait.until(EC.presence_of_element_located((By.TAG_NAME, "textarea")))
                text_area.send_keys(question)
                driver.find_element(By.XPATH, "//span[contains(text(), 'Post') or contains(text(), 'פרסום')]").click()
                status_dict[name] = "Q Posted ✅"
            except:
                status_dict[name] = "Q&A Failed"

        while True: time.sleep(1)
    except Exception:
        status_dict[name] = "Error/Closed"
    finally:
        driver.quit()


# --- GUI CLASS ---
class WebinarBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("D30 Professional Webinar Dashboard")
        self.root.geometry("700x850")

        self.manager = Manager()
        self.status_dict = self.manager.dict()
        self.processes = []
        self.is_running = False

        # Input Frame
        frm = tk.LabelFrame(root, text="Configuration", padx=10, pady=10)
        frm.pack(fill="x", padx=20, pady=10)

        tk.Label(frm, text="Meet URL:").grid(row=0, column=0, sticky="e")
        self.url_entry = tk.Entry(frm, width=50);
        self.url_entry.grid(row=0, column=1, pady=2)

        tk.Label(frm, text="Bot Count:").grid(row=1, column=0, sticky="e")
        self.count_entry = tk.Entry(frm, width=10);
        self.count_entry.insert(0, "20");
        self.count_entry.grid(row=1, column=1, sticky="w")

        tk.Label(frm, text="Start Time:").grid(row=2, column=0, sticky="e")
        self.time_entry = tk.Entry(frm, width=10);
        self.time_entry.insert(0, "18:00");
        self.time_entry.grid(row=2, column=1, sticky="w")

        tk.Label(frm, text="Duration (m):").grid(row=3, column=0, sticky="e")
        self.dur_entry = tk.Entry(frm, width=10);
        self.dur_entry.insert(0, "60");
        self.dur_entry.grid(row=3, column=1, sticky="w")

        # Custom Names & Questions
        txt_frm = tk.Frame(root)
        txt_frm.pack(fill="both", expand=True, padx=20)

        tk.Label(txt_frm, text="Custom Attendee Names (one per line):").pack(anchor="w")
        self.name_text = tk.Text(txt_frm, height=5, width=40)
        self.name_text.pack(fill="x", pady=5)

        tk.Label(txt_frm, text="Seeded Questions (one per line):").pack(anchor="w")
        self.q_text = tk.Text(txt_frm, height=5, width=40)
        self.q_text.pack(fill="x", pady=5)

        # Control
        btn_frm = tk.Frame(root)
        btn_frm.pack(pady=10)
        self.start_btn = tk.Button(btn_frm, text="Schedule & Start", command=self.start_thread, bg="#27ae60",
                                   fg="white", width=20, font=("Arial", 10, "bold"))
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = tk.Button(btn_frm, text="EMERGENCY STOP", command=self.kill_all, bg="#c0392b", fg="white",
                                  width=20, font=("Arial", 10, "bold"))
        self.stop_btn.pack(side="left", padx=5)

        self.status_label = tk.Label(root, text="STATUS: IDLE", font=("Arial", 12, "bold"))
        self.status_label.pack()

        # Table
        self.tree = ttk.Treeview(root, columns=("Name", "Status"), show='headings')
        self.tree.heading("Name", text="Attendee Name");
        self.tree.heading("Status", text="Status")
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

    def kill_all(self):
        self.is_running = False
        for p in self.processes: p.terminate()
        os.system("pkill -f chrome")
        messagebox.showwarning("System Kill", "All browser instances terminated.")

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

        # Parse inputs
        custom_names = [n for n in self.name_text.get("1.0", "end-1c").split("\n") if n.strip()]
        questions = [q for q in self.q_text.get("1.0", "end-1c").split("\n") if q.strip()]
        preset_names = ["James W.", "Maria G.", "Robert C.", "Sarah S.", "David M.", "Linda T.", "Kevin A.", "Elena R.",
                        "Tom H.", "S. Gupta"]

        while datetime.now().strftime("%H:%M") != target_time:
            if not self.is_running: return
            self.status_label.config(text=f"WAITING FOR {target_time}...")
            time.sleep(5)

        self.status_label.config(text="🚀 RUNNING...")
        end_time = datetime.now() + timedelta(minutes=duration)

        for i in range(count):
            if not self.is_running: break
            # Select name: Use custom first, then preset
            if i < len(custom_names):
                name = custom_names[i]
            else:
                name = preset_names[i % len(preset_names)] + (f" {i}" if i >= len(preset_names) else "")

            q_to_ask = questions[i] if i < len(questions) else None
            p = Process(target=launch_attendee, args=(url, name, self.status_dict, q_to_ask, 10 + (i * 2)))
            p.start()
            self.processes.append(p)
            time.sleep(random.randint(7, 15))

        while datetime.now() < end_time and self.is_running:
            rem = (end_time - datetime.now())
            self.status_label.config(text=f"LIVE | Time Remaining: {rem.seconds // 60}m {rem.seconds % 60}s")
            time.sleep(1)
        self.kill_all()


if __name__ == "__main__":
    root = tk.Tk();
    app = WebinarBotGUI(root);
    root.mainloop()