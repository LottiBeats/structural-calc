"""
templates.py — Standard document templates (A1-B3).

Each template is a list of block dicts without 'id' fields.
IDs are assigned by _load_template() in app.py at load time.

Block types used:
  heading — bold section heading
  text    — plain paragraph
  note    — orange note / placeholder prompt
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _h(text):
    return {"type": "heading", "text": text}

def _t(text):
    return {"type": "text", "text": text}

def _n(text):
    return {"type": "note", "text": text}


# ── Standard boilerplate strings ──────────────────────────────────────────────

_NORMS = (
    "Eurocode 0 — Konstruktioners sikkerhed (EN 1990)\n"
    "DS/EN 1990 DK NA:2024 — Projekteringsgrundlag for baerende konstruktioner\n\n"
    "Eurocode 1 — Laster paa konstruktioner (EN 1991)\n"
    "DS/EN 1991-1-1 DK NA:2024 — Densiteter, egenlast og nyttelast\n"
    "DS/EN 1991-1-2 DK NA:2014 — Brandlast\n"
    "DS/EN 1991-1-3 DK NA:2015 — Snelast\n"
    "DS/EN 1991-1-4 DK NA:2015 — Vindlast\n"
    "DS/EN 1991-1-5 DK NA:2012 — Termiske laster\n"
    "DS/EN 1991-1-7 DK NA:2013 — Ulykkeslast\n\n"
    "Eurocode 2 — Betonkonstruktioner (EN 1992)\n"
    "DS/EN 1992-1-1 DK NA:2021 — Generelle regler samt regler for bygningskonstruktioner\n"
    "DS/EN 1992-1-2 DK NA:2011 — Brandteknisk dimensionering\n\n"
    "Eurocode 3 — Staalkonstruktioner (EN 1993)\n"
    "DS/EN 1993-1-1 DK NA:2019 — Generelle regler samt regler for bygningskonstruktioner\n"
    "DS/EN 1993-1-8 DK NA:2019 — Samlinger\n\n"
    "Eurocode 5 — Traekonstruktioner (EN 1995)\n"
    "DS/EN 1995-1-1 DK NA:2019 — Almindelige regler samt regler for bygningskonstruktioner\n\n"
    "Eurocode 6 — Mur vaerkskonstruktioner (EN 1996)\n"
    "DS/EN 1996-1-1 DK NA:2019 — Generelle regler for armeret og uarmeret murvark\n\n"
    "Eurocode 7 — Geoteknik (EN 1997)\n"
    "DS/EN 1997-1 DK NA:2021 — Geoteknik, Del 1: Generelle regler\n"
    "DS/EN 1997-2 DK NA:2013 — Geoteknik, Del 2: Jordbundsundersoegelser\n\n"
    "Ovenstaaende omfatter ogsaa gaeldende Nationale annekser."
)

_LOAD_COMB = (
    "LAK 1: Anvendelsesgraensetilstand\n"
    "Haandteres under den enkelte bygningsdel med udgangspunkt i opsummerede karakteristiske laster.\n\n"
    "LAK 2: Brudgraensetilstand\n"
    "  LAK 2.1 — Nyttelast dominerende: KFI x (Gsup + 1,5 x (Q + psi_S x S + psi_V x V))\n"
    "  LAK 2.2 — Snelast dominerende:  KFI x (Gsup + 1,5 x (psi_Q x Q + S + psi_V x V))\n"
    "  LAK 2.3 — Vindlast dominerende: KFI x (Gsup + 1,5 x (psi_Q x Q + V))\n"
    "  LAK 2.4 — Vindlast dominerende: 0,9 x Ginf + 1,5 x KFI x V\n"
    "  LAK 2.5 — Egenlast dominerende: 1,2 x KFI x Gsup\n\n"
    "LAK 3: Ulykkesgr.tilstand / brand\n"
    "  LAK 3.1 — Nyttelast primær:  Gsup + psi_Q1 x Q\n"
    "  LAK 3.2 — Snelast primær:    Gsup + psi_Q2 x Q + psi_S1 x S\n"
    "  LAK 3.3 — Vindlast primær:   Gsup + psi_Q2 x Q + psi_V1 x V\n\n"
    "OBS: Afvigelser fra ovenstaaende lastkombinationer noteres ved den enkelte lastnedfoering."
)

_IMPERFECTIONS = (
    "Geometriske imperfektioner haandteres iht. DS/EN 1992-1-1 ved aekvivalente horisontale laster\n"
    "i de enkelte daekskivers tyngdepunkt.\n\n"
    "Bygningens overordnede stabilitet:\n"
    "  theta_i = theta_0 x alpha_h x alpha_m\n"
    "  theta_0 = 1/200  (basisvaerdi, DK)\n"
    "  alpha_h = 2/sqrt(l),  2/3 <= alpha_h <= 1\n"
    "  alpha_m = sqrt(0,5 x (1 + 1/m))\n"
    "  l = konstruktionens laengde eller hoejde [m]\n"
    "  m = antal lodrette konstruktionsdele\n\n"
    "For enkeltstaende baerende konstruktionsdele i afstivede systemer:\n"
    "  e_i = l_0 / 400"
)

_SEISMIC = (
    "Seismisk last beregnes iht. DS/EN 1990 DK NA, Tabel A1.3 DK NA:\n\n"
    "  Ad = (a_seis / g) x (sum Gk,j + psi_2,i x Qk,i)\n"
    "  Ad = 1,5% x (sum Gk,j + psi_2,i x Qk,i)\n\n"
    "Konstruktioner skal ikke undersoges for seismisk last og vindlast virkende samtidigt.\n"
    "Vindlast er dimensionsgivende naer: Ad < 1,67 x KFI x Wk"
)


# ── A1 — Konstruktionsgrundlag ────────────────────────────────────────────────

A1 = [
    _n("Naervaerende statiske dokumentation er opbygget iht. Bygningsreglementet (BR18) og er i "
       "overensstemmelse med SBi 271, 3. udg.\n"
       "[Udfyldes: angiv om dette er startudgave (myndighedsprojekt) / projekteringsudgave "
       "(hovedprojekt) / faerdigmelding.]"),

    # ── A1.1 Bygvaerk ──────────────────────────────────────────────────────────
    _h("A1.1 Bygvaerk"),
    _n("[Udfyldes: Nærværende dokument udgør [startudgaven / projekteringsudgaven] af den statiske "
       "dokumentation ifm. [ansøgning om byggetilladelse / ...].]"),

    _h("A1.1.1 Bygvaerkets art og anvendelse"),
    _n("[Udfyldes: Beskriv bygvaerkets type og anvendelse (boligblok, erhverv, industri), antal "
       "etager, samlet etageareal, boligtyper m.v. Indsaet visualisering / opstalt som figur.]"),

    _h("A1.1.2 Konstruktioners art og opbygning"),
    _n("[Udfyldes: Beskriv det baerende og stabiliserende system — materialer (beton / staal / trae "
       "/ murvaerk / CLT), princip for lodret og vandret lastnedfoering, tagkonstruktion og "
       "fundamentering. Indsaet oversigtsplan og -snit som figurer.]"),

    _h("A1.1.3 Konstruktionsafsnit"),
    _n("[Udfyldes: Tabel over konstruktionsafsnit.\n"
       "Kolonner: Afsnit-nr. | Afsnit | Konsekvensklasse / konstruktionsklasse | Ansvarlig\n"
       "Eksempel: A2.2.1 | Fundament | CC2/KK2 | [Firmanavn]]"),

    _h("A1.1.4 Udforelse"),
    _t("Projektet udfoeres i [totalentreprise / fagentreprise]. Bygningen udfoeres som traditionelt "
       "[element- / monolitisk] byggeri med foelgende hovedaktiviteter:\n"
       "1. Jordarbejder\n"
       "2. Stoebning af fundamenter\n"
       "3. Stoebning af terrandaek\n"
       "4. Montage / opforelse af vaegkonstruktioner\n"
       "5. Montage / stoebning af etagedaek\n"
       "6. Tagkonstruktion og -opbygning\n"
       "7. Facadeopbygning / aptering"),
    _n("[Tilpas til projektets entrepriseform, konstruktionsprincip og eventuelle saerlige "
       "omstaendigheder ved udfoereisen — fx fugtstrategi, midlertidig afstivning.]"),

    _h("A1.1.5 Beskrivelser, modeller og tegninger"),
    _t("Henvisning til dokumentfortegnelse i A3.1 Konstruktionstegninger og modeller. "
       "Udbygges ifm. projektering."),

    # ── A1.2 Grundlag ──────────────────────────────────────────────────────────
    _h("A1.2 Grundlag"),

    _h("A1.2.1 Normer og standarder"),
    _t(_NORMS),
    _n("[Tilpas listen til de normer der rent faktisk benyttes i projektet. Fjern ikke-relevante.]"),

    _h("A1.2.2 Konsekvensklasser og konstruktionsklasser"),
    _n("[Udfyldes: Angiv konsekvensklasse (CC1 / CC2 / CC3) og konstruktionsklasse (KK1 / KK2 / "
       "KK3 / KK4) med begrundelse iht. DS/INF 1990:2021 tabel 2.\n"
       "Dokumenter at projektet opfylder ID-kriterierne (stoerste spaen, hoejde, etager).\n"
       "Eksempel: CC2 — stoerste spaen 9 m < 16 m (ID1), max. 2 etager < 5 (ID1). KK2.]"),

    _h("A1.2.3 Sikkerhed"),
    _t("Kontrolklasse: Alle bygningsdele henfoeres til normal kontrolklasse.\n"
       "Miljoeklasse: Fastlaegges for de enkelte bygningsdele under hensyntagen til placering "
       "i byggeriet. Der henvises til materialespecifikation i generelnote under A3.1."),
    _n("[Udfyldes: Angiv geoteknisk kategori — typisk GK2 for normale bygvaerker.]"),

    _h("A1.2.4 IKT-vaerktojer"),
    _n("[Udfyldes: Angiv de beregningsmassige softwarevaerktojer der anvendes, fx:\n"
       "Microsoft Office 365 — Word / Excel\n"
       "RFEM / FEM Design / Karamba\n"
       "Tekla Tedds / Tedds for Word\n"
       "Revit / Tekla Structures]"),

    _h("A1.2.5 Referencer"),
    _t("[1] Bygningsreglement BR18\n"
       "[2] SBi-anvisning 271, 3. udgave — Dokumentation og kontrol af baerende konstruktioner\n"
       "[3] Teknisk Staabi, seneste udgave"),
    _n("[Tilfoej projektspecifikke referencer — geoteknisk rapport, brandstrategi, "
       "leverandoerdokumentation, faglitteratur m.v.]"),

    # ── A1.3 Forundersoegelser ─────────────────────────────────────────────────
    _h("A1.3 Forundersoegelser"),

    _h("A1.3.1 Grunden og lokale forhold"),
    _n("[Udfyldes: Beskriv grundens beliggenhed og terrnkaraktere. Fastlaeg terraenkategori iht. "
       "DS/EN 1991-1-4 DK NA tabel 4.1 (0 / I / II / III / IV) ud fra vurdering af omgivelserne "
       "inden for 1-km radius (brug Google Earth). Angiv terraenkoter og evt. terraenregulering.\n"
       "Tip: Lav udsnit fra Google Earth med 1-km cirkel rundt om bygvaerket.]"),

    _h("A1.3.2 Geotekniske forhold"),
    _n("[Udfyldes: Henvis til geoteknisk undersoegelse (bilag). Angiv:\n"
       "- Funderingsmetode: direkte (stribe- / punktfundamenter) eller paeledrivning\n"
       "- Frostfri dybde: min. 0,9 m under fremtidigt terraenniveau\n"
       "- Karakteristiske styrkepar.: friktionsvinkel phi_k, kohæsion c_u,k [kN/m²], "
       "rumvægt gamma [kN/m³]\n"
       "- Funderingsniveau / OSBL]"),

    _h("A1.3.3 Klima- og miljoetekniske forhold"),
    _n("[Udfyldes: Henvis til geo- og miljoeteknisk undersoegelse. Angiv evt. forureningsklasse "
       "for jordflytning. Skriv 'Ikke relevant' hvis ingen forurening er konstateret.]"),

    _h("A1.3.4 Eksisterende konstruktioner"),
    _n("[Udfyldes: 'Der findes ingen eksisterende konstruktioner paa matriklen.' eller beskriv "
       "eksisterende konstruktioner der berores af byggeriet. Indsaet billede fra BBR (ois.dk).]"),

    _h("A1.3.5 Tilstodende eksisterende bygvaerker"),
    _t("Ikke relevant for dokumentationen."),
    _n("[Erstat med beskrivelse hvis nabobygninger kan pavirkes — udgravning, pæleramning, m.v.]"),

    _h("A1.3.6 Tilstodende paataenkte bygvaerker"),
    _t("Ikke relevant for dokumentationen."),

    # ── A1.4 Konstruktioner ────────────────────────────────────────────────────
    _h("A1.4 Konstruktioner"),

    _h("A1.4.1 Statisk virke maoade"),
    _n("[Udfyldes: Beskriv lodret og vandret lastnedfoering med skitser / figurer.\n"
       "Lodret: hvad bærer hvad — tag til facader / skillevagger til fundament.\n"
       "Vandret: skivevirkning — daekskiver, stabiliserende vaegge, fundament.\n"
       "Indsaet principskitser som figurer.]"),

    _h("A1.4.2 Anvendelseskrav — Deformationer og vibrationer"),
    _t("Acceptable deformationer jf. nationale annekser til Eurocode 2, 3 og 5:\n\n"
       "  Beton: L/250 (kv.perm. kombination)  |  L/400 (variabel last)\n"
       "  Staal: L/400 (kv.perm., fradrag pilhojde)  |  L/400 (variabel, etageadsk.)\n"
       "  Trae:  L/400 (egenlast og nyttelast)  |  L/250 (karakteristisk vindlast)\n\n"
       "Vibrationer — boliger (DS/EN 1990 DK NA tabel A1.4):\n"
       "  Acceptabel egenfrekvens: ne > 8 Hz\n"
       "  Graenseacceleration:     < 0,1 % af tyngdeaccelerationen"),

    _h("A1.4.3 Funktionskrav"),
    _t("Der forventes ikke saerlige funktionskrav ud over de anbefalinger der fremgaar af "
       "konstruktionsnormerne. Evt. funktionskrav for stoerre facader, dor- og/eller "
       "vinduespartier bekraeftes eller bestemmes af leverandoer."),

    _h("A1.4.4 Robusthed"),
    _n("[Udfyldes: Henforer til CC-klasse og vurder robusthed iht. DS/EN 1990 DK NA:2024 "
       "Anneks E pkt. (1)-(5).\n\n"
       "Kollapsomfang (CC2/CC3): maks. 240 m² pr. etage eller 360 m² samlet. "
       "Dokumenter det kritiske bortfaldsscenarie (fx bortfald af 3 m vaeg).\n\n"
       "Traekforbindelser (CC2):\n"
       "  Periferi:  Ftie,per = li x 7,5 kN/m x faktor  (> 8 kN)\n"
       "  Interne:   Ftie = 15 kN/m x (l1+l2)/2 x faktor  (> 8 kN)\n"
       "  Vandrette: 15 x faktor = [vaerdi] kN/m i vaegtop\n\n"
       "Dokumentation udfoeres i A2.1 Statiske beregninger bygvaerk.]"),

    _h("A1.4.5 Levetid"),
    _t("Bygvaerket henfores til kategori 4 jf. DS/EN 1990 tabel 2.1 med forventet levetid "
       "paa 50 aar ved opfyldelse af almindelig god byggeskik og uden saerlige tiltag."),

    _h("A1.4.6 Brand"),
    _n("[Udfyldes: Angiv brandklasse (BK1 / BK2 / BK3 / BK4) iht. brandstrategirapporten. "
       "Angiv brandmodstandskrav for baerende bygningsdele jf. BR18 kap. 3 tabel 1. "
       "Henvis til brandstrategi som bilag. Indsaet relevant tabel fra BR18.]"),

    _h("A1.4.7 Udfoerelsesklasse"),
    _t("Bygvaerket henfores til udfoerelsesklasse EXC2 iht. DS/EN 1990 FU:2021."),
    _n("[Tilpas udfoerelsesklasse (EXC1 / EXC2 / EXC3) iht. valgt KK-klasse. "
       "KK2 svarer typisk til EXC2.]"),

    _h("A1.4.8 Drift og vedligehold"),
    _t("Ikke relevant for denne dokumentation."),

    # ── A1.5 Konstruktionsmaterialer ───────────────────────────────────────────
    _h("A1.5 Konstruktionsmaterialer"),

    _h("A1.5.1 Grund og jord"),
    _t("Alle permanente konstruktioner henfores til geoteknisk kategori 2 med "
       "modelfaktor gamma_s = 1,0.\n"
       "Partialkoefficienter for fundamenter bestemmes iht. saet M1 i DS/EN 1997-1 DK NA, "
       "tabel A-4:\n"
       "  Friktionsvinkel:            gamma_phi = 1,2 x gamma_s\n"
       "  Effektiv kohaesion:         gamma_c   = 1,2 x gamma_s\n"
       "  Udraenet forskydningsstyrke: gamma_cu  = 1,8 x gamma_s\n"
       "  Rumvaegt:                   gamma_r   = 1,0 x gamma_s"),
    _n("[Tilpas til projektets geoteknik. Skriv 'Ikke relevant' hvis ikke aktuelt.]"),

    _h("A1.5.2 Beton"),
    _n("[Udfyldes: Angiv eksponeringsklasse, betonstyrke fck, kontrolklasse, "
       "max. stenstorrelse dmax og daeklag for hver konstruktionsdel.\n"
       "Eksempel:\n"
       "  Fundament:  XC2, fck=25 MPa, N, dmax=32, daeklag=25 mm\n"
       "  Terraendaek: XC1, fck=25 MPa, N, dmax=32, daeklag=15 mm\n\n"
       "Armering: Y (ribbet), min. duktilit.kl. B, fyk=550 MPa.\n"
       "Skriv 'Ikke relevant' hvis beton ikke anvendes.]"),

    _h("A1.5.3 Staal"),
    _n("[Udfyldes: Angiv staalstyrke (S235 / S275 / S355), udfoerelsesklasse (EXC2), "
       "krav til svejsning (DS/EN ISO 3834-3) og boltekvalitet (8.8 standardklasse).\n"
       "Skriv 'Ikke relevant' hvis staal ikke anvendes i baerende konstruktioner.]"),

    _h("A1.5.4 Trae"),
    _n("[Udfyldes: Angiv anvendelsesklasse (1 / 2 / 3), limtraeskvalitet (GL24h / GL28h) "
       "og/eller konstruktionstrae-klasse (C18-C40). Angiv kmod og kdef-faktorer.\n"
       "For CLT: henvis til leverandoerdokumentation og DS/EN 1995 FU.\n"
       "Skriv 'Ikke relevant' hvis trae ikke anvendes.]"),

    # ── A1.6 Laster ────────────────────────────────────────────────────────────
    _h("A1.6 Laster"),

    _h("A1.6.1 Lastkombinationer"),
    _t(_LOAD_COMB),

    _h("A1.6.2 Lasttilfaelde"),
    _t("Relevante lasttilfaelde vurderes for hver enkelt bygningsdel i tilhoerende "
       "beregningsafsnit paa baggrund af de paaflagte laster."),

    _h("A1.6.3 Permanente laster"),
    _n("[Udfyldes: Angiv egenlaster for alle konstruktionsdele.\n"
       "Eksempel:\n"
       "  Tagkonstruktion (let tag):  0,5 kN/m²\n"
       "  Etagedaek (CLT 180 mm):     0,9 kN/m²\n"
       "  Parketgulv m. afretning:    0,9 kN/m²\n"
       "  Massivtrae vaeg 120 mm:     0,6 kN/m²\n"
       "  Facadeopbygning:            0,8 kN/m²\n"
       "Kopier fra lastnedfoering.]"),

    _h("A1.6.4 Nyttelast"),
    _t("Nyttelaster fastlaegges iht. DS/EN 1991-1-1 DK NA. Klassificeres som variable "
       "frie laster. Relevante kategorier:\n\n"
       "  Kat. A1 — Bolig og interne adgangsveje: qk=1,5 kN/m², Qk=2,0 kN  "
       "(psi0=0,5 / psi1=0,3 / psi2=0,2)\n"
       "  Inkl. lette skillevagge:                qk=2,0 kN/m²\n"
       "  Kat. A4 — Trapper:                      qk=3,0 kN/m², Qk=2,0 kN\n"
       "  Kat. A5 — Balkoner:                     qk=2,5 kN/m², Qk=2,0 kN\n"
       "  Kat. H  — Tag (ikke tilgaengeligt):     Qk=1,5 kN\n"
       "  Vandret paa vaern, kat. A:              qk,v=0,5 kN/m"),
    _n("[Fjern alle ikke-relevante lastkategorier og tilpas til projektets anvendelse.]"),

    _h("A1.6.5 Vindlast"),
    _n("[Udfyldes: Beregn vindlast iht. DS/EN 1991-1-4 DK NA.\n\n"
       "Basisvindhastighed: vb,0 = 24 m/s (27 m/s i randzonen nær Vestkysten / Ringkoebing Fjord)\n"
       "Arstidsfaktor:   cseason = 1,0 (konservativt)\n"
       "Retningsfaktor:  cdir = 1,0 (konservativt)\n"
       "Terraenkategori: [0 / I / II / III / IV] — se A1.3.1\n"
       "Bygningshoejde:  h = [?] m\n\n"
       "Beregn: vm, Iv, qb, qp og de relevante formfaktorer Cpe,10 for facader og tag.\n"
       "Angiv lastpaavirkning w = Cpe,10 x qp for de styrende zoner.]"),

    _h("A1.6.6 Snelast"),
    _n("[Udfyldes: s = 1,0 kN/m² (hele Danmark, 50-aarsperiode, DS/EN 1991-1-3 DK NA).\n\n"
       "Taghaldning: alpha_1 = [?]°,  alpha_2 = [?]°\n"
       "Termisk faktor:    Ct = 1,0\n"
       "Topografisk faktor: Ctop = 1,0\n"
       "Eksponeringsfaktor: Ce = 1,0\n"
       "Formfaktorer: mu_1 = 0,8 (for alpha <= 30°)\n\n"
       "Undersog tilfaelde (i), (ii) og (iii) jf. DS/EN 1991-1-3 figur 5.3.]"),

    _h("A1.6.7 Geometriske imperfektioner"),
    _t(_IMPERFECTIONS),

    _h("A1.6.8 Ulykkeslaster"),
    _t("Brandlaster: Der regnes med standard brandforlob. Baerende konstruktioner eftervises "
       "for brandpaavirkning. Se afsnit A1.4.6."),
    _n("[Udfyldes: Vurder paakorsels- og eksplosionslaster.\n"
       "Paakorselsslast: Antages haandteret via landskabsplan.\n"
       "Eksplosionslast: Vurderes ikke relevant for naerverende byggeri — begrund.\n"
       "Angiv saerlige tilfealde hvis aktuelt.]"),

    _h("A1.6.9 Seismisk last (vandret masselast)"),
    _t(_SEISMIC),

    _h("A1.6.10 Midlertidige laster"),
    _t("Ikke relevant."),

    # ── A1.7 Bilag ─────────────────────────────────────────────────────────────
    _h("A1.7 Bilag"),
    _n("[Udfyldes: Anfoor bilag i naervaerende dokument.\n"
       "Eksempel:\n"
       "  Bilag A — Geoteknisk rapport, [Raaadgiver], [dato]\n"
       "  Bilag B — Brandstrategi rapport, [Raaadgiver], [dato]\n"
       "  Bilag C — [Andre relevante bilag, fx forureningsrapport, vindundersogelse]]"),
]


# ── A2 — Statiske beregninger ─────────────────────────────────────────────────

A2 = [
    _n("A2 Statiske Beregninger — Dette dokument indeholder de statiske beregninger for "
       "konstruktionsafsnittene beskrevet i A1.1.3 Konstruktionsgrundlag.\n"
       "Der henvises til A1.1 for beregningsgrundlag, normer, laster og materialeparametre."),
    _h("Grundlag og forudsaetninger"),
    _t("Beregninger er udfoert i overensstemmelse med Bygningsreglementet BR18 og "
       "de i A1.2.1 naevnte Eurocodes med tilhoerende Danske nationale annekser."),
    _h("Konstruktionsberegninger"),
    _n("[Tilfoej beregningsblokke (staal / trae / beton / murvaerk) for hvert "
       "konstruktionsafsnit i overensstemmelse med tabel over konstruktionsafsnit "
       "i A1.1.3. Typisk raekkefoolge: fundament, terraendaek, vaegge, etagedaek, "
       "tagkonstruktion, stabilitet.]"),
]


# ── A3 — Konstruktionstegninger og modeller ───────────────────────────────────

A3 = [
    _n("A3 Konstruktionstegninger og modeller — Dette dokument udgoor "
       "dokumentfortegnelsen over konstruktionstegninger og modeller."),
    _h("Dokumentfortegnelse"),
    _n("[Udfyldes: Anfoor alle konstruktionstegninger med:\n"
       "  Tegnings-nr. | Titel | Revision | Dato | Ansvarlig\n\n"
       "Eksempel:\n"
       "  K001 — Fundering, plan og detaljer | Rev. A | [dato]\n"
       "  K002 — Baerende konstruktioner, plan stue | Rev. A | [dato]\n"
       "  K003 — Baerende konstruktioner, plan 1. sal | Rev. A | [dato]\n"
       "  K004 — Baerende konstruktioner, snit | Rev. A | [dato]\n"
       "  K100 — Generel note, materialer | Rev. A | [dato]]"),
    _h("Modeller"),
    _n("[Angiv beregningsmodeller der er anvendt (FEM-modeller m.v.) med filnavn og "
       "dato. Udbygges ifm. projektering.]"),
]


# ── A4 — Konstruktionsaendringer ──────────────────────────────────────────────

A4 = [
    _n("A4 Konstruktionsaendringer — Dette dokument registrerer aendringer i "
       "konstruktionsdokumentationen efter foerste udgivelse."),
    _h("AEndringsregister"),
    _n("[Udfyldes: For hver aendring angives:\n"
       "  Aendring-nr. | Dato | Beskrivelse af aendring | Paavirket dok. | Udarbejdet af | Godkendt af\n\n"
       "Eksempel:\n"
       "  AE001 | [dato] | Fundering aendret fra stribefundament til punktfundament pga. geoteknik | "
       "A1.1.3, A2.2.1 | [initialer] | [initialer]]"),
]


# ── B1 — Statisk projekteringsrapport ─────────────────────────────────────────

B1 = [
    _n("B1 Statisk Projekteringsrapport — Rapporten samler de vaesentligste konklusioner "
       "fra den statiske projektering og henvender sig til bygherre og myndigheder."),
    _h("Projektbeskrivelse"),
    _n("[Udfyldes: Kort beskrivelse af bygvaerket — samme overskrift som A1.1.1, "
       "men kortere og i ikke-teknisk sprog.]"),
    _h("Statisk system og konstruktionsprincipper"),
    _n("[Udfyldes: Beskriv i korte traek det baerende og stabiliserende system. "
       "Materialer, spandvidderne og de vaesentligste konstruktionsdele.]"),
    _h("Konsekvensklasse og konstruktionsklasse"),
    _n("[Udfyldes: Angiv CC og KK med kort begrundelse — se A1.2.2.]"),
    _h("Laster"),
    _n("[Udfyldes: Opsummér de styrende laster: egenlast, nyttelast, vindlast, snelast.]"),
    _h("Fundamentering"),
    _n("[Udfyldes: Beskriv funderingsprincip og geotekniske forudsaetninger.]"),
    _h("Materialeparametre"),
    _n("[Udfyldes: Opsummér de valgte konstruktionsmaterialer med styrker og klasser.]"),
    _h("Kontrol og godkendelse"),
    _n("[Udfyldes: Beskriv kontrolniveau iht. KK-klasse. Angiv hvem der har beregnet, "
       "kontrolleret og godkendt dokumentationen — se forsiden.]"),
    _h("Konklusion"),
    _n("[Udfyldes: Konkludér at konstruktionerne er dimensioneret iht. gaeldende normer "
       "og bygningsreglementet og er tilstraekkelig sikre og robuste til den paataenkte "
       "anvendelse.]"),
]


# ── B2 — Statisk kontrolplan ──────────────────────────────────────────────────

B2 = [
    _n("B2 Statisk Kontrolplan — Kontrolplanen beskriver, hvordan den statiske "
       "dokumentation kontrolleres iht. konstruktionsklasse og kraev i BR18 / SBi 271."),
    _h("Kontrolomfang"),
    _n("[Udfyldes: Angiv konstruktionsklasse (KK2) og det kraevede kontrolniveau:\n"
       "  KK2 — Udvidet egenkontrol (baade projektering og udforelse)\n"
       "  KK3 — Tredjeparts kontrol kraeves\n"
       "  KK4 — Saerlig kontrol kraeves\n"
       "Henvis til SBi 271, tabel 6.1 for kraevene.]"),
    _h("Kontrolorganisation"),
    _n("[Udfyldes: Angiv hvem der udforer kontrol:\n"
       "  Beregnet af:     [navn / initialer]\n"
       "  Kontrolleret af: [navn / initialer]\n"
       "  Godkendt af:     [navn / initialer]\n"
       "  Tredjepart:      [firmanavn] (kraeves ved KK3/KK4)]"),
    _h("Kontrolplan — projektering"),
    _n("[Udfyldes: Tabel over hvilke dokumenter der kontrolleres og paa hvilken maoade.\n"
       "Kolonner: Dokument | Kontroltype | Ansvarlig | Dato | Kontrol udfoert\n\n"
       "Eksempel:\n"
       "  A1.1 Konstruktionsgrundlag | Gennemlasning | [initialer] | [dato] | Ja\n"
       "  A2.1 Beregninger bygvaerk  | Stikproevekontrol | [initialer] | [dato] | Ja]"),
    _h("Kontrolplan — udforelse"),
    _n("[Udfyldes: Angiv tilsynsaktiviteter paa byggepladsen iht. kontrolklasse.\n"
       "Eksempel:\n"
       "  Fundament — kontrol af udgravning og betonstoebning\n"
       "  Elementmontage — kontrol af samlinger og afstivning\n"
       "  Slutkontrol — kontrol af faerdigmelding]"),
]


# ── B3 — Statisk kontrolrapport / tilsynsrapport ──────────────────────────────

B3 = [
    _n("B3 Statisk Kontrolrapport — Rapporten dokumenterer resultaterne af den "
       "statiske kontrol iht. B2 Statisk Kontrolplan."),
    _h("Kontrol af projekterende dokumentation"),
    _n("[Udfyldes: Anfoor resultater af gennemfoert kontrolaktiviteter.\n"
       "Kolonner: Dokument | Kontroltype | Kontrolleret af | Dato | Resultat | Bemaerkning]"),
    _h("Afvigelser og korrektioner"),
    _n("[Udfyldes: Anfoor alle konstaterede afvigelser og de korrektioner der er foretaget.\n"
       "Skriv 'Ingen afvigelser konstateret' hvis kontrollen forloeb uden anmaerkninger.]"),
    _h("Tilsynsrapporter"),
    _n("[Udfyldes: Referer til evt. tilsynsrapporter fra byggepladsbesoeg.\n"
       "Anfoor dato, hvem der udfoerte tilsynet og konklusionerne.]"),
    _h("Konklusion"),
    _n("[Udfyldes: Konkludér at den statiske dokumentation og/eller udfoereisen er "
       "kontrolleret iht. kontrolplanen og opfylder kravene i BR18 og gaeldende normer.]"),
    _h("Underskrifter"),
    _n("[Udfyldes: Kontrollen er udfoert af:\n"
       "  Kontrolleret af: ___________________ ([initialer])  Dato: ___________\n"
       "  Godkendt af:     ___________________ ([initialer])  Dato: ___________]"),
]


# ── Registry ──────────────────────────────────────────────────────────────────

DOC_TEMPLATES = {
    "A1": A1,
    "A2": A2,
    "A3": A3,
    "A4": A4,
    "B1": B1,
    "B2": B2,
    "B3": B3,
}
