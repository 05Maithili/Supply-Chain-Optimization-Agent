"""
Database seed: realistic supply-chain sample data (1000+ sales records).
"""
import random
from datetime import date, timedelta, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import (
    Product, Warehouse, Supplier, SupplierProduct,
    Sale, Inventory, Customer, TransportRoute, Shipment
)


# ── Products ────────────────────────────────────────────────────────────────
PRODUCTS = [
    ("P101", "Industrial Motor Drive A1",  "Electronics",      1250.00),
    ("P102", "Hydraulic Pump HP-200",       "Machinery",         890.00),
    ("P103", "Control Panel CP-400",        "Electronics",       640.00),
    ("P104", "Steel Beam S-300",            "Raw Materials",     210.00),
    ("P105", "Conveyor Belt CB-150",        "Machinery",         430.00),
    ("P106", "Safety Valve SV-80",          "Components",         95.00),
    ("P107", "Bearing Assembly BA-12",      "Components",        145.00),
    ("P108", "Industrial Filter IF-500",    "Components",         78.00),
    ("P109", "Electric Motor EM-75",        "Electronics",       520.00),
    ("P110", "Pressure Gauge PG-30",        "Instruments",        62.00),
    ("P111", "Compressor Unit CU-600",      "Machinery",        3400.00),
    ("P112", "Heat Exchanger HX-90",        "Equipment",        1850.00),
]

# ── Warehouses ──────────────────────────────────────────────────────────────
WAREHOUSES = [
    ("W001", "North Regional Warehouse",  "Delhi, India",     28.7041, 77.1025, 50000),
    ("W002", "West Distribution Center",  "Mumbai, India",    19.0760, 72.8777, 40000),
    ("W003", "South Fulfillment Hub",     "Chennai, India",   13.0827, 80.2707, 35000),
]

# ── Suppliers ───────────────────────────────────────────────────────────────
SUPPLIERS = [
    ("S001", "PrecisionParts Ltd",      "India",   92.0, 88.0, 7,  10000, 3,  97.5),
    ("S002", "GlobalMach Corp",         "Germany", 88.0, 95.0, 14, 8000,  5,  95.0),
    ("S003", "FastTrack Components",    "China",   75.0, 72.0, 5,  20000, 12, 90.0),
    ("S004", "QualityFirst Industries", "USA",     90.0, 92.0, 21, 5000,  2,  98.0),
    ("S005", "EcoSupply Networks",      "India",   85.0, 80.0, 10, 15000, 6,  93.0),
]


async def seed_all(session: AsyncSession):
    random.seed(42)

    # ── Products ─────────────────────────────────────────────────────────────
    products = []
    for pid, name, cat, price in PRODUCTS:
        p = Product(
            product_id=pid, product_name=name, category=cat,
            unit_price=price, sku=f"SKU-{pid}"
        )
        session.add(p)
        products.append(pid)

    # ── Warehouses ────────────────────────────────────────────────────────────
    warehouses = []
    for wid, name, loc, lat, lon, cap in WAREHOUSES:
        w = Warehouse(
            warehouse_id=wid, warehouse_name=name, location=loc,
            latitude=lat, longitude=lon, capacity=cap,
            current_utilization=random.uniform(40, 80)
        )
        session.add(w)
        warehouses.append(wid)

    # ── Suppliers ─────────────────────────────────────────────────────────────
    for sid, name, country, rel, qual, lt, cap, delays, fulfill in SUPPLIERS:
        s = Supplier(
            supplier_id=sid, supplier_name=name, country=country,
            reliability=rel, quality_score=qual, lead_time_days=lt,
            capacity=cap, historical_delays=delays, order_fulfillment_rate=fulfill
        )
        session.add(s)

    await session.flush()

    # ── Supplier-Product mappings ─────────────────────────────────────────────
    costs = {
        "P101": {"S001": 950, "S002": 1100, "S004": 1050},
        "P102": {"S001": 680, "S003": 590, "S005": 720},
        "P103": {"S001": 490, "S002": 550, "S004": 510},
        "P104": {"S003": 155, "S005": 168, "S001": 175},
        "P105": {"S001": 320, "S005": 310, "S003": 280},
        "P106": {"S003": 68,  "S005": 72,  "S001": 78},
        "P107": {"S001": 105, "S003": 95,  "S002": 115},
        "P108": {"S003": 55,  "S005": 60,  "S001": 65},
        "P109": {"S001": 390, "S002": 440, "S004": 420},
        "P110": {"S003": 42,  "S005": 46,  "S001": 50},
        "P111": {"S002": 2800,"S004": 3000,"S001": 2950},
        "P112": {"S002": 1450,"S004": 1550,"S001": 1500},
    }
    for pid, supplier_costs in costs.items():
        for sid, cost in supplier_costs.items():
            sp = SupplierProduct(
                supplier_id=sid, product_id=pid, unit_cost=cost,
                min_order_quantity=random.randint(5, 20)
            )
            session.add(sp)

    # ── Customers ─────────────────────────────────────────────────────────────
    cities = [
        ("C001", "Alpha Manufacturing", "Pune, India",      18.5204, 73.8567, "Enterprise"),
        ("C002", "Beta Industries",     "Hyderabad, India", 17.3850, 78.4867, "Enterprise"),
        ("C003", "Gamma Retail Group",  "Bangalore, India", 12.9716, 77.5946, "SMB"),
        ("C004", "Delta Logistics",     "Kolkata, India",   22.5726, 88.3639, "Enterprise"),
        ("C005", "Epsilon Corp",        "Ahmedabad, India", 23.0225, 72.5714, "SMB"),
    ]
    for cid, name, loc, lat, lon, seg in cities:
        session.add(Customer(
            customer_id=cid, customer_name=name, location=loc,
            latitude=lat, longitude=lon, segment=seg
        ))

    # ── Transport Routes ─────────────────────────────────────────────────────
    routes = [
        ("R001", "W001", "Pune, India",       1400, 18.5, 3, "Road",  "SpeedEx Carriers"),
        ("R002", "W001", "Hyderabad, India",  1500, 19.0, 4, "Road",  "BlueDart Logistics"),
        ("R003", "W001", "Kolkata, India",    1500, 20.0, 3, "Rail",  "Indian Rail Freight"),
        ("R004", "W002", "Bangalore, India",   980, 14.0, 2, "Road",  "SpeedEx Carriers"),
        ("R005", "W002", "Ahmedabad, India",   530, 10.0, 2, "Road",  "BlueDart Logistics"),
        ("R006", "W002", "Pune, India",        190,  5.5, 1, "Road",  "Local Freight Co"),
        ("R007", "W003", "Bangalore, India",   350,  7.0, 1, "Road",  "Southern Carriers"),
        ("R008", "W003", "Hyderabad, India",   630, 11.0, 2, "Road",  "BlueDart Logistics"),
        ("R009", "W001", "Ahmedabad, India",   940, 15.0, 2, "Road",  "SpeedEx Carriers"),
        ("R010", "W002", "Hyderabad, India",  1400, 18.0, 3, "Road",  "SpeedEx Carriers"),
    ]
    for rid, wid, dest, dist, cost, tt, mode, carrier in routes:
        session.add(TransportRoute(
            route_id=rid, origin_warehouse_id=wid, destination=dest,
            distance_km=dist, base_cost_per_unit=cost, transit_time_days=tt,
            transport_mode=mode, carrier=carrier
        ))

    await session.flush()

    # ── Historical Sales (1200 records, 18 months) ────────────────────────────
    end_date = date.today()
    start_date = end_date - timedelta(days=540)

    # Base demand per product (units/day across all warehouses)
    base_demand = {
        "P101": 3, "P102": 5, "P103": 7, "P104": 20, "P105": 6,
        "P106": 15, "P107": 12, "P108": 18, "P109": 8, "P110": 25,
        "P111": 2, "P112": 2,
    }
    # Price at time of sale (close to product price)
    price_map = dict(zip(
        [p[0] for p in PRODUCTS], [p[3] for p in PRODUCTS]
    ))

    sale_records = []
    current = start_date
    sale_id_counter = 0
    while current <= end_date:
        for pid in products:
            for wid in warehouses:
                base = base_demand[pid]
                # Seasonal factor (higher in Q4)
                month = current.month
                seasonal = 1.0 + 0.3 * ((month in [10, 11, 12]) - (month in [6, 7]))
                # Trend factor (slight upward)
                trend = 1.0 + 0.0003 * (current - start_date).days
                # Random noise
                noise = random.gauss(1.0, 0.25)
                qty = max(0, int(base * seasonal * trend * noise))
                if qty == 0 and random.random() > 0.3:
                    continue
                price = price_map[pid] * random.uniform(0.95, 1.05)
                sale_records.append(Sale(
                    product_id=pid,
                    warehouse_id=wid,
                    sale_date=current,
                    quantity_sold=qty,
                    unit_price=round(price, 2),
                    total_revenue=round(qty * price, 2),
                    customer_id=random.choice(["C001", "C002", "C003", "C004", "C005"]),
                ))
                sale_id_counter += 1
        current += timedelta(days=1)

    for s in sale_records:
        session.add(s)

    # ── Inventory Records ─────────────────────────────────────────────────────
    stock_levels = {
        "P101": {"W001": 85,  "W002": 60,  "W003": 45},
        "P102": {"W001": 320, "W002": 180, "W003": 95},  # P102 at risk
        "P103": {"W001": 240, "W002": 310, "W003": 120},
        "P104": {"W001": 800, "W002": 500, "W003": 650},
        "P105": {"W001": 110, "W002": 95,  "W003": 75},
        "P106": {"W001": 450, "W002": 380, "W003": 280},
        "P107": {"W001": 360, "W002": 420, "W003": 180},
        "P108": {"W001": 540, "W002": 320, "W003": 410},
        "P109": {"W001": 95,  "W002": 65,  "W003": 40},  # P109 at risk
        "P110": {"W001": 750, "W002": 620, "W003": 480},
        "P111": {"W001": 12,  "W002": 8,   "W003": 5},   # P111 critical
        "P112": {"W001": 18,  "W002": 14,  "W003": 9},
    }
    safety_stocks = {
        "P101": 30, "P102": 100, "P103": 80, "P104": 200,
        "P105": 40, "P106": 120, "P107": 100, "P108": 150,
        "P109": 50, "P110": 200, "P111": 5, "P112": 6,
    }
    reorder_points = {
        "P101": 60, "P102": 200, "P103": 160, "P104": 350,
        "P105": 80, "P106": 200, "P107": 175, "P108": 250,
        "P109": 90, "P110": 320, "P111": 8, "P112": 10,
    }
    for pid in products:
        for wid in warehouses:
            session.add(Inventory(
                product_id=pid,
                warehouse_id=wid,
                current_stock=stock_levels.get(pid, {}).get(wid, random.randint(50, 500)),
                safety_stock=safety_stocks.get(pid, 50),
                reorder_point=reorder_points.get(pid, 100),
                max_stock=stock_levels.get(pid, {}).get(wid, 500) * 3,
            ))

    # ── Shipments ─────────────────────────────────────────────────────────────
    statuses = ["Pending", "In Transit", "Delivered", "Delayed"]
    today = date.today()
    for i in range(30):
        pid = random.choice(products)
        wid = random.choice(warehouses)
        dest_city = random.choice(["Pune, India", "Hyderabad, India", "Bangalore, India",
                                   "Kolkata, India", "Ahmedabad, India"])
        ship_offset = random.randint(-10, 2)
        deliver_offset = ship_offset + random.randint(1, 5)
        status = random.choice(statuses)
        session.add(Shipment(
            shipment_id=f"SHP-{i+1:03d}",
            product_id=pid,
            warehouse_id=wid,
            destination=dest_city,
            quantity=random.randint(10, 200),
            status=status,
            ship_date=today + timedelta(days=ship_offset),
            estimated_delivery=today + timedelta(days=deliver_offset),
            transportation_cost=round(random.uniform(500, 8000), 2),
        ))

    await session.commit()
