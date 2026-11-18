import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.environ.get("TELEMETRY_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "telemetry.db"))

def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS meters (
            meter_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            utility TEXT NOT NULL,
            role TEXT,
            name TEXT NOT NULL,
            config_name TEXT,
            meter_type TEXT,
            supports_hourly INTEGER DEFAULT 0,
            unit TEXT DEFAULT 'kWh',
            note TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS readings (
            meter_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            resolution TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            is_estimated INTEGER DEFAULT 0,
            created_at TEXT,
            PRIMARY KEY(meter_id, timestamp, resolution)
        );

        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            claim_number TEXT,
            location TEXT,
            period TEXT,
            issued_date TEXT,
            due_date TEXT,
            amount_isk REAL,
            is_paid INTEGER DEFAULT 1,
            pdf_url TEXT,
            updated_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_readings_query 
        ON readings(meter_id, resolution, timestamp);

        CREATE INDEX IF NOT EXISTS idx_invoices_due 
        ON invoices(due_date DESC);
        """)
        conn.commit()

def save_meter(meter: Dict[str, Any]):
    init_db()
    with get_connection() as conn:
        conn.execute("""
        INSERT OR REPLACE INTO meters (
            meter_id, provider, utility, role, name, config_name, meter_type, supports_hourly, unit, note, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(meter.get("meter_number") or meter.get("meter_id")),
            meter.get("provider", ""),
            meter.get("utility", ""),
            meter.get("role", ""),
            meter.get("name", ""),
            meter.get("config_name", ""),
            meter.get("meter_type", ""),
            1 if meter.get("supports_hourly") else 0,
            meter.get("unit", "kWh"),
            meter.get("note", ""),
            datetime.now().isoformat()
        ))
        conn.commit()

def save_readings(meter_id: str, readings: List[Dict[str, Any]], resolution: str, unit: str = "kWh", is_estimated: bool = False):
    init_db()
    now_iso = datetime.now().isoformat()
    with get_connection() as conn:
        for r in readings:
            ts = r.get("timestamp") or r.get("date")
            val = r.get("kwh") if "kwh" in r else r.get("usage_value") if "usage_value" in r else r.get("value", 0.0)
            if ts is not None and val is not None:
                conn.execute("""
                INSERT OR REPLACE INTO readings (
                    meter_id, timestamp, resolution, value, unit, is_estimated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(meter_id),
                    str(ts),
                    resolution.lower(),
                    float(val),
                    unit,
                    1 if is_estimated else 0,
                    now_iso
                ))
        conn.commit()

def get_readings(meter_id: str, resolution: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db()
    query = "SELECT timestamp, value, unit, is_estimated FROM readings WHERE meter_id = ? AND resolution = ?"
    params = [str(meter_id), resolution.lower()]

    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)
    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date + "T23:59:59" if "T" not in end_date else end_date)

    query += " ORDER BY timestamp ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [
            {
                "timestamp": r["timestamp"],
                "value": round(r["value"], 3),
                "unit": r["unit"],
                "is_estimated": bool(r["is_estimated"])
            }
            for r in rows
        ]

def save_invoices(invoices: List[Dict[str, Any]]):
    init_db()
    now_iso = datetime.now().isoformat()
    with get_connection() as conn:
        for inv in invoices:
            inv_id = str(inv.get("invoice_id") or inv.get("id"))
            conn.execute("""
            INSERT OR REPLACE INTO invoices (
                invoice_id, provider, claim_number, location, period, issued_date, due_date, amount_isk, is_paid, pdf_url, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv_id,
                inv.get("provider", ""),
                inv.get("claim_number") or inv.get("claim"),
                inv.get("location", ""),
                inv.get("period", ""),
                inv.get("issued_date", ""),
                inv.get("due_date", ""),
                float(inv.get("amount_isk") or inv.get("amount_num") or inv.get("amount_incl_vat_isk") or 0.0),
                1 if inv.get("paid") or inv.get("is_paid") else 0,
                inv.get("pdf_url") or inv.get("url") or inv.get("invoice_url"),
                now_iso
            ))
        conn.commit()

def get_invoices_from_db(limit: int = 10, provider: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db()
    query = "SELECT * FROM invoices"
    params = []
    if provider and provider != "all":
        query += " WHERE lower(provider) = ?"
        params.append(provider.lower())

    query += " ORDER BY due_date DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [
            {
                "invoice_id": r["invoice_id"],
                "provider": r["provider"],
                "claim_number": r["claim_number"],
                "location": r["location"],
                "period": r["period"],
                "issued_date": r["issued_date"],
                "due_date": r["due_date"],
                "amount_isk": r["amount_isk"],
                "is_paid": bool(r["is_paid"]),
                "pdf_url": r["pdf_url"]
            }
            for r in rows
        ]

if __name__ == "__main__":
    init_db()
    print("Initialized database:", DB_PATH)
