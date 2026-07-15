"""
CityHire Fleet & Stock Intelligence - synthetic data generator.

Product names/categories are grounded in the real public category structure
and product listings on cityhire.co.uk (plant/tool hire). All quantities,
serial numbers, costs, dates, utilisation, and transaction data below are
SYNTHETIC - generated for a portfolio/demo project, not real business data.
"""
import random
import string
import sqlite3
from datetime import date, timedelta
from pathlib import Path
import csv

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

TODAY = date(2026, 7, 15)
HISTORY_DAYS = 365  # 12 months of daily stats

# ---------------------------------------------------------------------------
# Real category -> subcategory -> product data scraped from cityhire.co.uk
# ---------------------------------------------------------------------------
CATALOG = {
    "Plant": {
        "Excavators": ["Micro Excavator 0.8t", "5 Ton Excavator", "Mini Excavator 1.7t",
                        "13 Ton Excavator", "Micro Excavator 1t", "Hydraulic Breaker Excavator Attachment",
                        "3 Ton Excavator", "8 Ton Excavator", "20 Ton Excavator"],
        "Trailers": ["Plant Trailer"],
        "Dumpers": ["3 Ton Straight Dumper", "6 Ton Straight Dumper", "1t Skip Loading Dumper",
                     "550kg Tracked Dumper"],
        "Telehandlers": ["4m Telehandler", "14m Telehandler", "17m Telehandler",
                          "10.5m Telehandler", "6m Telehandler"],
        "Vibrating Rollers": ["1200mm Roller", "Pedestrian Roller", "800mm Roller"],
        "Concrete Crushers": ["Red Rhino 4000 Mini Concrete Crusher", "Forst TR6D Tracked Wood Chipper"],
    },
    "Powered Access": {
        "Slab Scissor Lifts": ["12m Electric Scissor Lift", "5m Electric Scissor Lift",
                                "10m Electric Scissor Lift", "8m Electric Scissor Lift", "16m Electric Scissor Lift"],
        "Low Level Access": ["Eco Lift", "Nano", "Snorkel S3010P 5m Scissor Lift", "Peco Lift"],
        "Cherry Pickers": ["40m Articulating Boom Lift", "Nifty Lift HR21 20.8m Hybrid Boom Lift",
                            "17.5m Articulating Boom Lift", "Nifty Lift HR17 17m Hybrid Boom Lift",
                            "24m Articulating Boom Lift", "Nifty Lift HR12 12.2m Bi Fuel Boom Lift",
                            "Nifty Lift HR15 15.5m Hybrid Boom Lift", "Nifty Lift HR28 28m Hybrid Boom Lift",
                            "13.5m Electric Boom Lift", "16m Articulating Boom Lift", "18m Articulating Boom Lift"],
        "Rough Terrain Scissor Lifts": ["12m Rough Terrain Scissor Lift", "10m Rough Terrain Scissor Lift",
                                         "14.5m Rough Terrain Scissor Lift", "17m Rough Terrain Scissor Lift"],
        "Mast Booms": ["Skyjack SJ12 5.5m Vertical Mast", "Skyjack SJ16 6.6m Vertical Mast", "10m Vertical Mast"],
        "Spider Booms": ["15.4m Tracked Spider Boom", "26m Tracked Spider Boom",
                          "17m Tracked Spider Boom", "20m Tracked Spider Boom"],
        "Van & Truck Mounted Booms": ["Truck Mount Boom Lift"],
    },
    "Breakers & Drills": {
        "Drilling": ["Cordless Drill", "Hilti TE 60-ATC-AVR Rotary Hammer Drill",
                      "Hilti Nuron TE 6-22 Cordless Hammer Drill - 22V", "Cordless SDS Max Rotary Hammer Drill",
                      "Heavy Duty Rotary Hammer Drill SDS Max", "Angle Drill", "Heavy Duty Multi Drill",
                      "Rotary Hammer Drill", "Hilti TE 30-AVR Rotary Hammer Drill",
                      "36V Cordless Rotary Hammer Drill", "18V Cordless Rotary Hammer Drill"],
        "Pneumatic Breakers": ["Soil Pick", "Pole Scabbler", "Hand Scabbler", "Heavy Air Breaker",
                                "Light Air Breaker", "Medium Air Breaker"],
        "Core Drills": ["Heavy Duty Diamond Core Drill", "Hilti DD110 Diamond Core Drill",
                         "Dry Diamond Core Drill", "Medium Diamond Core Drill"],
        "Breaking": ["Hilti TE 3000-AVR Heavy Breaker", "110V Makita Heavy Breaker", "110V Makita Medium Breaker",
                      "Medium Breaker (Hilti TE-1000)", "Hydraulic Breaker", "Darda Concrete Splitter",
                      "Hilti TE 2000 AVR Medium Breaker", "Petrol Heavy Breaker", "Light Breaker/Chiseller",
                      "Hilti TE 700-AVR Medium Breaker"],
        "Magnetic Drills": ["Magnetic Drill", "Magnetic Compact Drill"],
    },
    "Material Handling & Logistics": {
        "Trucks & Trolleys": ["Heavy Duty Plasterboard Trolley - Loadall", "Flatbed Turntable Truck",
                               "Pipe Rack Trolley", "Dolly Truck", "Powered Stair Climber", "Glass Trolley",
                               "Beam Kart", "Sack Truck", "Loadall Plasterboard Trolley", "Pipe Trolley", "Panel Trolley"],
        "Pallet Trucks": ["2T Electric Pallet Truck", "2.5T Pallet Truck", "Long Reach Pallet Truck",
                           "Rough Terrain Pallet Truck", "1.8t Semi-Electric Pallet Truck",
                           "Electric Rough Terrain Pallet Truck"],
        "Conveyors": ["Conveyor Belt", "Bumpa Hoist"],
        "Skips": ["Boat Skip", "Hoist Tipping Skip", "Auto-Lock Forklift Tipping Skip", "Forklift Tipping Skip"],
        "Bins": ["Site Waste Bin - 4 wheel", "Wheelie Bin", "Rubble Truck Site Waste Bin"],
        "Steel Strapping": ["Steel Strapping Unit"],
    },
    "Lifting Equipment": {
        "Materials Lifts": ["Plasterboard Installer - Combi", "Genie Super Hoist Gas Lift", "Beam Lifter",
                             "Genie SLK Counterbalanced Materials Lift", "Genie SLA Materials Lift", "Roustabout Lift"],
        "Hoists": ["Gantry Hoist Set", "Tractel TR50 Minifor Hoist", "Beam Hoist", "Scaffold Hoist"],
        "Gantrys": ["2T Portable Gantry", "Portable Gantry"],
        "Chain Blocks": ["Electric Chain Hoist", "Manual Chain Block"],
        "Forklift Trucks": ["Counterbalance Forklift"],
        "Forklift Attachments": ["Forklift Hook Attachment", "Powerbrush Sweeper Attachment", "Fork Truck Extensions"],
        "Grabs": ["Block Grab", "Kerb & Slab Layer"],
        "Winches": ["Tirfor Rope Winch"],
    },
    "Accommodation, Storage & Welfare": {
        "Welfare Units": ["6-8 man Welfare Unit (12ft)", "12-16 Man Welfare Unit (20ft)", "10-12 Man Welfare Unit (16ft)"],
        "Storage": ["Personnel Locker", "Foldable Gas Cage", "Chemical Store - ChemBank", "City Shed - Collapsible Site Unit",
                     "FittingStor Storage Cabinet", "Battery Bank Charging Locker", "Secure Site Box",
                     "Chemical Store - FlamBank"],
        "Water & Sanitation": ["IBC Water Tank", "Single Mains Toilet", "Chemical Toilet (Serviced)"],
    },
    "Cutting & Grinding": {
        "Disc Cutters": ["Petrol Disc Cutter", "Electric Disc Cutter"],
        "Cutting Stations": ["Acoustic Tent", "Armorgard SS7 Cutting Station", "Armorgard SS7X Cutting Station"],
        "Plunge Saws": ["Plunge Rail Saw"],
        "Floor Saws": ["Floor Saw"],
        "Masonry & Tile Saws": ["Masonry Saw Bench (14 inch) - Radial Arm", "Masonry Saw Bench (18 inch)",
                                 "Masonry Saw Bench (14 inch)", "Diamond Tile Saw"],
        "Wallsaws": ["Arbortech AS170 Allsaw"],
        "Reciprocating Saws": ["Makita Reciprocating Saw", "Hilti Reciprocating Saw", "Cordless Reciprocating Saw"],
        "Wall Chasers": ["Hilti Wall Chaser", "Makita Wall Chaser"],
        "Chop Saws": ["Metal Cutting Chop Saw", "Mitre Saw Stand", "Abrasive Chop Saw", "Compound Mitre Saw"],
        "Circular Saws": ["Cordless Circular Saw", "Electric Circular Saw"],
        "Angle Grinders": ["Electric Angle Grinder", "18V Cordless Angle Grinder"],
    },
    # Remaining categories extrapolated (name-plausible, same catalog structure) to
    # cover City Hire's full 24-category range without full manual scraping of each.
    "Access": {"Towers": ["3T Aluminium Tower - 4.2m", "3T Aluminium Tower - 6.2m", "Podium Steps", "Folding Trestle"]},
    "Cleaning": {"Vacuums & Sweepers": ["Hilti VC Wet & Dry Vacuum", "Ride-On Sweeper", "Pressure Washer 150 Bar", "Industrial Wet Vac"]},
    "Sanding & Woodworking": {"Sanders & Planers": ["Floor Sander - Belt", "Edging Sander", "Makita Planer", "Biscuit Jointer"]},
    "Landscaping & Gardening": {"Turf & Ground Care": ["Turf Cutter", "Rotavator", "Stump Grinder", "Hedge Trimmer Long Reach"]},
    "Mechanical & Electrical": {"Test & Install": ["Cable Detector", "Pipe Freezing Kit", "Threading Machine"]},
    "Painting & Decorating": {"Sprayers": ["Airless Paint Sprayer", "Wallpaper Steamer", "Floor Prep Grinder"]},
    "Consumables": {"Site Consumables": ["Diamond Blade 350mm", "SDS Drill Bit Set", "Fixing Screws Box"]},
    "Climate Control": {"Heating & Drying": ["Indirect Diesel Heater 85kW", "Dehumidifier 50L", "Industrial Fan 24in"]},
    "Safety, Ventilation & Extraction": {"Extraction": ["Air Mover", "Ventilation Fan 12in", "Dust Extractor M-Class"]},
    "Propping & Support": {"Support": ["Acrow Prop Size 3", "Strongboy Support", "Trench Strut"]},
    "Lighting": {"Site Lighting": ["LED Tower Light", "Festoon Lighting Kit", "Balloon Light 1000W"]},
    "Fencing & Barriers": {"Fencing": ["Heras Fence Panel", "Pedestrian Barrier", "Water Filled Barrier"]},
    "Fixing & Fastening": {"Fixing Tools": ["Cartridge Fixing Gun", "Rivet Gun", "Staple Gun Pneumatic"]},
    "Concreting & Compaction": {"Compaction": ["Plate Compactor 90kg", "Trench Rammer", "Concrete Mixer 110V", "Poker Vibrator"]},
    "Fuel & Gas": {"Fuel & Gas": ["Diesel Bowser 900L", "Propane Cylinder 47kg", "Fuel Transfer Pump"]},
    "Survey & Location": {"Survey": ["Rotary Laser Level", "CAT & Genny Locator", "Total Station"]},
    "Site Equipment & Groundworks": {"Groundworks": ["Whacker Plate", "Road Plate 2.4m", "Trench Box"]},
    "Power & Electrics": {"Generators & Distribution": ["Generator 6kVA Silent", "Generator 20kVA", "Transformer 5kVA 110V", "Cable Reel 25m"]},
}

DEPOTS = ["London North", "London South", "Birmingham", "Manchester", "Bristol", "Leeds"]
CONDITIONS = ["Excellent", "Good", "Fair", "Needs Assessment"]
BRANDS_BY_KEYWORD = {"Hilti": "Hilti", "Makita": "Makita", "Genie": "Genie", "Nifty Lift": "Niftylift",
                      "Skyjack": "Skyjack", "Tractel": "Tractel", "Armorgard": "Armorgard", "Arbortech": "Arbortech"}

CATEGORY_CAPEX_BAND = {
    "Plant": (8000, 65000), "Powered Access": (9000, 85000), "Lifting Equipment": (1200, 18000),
    "Material Handling & Logistics": (300, 6000), "Breakers & Drills": (250, 5500),
    "Accommodation, Storage & Welfare": (1500, 12000), "Cutting & Grinding": (200, 4500),
    "Access": (400, 3500), "Cleaning": (150, 4000), "Sanding & Woodworking": (200, 2500),
    "Landscaping & Gardening": (300, 6000), "Mechanical & Electrical": (250, 5000),
    "Painting & Decorating": (150, 2500), "Consumables": (5, 150), "Climate Control": (600, 9000),
    "Safety, Ventilation & Extraction": (300, 4000), "Propping & Support": (80, 900),
    "Lighting": (200, 2200), "Fencing & Barriers": (60, 400), "Fixing & Fastening": (150, 1800),
    "Concreting & Compaction": (500, 7000), "Fuel & Gas": (400, 12000), "Survey & Location": (600, 9000),
    "Site Equipment & Groundworks": (200, 3500), "Power & Electrics": (600, 15000),
}


def brand_of(name: str) -> str:
    for kw, brand in BRANDS_BY_KEYWORD.items():
        if kw.lower() in name.lower():
            return brand
    return "City Hire Fleet"


def gen_stock_code(category: str, idx: int) -> str:
    prefix = "".join(w[0] for w in category.split()[:3]).upper()[:3]
    return f"{prefix}-{idx:05d}"


# ---------------------------------------------------------------------------
# 1) STOCK MASTER
# ---------------------------------------------------------------------------
stock_master = []
sale_codes = []
idx = 1000
for category, subcats in CATALOG.items():
    lo, hi = CATEGORY_CAPEX_BAND.get(category, (200, 5000))
    for subcat, products in subcats.items():
        for product in products:
            # number of physical units of this asset type in the fleet
            units = random.randint(2, 14) if lo < 2000 else random.randint(1, 6)
            for u in range(units):
                idx += 1
                code = gen_stock_code(category, idx)
                purchase_offset = random.randint(30, 1825)  # up to 5 years old
                purchase_date = TODAY - timedelta(days=purchase_offset)
                capex = round(random.uniform(lo, hi), 2)
                age_years = purchase_offset / 365
                depreciation_rate = 0.20  # straight-line-ish, 20%/yr, floor at 10% of capex
                book_value = round(max(capex * (1 - depreciation_rate * age_years), capex * 0.10), 2)
                utilisation = round(min(max(random.gauss(63, 14), 8), 98), 1)
                status_roll = random.random()
                if status_roll < 0.62:
                    status = "On Hire"
                elif status_roll < 0.80:
                    status = "Available"
                elif status_roll < 0.93:
                    status = "Workshop"
                else:
                    status = "Auction Pending"
                last_service_offset = random.randint(1, 220)
                stock_master.append({
                    "stock_code": code,
                    "category": category,
                    "subcategory": subcat,
                    "product_name": product,
                    "brand": brand_of(product),
                    "depot": random.choice(DEPOTS),
                    "purchase_date": purchase_date.isoformat(),
                    "capex_gbp": capex,
                    "book_value_gbp": book_value,
                    "age_years": round(age_years, 2),
                    "condition": random.choices(CONDITIONS, weights=[35, 40, 18, 7])[0],
                    "status": status,
                    "utilisation_pct_ytd": utilisation,
                    "day_rate_gbp": round(capex * random.uniform(0.008, 0.018), 2),
                    "last_service_date": (TODAY - timedelta(days=last_service_offset)).isoformat(),
                    "next_service_due": (TODAY - timedelta(days=last_service_offset) + timedelta(days=180)).isoformat(),
                    "min_stock_level": max(1, units // 4),
                    "current_units_at_depot": 1,
                })

print(f"Stock master rows: {len(stock_master)}")

# ---------------------------------------------------------------------------
# 2) SALE / PARTS / HIRE CODE REGISTER  (JD: creation of stock/parts/sale codes)
# ---------------------------------------------------------------------------
code_types = ["Hire Stock Code", "Parts Code", "Sale Code"]
for i, row in enumerate(random.sample(stock_master, 120)):
    sale_codes.append({
        "code_id": f"SC-{2000+i}",
        "linked_stock_code": row["stock_code"],
        "code_type": random.choices(code_types, weights=[55, 30, 15])[0],
        "created_date": (TODAY - timedelta(days=random.randint(1, 400))).isoformat(),
        "created_by": random.choice(["A. Apollis", "Ops Team", "System Auto"]),
        "status": random.choices(["Active", "Pending Review", "Archived"], weights=[80, 12, 8])[0],
    })

# ---------------------------------------------------------------------------
# 3) DAILY STOCK STATS  (JD: daily stock stats, fleeting, utilisation)
# ---------------------------------------------------------------------------
daily_stats = []
categories = list(CATALOG.keys())
for d in range(HISTORY_DAYS, -1, -1):
    day = TODAY - timedelta(days=d)
    for depot in DEPOTS:
        for category in categories:
            fleet_units = sum(1 for r in stock_master if r["category"] == category and r["depot"] == depot)
            if fleet_units == 0:
                continue
            seasonal = 1 + 0.15 * (1 if day.month in (4, 5, 6, 7, 8, 9) else -0.5)  # summer construction bump
            base_util = min(max(random.gauss(60 * seasonal / 1.05, 10), 5), 99)
            on_hire = round(fleet_units * base_util / 100)
            # workshop % improvement trend: was ~22% a year ago, driven down toward the
            # 15% target (JD 6-12 month success point) through better preventative
            # maintenance scheduling and external repair turnaround.
            workshop_target_start, workshop_target_end = 0.23, 0.11
            workshop_frac = workshop_target_end + (workshop_target_start - workshop_target_end) * (d / HISTORY_DAYS)
            workshop_frac = min(max(workshop_frac + random.uniform(-0.03, 0.03), 0.03), 0.32)
            workshop = round(fleet_units * workshop_frac)
            available = max(fleet_units - on_hire - workshop, 0)
            daily_stats.append({
                "date": day.isoformat(),
                "depot": depot,
                "category": category,
                "fleet_units": fleet_units,
                "units_on_hire": on_hire,
                "units_in_workshop": workshop,
                "units_available": available,
                "utilisation_pct": round(on_hire / fleet_units * 100, 1) if fleet_units else 0,
                "workshop_pct": round(workshop / fleet_units * 100, 1) if fleet_units else 0,
            })

print(f"Daily stats rows: {len(daily_stats)}")

# ---------------------------------------------------------------------------
# 4) EXTERNAL REPAIRS  (JD: external repairs, approval of external repairs)
# ---------------------------------------------------------------------------
repair_suppliers = ["Speedy Fleet Services", "Vp Plant Repairs", "AFI Technical", "Independent Hydraulics Ltd",
                     "National Plant Repair Co", "Southern Access Engineering"]
external_repairs = []
for i, row in enumerate(random.sample(stock_master, 90)):
    cost = round(random.uniform(80, 4200), 2)
    logged = TODAY - timedelta(days=random.randint(1, 300))
    external_repairs.append({
        "repair_id": f"REP-{3000+i}",
        "stock_code": row["stock_code"],
        "category": row["category"],
        "supplier": random.choice(repair_suppliers),
        "fault_reported": random.choice(["Hydraulic leak", "Engine fault", "Electrical fault",
                                          "Structural damage", "Battery/charging fault", "Wear & tear service",
                                          "Safety recall check", "Tyre/track replacement"]),
        "date_logged": logged.isoformat(),
        "cost_gbp": cost,
        "requires_approval": cost >= 500,
        "approval_status": (random.choices(["Approved", "Pending", "Rejected"], weights=[75, 15, 10])[0]
                             if cost >= 500 else "Not Required"),
        "approved_by": ("National Ops & Systems Manager" if cost >= 500 else ""),
        "days_out_of_service": random.randint(1, 21),
    })

# ---------------------------------------------------------------------------
# 5) AUCTION & PARTS APPROVALS >£500  (JD: auction & parts approvals)
# ---------------------------------------------------------------------------
approvals = []
for i, row in enumerate([r for r in stock_master if r["status"] == "Auction Pending"] +
                         random.sample(stock_master, 40)):
    value = round(random.uniform(500, 22000), 2)
    req_type = "Auction Disposal" if row["status"] == "Auction Pending" else random.choice(
        ["Parts Purchase", "Auction Disposal", "Capital Replacement"])
    approvals.append({
        "approval_id": f"APR-{4000+i}",
        "stock_code": row["stock_code"],
        "category": row["category"],
        "request_type": req_type,
        "value_gbp": value,
        "requested_date": (TODAY - timedelta(days=random.randint(1, 250))).isoformat(),
        "status": random.choices(["Approved", "Pending", "Rejected"], weights=[68, 22, 10])[0],
        "requested_by": random.choice(["Depot Manager - London North", "Depot Manager - Birmingham",
                                        "Depot Manager - Manchester", "Workshop Controller"]),
    })

# ---------------------------------------------------------------------------
# 6) CAPEX MONTHLY SPEND vs BUDGET  (JD: capex spends not exceeding budget)
# ---------------------------------------------------------------------------
capex_monthly = []
months = []
d = date(TODAY.year - 1, TODAY.month, 1)
while d <= TODAY.replace(day=1):
    months.append(d)
    d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)

# A handful of categories run structurally hot on capex (real-world pattern: high
# breakdown/attrition asset classes or categories mid capital refresh cycle).
overspend_categories = {"Powered Access", "Plant", "Survey & Location"}

for category in categories:
    lo, hi = CATEGORY_CAPEX_BAND.get(category, (200, 5000))
    monthly_budget = round((lo + hi) / 2 * random.uniform(1.5, 4), 2)
    for m in months:
        if category in overspend_categories:
            spend_mult = random.uniform(0.85, 1.35)
        else:
            spend_mult = random.uniform(0.55, 1.18)
        spend = round(monthly_budget * spend_mult, 2)
        capex_monthly.append({
            "month": m.isoformat(),
            "category": category,
            "budget_gbp": monthly_budget,
            "actual_spend_gbp": spend,
            "variance_gbp": round(monthly_budget - spend, 2),
            "over_budget": spend > monthly_budget,
        })

# ---------------------------------------------------------------------------
# 7) STOCK SHORTAGE BALANCING  (JD: stock shortage balancing between depots)
# ---------------------------------------------------------------------------
shortages = []
for i in range(150):
    category = random.choice(categories)
    from_depot, to_depot = random.sample(DEPOTS, 2)
    shortages.append({
        "transfer_id": f"XFER-{5000+i}",
        "date": (TODAY - timedelta(days=random.randint(1, 300))).isoformat(),
        "category": category,
        "from_depot": from_depot,
        "to_depot": to_depot,
        "units_transferred": random.randint(1, 4),
        "reason": random.choice(["Shortage cover", "Rebalance to demand", "Emergency same-day request",
                                  "Planned redistribution"]),
        "fulfilled": random.random() > 0.08,
    })

# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------
def write_csv(name, rows):
    if not rows:
        return
    path = RAW / f"{name}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path} ({len(rows)} rows)")


write_csv("stock_master", stock_master)
write_csv("sale_codes", sale_codes)
write_csv("daily_stock_stats", daily_stats)
write_csv("external_repairs", external_repairs)
write_csv("approvals", approvals)
write_csv("capex_monthly", capex_monthly)
write_csv("stock_transfers", shortages)

# ---------------------------------------------------------------------------
# Build SQLite DB for SQL analysis layer
# ---------------------------------------------------------------------------
db_path = PROC / "cityhire_fleet.db"
if db_path.exists():
    db_path.unlink()
conn = sqlite3.connect(db_path)
cur = conn.cursor()

def load_table(name, rows):
    if not rows:
        return
    cols = list(rows[0].keys())
    col_defs = ", ".join(f'"{c}"' for c in cols)
    cur.execute(f'CREATE TABLE "{name}" ({col_defs})')
    placeholders = ", ".join("?" for _ in cols)
    cur.executemany(f'INSERT INTO "{name}" VALUES ({placeholders})',
                     [tuple(r[c] for c in cols) for r in rows])

load_table("stock_master", stock_master)
load_table("sale_codes", sale_codes)
load_table("daily_stock_stats", daily_stats)
load_table("external_repairs", external_repairs)
load_table("approvals", approvals)
load_table("capex_monthly", capex_monthly)
load_table("stock_transfers", shortages)
conn.commit()
conn.close()
print(f"SQLite DB written: {db_path}")
