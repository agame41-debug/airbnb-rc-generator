#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Airbnb RC Generator - GUI dla Windows
Spustit: python airbnb_rc_gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os
import io

# Pridame adresar skriptu do cesty, aby slo importovat generate_airbnb_rc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_airbnb_rc import generate_xml, get_eur_rate_cnb


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Airbnb RC Generator pro Money S3")
        self.resizable(False, False)
        self.configure(padx=18, pady=14, bg="#f0f0f0")

        # ── Barvy ──
        BG   = "#f0f0f0"
        CARD = "#ffffff"
        BLUE = "#0057a8"
        GREEN= "#1a7a1a"
        FONT = ("Segoe UI", 10)
        BOLD = ("Segoe UI", 10, "bold")

        # ── CSV soubor ──
        frm1 = tk.LabelFrame(self, text=" 1. CSV soubor ", bg=BG, font=BOLD, padx=8, pady=6)
        frm1.grid(row=0, column=0, sticky="ew", pady=(0,8))
        self.csv_var = tk.StringVar()
        tk.Entry(frm1, textvariable=self.csv_var, width=52, font=FONT).grid(row=0, column=0, padx=(0,6))
        tk.Button(frm1, text="Vybrat...", command=self.pick_csv,
                  bg=BLUE, fg="white", font=FONT, relief="flat",
                  padx=10).grid(row=0, column=1)

        # ── Nastaveni ──
        frm2 = tk.LabelFrame(self, text=" 2. Nastaveni ", bg=BG, font=BOLD, padx=8, pady=8)
        frm2.grid(row=1, column=0, sticky="ew", pady=(0,8))

        tk.Label(frm2, text="Prvni cislo dokladu:", bg=BG, font=FONT).grid(row=0, column=0, sticky="w")
        self.first_num_var = tk.StringVar(value="10")
        tk.Entry(frm2, textvariable=self.first_num_var, width=10, font=FONT).grid(row=0, column=1, sticky="w", padx=(6,24))

        tk.Label(frm2, text="Kurz EUR/CZK:", bg=BG, font=FONT).grid(row=0, column=2, sticky="w")
        self.kurz_var = tk.StringVar(value="")
        self.kurz_entry = tk.Entry(frm2, textvariable=self.kurz_var, width=10, font=FONT)
        self.kurz_entry.grid(row=0, column=3, sticky="w", padx=(6,6))
        self.cnb_btn = tk.Button(frm2, text="Stahnout z CNB", command=self.fetch_rate,
                                 bg="#e0e0e0", font=FONT, relief="flat", padx=8)
        self.cnb_btn.grid(row=0, column=4, padx=(4,0))

        # ── Log ──
        frm3 = tk.LabelFrame(self, text=" 3. Vystup ", bg=BG, font=BOLD, padx=8, pady=6)
        frm3.grid(row=2, column=0, sticky="ew", pady=(0,8))
        self.log = scrolledtext.ScrolledText(frm3, width=72, height=14,
                                             font=("Consolas", 9), state="disabled",
                                             bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self.log.grid(row=0, column=0)

        # ── Tlacitko ──
        self.gen_btn = tk.Button(self, text="  Generovat XML  ",
                                 command=self.run_generate,
                                 bg=GREEN, fg="white", font=("Segoe UI", 11, "bold"),
                                 relief="flat", padx=16, pady=8)
        self.gen_btn.grid(row=3, column=0, pady=(0,4))

    def pick_csv(self):
        path = filedialog.askopenfilename(
            title="Vyberte CSV soubor Airbnb",
            filetypes=[("CSV soubory", "*.csv"), ("Vsechny soubory", "*.*")]
        )
        if path:
            self.csv_var.set(path)

    def fetch_rate(self):
        self.log_write("Stahuji kurz CNB...\n")
        self.cnb_btn.config(state="disabled")
        def task():
            try:
                rate = get_eur_rate_cnb()
                self.kurz_var.set(f"{rate:.2f}")
                self.log_write(f"Kurz CNB: 1 EUR = {rate:.2f} CZK\n")
            except Exception as e:
                self.log_write(f"Chyba CNB: {e}\n")
                messagebox.showerror("Chyba", str(e))
            finally:
                self.cnb_btn.config(state="normal")
        threading.Thread(target=task, daemon=True).start()

    def run_generate(self):
        csv_path = self.csv_var.get().strip()
        if not csv_path or not os.path.isfile(csv_path):
            messagebox.showerror("Chyba", "Vyberte platny CSV soubor.")
            return
        try:
            first_num = int(self.first_num_var.get())
        except ValueError:
            messagebox.showerror("Chyba", "Prvni cislo dokladu musi byt cele cislo.")
            return
        kurz_str = self.kurz_var.get().strip()
        kurz = float(kurz_str.replace(",", ".")) if kurz_str else None
        if kurz is None:
            if not messagebox.askyesno("Kurz", "Kurz nezadan. Stahnout automaticky z CNB?"):
                return

        out_path = os.path.splitext(csv_path)[0] + "_RC.xml"
        self.gen_btn.config(state="disabled", text="  Generuji...  ")
        self.log_clear()

        def task():
            try:
                # Presmerujeme stdout do logu
                old_stdout = sys.stdout
                sys.stdout = LogCapture(self.log_write)
                generate_xml(csv_path, first_num, out_path, kurz_override=kurz)
                sys.stdout = old_stdout
                self.log_write(f"\nHotovo! Soubor: {out_path}\n")
                messagebox.showinfo("Hotovo", f"XML vygenerovano:\n{out_path}")
            except Exception as e:
                sys.stdout = old_stdout
                self.log_write(f"\nCHYBA: {e}\n")
                messagebox.showerror("Chyba", str(e))
            finally:
                self.gen_btn.config(state="normal", text="  Generovat XML  ")

        threading.Thread(target=task, daemon=True).start()

    def log_write(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def log_clear(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")


class LogCapture:
    def __init__(self, write_fn):
        self.write_fn = write_fn
    def write(self, text):
        if text:
            self.write_fn(text)
    def flush(self):
        pass


if __name__ == "__main__":
    app = App()
    app.mainloop()
