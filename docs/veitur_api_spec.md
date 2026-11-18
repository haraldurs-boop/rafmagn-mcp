# Veitur API Specification (`minarsidur.veitur.is`)

## 1. Authentication & Session Management
- **Base Domain:** `https://minarsidur.veitur.is`
- **Login Domain:** `https://innskraning.veitur.is` (and `https://idp.kenni.is/minarsidur.veitur.is`)
- **Authentication Flow:**
  1. User authenticates via Icelandic Electronic ID (Auðkenni / Ísland.is) at `idp.kenni.is`.
  2. Redirects to `https://innskraning.veitur.is/api/auth/callback/kenni?code={code}&state={state}`.
  3. Redirects to `https://minarsidur.veitur.is/api/auth-return?to=/yfirlit&nationalId={ssn}`.
  4. Final redirect sets session cookies on `minarsidur.veitur.is`.
- **Key Cookies:**
  - `veitur-service.session-token`: Primary session cookie for Next.js App Router on `minarsidur.veitur.is`.
  - `veitur-auth.session-token`: Auth session cookie on `innskraning.veitur.is`.
- **Session Check Endpoint:**
  - `GET https://minarsidur.veitur.is/api/auth/session`
  - **Response (200 OK):**
    ```json
    {
      "user": {
        "name": "<Customer Name>",
        "sub": "<uuid>",
        "nationalId": "<SSN>",
        "selectedNationalId": "<SSN>"
      },
      "expires": "2026-12-18T20:47:19.289Z"
    }
    ```
  - **Token TTL:** ~30 days from issuance.

---

## 2. Meters & Assets Overview
- **Endpoint:** `GET https://minarsidur.veitur.is/yfirlit`
- **Data Transport:** Next.js Server Components (RSC) serialized into `self.__next_f.push([1, "..."])`.
- **Extracted Fields:**
  - Electricity Meters (`/notkun/rafmagn?meter={meterId}`):
    - `meterId`: e.g. `62858`
    - `label`: Property location / address
    - `description`: Smart meter serial (e.g. `Snjallmælir 6092777587`)
    - `unit`: `kWh`
  - Hot Water Meters (`/notkun/heitt-vatn?meter={meterId}`):
    - `meterId`: e.g. `30968`
    - `label`: Property location / address
    - `description`: Smart meter serial (e.g. `Snjallmælir 4081726607`)
    - `unit`: `m³`

---

## 3. Consumption Telemetry (Notkun)
Veitur exposes granular consumption telemetry directly through Next.js server-rendered pages supporting rich query parameters.

### A. Electricity (`rafmagn`)
- **Endpoint:** `GET https://minarsidur.veitur.is/notkun/rafmagn`
- **Query Parameters:**
  - `meter`: Meter ID (e.g. `62858`)
  - `period`: `day` | `month` | `year` | `last7Days` | `last30Days` | `last12Months`
  - `date`: `YYYY-MM-DD` (e.g. `2026-11-15`)
- **Granularity:**
  - When `period=day`: Hourly resolution (24 points, `00:00` to `23:00`).
  - When `period=month`: Daily resolution (28-31 points).
  - When `period=last12Months`: Monthly resolution (12 points).
- **Data Payload Structure (inside RSC data array):**
  ```json
  {
    "date": "2026-11-15T00:00:00",
    "tickLabel": "00:00",
    "tooltipLabel": "00:00 sunnudagur 15. nóvember 2026",
    "usageValue": 0.85,
    "unit": "kWh"
  }
  ```

### B. Hot Water (`heitt-vatn`)
- **Endpoint:** `GET https://minarsidur.veitur.is/notkun/heitt-vatn`
- **Query Parameters:** Same as electricity (`meter`, `period`, `date`).
- **Granularity & Unit:**
  - Hourly, daily, or monthly in cubic meters (`m³`).
- **Data Payload Structure:**
  ```json
  {
    "date": "2026-11-15T00:00:00",
    "tickLabel": "00:00",
    "tooltipLabel": "00:00 sunnudagur 15. nóvember 2026",
    "usageValue": 0.05,
    "unit": "m³"
  }
  ```

---

## 4. Invoices & Claims (Reikningar & Kröfur)
- **Endpoint:** `GET https://minarsidur.veitur.is/reikningar`
- **Data Payload Structure:**
  ```json
  {
    "claimNumber": "8481823",
    "companyId": "Veitur",
    "dueDate": "2026-11-20T00:00:00.000Z",
    "finalDueDate": "2026-12-03T00:00:00.000Z",
    "isPaid": true,
    "originalAmount": 23287,
    "currentAmount": 0,
    "paymentMethodDescription": "Kreditkort",
    "referralClaim": "GST-303774-7",
    "documentReferenceToken": "5Sltd/HkM7sAjusFejkCagPaARW61AF..."
  }
  ```

### Invoice PDF Download
- **Endpoint:** `GET https://minarsidur.veitur.is/reikningar/krofur/download?token={documentReferenceToken}`
- **Headers Returned:**
  - `Content-Type: application/pdf`
  - `Content-Disposition: attachment; filename="claim.pdf"`
- **Response Body:** Binary PDF document.
