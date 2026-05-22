"""
templates.py — Standard document templates (A1-B3).

Each template is a list of block dicts (no 'id' fields — assigned at load time).
Only inline block types are used: heading, text, note.

Design principles:
  - One heading per logical section
  - Standard/reusable content → text block (pre-filled, edit as needed)
  - Project-specific content → note block (orange placeholder)
  - Related short paragraphs are merged into one block
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _h(text):
    return {"type": "heading", "text": text}

def _t(text):
    return {"type": "text", "text": text}

def _n(text):
    return {"type": "note", "text": text}


# ── Reusable standard strings ─────────────────────────────────────────────────

_NORMS = """\
Eurocode 0 — Konstruktioners sikkerhed
DS/EN 1990 DK NA:2024 — Projekteringsgrundlag for baerende konstruktioner

Eurocode 1 — Laster paa konstruktioner
DS/EN 1991-1-1 DK NA:2024 — Densiteter, egenlast og nyttelast
DS/EN 1991-1-2 DK NA:2014 — Brandlast
DS/EN 1991-1-3 DK NA:2015 — Snelast
DS/EN 1991-1-4 DK NA:2015 — Vindlast
DS/EN 1991-1-7 DK NA:2013 — Ulykkeslast

Eurocode 2 — Betonkonstruktioner
DS/EN 1992-1-1 DK NA:2021 — Generelle regler samt regler for bygningskonstruktioner

Eurocode 3 — Staalkonstruktioner
DS/EN 1993-1-1 DK NA:2019 — Generelle regler samt regler for bygningskonstruktioner

Eurocode 5 — Traekonstruktioner
DS/EN 1995-1-1 DK NA:2019 — Almindelige regler samt regler for bygningskonstruktioner

Eurocode 6 — Murvaerkskonstruktioner
DS/EN 1996-1-1 DK NA:2019 — Generelle regler for armeret og uarmeret murvaerk

Eurocode 7 — Geoteknik
DS/EN 1997-1 DK NA:2021 — Geoteknik, Del 1: Generelle regler

Ovenstaaende omfatter ogsaa gaeldende Nationale annekser.\
"""

_LOAD_COMB = """\
LAK 1 — Anvendelsesgraensetilstand (SLS)
Haandteres under den enkelte bygningsdel med udgangspunkt i karakteristiske laster.

LAK 2 — Brudgraensetilstand (ULS)
  LAK 2.1  Nyttelast dominerende:  KFI x (Gsup + 1,5 x (Q + psi_S x S + psi_V x V))
  LAK 2.2  Snelast dominerende:    KFI x (Gsup + 1,5 x (psi_Q x Q + S + psi_V x V))
  LAK 2.3  Vindlast dominerende:   KFI x (Gsup + 1,5 x (psi_Q x Q + V))
  LAK 2.4  Vindlast dominerende:   0,9 x Ginf + 1,5 x KFI x V
  LAK 2.5  Egenlast dominerende:   1,2 x KFI x Gsup

LAK 3 — Ulykkesgrensetilstand / brand
  LAK 3.1  Nyttelast primaer:  Gsup + psi_Q1 x Q
  LAK 3.2  Snelast primaer:    Gsup + psi_Q2 x Q + psi_S1 x S
  LAK 3.3  Vindlast primaer:   Gsup + psi_Q2 x Q + psi_V1 x V

Afvigelser fra ovenstaaende lastkombinationer noteres ved den enkelte lastnedforing.\
"""

_IMPERFECTIONS = """\
Geometriske imperfektioner haandteres iht. DS/EN 1992-1-1 som aekvivalente horisontale laster.

Bygningens overordnede stabilitet:
  theta_i = theta_0 x alpha_h x alpha_m
  theta_0 = 1/200  (basisvaerdi)
  alpha_h = 2/sqrt(l),   2/3 <= alpha_h <= 1
  alpha_m = sqrt(0,5 x (1 + 1/m))

Enkeltstaende baerende konstruktionsdele i afstivede systemer:
  e_i = l_0 / 400\
"""

_SEISMIC = """\
Seismisk last iht. DS/EN 1990 DK NA, Tabel A1.3 DK NA:
  Ad = (a_seis / g) x (sum Gk,j + psi_2,i x Qk,i)  =  1,5% x (sum Gk,j + psi_2,i x Qk,i)

Konstruktioner undersoges ikke for seismisk last og vindlast virkende samtidigt.
Vindlast er dimensionsgivende naer:  Ad < 1,67 x KFI x Wk\
"""


# ── A1 — Konstruktionsgrundlag ────────────────────────────────────────────────

A1 = [

    # ── Intro ──────────────────────────────────────────────────────────────────
    _n(
        "[Udfyldes: Angiv om dette dokument er startudgaven (myndighedsprojekt), "
        "projekteringsudgaven (hovedprojekt) eller faerdigmeldingen.\n\n"
        "Nærværende statiske dokumentation er opbygget iht. Bygningsreglementet (BR18) "
        "og er i overensstemmelse med SBi 271, 3. udg.]"
    ),

    # ── A1.1 Bygværk ───────────────────────────────────────────────────────────
    _h("A1.1 Bygvaerk"),

    _n(
        "A1.1.1 Bygvaerkets art og anvendelse\n"
        "[Udfyldes: Beskriv bygvaerkets type og anvendelse (bolig, erhverv, industri), "
        "antal etager, samlet areal og boligtyper. Indsaet visualisering / opstalt som figur.]\n\n"
        "A1.1.2 Konstruktioners art og opbygning\n"
        "[Udfyldes: Beskriv det baerende og stabiliserende system — materialer, princip for "
        "lodret og vandret lastnedfoering, tagkonstruktion og fundamentering. "
        "Indsaet oversigtsplan og -snit.]\n\n"
        "A1.1.3 Konstruktionsafsnit\n"
        "[Udfyldes: Tabel — Afsnit-nr. | Afsnit | CC / KK | Ansvarlig\n"
        "Eks: A2.2.1 | Fundament | CC2 / KK2 | [Firma]]"
    ),

    _h("A1.1.4 Udforelse"),
    _t(
        "Projektet udfoeres i [totalentreprise / fagentreprise] som traditionelt "
        "[element- / monolitisk] byggeri med foelgende hovedaktiviteter:\n"
        "1. Jordarbejder\n"
        "2. Stoebning af fundamenter og terraendaek\n"
        "3. Montage / opforelse af vaegkonstruktioner\n"
        "4. Montage / stoebning af etagedaek\n"
        "5. Tagkonstruktion og -opbygning\n"
        "6. Facadeopbygning / aptering"
    ),
    _n("[Tilpas til projektets entrepriseform og konstruktionsprincip.]"),

    # ── A1.2 Grundlag ──────────────────────────────────────────────────────────
    _h("A1.2 Grundlag"),

    _h("A1.2.1 Normer og standarder"),
    _t(_NORMS),
    _n("[Tilpas normlisten: fjern normer der ikke er relevante for dette projekt.]"),

    _h("A1.2.2 Konsekvensklasse og konstruktionsklasse"),
    _n(
        "[Udfyldes: Angiv CC og KK med begrundelse iht. DS/INF 1990:2021 tabel 2.\n"
        "Dokumenter at projektet opfylder ID-kriterierne (stoerste spand, hoejde, etager).\n\n"
        "Eks: CC2 — stoerste spand 9 m < 16 m (ID1), max. 2 etager < 5 (ID1). => KK2.]"
    ),

    _h("A1.2.3-2.5 Sikkerhed, IKT og referencer"),
    _t(
        "Kontrolklasse: Alle bygningsdele henfoeres til normal kontrolklasse.\n"
        "Miljoeklasse: Fastlaegges for de enkelte bygningsdele under hensyn til placering i byggeriet.\n"
        "Levetid: Kategori 4, forventet levetid 50 aar (DS/EN 1990 tabel 2.1).\n"
        "Udfoerelsesklasse: EXC2 iht. DS/EN 1990 FU:2021.\n\n"
        "Referencer:\n"
        "[1] Bygningsreglement BR18\n"
        "[2] SBi-anvisning 271, 3. udgave — Dokumentation og kontrol af baerende konstruktioner\n"
        "[3] Teknisk Staabi, seneste udgave"
    ),
    _n(
        "[Udfyldes:\n"
        "- Geoteknisk kategori (typisk GK2)\n"
        "- Software / IKT-vaerktojer (RFEM, Tedds, Revit, Excel m.m.)\n"
        "- Projektspecifikke referencer (geoteknisk rapport, brandstrategi, leverandoerdok.)]"
    ),

    # ── A1.3 Forundersøgelser ──────────────────────────────────────────────────
    _h("A1.3 Forundersoegelser"),

    _n(
        "A1.3.1 Grunden og lokale forhold\n"
        "[Udfyldes: Beliggenhed, terraenkarakter og terraenkategori iht. DS/EN 1991-1-4 DK NA "
        "tabel 4.1 (0 / I / II / III / IV) ud fra vurdering af omgivelserne inden for 1-km radius. "
        "Angiv terraenkoter og evt. terraenregulering.]\n\n"
        "A1.3.2 Geotekniske forhold\n"
        "[Udfyldes: Henvis til geoteknisk undersoegelse (bilag). Angiv funderingsmetode, "
        "frostfri dybde (min. 0,9 m u. fremtidigt terraen), styrkepar. (phi_k, c_u,k, gamma) "
        "og funderingsniveau OSBL.]\n\n"
        "A1.3.3-3.4 Miljoetekniske og eksisterende forhold\n"
        "[Udfyldes: Evt. forureningsklasse. Beskriv eksisterende konstruktioner paa matriklen "
        "— skriv 'Ingen eksisterende konstruktioner' hvis relevant.]"
    ),

    _t("A1.3.5-3.6 Tilstodende bygvaerker: Ikke relevant for denne dokumentation."),
    _n("[Erstat med beskrivelse hvis nabobygninger kan pavirkes af byggeriet.]"),

    # ── A1.4 Konstruktioner ────────────────────────────────────────────────────
    _h("A1.4 Konstruktioner"),

    _n(
        "A1.4.1 Statisk virkemaade\n"
        "[Udfyldes: Beskriv lodret og vandret lastnedfoering med skitser / figurer.\n"
        "Lodret: hvad baerer hvad — tag => facader / skillevagge => fundament.\n"
        "Vandret: skivevirkning — daekskiver, stabiliserende vaegge, fundament.\n"
        "Indsaet principskitser som figurer.]"
    ),

    _h("A1.4.2 Deformationer, vibrationer og robusthed"),
    _t(
        "Acceptable deformationer iht. nationale annekser:\n"
        "  Beton: L/250 (kv.perm.)  |  L/400 (variabel last)\n"
        "  Staal: L/400 (kv.perm.)  |  L/400 (variabel, etageadskillelse)\n"
        "  Trae:  L/400 (G + Q)     |  L/250 (karakteristisk vindlast)\n\n"
        "Vibrationer — boliger (DS/EN 1990 DK NA tabel A1.4):\n"
        "  Egenfrekvens: ne > 8 Hz  |  Graenseacceleration: < 0,1 % g\n\n"
        "Levetid: Kategori 4 — 50 aar ved opfyldelse af god byggeskik uden saerlige tiltag.\n"
        "Udfoerelsesklasse: EXC2 iht. DS/EN 1990 FU:2021."
    ),
    _n(
        "[Udfyldes: Robusthed iht. DS/EN 1990 DK NA:2024 Anneks E.\n"
        "CC2: maks. kollapsomfang 240 m² pr. etage / 360 m² samlet.\n"
        "Traekforbindelser: Ftie,per = li x 7,5 kN/m (> 8 kN).\n"
        "Dokumentation udfoeres i A2 Statiske beregninger.\n\n"
        "Brandklasse: [BK1 / BK2 / BK3 / BK4] iht. brandstrategi (bilag).\n"
        "Brandmodstandskrav for baerende bygningsdele: [REI xx / R xx] jf. BR18 kap. 3.]"
    ),

    # ── A1.5 Konstruktionsmaterialer ───────────────────────────────────────────
    _h("A1.5 Konstruktionsmaterialer"),

    _t(
        "Geoteknik: Alle permanente konstruktioner henfoeres til geoteknisk kategori 2, "
        "modelfaktor gamma_s = 1,0. Partialkoefficienter iht. saet M1 i DS/EN 1997-1 DK NA tabel A-4:\n"
        "  Friktionsvinkel:             gamma_phi = 1,2\n"
        "  Effektiv kohaesion:          gamma_c   = 1,2\n"
        "  Udraenet forskydningsstyrke: gamma_cu  = 1,8\n"
        "  Rumvaegt:                    gamma_r   = 1,0"
    ),
    _n(
        "[Udfyldes:\n\n"
        "Beton — angiv for hver konstruktionsdel: eksponeringsklasse, fck, kontrolklasse, "
        "dmax og daeklag.\n"
        "Eks: Fundament: XC2, fck=25 MPa, N, dmax=32, daeklag=25 mm\n\n"
        "Staal — styrke (S235/S275/S355), EXC2, svejsning (DS/EN ISO 3834-3), bolte 8.8.\n\n"
        "Trae — anvendelsesklasse (1/2/3), kvalitet (GL24h / C24), kmod og kdef.\n\n"
        "Skriv 'Ikke relevant' for materialer der ikke anvendes.]"
    ),

    # ── A1.6 Laster ────────────────────────────────────────────────────────────
    _h("A1.6 Laster"),

    _h("A1.6.1 Lastkombinationer"),
    _t(_LOAD_COMB),

    _h("A1.6.2-6.6 Laster"),
    _t(
        "Nyttelaster iht. DS/EN 1991-1-1 DK NA:\n"
        "  Kat. A1 Bolig / adgangsveje:  qk = 1,5 kN/m²  (+ 0,5 kN/m² lette skillevagge)\n"
        "  Kat. A4 Trapper:              qk = 3,0 kN/m²\n"
        "  Kat. A5 Balkoner:             qk = 2,5 kN/m²\n"
        "  Kat. H  Tag (utilgaengeligt): Qk = 1,5 kN\n"
        "  Vandret paa vaern kat. A:     qk,v = 0,5 kN/m"
    ),
    _n(
        "[Udfyldes:\n\n"
        "Permanente laster — angiv egenlaster for alle konstruktionsdele (kN/m²):\n"
        "  Tagkonstruktion:  [?] kN/m²\n"
        "  Etagedaek:        [?] kN/m²\n"
        "  Gulvopbygning:    [?] kN/m²\n"
        "  Ydervaegsopbygning: [?] kN/m²\n\n"
        "Vindlast iht. DS/EN 1991-1-4 DK NA:\n"
        "  vb,0 = 24 m/s  |  Terraenkategori: [0/I/II/III/IV]  |  h = [?] m\n"
        "  Beregn vm, Iv, qb, qp og formfaktorer Cpe,10 for facader og tag.\n\n"
        "Snelast: s = 1,0 kN/m² (hele Danmark). mu_1 = 0,8 (alpha <= 30 grader).\n"
        "Undersoeg tilfaelde (i), (ii) og (iii) jf. DS/EN 1991-1-3 figur 5.3.\n\n"
        "Ulykkeslaster — vurder paakorsels- og eksplosionslast. Angiv saerlige tilpaeldge.]"
    ),

    _h("A1.6.7-6.9 Imperfektioner og seismisk last"),
    _t(_IMPERFECTIONS + "\n\n" + _SEISMIC),

    # ── A1.7 Bilag ─────────────────────────────────────────────────────────────
    _h("A1.7 Bilag"),
    _n(
        "[Udfyldes: Anfoor bilag:\n"
        "  Bilag A — Geoteknisk rapport, [Raadgiver], [dato]\n"
        "  Bilag B — Brandstrategi, [Raadgiver], [dato]\n"
        "  Bilag C — [Andre relevante bilag]]"
    ),
]


# ── A2 — Statiske beregninger ─────────────────────────────────────────────────

A2 = [
    _n(
        "A2 Statiske beregninger\n\n"
        "Dette dokument indeholder de statiske beregninger for konstruktionsafsnittene "
        "beskrevet i A1.1.3. Beregningsgrundlag, normer, laster og materialeparametre "
        "fremgaar af A1 Konstruktionsgrundlag."
    ),
    _h("Fundament og geoteknik"),
    _n("[Indsaet beregningsblokke for fundament — brug + Calculation block nedenfor.]"),
    _h("Baerende vaegge og daek"),
    _n("[Indsaet beregningsblokke for vaegge og daek.]"),
    _h("Tagkonstruktion"),
    _n("[Indsaet beregningsblokke for tagkonstruktion.]"),
    _h("Stabilitet"),
    _n("[Indsaet beregningsblokke for vandret stabilitet, skiver og samlinger.]"),
]


# ── A3 — Konstruktionstegninger og modeller ───────────────────────────────────

A3 = [
    _n(
        "A3 Konstruktionstegninger og modeller\n\n"
        "Dette dokument udgoor dokumentfortegnelsen over konstruktionstegninger og modeller."
    ),
    _h("Dokumentfortegnelse"),
    _n(
        "[Udfyldes: Anfoor alle konstruktionstegninger:\n"
        "  Tegnings-nr. | Titel | Revision | Dato | Ansvarlig\n\n"
        "  K001 — Fundering, plan og detaljer | Rev. A | [dato]\n"
        "  K002 — Baerende konstruktioner, plan stue | Rev. A | [dato]\n"
        "  K003 — Baerende konstruktioner, plan 1. sal | Rev. A | [dato]\n"
        "  K004 — Baerende konstruktioner, snit | Rev. A | [dato]\n"
        "  K100 — Generel note, materialer | Rev. A | [dato]]"
    ),
    _h("Beregningsmodeller"),
    _n("[Angiv FEM-modeller og andre beregningsmodeller med filnavn og dato.]"),
]


# ── A4 — Konstruktionsændringer ───────────────────────────────────────────────

A4 = [
    _n(
        "A4 Konstruktionsaendringer\n\n"
        "Registrerer aendringer i konstruktionsdokumentationen efter foerste udgivelse."
    ),
    _h("Aendringsregister"),
    _n(
        "[Udfyldes: For hver aendring:\n"
        "  Nr. | Dato | Beskrivelse | Paavirket dok. | Udarbejdet | Godkendt\n\n"
        "  AE001 | [dato] | [Beskrivelse af aendring] | [dok. ref.] | [ini.] | [ini.]]"
    ),
]


# ── B1 — Statisk projekteringsrapport ─────────────────────────────────────────

B1 = [
    _n(
        "B1 Statisk Projekteringsrapport\n\n"
        "Rapporten samler de vaesentligste konklusioner fra den statiske projektering "
        "og henvender sig til bygherre og myndigheder."
    ),
    _h("Projektbeskrivelse og statisk system"),
    _n(
        "[Udfyldes: Kort ikke-teknisk beskrivelse af bygvaerket.\n"
        "Beskriv det baerende og stabiliserende system — materialer, "
        "spaendvidderne og de vaesentligste konstruktionsdele.]"
    ),
    _h("Konsekvensklasse, konstruktionsklasse og laster"),
    _n(
        "[Udfyldes: Angiv CC og KK med begrundelse (se A1.2.2).\n"
        "Opsummér styrende laster: egenlast, nyttelast, vindlast, snelast.]"
    ),
    _h("Fundamentering og materialeparametre"),
    _n(
        "[Udfyldes: Funderingsprincip og geotekniske forudsaetninger.\n"
        "Opsummér konstruktionsmaterialer med styrker og klasser.]"
    ),
    _h("Kontrol, godkendelse og konklusion"),
    _n(
        "[Udfyldes: Beskriv kontrolniveau iht. KK-klasse. Angiv beregnet / kontrolleret / godkendt af.\n\n"
        "Konklusion: Konstruktionerne er dimensioneret iht. gaeldende normer og BR18 og er "
        "tilstraekkelig sikre og robuste til den paataenkte anvendelse.]"
    ),
]


# ── B2 — Statisk kontrolplan ──────────────────────────────────────────────────

B2 = [
    _n(
        "B2 Statisk Kontrolplan\n\n"
        "Kontrolplanen beskriver, hvordan den statiske dokumentation kontrolleres "
        "iht. konstruktionsklasse og krav i BR18 / SBi 271."
    ),
    _h("Kontrolomfang og -organisation"),
    _n(
        "[Udfyldes: Angiv KK-klasse og kraevet kontrolniveau:\n"
        "  KK2 — Udvidet egenkontrol\n"
        "  KK3 — Tredjeparts kontrol\n"
        "  KK4 — Saerlig kontrol\n\n"
        "  Beregnet af:     [navn / initialer]\n"
        "  Kontrolleret af: [navn / initialer]\n"
        "  Godkendt af:     [navn / initialer]\n"
        "  Tredjepart:      [firmanavn] (kun KK3/KK4)]"
    ),
    _h("Kontrolplan — projektering"),
    _n(
        "[Udfyldes: Dokument | Kontroltype | Ansvarlig | Dato | Udfoert\n\n"
        "  A1 Konstruktionsgrundlag      | Gennemlaesning       | [ini.] | [dato] | Ja/Nej\n"
        "  A2 Statiske beregninger       | Stikproevekontrol    | [ini.] | [dato] | Ja/Nej\n"
        "  A3 Konstruktionstegninger     | Gennemlaesning       | [ini.] | [dato] | Ja/Nej]"
    ),
    _h("Kontrolplan — udforelse"),
    _n(
        "[Udfyldes: Tilsynsaktiviteter paa byggepladsen:\n"
        "  - Fundament: kontrol af udgravning og betonstoebning\n"
        "  - Elementmontage: kontrol af samlinger og afstivning\n"
        "  - Slutkontrol: kontrol af faerdigmelding]"
    ),
]


# ── B3 — Statisk kontrolrapport ───────────────────────────────────────────────

B3 = [
    _n(
        "B3 Statisk Kontrolrapport\n\n"
        "Dokumenterer resultaterne af den statiske kontrol iht. B2 Statisk Kontrolplan."
    ),
    _h("Kontrol af projekterende dokumentation"),
    _n(
        "[Udfyldes: Dokument | Kontroltype | Kontrolleret af | Dato | Resultat | Bemaerkning\n\n"
        "Angiv alle gennemfoerte kontrolaktiviteter med resultat.]"
    ),
    _h("Afvigelser og tilsynsrapporter"),
    _n(
        "[Udfyldes: Anfoor konstaterede afvigelser og de korrektioner der er foretaget.\n"
        "Skriv 'Ingen afvigelser konstateret' hvis kontrollen forloeb uden anmaerkninger.\n\n"
        "Referer til evt. tilsynsrapporter fra byggepladsbesoeg (dato, hvem, konklusioner).]"
    ),
    _h("Konklusion og underskrifter"),
    _n(
        "[Udfyldes: Den statiske dokumentation og/eller udfoereisen er kontrolleret "
        "iht. kontrolplanen og opfylder kravene i BR18 og gaeldende normer.\n\n"
        "  Kontrolleret af: ___________________ ([ini.])  Dato: ___________\n"
        "  Godkendt af:     ___________________ ([ini.])  Dato: ___________]"
    ),
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
