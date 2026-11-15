# Orkusalan (`minarsidur.orkusalan.is`) Specification

## 1. Overview & Architecture
- **Host:** `https://minarsidur.orkusalan.is`
- **Frontend / Backend Architecture:** Next.js application with standard REST API endpoints.
- **Data Delivery:** Native JSON REST API.
- **Session Mechanism:** Standard HTTP session cookie `connect.sid`.

## 2. Authentication Mechanics
Orkusalan features a clean, direct REST authentication flow:

### 2.1 Start Authentication
- **URL:** `POST https://minarsidur.orkusalan.is/auth/start`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "identifier": "5812345",
    "method": "Sim"
  }
  ```
- **Response:**
  ```json
  {
    "authRequestId": "xmSvvPvqnwkXe1QPrchYwa3BT-0",
    "verificationCode": "B4P1",
    "pollingInterval": 2
  }
  ```

### 2.2 Poll Authentication Status
- **URL:** `GET https://minarsidur.orkusalan.is/auth/poll?authRequestId={authRequestId}`
- **Headers:** `Content-Type: application/json`
- **Pending Response:**
  ```json
  {
    "statusMessage": "Beðið eftir að notandi auðkenni sig",
    "waitingForUserInput": true
  }
  ```
- **Completed Response:**
  - HTTP `Set-Cookie`: `connect.sid={cookie_value}; Path=/; HttpOnly; Secure; SameSite=Lax`
  - Body:
    ```json
    {
      "customer": {
        "name": "Jón Jónsson",
        "ssn": "0101901239",
        "phoneNumber": "5812345",
        "token": "...",
        "flowKey": "..."
      },
      "statusMessage": "Ok",
      "waitingForUserInput": false
    }
    ```

## 3. Discovered Endpoints

### 3.1 User & Connection / Meter List
- **URL:** `GET https://minarsidur.orkusalan.is/_next/data/{buildId}/minar-sidur.json` (or extracted via session status)
- **Response Structure:**
  ```json
  {
    "pageProps": {
      "user": {
        "id": "0101901239",
        "name": "Jón Jónsson",
        "phone": "5812345",
        "address": "Dæmigata 1",
        "pnr": "200 Kópavogi",
        "connections": [
          {
            "id": "CON-2207334",
            "name": "Dæmigata 1\n200 Kópavogi",
            "meterNumber": "200-6092777587",
            "latestReadingDate": "2025-03-01T00:00:00Z",
            "latestReadingIndex": 3162.39,
            "dailyAverageConsumption": 14.48,
            "estimatedAnnualValue": 52427.25,
            "estimatedYearlyConsumption": 5285,
            "estimatedYearlyConsumptionUnit": "kWh",
            "configType": "AMR mælir",
            "configName": "Config_10619453",
            "EanId": "10619453",
            "active": true
          },
          {
            "id": "CON-2068111",
            "name": "Dæmivegur 10 sumarhús\n805 Selfossi",
            "meterNumber": "101-36815202",
            "latestReadingDate": "2026-10-26T00:00:00Z",
            "latestReadingIndex": 4088,
            "dailyAverageConsumption": 17.33,
            "estimatedAnnualValue": 55257.15,
            "estimatedYearlyConsumption": 6324,
            "estimatedYearlyConsumptionUnit": "kWh",
            "configType": "MMR mælir",
            "configName": "Config_10379380",
            "EanId": "10379380",
            "active": true
          }
        ]
      }
    }
  }
  ```

### 3.2 Electricity Consumption
- **URL:** `GET https://minarsidur.orkusalan.is/api/user/consumption`
- **Query Parameters:**
  - `configurationName`: e.g. `Config_10619453` (from connection `configName`)
  - `timePeriod`: `Hourly` | `Daily` | `Monthly` *(Note: `Hourly` is supported on AMR smart meters; MMR meters return 500 for Hourly but support Daily and Monthly)*
  - `unitOfMesure`: `kWh`
  - `startDate`: `YYYY-MM-DD`
  - `endDate`: `YYYY-MM-DD`
- **Sample Response:**
  ```json
  [
    {
      "StartDate": "2026-11-01T01:00:00Z",
      "Value": 0.799
    },
    {
      "StartDate": "2026-11-01T02:00:00Z",
      "Value": 0.654
    }
  ]
  ```

### 3.3 Invoices List
- **URL:** `GET https://minarsidur.orkusalan.is/api/user/invoices?from={from_iso}&to={to_iso}&page={page}&pageSize={pageSize}`
- **Sample Query:** `from=2025-01-01T00:00:00.000Z&to=2026-12-31T23:59:59.000Z&page=1&pageSize=100`
- **Sample Response:**
  ```json
  [
    {
      "claimNumber": "0318391",
      "invoiceId": "Or2935773",
      "amountExclVAT": 4069,
      "amountInclVAT": 5046,
      "issuedDate": "2026-10-31T12:00:00",
      "dueDate": "2026-12-02T12:00:00",
      "lastSettleDate": "2026-12-02T12:00:00",
      "fullyPaidDate": "2026-11-13T12:00:00",
      "locationName": "",
      "amountInBank": 0,
      "cost": 0,
      "pathToInvoice": "https://skeyti.advania.is/skeytamidlunBirting/getinvoicehtml?sessid=...",
      "paid": true,
      "inDeptCollection": false
    }
  ]
  ```
