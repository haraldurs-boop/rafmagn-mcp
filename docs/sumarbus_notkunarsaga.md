# Raun-rafmagnsnotkun í Sumarbústað (Hallkelshólar lóð 105)

Greining á raunverulegri raforkunotkun, afli og kostnaði byggt á gögnum frá **RARIK** (dreifiveita) og **Orkusölunni** (raforkusali).

> **Athugasemd um mælingar:**  
> Mælirinn í sumarbústaðnum er orkumælir (kWh) án klukkustundar-tímaraða (MMR mælir í gagnagrunni Orkusölunnar/RARIK). Hinn 24. febrúar 2026 var settur upp nýr mælir (`36815202`) sem lesinn er mánaðarlega. Fyrir þann tíma var eldri mælir (`9321688`) lesinn árlega.  
> Þar sem mælirinn skráir eingöngu heildarorku (kWh) en ekki 15-mínútna afltoppa eða stundarmælingar, er **meðalafl (W)** reiknað nákvæmlega út frá raunorku og dögum, en stundarhámarksafl (kW toppur) og dags-/næturnotkun eru metin með verkfræðilegu líkani út frá raungögnunum.

---

## 1. Mánaðarleg samantekt (Rauntölur)

Taflan sýnir raunmælingar hvers tímabils frá uppsetningu nýja mælisins í febrúar 2026 ásamt árlegum samanburðartímabilum eldri mælis allt aftur til ársins 2023.

| Mánuður / Tímabil | Mælisnúmer | Dagar | Heildarnotkun (kWh) | Meðalnotkun (kWh/dag) | Meðalafl (W) | Áætlað hámarksafl (kW)* |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Október 2026** (27.09–26.10) | 36815202 | 29 | **520 kWh** | 17,9 kWh/dag | **747 W** | ~2,5 – 4,5 kW |
| **September 2026** (27.08–27.09) | 36815202 | 31 | **470 kWh** | 15,2 kWh/dag | **632 W** | ~2,0 – 3,5 kW |
| **Ágúst 2026** (27.07–27.08) | 36815202 | 31 | **550 kWh** | 17,7 kWh/dag | **739 W** | ~2,5 – 4,0 kW |
| **Júlí 2026** (27.06–27.07) | 36815202 | 30 | **574 kWh** | 19,1 kWh/dag | **797 W** | ~3,0 – 5,0 kW |
| **Júní 2026** (27.05–27.06) | 36815202 | 31 | **249 kWh** | **8,0 kWh/dag** | **335 W** | ~0,8 – 1,5 kW |
| **Maí 2026** (27.04–27.05) | 36815202 | 30 | **386 kWh** | 12,9 kWh/dag | **536 W** | ~1,5 – 3,0 kW |
| **Apríl 2026** (26.03–27.04) | 36815202 | 32 | **611 kWh** | 19,1 kWh/dag | **796 W** | ~2,5 – 4,5 kW |
| **Mars 2026** (24.02–26.03) | 36815202 | 30 | **728 kWh** | 24,3 kWh/dag | **1.011 W** | ~3,5 – 5,5 kW |
| **Vetur 2025/2026** (14.11–24.02) | 9321688 | 101 | **2.770 kWh** | **27,4 kWh/dag** | **1.143 W** | ~4,0 – 6,0 kW |
| **Árið 2024/2025** (25.10–14.11) | 9321688 | 386 | **7.556 kWh** | 19,6 kWh/dag | **816 W** | ~5,0 – 7,0 kW |
| **Árið 2023/2024** (12.10–25.10) | 9321688 | 379 | **8.535 kWh** | 22,5 kWh/dag | **938 W** | ~5,0 – 7,0 kW |

*\*Hámarksafl (kW toppur) er ekki mælt af RARIK fyrir þennan mæli (enginn 15 mín. aflmælir er til staðar). Áætlað hámarksafl er reiknað út frá dæmigerðu álagi þegar ofnar, vatnshitari eða helluborð slá inn samtímis.*

---

## 2. Dags- vs. næturnotkun eftir árstíðum

Þar sem mælirinn sendir ekki klukkustundagögn í gagnagrunn, er skiptingin milli **dagtíma** (kl. 09:00–18:00, 9 klst.) og **kvöld-/nætur-/morguntíma** (kl. 18:00–09:00, 15 klst.) byggð á hitaálagi, útihitastigi og bústaðanotkun:

| Árstíð | Tímabil dags | Hlutfall orku | Meðalnotkun á dag | Meðalafl á klst. (W) | Skýring á álagi |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Vetur** (Okt – Mars)<br>*(Heild: ~25,0 kWh/dag)* | **Dagtími** (09:00–18:00)<br>*(9 klst.)* | 33% | **8,3 kWh** | **920 W** | Sólaráhrif/hærri útihiti draga úr ofnahitun yfir daginn. |
| | **Nætur-/kvöldtími** (18:00–09:00)<br>*(15 klst.)* | 67% | **16,7 kWh** | **1.115 W** | Kaldari nætur valda því að frostlögur/ofnar ganga oftar. |
| **Sumar** (Apríl – Sept)<br>*(Heild: ~15,0 kWh/dag)* | **Dagtími** (09:00–18:00)<br>*(9 klst.)* | 42% | **6,3 kWh** | **700 W** | Eldamennska, heimsóknir og virkni yfir bjartasta tímann. |
| | **Nætur-/kvöldtími** (18:00–09:00)<br>*(15 klst.)* | 58% | **8,7 kWh** | **580 W** | Hitakútur, biðstraumur og lítilsháttar næturhitun í köldum vikum. |

---

## 3. Grunnálag (Baseload)

Raungögnin sýna lágmarksálag bústaðarins mjög skýrt:

### A. Sumargrunnálag (Tómur bústaður í júní 2026): **~335 W** (8,0 kWh/dag)
- Í júnímánuði 2026 mældist notkunin aðeins **249 kWh á 31 degi**, sem gerir **8,03 kWh á dag**.
- Þetta jafngildir stöðugu meðalafli upp á **335 Watt**:
  - **Ísskápur:** ~50 – 80 W (meðalgildi með þjöppugangi)
  - **Ring myndavélar, 4G beinir og snjalltæki:** ~20 – 30 W
  - **Vatnshitari / hitakútur (biðhitatap):** ~150 – 200 W
  - **Ofnar og pottur:** Slökkt / óvirkt.

### B. Vetrargrunnálag (Tómur bústaður með frostvörn): **~1.000 – 1.140 W** (24 – 27 kWh/dag)
- Yfir vetrartímann (nóvember 2025 til mars 2026) lá dagleg meðalnotkun á bilinu **24,3 til 27,4 kWh á dag**.
- Þetta jafngildir stöðugu meðalafli upp á **1.011 til 1.143 Watt**:
  - **Frostvörn á ofnum (5–10°C stilling):** ~700 – 850 W
  - **Ísskápur, Ring myndavélar og nettæki:** ~100 – 120 W
  - **Vatnshitari (biðhiti í köldu umhverfi):** ~200 – 250 W

---

## 4. Helgar vs. virkir dagar

Þar sem bústaðurinn er orkumældur mánaðarlega er munurinn á helgum og virkum dögum greindur með því að bera saman **mánuði með mikilli helgarnotkun** (júlí/ágúst með ~18–19 kWh/dag) við **mánuði með engri eða lítilli dvöl** (júní með 8 kWh/dag):

| Tímabil | Virkir dagar (Mán–Fim) | Helgar (Fös–Sun) | Skýring og áhrif dvalar |
| :--- | :---: | :---: | :--- |
| **Sumar** (Apríl – Sept) | **~8 – 11 kWh/dag**<br>*(330–460 W)* | **~24 – 32 kWh/dag**<br>*(1.000–1.330 W)* | Á virkum dögum er bústaðurinn í lágmarksgrunni (335 W). Um helgar bætast við heitavatnsnotkun, eldamennska, lýsing og tæki. |
| **Vetur** (Okt – Mars) | **~22 – 25 kWh/dag**<br>*(920–1.040 W)* | **~30 – 38 kWh/dag**<br>*(1.250–1.580 W)* | Grunnurinn á virkum dögum er hár vegna frostvarnar (~24 kWh/d). Um helgar þegar hækkað er á ofnum fer dagsnotkun upp í 30–38 kWh/dag. |

---

## 5. Rafmagnsverð og kostnaður á reikningum

Kostnaði við rafmagn í sumarbústaðnum er skipt í tvennt: **Orkusölu** (Orkusalan) og **Orkudreifingu/flutning** (RARIK).  
Tölurnar hér að neðan eru teknar beint úr raunverulegum reikningum fyrir bústaðinn (**Október 2026**, 520 kWh):

### A. Dreifing og flutningur (RARIK reikningur `Or2048494`)
- **Gjaldskrá/taxti:** `VO130 - Orkudreifing (Taxtaflokkur B - Sumarhús)`
- **Fastagjald dreifingar:** **146,66 kr./dag** án vsk (*4.253 kr./mán án vsk eða 5.275 kr. m/vsk*)
- **Dreifing orku:** ~4,20 kr./kWh
- **Flutningur Landsnets:** ~1,85 kr./kWh
- **Jöfnunar- og dreifbýlisgjald:** ~0,45 kr./kWh
- **Greiðslugjald:** 298 kr.
- **Samtals dreifing í október:** **10.828 kr. m/vsk**

### B. Raforkusala (Orkusalan reikningur `Or2935765`)
- **Raforkuverð:** ~**7,21 kr./kWh án vsk** (~**8,95 kr./kWh m/vsk**)
- **Heildarkostnaður orkusölu í október:** **4.652 kr. m/vsk**

### C. Samanlagður raforkukostnaður (Október 2026 - 520 kWh)
- **Dreifing (RARIK):** 10.828 kr. (69,9%)
- **Orka (Orkusalan):** 4.652 kr. (30,1%)
- **Heildarkostnaður mánaðarins:** **15.480 kr. m/vsk**
- **Virkt heildarverð á hverja kWh (með öllum fastagjöldum og vsk):** **~29,77 kr./kWh**  
  *(Vegna hás fastagjalds í dreifbýli hjá RARIK er hlutfall fastakostnaðar umtalsvert þegar notkun er lág).*
