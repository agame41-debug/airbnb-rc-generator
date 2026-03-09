#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Airbnb RC XML Generator pro Money S3
Generuje interni doklady (priznani + odpocet RC) z Airbnb CSV exportu.

Kurz EUR/CZK se automaticky stahuje z CNB (posledni pracovni den).
Struktura dokladu:
  - SouhrnDPH  -> castky v CZK  (zaklad x kurz)
  - <Valuty>   -> castky v EUR  + kurz CNB
  - DatUplDPH  -> posledni den predchoziho mesice

Pouziti:
    python generate_airbnb_rc.py <csv> <prvni_cislo_dokladu>
    python generate_airbnb_rc.py <csv> <cislo> <kurz>    # rucni kurz, napr. 25.15
"""

import csv
import re
import sys
import os
import urllib.request
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timedelta


# ── Konfigurace ────────────────────────────────────────────────────────────
HOSPROK_OD = "2026-01-01"
HOSPROK_DO = "2026-12-31"
IC_AGENDY  = "19088094"
OBCH_NAZEV = "Airbnb Ireland UC"
ULICE      = "South Lotts Road"
MISTO      = "Dublin 4"
PSC        = "Ringsend"
STAT       = "Ireland"
KOD_STATU  = "IE"
DIC        = "IE9827384L"
VYST       = "Nikita S."
D_RADA     = "IDFrr"
SSAZBA     = "12"
ZSAZBA     = "21"
VAT_RATE   = 0.21
# ──────────────────────────────────────────────────────────────────────────


def get_eur_rate_cnb() -> float:
    """Stahne kurz EUR/CZK z CNB XML API."""
    url = ("https://www.cnb.cz/cs/financni_trhy/devizovy_trh/"
           "kurzy_devizoveho_trhu/denni_kurz.xml")
    print(f"  Stahuji kurz CNB: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        # <kurzy><tabulka><radek mena="EUR" mnozstvi="1" kurz="25,150" .../>
        for radek in root.iter("radek"):
            if radek.get("mena") == "EUR":
                rate = float(radek.get("kurz", "").replace(",", "."))
                print(f"  Kurz CNB EUR/CZK: {rate}")
                return rate
        raise ValueError("EUR nenalezeno v odpovedi CNB")
    except Exception as e:
        raise RuntimeError(
            f"Nepodarilo se stahnout kurz CNB: {e}\n"
            "Zadejte kurz rucne jako treti argument, napr: 25.15"
        ) from e


def last_day_of_prev_month() -> str:
    first_of_this = datetime.today().replace(day=1)
    return (first_of_this - timedelta(days=1)).strftime("%Y-%m-%d")


def extract_invoice_number(raw: str) -> str:
    m = re.search(r'AIUC-[^\s",)]+', raw)
    return m.group(0) if m else raw.strip()


def build_intdokl(doklad_id, popis, pr_kont, cleneni,
                  date_str, dat_upl_dph, prijat_dokl,
                  zaklad_eur, kurz):
    zaklad_czk = round(zaklad_eur * kurz, 2)
    dph_czk    = round(zaklad_czk * VAT_RATE, 2)
    celkem_czk = round(zaklad_czk + dph_czk, 2)
    dph_eur    = round(zaklad_eur * VAT_RATE, 2)
    celkem_eur = round(zaklad_eur + dph_eur, 2)

    el = Element("IntDokl")
    SubElement(el, "Doklad").text     = doklad_id
    SubElement(el, "Popis").text      = popis
    SubElement(el, "DatUcPr").text    = date_str
    SubElement(el, "DatPln").text     = date_str
    SubElement(el, "DatUplDPH").text  = dat_upl_dph
    SubElement(el, "CisloZapoc").text = "0"
    SubElement(el, "PrijatDokl").text = prijat_dokl

    adresa = SubElement(el, "Adresa")
    SubElement(adresa, "ObchNazev").text = OBCH_NAZEV
    obch = SubElement(adresa, "ObchAdresa")
    SubElement(obch, "Ulice").text    = ULICE
    SubElement(obch, "Misto").text    = MISTO
    SubElement(obch, "PSC").text      = PSC
    SubElement(obch, "Stat").text     = STAT
    SubElement(obch, "KodStatu").text = KOD_STATU
    SubElement(adresa, "DIC").text       = DIC
    SubElement(adresa, "PlatceDPH").text = "1"
    SubElement(adresa, "FyzOsoba").text  = "0"

    SubElement(el, "PrKont").text   = pr_kont
    SubElement(el, "Cleneni").text  = cleneni
    SubElement(el, "ZpVypDPH").text = "1"
    SubElement(el, "SSazba").text   = SSAZBA
    SubElement(el, "ZSazba").text   = ZSAZBA

    # SouhrnDPH v CZK (hlavni)
    s = SubElement(el, "SouhrnDPH")
    SubElement(s, "Zaklad0").text  = "0"
    SubElement(s, "Zaklad5").text  = "0"
    SubElement(s, "Zaklad22").text = f"{zaklad_czk:.2f}"
    SubElement(s, "DPH5").text     = "0"
    SubElement(s, "DPH22").text    = f"{dph_czk:.2f}"
    SubElement(el, "Celkem").text  = f"{celkem_czk:.2f}"

    # Valuty – EUR + kurz CNB
    valuty = SubElement(el, "Valuty")
    mena = SubElement(valuty, "Mena")
    SubElement(mena, "Kod").text      = "EUR"
    SubElement(mena, "Mnozstvi").text = "1"
    SubElement(mena, "Kurs").text     = f"{kurz:.2f}"
    sv = SubElement(valuty, "SouhrnDPH")
    SubElement(sv, "Zaklad0").text  = "0"
    SubElement(sv, "Zaklad5").text  = "0"
    SubElement(sv, "Zaklad22").text = f"{zaklad_eur:.2f}"
    SubElement(sv, "DPH5").text     = "0"
    SubElement(sv, "DPH22").text    = f"{dph_eur:.2f}"
    SubElement(valuty, "Celkem").text = f"{celkem_eur:.2f}"

    SubElement(el, "DRada").text   = D_RADA
    SubElement(el, "Vyst").text    = VYST
    SubElement(el, "Rezim").text   = "0"
    SubElement(el, "TypDokl").text = "RCH"
    return el


def prettify(element):
    rough = tostring(element, encoding="unicode")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ", encoding=None)


def generate_xml(csv_path, first_doc_num, output_path,
                 kurz_override=None, limit=None):
    dat_upl_dph = last_day_of_prev_month()
    print(f"DatUplDPH: {dat_upl_dph}")

    kurz = kurz_override if kurz_override else get_eur_rate_cnb()
    print(f"Kurz EUR/CZK: {kurz:.2f}")

    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            raw_invoice = row.get("\u010c\u00edslo faktury", "").strip()
            raw_date    = row.get("Datum poskytnut\u00ed slu\u017eby", "").strip()
            raw_amount  = row.get("\u010cist\u00e1 \u010d\u00e1stka", "0").strip()

            try:
                amount = float(raw_amount)
            except ValueError:
                print(f"  [SKIP {i}] nelze prevest: {raw_amount!r}")
                continue
            if amount == 0.0:
                print(f"  [SKIP {i}] nulova castka – {raw_invoice[:40]}")
                continue

            invoice = extract_invoice_number(raw_invoice)
            if not invoice:
                print(f"  [SKIP {i}] prazdne cislo faktury")
                continue

            try:
                date_str = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                print(f"  [SKIP {i}] neznamy format data: {raw_date!r}")
                continue

            rows.append({"invoice": invoice, "date": date_str, "zaklad": round(amount, 2)})

    print(f"\nNalezeno {len(rows)} faktur.")
    if limit:
        rows = rows[:limit]
        print(f"Omezeno na {limit} pro test.")

    year2 = HOSPROK_OD[2:4]
    root = Element("MoneyData")
    root.set("ICAgendy", IC_AGENDY); root.set("KodAgendy", "")
    root.set("HospRokOd", HOSPROK_OD); root.set("HospRokDo", HOSPROK_DO)
    root.set("description", "interni doklady")
    root.set("ExpZkratka", "_ID"); root.set("JazykVerze", "CZ")
    seznam = SubElement(root, "SeznamIntDokl")

    counter = first_doc_num
    for row in rows:
        id1 = f"IDF{year2}{counter:04d}"; counter += 1
        id2 = f"IDF{year2}{counter:04d}"; counter += 1

        seznam.append(build_intdokl(id1, "RC priznani", "REVCHU", "19Ř05,06",
                                    row["date"], dat_upl_dph, row["invoice"],
                                    row["zaklad"], kurz))
        seznam.append(build_intdokl(id2, "RC odpocet", "REVCHP", "19Ř43,44",
                                    row["date"], dat_upl_dph, row["invoice"],
                                    row["zaklad"], kurz))

        czk = round(row["zaklad"] * kurz, 2)
        dph = round(czk * VAT_RATE, 2)
        print(f"  ok {id1}/{id2}  {row['invoice']}  {row['date']}"
              f"  {row['zaklad']:.2f} EUR x {kurz:.2f} = {czk:.2f} CZK  DPH {dph:.2f} CZK")

    xml_str = prettify(root)
    xml_str = ('<?xml version="1.0" encoding="UTF-8"?>\n' +
               "\n".join(xml_str.splitlines()[1:]))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"\n OK {len(rows)*2} dokladu ({len(rows)} paru)  |  kurz {kurz:.2f}  |  {output_path}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)

    csv_file, first_num = sys.argv[1], int(sys.argv[2])
    manual_rate = float(sys.argv[3]) if len(sys.argv) == 4 else None

    if not os.path.isfile(csv_file):
        print(f"Soubor nenalezen: {csv_file!r}"); sys.exit(1)

    out = os.path.splitext(csv_file)[0] + "_RC.xml"
    generate_xml(csv_file, first_num, out, kurz_override=manual_rate)
