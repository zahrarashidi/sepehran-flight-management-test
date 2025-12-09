import json
import sqlite3
import os
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Body
from pydantic import BaseModel, Field

# --- Configuration ---
JSON_FILENAME = "flights_sample.json"
TABLE_NAME = "flights"


# --- Database Helpers ---

def get_db_connection():
    """Establishes a connection to the in-memory SQLite database."""
    conn = sqlite3.connect("file::memory:?cache=shared", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


db_conn = None


def init_json_file():
    """Creates a dummy JSON file with flight data if it doesn't exist."""
    if not os.path.exists(JSON_FILENAME):
        dummy_data = [
            {
                "flight_id": 1,
                "flight_number": "SP1001",
                "origin": "JED",
                "destination": "JED",
                "departure_time": "2025-11-08T01:00:00",
                "arrival_time": "2025-11-08T01:57:00",
                "duration_minutes": 57,
                "aircraft_type": "A321",
                "seats_total": 150,
                "seats_available": 26,
                "status": "departed",
                "created_at": "2025-10-10T01:00:00",
                "updated_at": "2025-11-08T01:00:00",
                "process_id": "P-238"
            },
            {
                "flight_id": 2,
                "flight_number": "SP1002",
                "origin": "THR",
                "destination": "JED",
                "departure_time": "2025-11-05T18:00:00",
                "arrival_time": "2025-11-05T19:00:00",
                "duration_minutes": 60,
                "aircraft_type": "A321",
                "seats_total": 250,
                "seats_available": 6,
                "status": "departed",
                "created_at": "2025-10-13T18:00:00",
                "updated_at": "2025-11-02T18:00:00",
                "process_id": "P-215"
            }
        ]
        with open(JSON_FILENAME, "w") as f:
            json.dump(dummy_data, f, indent=4)


def load_json_to_sqlite():
    """Reads JSON and populates the SQLite table."""
    global db_conn
    db_conn = get_db_connection()
    cursor = db_conn.cursor()

    cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")

    # Updated Schema
    cursor.execute(f"""
        CREATE TABLE {TABLE_NAME} (
            flight_id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_number TEXT,
            origin TEXT,
            destination TEXT,
            departure_time TEXT,
            arrival_time TEXT,
            duration_minutes INTEGER,
            aircraft_type TEXT,
            seats_total INTEGER,
            seats_available INTEGER,
            status TEXT,
            created_at TEXT,
            updated_at TEXT,
            process_id TEXT
        )
    """)

    try:
        with open(JSON_FILENAME, "r") as f:
            data = json.load(f)

        if data:
            for item in data:
                cursor.execute(f"""
                    INSERT INTO {TABLE_NAME} 
                    (flight_id, flight_number, origin, destination, departure_time, arrival_time, 
                     duration_minutes, aircraft_type, seats_total, seats_available, status, 
                     created_at, updated_at, process_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get("flight_id"), item.get("flight_number"), item.get("origin"),
                    item.get("destination"), item.get("departure_time"), item.get("arrival_time"),
                    item.get("duration_minutes"), item.get("aircraft_type"), item.get("seats_total"),
                    item.get("seats_available"), item.get("status"), item.get("created_at"),
                    item.get("updated_at"), item.get("process_id")
                ))
            db_conn.commit()
            print(f"Loaded {len(data)} flights from JSON to SQLite.")
    except Exception as e:
        print(f"Error loading JSON: {e}")


def save_sqlite_to_json():
    """Dumps the current SQLite table back to the JSON file."""
    global db_conn
    cursor = db_conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_NAME}")
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]

    with open(JSON_FILENAME, "w") as f:
        json.dump(data, f, indent=4)


# --- Pydantic Models ---

class FlightBase(BaseModel):
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    aircraft_type: str
    seats_total: int
    seats_available: int
    status: str
    process_id: str


class FlightCreate(FlightBase):
    pass  # ID and Timestamps are handled by the system


class FlightUpdate(BaseModel):
    # All fields optional for update
    flight_number: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    aircraft_type: Optional[str] = None
    seats_total: Optional[int] = None
    seats_available: Optional[int] = None
    status: Optional[str] = None
    process_id: Optional[str] = None


# --- FastAPI Lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_json_file()
    load_json_to_sqlite()
    yield
    if db_conn:
        db_conn.close()


app = FastAPI(lifespan=lifespan)


# --- Routes ---

@app.get("/flights")
def get_flights(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        sort_by: str = Query("flight_id"),
        sort_order: str = Query("asc", regex="^(asc|desc)$"),
        columns: str = Query("*"),
        filter_field: Optional[str] = Query(None),
        filter_value: Optional[str] = Query(None)
):
    cursor = db_conn.cursor()

    # 1. Allowed Columns Safelist
    allowed_columns = {
        "flight_id", "flight_number", "origin", "destination", "departure_time",
        "arrival_time", "duration_minutes", "aircraft_type", "seats_total",
        "seats_available", "status", "created_at", "updated_at", "process_id"
    }

    # 2. Column Selection
    selected_columns = columns.split(",")
    if columns != "*":
        for col in selected_columns:
            if col.strip() not in allowed_columns:
                raise HTTPException(status_code=400, detail=f"Invalid column: {col}")
        select_clause = ",".join(selected_columns)
    else:
        select_clause = "*"

    if sort_by not in allowed_columns:
        raise HTTPException(status_code=400, detail="Invalid sort column")

    # 3. Build Query
    query = f"SELECT {select_clause} FROM {TABLE_NAME}"
    params = []

    if filter_field and filter_value:
        if filter_field not in allowed_columns:
            raise HTTPException(status_code=400, detail="Invalid filter field")
        # Use LIKE for string fields, exact match for numbers/IDs might be better depending on use case
        # keeping LIKE for flexibility
        query += f" WHERE {filter_field} LIKE ?"
        params.append(f"%{filter_value}%")

    query += f" ORDER BY {sort_by} {sort_order.upper()}"

    offset = (page - 1) * per_page
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/flights")
def add_flight(flight: FlightCreate):
    cursor = db_conn.cursor()

    # Auto-generate timestamps
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (
                flight_number, origin, destination, departure_time, arrival_time, 
                duration_minutes, aircraft_type, seats_total, seats_available, 
                status, created_at, updated_at, process_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            flight.flight_number, flight.origin, flight.destination, flight.departure_time,
            flight.arrival_time, flight.duration_minutes, flight.aircraft_type,
            flight.seats_total, flight.seats_available, flight.status,
            current_time, current_time, flight.process_id
        ))

        db_conn.commit()
        new_id = cursor.lastrowid
        save_sqlite_to_json()

        return {
            "flight_id": new_id,
            **flight.dict(),
            "created_at": current_time,
            "updated_at": current_time,
            "message": "Flight created"
        }
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/flights/{flight_id}")
def update_flight(flight_id: int, flight: FlightUpdate):
    cursor = db_conn.cursor()

    cursor.execute(f"SELECT flight_id FROM {TABLE_NAME} WHERE flight_id = ?", (flight_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Flight not found")

    fields = flight.dict(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Auto-update 'updated_at'
    fields['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    set_clause = ", ".join([f"{key} = ?" for key in fields.keys()])
    values = list(fields.values())
    values.append(flight_id)

    try:
        cursor.execute(f"UPDATE {TABLE_NAME} SET {set_clause} WHERE flight_id = ?", values)
        db_conn.commit()
        save_sqlite_to_json()
        return {"message": "Flight updated", "updated_fields": fields}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/flights/{flight_id}")
def delete_flight(flight_id: int):
    cursor = db_conn.cursor()

    cursor.execute(f"SELECT flight_id FROM {TABLE_NAME} WHERE flight_id = ?", (flight_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Flight not found")

    try:
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE flight_id = ?", (flight_id,))
        db_conn.commit()
        save_sqlite_to_json()
        return {"message": "Flight deleted"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)