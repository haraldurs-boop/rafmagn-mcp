# Tæknirýni: Íslenskur Orkugagna FastMCP Þjónn & Mælaborð (Orkusalan, RARIK og Veitur)

> **Tilgangur skjals:** Þetta skjal inniheldur heildaryfirlit yfir uppsetningu, kóðun og gagnastrauma fyrir staðbundinn Python FastMCP þjón og mælaborð sem tengist Orkusölunni, RARIK og Veitum. Skjalinu er ætlað að vera lagt fyrir Gemini Hydrogen til tæknirýni og ráðgjafar um gæði gagna og áreiðanleika kerfisins.

---

## 0. Hlutverkaskipting á Veitumarkaði (Lykilatriði)

Til að gæta fyllstu nákvæmni er mikilvægt að skilja hvernig hlutverkin skiptast á milli þessara þriggja aðila samkvæmt íslenskum raforkulögum:

| Fyrirtæki | Hlutverk | Umfang hjá okkur | Mælir / Auðkenni |
| :--- | :--- | :--- | :--- |
| **Orkusalan** | **Raforkusali (Smásala orku)** | Selur **ALLT rafmagn** bæði fyrir **Heimilið** og **Sumarbústaðinn** | Heimili: `200-6092777587`<br>Bústaður: `101-36815202` |
| **RARIK** | **Dreifiveita (Flutningur raforku)** | Sér um **flutning og dreifingu** raforku fyrir **Sumarbústaðinn** | Bústaður: `101-36815202` (MMR handvirkur) |
| **Veitur** | **Dreifiveita (Flutningur raforku)** | Sér um **flutning og dreifingu** raforku fyrir **Heimilið** | Heimili: `62858` (Snjallmælir 6092777587) |
| **Veitur** | **Hitaveita (Heitt vatn)** | Selur og afhendir **jarðvarmaheitt vatn ($m^3$)** fyrir **Heimilið** | Heimili: `30968` (Snjallmælir 4081726607) |

Þetta þýðir að fyrir rafmagn fær heimilið tvo reikninga (Orkusalan = orka, Veitur = flutningur), bústaðurinn fær tvo reikninga (Orkusalan = orka, RARIK = flutningur), og heimilið fær auk þess hitaveitureikning frá Veitum.

---

## 1. Heildararkitektúr og Kerfiseiningar

Kerfið er hannað sem staðbundin þjónusta sem keyrir á heimanetþjóni fjölskyldunnar (`r8q`, IP-tala `192.168.68.87`) sem tvær sjálfvirkar kerfisþjónustur (`systemd`):

1. **FastMCP Þjónn (`server.py`):**
   - Byggður á `FastMCP` (Python `mcp` safninu).
   - Styður bæði **SSE (Server-Sent Events)** á tengi 8051 (`/sse`) fyrir veflausnir og **stdio yfir SSH** (`ssh r8q .../python3 .../server.py`) fyrir staðbundin málmódel (Claude Desktop, Antigravity, o.fl.).
   - Útvegar tól: `get_electricity_usage`, `get_water_usage`, `get_meters`, `get_invoices`, `check_auth_status`.

2. **Vefmælaborð (`dashboard/`):**
   - Skrifað í Python með `Starlette` og `Uvicorn` á tengi 8050 (`http://192.168.68.87:8050`).
   - Notar skandinavíska léttmótun (Scandinavian light-mode) með TailwindCSS og Chart.js.
   - Býr yfir sjálfvirkum bakgrunnsþræði sem uppfærir gögn reglulega og vistar á staðbundið skyndiminni á diski (`/var/cache/rafmagn_dashboard.json`), þannig að mælaborðið hleðst á innan við 50ms án þess að bíða eftir ytri vefþjónum.

3. **Auðkenningarkerfi (`auth_helper.py`):**
   - Samþættir auðkenningu fyrir öll þrjú kerfin með rafrænum skilríkjum á síma.
   - Orkusalan notar sjálfvirka REST-púlsun (polling) út frá símanúmeri.
   - RARIK og Veitur nota headed Playwright Chromium glugga sem bíður eftir samþykki og fangar vefkökur.
   - Kökur eru vistaðar í `.auth_session.json` (sem er stranglega útilokað frá Git).

---

## 2. Greining á Gagnastraumum og Mælum

### A. Orkusalan (`minarsidur.orkusalan.is`) — Smásali Rafmagns
- **Hlutverk:** Selur alla raforku til bæði heimilis og bústaðar.
- **Auðkenning:** REST straumur (`POST /auth/start` -> `GET /auth/poll`), auðkenningarkaka `connect.sid`. Setutími (TTL): ~2–4 dagar.
- **Endapunktur:** `GET /api/user/consumption?configurationName={config}&timePeriod={Hourly|Daily|Monthly}&unitOfMesure=kWh&startDate={start}&endDate={end}`
- **Mælar í notkun:**
  1. **Heimilið (AMR Snjallmælir):** Mælir `200-6092777587` (`Config_10619453`). Skilar fullri klukkustundanákvæmni (Hourly kWh). Gögnin eru 100% rauntími og áreiðanleg.
  2. **Sumarbústaðurinn (MMR Handvirkur mælir):** Mælir `101-36815202` (`Config_10379380`). Ef beðið er um `Hourly` gögn frá API hjá Orkusölunni lendir fyrirspurnin í `ReadTimeout` vegna þess að gagnagrunnurinn á engar klukkustundamælingar. Virkar aðeins með `Daily` eða `Monthly`.

### B. RARIK (`minarsidur.rarik.is`) — Dreifiveita í Sumarbústað
- **Hlutverk:** Sér um flutning og dreifingu rafmagns í sumarbústaðinn.
- **Auðkenning:** ASP.NET Forms authentication kökur (`.ASPXAUTH`, `ASP.NET_SessionId`, `.LRoles`). Setutími (TTL): ~2–3 dagar.
- **Gagnasöfnun:** HTML-töfluskrapun á `/yfirlit/notkun/nanar/notkunarsaga/` eða XLSX útflutningur með `POST /yfirlit/notkun/nanar/notkunarsaga/$MeterReading/ExportToExcel/`.
- **Eðli gagna:** Mælirinn `101-36815202` er eldri gerð af mæli án sjálfvirks fjarlestrar. Gögnin koma sem mánaðarlegar stöður, áætluð mánaðarnotkun eða uppgjörsreikningar. Dagnákvæmni er aðeins reiknuð út sem jöfn dreifing á milli álestra.

### C. Veitur (`minarsidur.veitur.is`) — Dreifiveita og Hitaveita á Heimili
- **Hlutverk:** Sér um flutning og dreifingu rafmagns á heimilinu og selur/dreifir heitu vatni.
- **Auðkenning:** Next.js App Router með dulkóðuðu tákni (`veitur-service.session-token`). Setutími (TTL): **30 dagar**.
- **Gagnasöfnun (`veitur_client.py`):** Afkóðar Next.js React Server Components (RSC) strauma úr `self.__next_f.push`.
- **Mælar í notkun:**
  1. **Rafmagnsdreifing:** Mælir `62858` (sami líkamlegi snjallmælir og Orkusalan selur inn á, raðnúmer `6092777587`). Skilar klukkustunda- og daganotkun.
  2. **Hitaveita:** Mælir `30968` (raðnúmer `4081726607`). Mælir heitt vatn í rúmmetrum ($m^3$) með klukkustunda- og daganákvæmni (t.d. 52,7 $m^3$ í október 2026).
  3. **Kröfur og Reikningar:** Allar kröfur og sundurliðanir sóttar með beinum niðurhalshlekkjum á PDF reikninga (`/reikningar/krofur/download?token=...`).

---

## 3. Spurningar til Gemini Hydrogen

Kæri Gemini Hydrogen, vinsamlegast rýndu í eftirfarandi tæknilegar spurningar út frá ofangreindum forsendum:

### 1. Gæði og Nægjanleiki Gagna (Orkusalan vs. RARIK)
- Hvernig metur þú gæði gagnanna sem við erum að fá?
- Skila gögnin frá Orkusölunni og RARIK sér nógu vel miðað við þarfir greiningar á orkunotkun, sérstaklega í ljósi þess að sumarbústaðurinn er á handvirkum MMR mæli en heimilið á AMR snjallmæli?
- Hverjir eru helstu blindu blettirnir (blind spots) í gögnunum sem við verðum að vara notandann við í mælaborðinu (t.d. að dagleg notkun í bústað sé jafndreift reiknilíkan en ekki raunveruleg dægursveifla)?

### 2. Aðferðafræði við Útreikning á Grunnhleðslu (Baseload) og Árstíðasveiflum
- Í ljósi þess að bústaðurinn hefur ekki klukkustundamælingar: Hver er besta tölfræðilega aðferðin til að einangra raunverulega grunnhleðslu (t.d. frostlög á ofnum, ísskápur, eftirlitsmyndavélar) annars vegar yfir vetrarmánuði (okt–mars) og hins vegar yfir sumarmánuði (apríl–sept)?
- Er skynsamlegra að byggja greininguna á bústaðnum fyrst og fremst á sögunni frá RARIK (gegnum Excel export) eða Orkusölunni?

### 3. Harðgerving á Auðkenningu og Sjálfvirknivæðing (Session Resiliency)
- Veitur endast í 30 daga á sama tákni, en Orkusalan og RARIK renna út á 2–4 dögum vegna öryggiskrafna um innskráningu með rafrænum skilríkjum.
- Hver er besta hagnýta nálgunin til að lágmarka áreiti á notandann en viðhalda samfelldum gagnagrunni (t.d. bakgrunnsvöktun, tilkynningar í Signal/Telegram þegar seta fellur úr gildi, eða söguleg varðveisla í staðbundnum SQLite gagnagrunni)?

### 4. Heildarmat á Kóðun og Uppbyggingu
- Hvernig lýst þér á samsetninguna á FastMCP, Starlette vefþjóni, RSC afkóðun og systemd uppsetningu á innra neti (`r8q`)?
- Eru einhverjir hnökrar, flöskuhálsar eða hönnunarmynstur sem þú myndir mæla með að bæta við eða einfalda?
