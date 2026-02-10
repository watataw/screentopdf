import os
import time
import threading
import pyautogui
from PIL import Image
import customtkinter as ctk
from tkinter import messagebox
from pynput import mouse

# ==========================
# CONFIGURATION
# ==========================
DEFAULT_DELAY = 3
DEFAULT_OUTPUT_FOLDER = "screenshots"
DEFAULT_PDF_NAME = "output.pdf"
# ==========================

running = False
counter = 1

region = None
click_point = None

setup_mode = None
setup_points = []

mouse_listener = None


def png_to_pdf(input_folder, output_pdf):
    """
    Convert all PNG files in input_folder to a single PDF.
    Returns (success, message)
    """
    files = sorted([f for f in os.listdir(input_folder) if f.lower().endswith(".png")])
    if not files:
        return False, "No PNG files found."

    images = []
    for f in files:
        path = os.path.join(input_folder, f)
        img = Image.open(path).convert("RGB")
        images.append(img)

    first = images[0]
    rest = images[1:]
    first.save(output_pdf, save_all=True, append_images=rest)

    return True, f"PDF created: {output_pdf}"


def delete_png_files(folder):
    """
    Delete all PNG files in the specified folder.
    Returns count of deleted files.
    """
    deleted = 0
    for f in os.listdir(folder):
        if f.lower().endswith(".png"):
            try:
                os.remove(os.path.join(folder, f))
                deleted += 1
            except Exception:
                pass
    return deleted


def screenshot_loop(folder, delay, max_shots, focus_callback, progress_callback, stop_callback):
    """
    Main screenshot loop - takes screenshots and performs clicks at regular intervals.
    """
    global running, counter

    os.makedirs(folder, exist_ok=True)

    while running:
        if max_shots > 0 and counter > max_shots:
            running = False
            stop_callback("Maximum reached")
            break

        filename = os.path.join(folder, f"screenshot_{counter:05d}.png")

        img = pyautogui.screenshot(region=region)
        img.save(filename)

        pyautogui.click(click_point[0], click_point[1])

        # Refocus GUI
        focus_callback()

        progress_callback(counter, filename)

        counter += 1
        time.sleep(delay)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AutoScreenshot Pro")
        self.geometry("860x760")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Variables
        self.folder = ctk.StringVar(value=DEFAULT_OUTPUT_FOLDER)
        self.delay = ctk.IntVar(value=DEFAULT_DELAY)
        self.max_shots = ctk.IntVar(value=0)
        self.pdf_name = ctk.StringVar(value=DEFAULT_PDF_NAME)
        self.delete_after_pdf = ctk.BooleanVar(value=False)

        self.status = ctk.StringVar(value="Ready.")
        self.last_file = ctk.StringVar(value="No files yet.")
        self.setup_status_text = ctk.StringVar(value="Setup: Not completed")

        self.grid_columnconfigure(0, weight=1)

        # Title
        title = ctk.CTkLabel(self, text="📸 AutoScreenshot Pro", font=("Arial", 28, "bold"))
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # SETTINGS FRAME
        settings_frame = ctk.CTkFrame(self, corner_radius=15)
        settings_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(settings_frame, text="Output folder:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        ctk.CTkEntry(settings_frame, textvariable=self.folder).grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(settings_frame, text="Delay (seconds):").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        ctk.CTkEntry(settings_frame, textvariable=self.delay).grid(row=1, column=1, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(settings_frame, text="Max screenshots (0 = infinite):").grid(row=2, column=0, padx=15, pady=10, sticky="w")
        ctk.CTkEntry(settings_frame, textvariable=self.max_shots).grid(row=2, column=1, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(settings_frame, text="PDF name:").grid(row=3, column=0, padx=15, pady=10, sticky="w")
        ctk.CTkEntry(settings_frame, textvariable=self.pdf_name).grid(row=3, column=1, padx=15, pady=10, sticky="ew")

        self.delete_checkbox = ctk.CTkCheckBox(
            settings_frame,
            text="Delete PNG screenshots after creating PDF",
            variable=self.delete_after_pdf
        )
        self.delete_checkbox.grid(row=4, column=0, columnspan=2, padx=15, pady=(5, 15), sticky="w")

        # SETUP FRAME
        setup_frame = ctk.CTkFrame(self, corner_radius=15)
        setup_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        setup_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(setup_frame, text="Setup", font=("Arial", 18, "bold")).grid(
            row=0, column=0, padx=15, pady=10, sticky="w"
        )

        self.setup_label = ctk.CTkLabel(setup_frame, textvariable=self.setup_status_text, font=("Arial", 13))
        self.setup_label.grid(row=0, column=1, padx=15, pady=10, sticky="w")

        self.btn_zone = ctk.CTkButton(setup_frame, text="📌 Select screenshot area", command=self.start_zone_setup)
        self.btn_zone.grid(row=1, column=0, padx=15, pady=10, sticky="ew")

        self.btn_click = ctk.CTkButton(setup_frame, text="🖱️ Select click point", command=self.start_click_setup)
        self.btn_click.grid(row=1, column=1, padx=15, pady=10, sticky="ew")

        self.btn_reset = ctk.CTkButton(setup_frame, text="♻ Reset points", command=self.reset_points, fg_color="gray")
        self.btn_reset.grid(row=1, column=2, padx=15, pady=10, sticky="ew")

        # PROGRESS FRAME
        progress_frame = ctk.CTkFrame(self, corner_radius=15)
        progress_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(progress_frame, text="Progress", font=("Arial", 18, "bold")).grid(
            row=0, column=0, padx=15, pady=(10, 5), sticky="w"
        )

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=15, pady=10, sticky="ew")
        self.progress_bar.set(0)

        self.count_label = ctk.CTkLabel(progress_frame, text="Screenshots: 0", font=("Arial", 14))
        self.count_label.grid(row=2, column=0, padx=15, pady=5, sticky="w")

        self.last_label = ctk.CTkLabel(progress_frame, textvariable=self.last_file, font=("Arial", 12))
        self.last_label.grid(row=3, column=0, padx=15, pady=5, sticky="w")

        # START/STOP FRAME
        control_frame = ctk.CTkFrame(self, corner_radius=15)
        control_frame.grid(row=4, column=0, padx=20, pady=(10, 15), sticky="ew")
        control_frame.grid_columnconfigure((0, 1), weight=1)

        self.start_btn = ctk.CTkButton(control_frame, text="▶ Start", command=self.start, fg_color="green")
        self.start_btn.grid(row=0, column=0, padx=15, pady=15, sticky="ew")

        self.stop_btn = ctk.CTkButton(control_frame, text="⛔ Stop (Enter)", command=self.stop_manual, fg_color="red", state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=15, pady=15, sticky="ew")

        self.status_label = ctk.CTkLabel(self, textvariable=self.status, font=("Arial", 14))
        self.status_label.grid(row=5, column=0, padx=20, pady=(0, 15), sticky="w")

        # Bind Enter key to stop
        self.bind("<Return>", lambda e: self.stop_manual())

        self.update_setup_status()

    def update_setup_status(self):
        """Update the setup status display based on current configuration."""
        global region, click_point

        if region and click_point:
            self.setup_status_text.set(f"OK | Area={region} | Click={click_point}")
        elif region and not click_point:
            self.setup_status_text.set(f"Area OK | Click point not selected")
        elif not region and click_point:
            self.setup_status_text.set(f"Click OK | Area not selected")
        else:
            self.setup_status_text.set("Setup: Not completed")

    def reset_points(self):
        """Reset all setup points to their default state."""
        global region, click_point, setup_mode, setup_points
        region = None
        click_point = None
        setup_mode = None
        setup_points = []
        self.update_setup_status()
        self.status.set("Points reset.")

    def start_mouse_listener(self):
        """Start the mouse listener for setup mode."""
        global mouse_listener

        if mouse_listener is not None:
            return

        def on_click(x, y, button, pressed):
            global setup_mode, setup_points, region, click_point

            if not pressed:
                return

            if setup_mode is None:
                return

            if setup_mode == "zone":
                setup_points.append((x, y))

                if len(setup_points) == 1:
                    self.after(0, lambda: self.status.set(f"Area: Point 1 recorded ({x},{y}). Click point 2."))
                elif len(setup_points) == 2:
                    p1 = setup_points[0]
                    p2 = setup_points[1]

                    left = min(p1[0], p2[0])
                    top = min(p1[1], p2[1])
                    width = abs(p2[0] - p1[0])
                    height = abs(p2[1] - p1[1])

                    region = (left, top, width, height)

                    setup_mode = None
                    setup_points = []

                    def done():
                        self.update_setup_status()
                        self.status.set("Screenshot area saved.")
                        messagebox.showinfo("Area OK", f"Selected area:\n{region}")

                    self.after(0, done)

            elif setup_mode == "click":
                click_point = (x, y)
                setup_mode = None

                def done():
                    self.update_setup_status()
                    self.status.set("Click point saved.")
                    messagebox.showinfo("Click OK", f"Click point:\n{click_point}")

                self.after(0, done)

        mouse_listener = mouse.Listener(on_click=on_click)
        mouse_listener.daemon = True
        mouse_listener.start()

    def start_zone_setup(self):
        """Start the screenshot area selection process."""
        global setup_mode, setup_points
        self.start_mouse_listener()

        setup_mode = "zone"
        setup_points = []
        self.status.set("Area setup: click top-left corner, then bottom-right corner.")
        messagebox.showinfo("Area Setup", "Click the TOP-LEFT then BOTTOM-RIGHT corners (anywhere on screen).")

    def start_click_setup(self):
        """Start the click point selection process."""
        global setup_mode
        self.start_mouse_listener()

        setup_mode = "click"
        self.status.set("Click setup: click on the desired click point.")
        messagebox.showinfo("Click Setup", "Click on the point where you want to click (anywhere on screen).")

    def focus_gui(self):
        """Bring the GUI window to the foreground."""
        try:
            self.after(0, self.lift)
            self.after(0, self.focus_force)
        except Exception:
            pass

    def progress_callback(self, count, filename):
        """Update progress display with current count and filename."""
        self.count_label.configure(text=f"Screenshots: {count}")
        self.last_file.set(f"Last file: {filename}")

        try:
            max_shots = int(self.max_shots.get())
        except ValueError:
            max_shots = 0

        if max_shots > 0:
            self.progress_bar.set(min(count / max_shots, 1.0))
        else:
            self.progress_bar.set((count % 100) / 100)

    def stop_callback_auto(self, reason):
        """Callback for automatic stopping."""
        self.after(0, lambda: self.stop_after_loop(reason))

    def stop_after_loop(self, reason):
        """Handle post-loop cleanup after automatic stop."""
        self.status.set(f"Stopped automatically ({reason}).")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

        self.btn_zone.configure(state="normal")
        self.btn_click.configure(state="normal")
        self.btn_reset.configure(state="normal")

        self.ask_pdf_export()

    def start(self):
        """Start the screenshot automation process."""
        global running, counter

        if region is None or click_point is None:
            messagebox.showwarning("Setup Required", "Please select both the screenshot area AND click point before starting.")
            return

        try:
            delay = int(self.delay.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid delay value.")
            return

        try:
            max_shots = int(self.max_shots.get())
            if max_shots < 0:
                max_shots = 0
        except ValueError:
            messagebox.showerror("Error", "Invalid max screenshots value.")
            return

        folder = self.folder.get().strip()
        if folder == "":
            messagebox.showerror("Error", "Invalid folder name.")
            return

        counter = 1
        running = True

        self.status.set("Running... (Press Enter to stop)")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        self.btn_zone.configure(state="disabled")
        self.btn_click.configure(state="disabled")
        self.btn_reset.configure(state="disabled")

        def thread_target():
            screenshot_loop(
                folder=folder,
                delay=delay,
                max_shots=max_shots,
                focus_callback=self.focus_gui,
                progress_callback=lambda c, f: self.after(0, lambda: self.progress_callback(c, f)),
                stop_callback=self.stop_callback_auto
            )

        threading.Thread(target=thread_target, daemon=True).start()

    def stop_manual(self):
        """Manually stop the screenshot automation process."""
        global running

        if not running:
            return

        running = False

        self.status.set("Stopped manually.")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

        self.btn_zone.configure(state="normal")
        self.btn_click.configure(state="normal")
        self.btn_reset.configure(state="normal")

        self.ask_pdf_export()

    def ask_pdf_export(self):
        """Ask user if they want to convert screenshots to PDF."""
        folder = self.folder.get().strip()
        pdf_name = self.pdf_name.get().strip()

        if pdf_name == "":
            pdf_name = DEFAULT_PDF_NAME

        if not pdf_name.lower().endswith(".pdf"):
            pdf_name += ".pdf"

        output_pdf = os.path.join(folder, pdf_name)

        if messagebox.askyesno("PDF Conversion", f"Do you want to convert screenshots to PDF?\n\nName: {pdf_name}"):
            success, msg = png_to_pdf(folder, output_pdf)

            if success:
                messagebox.showinfo("PDF", msg)

                if self.delete_after_pdf.get():
                    deleted = delete_png_files(folder)
                    messagebox.showinfo("Cleanup", f"{deleted} PNG files deleted.")
            else:
                messagebox.showerror("PDF", msg)


if __name__ == "__main__":
    pyautogui.FAILSAFE = True

    app = App()
    app.mainloop()
