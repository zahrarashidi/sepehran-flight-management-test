# ✈️ Sepehran Flight Management Test
This FastAPI application provides a robust API for managing flight records. It leverages **raw SQL queries** against an in-memory SQLite database, with a JSON file (`flights_sample.json`) acting as the persistent storage layer.

The core goal is to demonstrate complex data operations (Pagination, Filtering, Sorting) using standard SQL commands while using a non-traditional backend store.

## ✨ Features

* **Zero Database Setup:** Uses a simple `flights_sample.json` file for persistence.
* **Direct SQL Queries:** **No ORM** (Object Relational Mapper). All data access is handled via raw SQLite SQL commands.
* **Advanced Reading (SQL-Powered):**
    * **Pagination:** Use `page` and `per_page` parameters (`LIMIT`/`OFFSET`).
    * **Sorting:** Sort by any column (e.g., `departure_time`) in ascending or descending order (`ORDER BY`).
    * **Filtering:** Use `filter_field` and `filter_value` to search (uses SQL `LIKE '%value%'`).
    * **Column Selection:** Fetch only specific fields (e.g., `'flight_number, status'`).
* **CRUD Operations:** Full Create, Read, Update, and Delete capabilities.
* **Time Tracking:** Automatically manages `created_at` and `updated_at` timestamps.

---

## 🛠️ Architecture: JSON Mirroring

The application uses an **In-Memory SQLite Mirroring** approach to provide high-speed SQL access on top of a JSON file:

1.  **Startup:** Reads `flights_sample.json` and loads all data into a temporary, in-memory SQLite table named `flights`.
2.  **Operations:** All API requests execute raw SQL against the memory table.
3.  **Persistence:** On any successful write operation (`POST`, `PUT`, `DELETE`), the application immediately dumps the entire state of the SQLite table back into `flights_sample.json`, ensuring persistence.

---

## 📦 Prerequisites & Installation

* **Python 3.8+**

1.  **Install dependencies:**
    ```bash
    pip install fastapi uvicorn pydantic
    ```

## 🏃‍♂️ Running the Application

1.  **Start the server:**
    ```bash
    python main.py
    ```
    *The server will start at `http://127.0.0.1:8000`.*
    *If `flights_sample.json` does not exist, the app will create it with dummy flight data.*

2.  **Access the Interactive Docs (Swagger UI):**
    Open your browser to: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🔌 API Usage Examples

The base URL is `http://127.0.0.1:8000`.

### 1. Reading Flights (GET) 📚

**Endpoint:** `GET /flights`

**Example: Filter, Sort, and Select Columns**

```bash
curl -X GET "[http://127.0.0.1:8000/flights?page=1&per_page=5&sort_by=departure_time&sort_order=desc&columns=flight_number,destination,status&filter_field=destination&filter_value=JFK](http://127.0.0.1:8000/flights?page=1&per_page=5&sort_by=departure_time&sort_order=desc&columns=flight_number,destination,status&filter_field=destination&filter_value=JFK)"
```
### 2. Adding a Flight (POST) ➕
Creates a new flight record. `flight_id`, `created_at`, and `updated_at` are generated automatically.

Endpoint: `POST /flights`

```bash
curl -X POST "[http://127.0.0.1:8000/flights](http://127.0.0.1:8000/flights)" \
     -H "Content-Type: application/json" \
     -d '{
    "flight_number": "LH9010",
    "origin": "FRA",
    "destination": "ATL",
    "departure_time": "2025-12-16 08:00:00",
    "arrival_time": "2025-12-16 12:00:00",
    "duration_minutes": 480,
    "aircraft_type": "Airbus A350",
    "seats_total": 280,
    "seats_available": 280,
    "status": "Scheduled",
    "process_id": "proc_lh_atlantic"
}'
```
### 3. Changing/Updating a Flight (PUT) 🔄
Modifies an existing flight record using its `flight_id`. Only fields included in the JSON body are changed. The updated_at timestamp is automatically refreshed.

Endpoint: `PUT /flights/{flight_id}` (Example uses `flight_id` 1)

Example: Change Status and Seat Availability

```bash
curl -X PUT "[http://127.0.0.1:8000/flights/1](http://127.0.0.1:8000/flights/1)" \
     -H "Content-Type: application/json" \
     -d '{
    "status": "Boarding",
    "seats_available": 105
}'
```

### 4. Deleting a Flight (DELETE) 🗑️
Permanently removes a flight record by its `flight_id`.

Endpoint: `DELETE /flights/{flight_id}` (Example deletes `flight_id` 2)

```bash
curl -X DELETE "[http://127.0.0.1:8000/flights/2](http://127.0.0.1:8000/flights/2)"
```
### ⚠️ Notes
* **Concurrency:** This application is primarily for demonstration. Since every write operation overwrites the entire JSON file, it is not suitable for high-concurrency production environments.

* **Security:** The application uses Parameterized Queries for all user-provided data and validates column names to prevent SQL Injection risks.
