# RARIK (`minarsidur.rarik.is`) Specification

## 1. Overview & Architecture
- **Host:** `https://minarsidur.rarik.is`
- **Backend Architecture:** ASP.NET MVC web application.
- **Data Delivery:** Server-rendered HTML tables with dedicated AJAX endpoints for structured Excel (XLSX) and PDF downloads.
- **Session Lifespan:** Handled via ASP.NET session and authentication cookies.

## 2. Authentication Mechanics
Authentication is delegated via Signet (`login.signet.is`) utilizing Icelandic Electronic ID (Rafræn skilríki).
Once authenticated, the following cookies are set on domain `minarsidur.rarik.is`:
- `.ASPXAUTH`: Primary encrypted ASP.NET forms authentication ticket (HttpOnly, SameSite=Lax).
- `ASP.NET_SessionId`: ASP.NET session identifier (HttpOnly, Secure, SameSite=Lax).
- `.LRoles`: Role definitions ticket (HttpOnly, SameSite=Lax).

*(Sensitive values are redacted in repository documentation and stored locally in `.auth_session.json`)*

## 3. Discovered Endpoints

### 3.1 Meter List & Connection Overview
- **URL:** `GET https://minarsidur.rarik.is/yfirlit/notkun/`
- **Headers:** Standard browser headers with authenticated cookies.
- **Response:** HTML containing meter cards and connection parameters:
  - `ConnectionId`: e.g. `CON-2068111`
  - `EanId`: e.g. `10379380`
  - `Address`: Service location (e.g., `Dæmivegur 10, 805 Selfoss`)
  - `AlesturActive`: Boolean (`True`/`False`)
  - `type`: Meter type (`Fjarálestur` / remote reading, or manual)

### 3.2 Detailed Meter Readings & History (Table)
- **URL:** `GET https://minarsidur.rarik.is/yfirlit/notkun/nanar/notkunarsaga/`
- **Query Parameters:**
  - `ConnectionId`: Connection identifier
  - `EanId`: EAN meter identifier
  - `Address`: Encoded address
  - `AlesturActive`: `True`
  - `type`: `Fjarálestur`
  - `nationalId`: User national identification number (kennitala)
- **Response:** HTML table `.alestrarsagatable` containing:
  - `Dags. álestur`: Reading date (DD.MM.YYYY)
  - `Mælisnúmer`: Physical meter serial number
  - `Rás`: Channel number (e.g. `1`)
  - `Dagar frá síðasta álestri`: Days elapsed since previous reading
  - `Tegund álesturs`: Reading type (`ORIG`, etc.)
  - `Staða mælis`: Meter index (e.g. `4.088`)
  - `Eining`: Unit (`kWh`)
  - `Notkun frá síðasta álestri`: Consumption since last reading (kWh)
  - `Meðalnotkun á dag`: Average daily consumption (kWh/day)

### 3.3 Historical Usage Export (Excel / XLSX)
- **URL:** `POST https://minarsidur.rarik.is/yfirlit/notkun/nanar/notkunarsaga/$MeterReading/ExportToExcel/`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Form Parameters:**
  - `EanId`: EAN identifier (e.g. `10379380`)
  - `ChannelNr`: Channel number (e.g. `1`)
  - `startDate`: Start date format `DD.MM.YYYY` (e.g. `01.01.2025`)
  - `endDate`: End date format `DD.MM.YYYY` (e.g. `01.11.2026`)
- **Response:** `text/html; charset=utf-8` containing raw base64 string before any trailing HTML tag.
- **Payload Decoding:**
  ```python
  raw_base64 = response.text.split("<")[0].strip()
  xlsx_bytes = base64.b64decode(raw_base64)
  ```
- **XLSX Columns:**
  - `DAGS.ÁLESTUR`
  - `NÚMER MÆLIS`
  - `RÁS`
  - `DAGAR FRÁ SÍÐASTA ÁLESTRI`
  - `TEGUND`
  - `STAÐA MÆLIS`
  - `NOTKUN FRÁ SÍÐASTA ÁLESTRI`
  - `MEÐALNOTKUN Á DAG`
  - `ÁÆTLUÐ ÁRSNOTKUN`

### 3.4 Invoices List
- **URL:** `GET https://minarsidur.rarik.is/yfirlit/reikningar/?nationalId={nationalId}`
- **Response:** HTML table listing invoice rows:
  - `Reikningur`: Invoice number (e.g. `Or2048494`)
  - `Útgáfudagur`: Issue date (`DD.MM.YYYY`)
  - `Gjalddagi`: Due date (`DD.MM.YYYY`)
  - `Upphæð`: Total amount in ISK
  - `Kostnaður`: Cost
  - `EftirStöðvar`: Remaining balance
  - `Uppgreiðslud.`: Settlement date

### 3.5 Invoice PDF Download
- **URL:** `GET https://minarsidur.rarik.is/yfirlit/$Invoice/GetInvoicePDF/?invoiceNr={invoiceNr}&nationalId={nationalId}`
- **Response:** `application/pdf; charset=utf-8` binary stream.
