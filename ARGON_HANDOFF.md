# Handoff til Gemini Hydrogen / High / Argon

Afritaðu allan textann hér að neðan og límdu inn í Gemini í vafraglugganum þínum (þar sem þú ert með Gemini Hydrogen / High virkt). Þegar Gemini svarar geturðu límt svarið inn í `ARGON_RESPONSE.md`.

---

```markdown
Hæ Gemini! Ég vil fá ítarlega tæknirýni á uppsetningu, kóðunararkitektúr og gæðum gagnastrauma í Python FastMCP þjóni og staðbundnu mælaborði sem við höfum smíðað til að tengjast þremur íslenskum veitustofnunum: Orkusölunni, RARIK og Veitum.

### 1. Arkitektúr og Kerfiseiningar
- **Bakendi:** Python FastMCP þjónn (`server.py`) sem styður bæði SSE (Server-Sent Events) á porti 8051 og stdio yfir SSH.
- **Vefmælaborð:** Starlette/Uvicorn þjónusta (`dashboard/`) á porti 8050 með bakgrunns-uppfærsluþræði og disk-skyndiminni (`/var/cache/rafmagn_dashboard.json`). Skandinavískt léttmótunarviðmót (TailwindCSS + Chart.js).
- **Hýsing:** Keyrir á heimanetþjóni (`r8q`, 192.168.68.87) sem sjálfvirkar kerfisþjónustur (`systemd`: `rafmagn-mcp.service` og `rafmagn-dashboard.service`).
- **Auðkenning:** `auth_helper.py` sem sameinar REST síma-polling (Orkusalan) og headed Playwright Chromium innskráningu (RARIK og Veitur) fyrir rafræn skilríki á síma. Session-kökur vistaðar í `.auth_session.json`.

---

### 2. Staða og Eðli Gagnastraumanna

#### A. RARIK (`minarsidur.rarik.is`) — Sumarbústaðurinn
- **Mælir:** `101-36815202` (Handvirkur MMR mælir).
- **Auðkenning:** ASP.NET Forms authentication kökur (`.ASPXAUTH`, `ASP.NET_SessionId`, `.LRoles`). Setutími: ~2-3 dagar.
- **Gagnasöfnun:** Sótt með vefskrapun á `/yfirlit/notkun/nanar/notkunarsaga/` eða XLSX útflutningi gegnum `$MeterReading/ExportToExcel/`.
- **Eðli gagna:** Engin rauntímagögn eða klukkustundagögn. Gögnin koma í mánaðarlegum álestrarklumpar eða áætlun/uppgjöri sem dreifist jafnt yfir mánuðinn.

#### B. Orkusalan (`minarsidur.orkusalan.is`) — Heimili og Bústaður
- **Mælar:**
  1. *Heimili:* AMR snjallmælir (`200-6092777587`, `Config_10619453`). Full klukkustundanákvæmni (Hourly kWh).
  2. *Sumarbústaður:* MMR mælir (`101-36815202`, `Config_10379380`). Ef beðið er um `Hourly` í REST API hendir kerfið ReadTimeout; virkar aðeins með `Daily` eða `Monthly`.
- **Auðkenning:** Native REST straumur (`POST /auth/start` + `GET /auth/poll`), session vistað í `connect.sid`. Setutími: ~2-4 dagar.
- **Endapunktur:** `GET /api/user/consumption?configurationName={config}&timePeriod={Hourly|Daily|Monthly}&unitOfMesure=kWh&startDate=...&endDate=...`

#### C. Veitur (`minarsidur.veitur.is`) — Heimilið (Dreifing & Hitaveita)
- **Mælar:**
  1. *Rafmagnsdreifing:* Snjallmælir `62858` (sami líkamlegi mælir og Orkusalan selur inn á, raðnúmer 6092777587).
  2. *Hitaveita:* Snjallmælir `30968` (raðnúmer 4081726607). Mælir heitt vatn í rúmmetrum ($m^3$).
- **Auðkenning:** Next.js App Router (RSC). Session kökur `veitur-service.session-token` sem gilda í 30 daga.
- **Gagnasöfnun:** `veitur_client.py` afkóðar `self.__next_f.push` React Server Component strauma. Bæði klukkustunda- og daganotkun virkar með fyrirspurnum eins og `/notkun/heitt-vatn?meter=30968&period=day&date=2026-11-15`. Einnig eru allar kröfur og PDF reikningar sóttir beint.

---

### 3. Sérstakar Spurningar til að rýna:

1. **Gæði gagna frá Orkusölunni og RARIK:**
   - Eru gögnin frá Orkusölunni og RARIK að skila sér nógu vel miðað við þarfir mælaborðs og AI aðstoðarmanns?
   - Hvar liggja helstu blindu blettirnir (blind spots) – t.d. MMR mælingar í bústaðnum þar sem dagnákvæmni er aðeins reiknuð jöfn dreifing á milli mánaðarálestra?

2. **Aðferðafræði við greiningu á grunnhleðslu (Baseload) og árstíðasveiflum:**
   - Hvernig brúum við best bilið á milli AMR klukkustundamælinga (Heimilið) og MMR mánaðargagna (Bústaðurinn) þegar við viljum reikna raunverulegt grunnafl í bústaðnum (t.d. frostvörn á veturna vs. slökkt á sumrin)?
   - Er skynsamlegra að treysta frekar á RARIK XLSX útflutninginn eða Orkusöluna fyrir bústaðinn?

3. **Harðgerving og sjálfvirknivæðing (Session Resiliency):**
   - Veitur endast í 30 daga, en RARIK og Orkusalan renna út á 2–4 dögum vegna öryggiskrafna um auðkenningu.
   - Hvaða aðferð er best til að lágmarka óþægindi fyrir notandann (t.d. sjálfvirk áminning, bakgrunns-cache, eða blendingur af CLI SMS-kóða)?

4. **Kóðun og heildararkitektúr:**
   - Hvaða breytingar eða fínpússun myndir þú mæla með á MCP tólunum og Starlette bakendanum?
```
