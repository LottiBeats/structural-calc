"""
templates.py -- Standard document templates (A1-B3).

Each template is a list of block dicts (no 'id' fields -- assigned at load time).
Block types used: heading, text, note, figure, table.

Design principles:
  - One heading per logical section
  - Standard/reusable content -> text block (pre-filled, edit as needed)
  - Project-specific content -> note block (orange placeholder)
  - Figure placeholders -> figure block (empty path, descriptive caption)
  - Tabular data -> table block (pre-filled headers and example rows)
  - Related short paragraphs are merged into one block
"""

# -- Helpers ------------------------------------------------------------------

def _h(text):
    return {"type": "heading", "text": text}

def _t(text):
    return {"type": "text", "text": text}

def _n(text):
    return {"type": "note", "text": text}

def _f(caption):
    """Figure placeholder -- empty path, descriptive caption."""
    return {"type": "figure", "path": "", "caption": caption, "width": "full"}

def _tbl(headers, rows, caption=""):
    """Table block with pre-filled headers and rows."""
    return {"type": "table", "caption": caption, "headers": headers, "rows": rows}


# -- Reusable standard strings ------------------------------------------------

_NORMS = """\
Eurocode 0 -- Konstruktioners sikkerhed
DS/EN 1990 DK NA:2024 -- Projekteringsgrundlag for baerende konstruktioner

Eurocode 1 -- Laster paa konstruktioner
DS/EN 1991-1-1 DK NA:2024 -- Densiteter, egenlast og nyttelast
DS/EN 1991-1-2 DK NA:2014 -- Brandlast
DS/EN 1991-1-3 DK NA:2015 -- Snelast
DS/EN 1991-1-4 DK NA:2015 -- Vindlast
DS/EN 1991-1-7 DK NA:2013 -- Ulykkeslast

Eurocode 2 -- Betonkonstruktioner
DS/EN 1992-1-1 DK NA:2021 -- Generelle regler samt regler for bygningskonstruktioner

Eurocode 3 -- Staalkonstruktioner
DS/EN 1993-1-1 DK NA:2019 -- Generelle regler samt regler for bygningskonstruktioner

Eurocode 5 -- Traekonstruktioner
DS/EN 1995-1-1 DK NA:2019 -- Almindelige regler samt regler for bygningskonstruktioner

Eurocode 6 -- Murvaerkskonstruktioner
DS/EN 1996-1-1 DK NA:2019 -- Generelle regler for armeret og uarmeret murvaerk

Eurocode 7 -- Geoteknik
DS/EN 1997-1 DK NA:2021 -- Geoteknik, Del 1: Generelle regler

Ovenstaaende omfatter ogsaa gaeldende Nationale annekser.\
"""

_LOAD_COMB = """\
LAK 1 -- Anvendelsesgraensetilstand (SLS)
Haandteres under den enkelte bygningsdel med udgangspunkt i karakteristiske laster.

LAK 2 -- Brudgraensetilstand (ULS)
  LAK 2.1  Nyttelast dominerende:  KFI x (Gsup + 1,5 x (Q + psi_S x S + psi_V x V))
  LAK 2.2  Snelast dominerende:    KFI x (Gsup + 1,5 x (psi_Q x Q + S + psi_V x V))
  LAK 2.3  Vindlast dominerende:   KFI x (Gsup + 1,5 x (psi_Q x Q + V))
  LAK 2.4  Vindlast dominerende:   0,9 x Ginf + 1,5 x KFI x V
  LAK 2.5  Egenlast dominerende:   1,2 x KFI x Gsup

LAK 3 -- Ulykkesgrensetilstand / brand
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


# -- A1 -- Konstruktionsgrundlag ----------------------------------------------

A1 = [

    # -- Intro -----------------------------------------------------------------
    _n(
        "[Udfyldes: Angiv om dette dokument er startudgaven (myndighedsprojekt), "
        "projekteringsudgaven (hovedprojekt) eller faerdigmeldingen.\n\n"
        "Naervaerende statiske dokumentation er opbygget iht. Bygningsreglementet (BR18) "
        "og er i overensstemmelse med SBi 271, 3. udg.]"
    ),

    # -- A1.1 Bygvaerk ---------------------------------------------------------
    _h("A1.1 Bygvaerk"),

    _h("A1.1.1 Bygvaerkets art og anvendelse"),
    _n(
        "[Udfyldes: Beskriv bygvaerkets type og anvendelse (bolig, erhverv, industri), "
        "antal etager, samlet areal og boligtyper.\n\n"
        "Eks:\n"
        "Bygningen er en etagebebyggelse i [antal] etager med [?] m2 samlet bruttoareal. "
        "Bygningen anvendes som [bolig / erhverv / blandet]. "
        "Stueetagen indeholder [?] og etage 1-[?] indeholder [boliger / kontorer].]"
    ),
    _f("Figur 1.1 -- Visualisering / opstalt"),

    _h("A1.1.2 Konstruktioners art og opbygning"),
    _n(
        "[Udfyldes: Beskriv det baerende og stabiliserende system.\n\n"
        "Lodret lastnedfoering: Beskriv hvilke konstruktionsdele der tager vertikale laster "
        "(tag -> etageadskillelser -> vaegge -> fundament).\n\n"
        "Vandret lastnedfoering: Beskriv stabiliserende system (skivevirkende daek, stabiliserende "
        "vaegge, kerne, facaderammer). Angiv retning og fordeling.\n\n"
        "Fundamentering: Beskriv funderingsprincip (direkte / paeledrevet / pilotering).]"
    ),
    _f("Figur 1.2 -- Oversigtsplan"),
    _f("Figur 1.3 -- Oversigtssnit"),
    _f("Figur 1.4 -- Oversigtsplan, baerende konstruktioner"),
    _f("Figur 1.5 -- Oversigtssnit, baerende konstruktioner"),

    _h("A1.1.3 Konstruktionsafsnit"),
    _n("[Udfyldes: Opdater tabellen nedenfor med projektets konstruktionsafsnit og ansvarsfordeling.]"),
    _tbl(
        headers=["Afsnit-nr.", "Beskrivelse", "CC / KK", "Ansvarlig"],
        rows=[
            ["A2.1", "Fundament og geoteknik",        "CC2 / KK2", ""],
            ["A2.2", "Baerende vaegge",                "CC2 / KK2", ""],
            ["A2.3", "Etagedaek",                     "CC2 / KK2", ""],
            ["A2.4", "Tagkonstruktion",                "CC2 / KK2", ""],
            ["A2.5", "Stabilitet -- vandret lastnedf.", "CC2 / KK2", ""],
        ],
        caption="Tabel 1.1 -- Konstruktionsafsnit",
    ),

    _h("A1.1.4 Udfoereise og entreprise"),
    _t(
        "Projektet udfoeres i [totalentreprise / fagentreprise] som [element- / monolitisk] "
        "byggeri med foelgende hovedaktiviteter:\n"
        "1. Jordarbejder og udgravning\n"
        "2. Stoebning af fundamenter og terraendaek\n"
        "3. Montage / opforelse af baerende vaegge\n"
        "4. Montage / stoebning af etagedaek\n"
        "5. Tagkonstruktion og tagopbygning\n"
        "6. Facadeopbygning og aptering"
    ),
    _n("[Tilpas til projektets entrepriseform og konstruktionsprincip.]"),

    _h("A1.1.5 Beskrivelser, modeller og tegninger"),
    _n(
        "[Udfyldes: Angiv hvilke supplerende beskrivelser, beregningsmodeller og tegninger "
        "der indgaar i dokumentationen:\n\n"
        "  Beregningsmodel: [FEM-program, version, filnavn]\n"
        "  Konstruktionstegninger: [tegningsliste eller reference til A3]\n"
        "  Leverandoerberegninger: [liste over leverandoerdokumentation]\n"
        "  Brandstrategi: [reference]\n"
        "  Geoteknisk rapport: [reference]]"
    ),

    # -- A1.2 Grundlag ---------------------------------------------------------
    _h("A1.2 Grundlag"),

    _h("A1.2.1 Normer og standarder"),
    _t(_NORMS),
    _n("[Tilpas normlisten: fjern normer der ikke er relevante for dette projekt.]"),

    _h("A1.2.2 Konsekvensklasse og konstruktionsklasse"),
    _t(
        "Konsekvensklasse (CC) fastlaegges iht. DS/INF 1990:2021 tabel 2 ud fra ID-kriterierne "
        "for stoerste spaend, stoerste hoejde over/under terraen og stoerste antal etager.\n\n"
        "Konstruktionsklasse (KK) svarer som udgangspunkt til konsekvensklassen:\n"
        "  CC1  =>  KK1  (reduceret egenkontrol)\n"
        "  CC2  =>  KK2  (normal egenkontrol / udvidet egenkontrol)\n"
        "  CC3  =>  KK3  (tredjeparts kontrol)\n"
        "  CC4  =>  KK4  (saerlig kontrol)\n\n"
        "KK-klassen kan forhojes som foelge af konstruktiv eller udfoerelsesmaessig kompleksitet, "
        "jf. DS/INF 1990:2021 afsnit 5."
    ),
    _tbl(
        headers=["Kriterie (DS/INF 1990:2021 tabel 2)", "ID1 / CC2 graense", "Projekt", "Opfyldt"],
        rows=[
            ["Stoerste konstruktive spaend [m]",                     "16",   "", ""],
            ["Stoerste hoejde over terraen [m]",                     "12",   "", ""],
            ["Stoerste dybde under terraen [m]",                     "6",    "", ""],
            ["Stoerste antal etager over terraen [stk.]",            "5",    "", ""],
        ],
        caption="Tabel 2 -- Konsekvensklasse CC2 iht. DS/INF 1990:2021 tabel 2 (ID1-kriterier)",
    ),
    _n(
        "[Udfyldes:\n"
        "1. Indfoer projektvaerdier i kolonnen 'Projekt'.\n"
        "2. Marker 'Ja' / 'Nej' i kolonnen 'Opfyldt' for hvert kriterie.\n"
        "3. Angiv den endelige CC og KK og begrundelse nedenfor.\n\n"
        "Konklusion:\n"
        "Stoerste spaend [?] m <= 16 m  =>  ID1 opfyldt.\n"
        "Stoerste hoejde [?] m <= 12 m  =>  ID1 opfyldt.\n"
        "Antal etager [?] <= 5          =>  ID1 opfyldt.\n\n"
        "=> Bygvaerket henfoeres til CC[?] / KK[?].\n"
        "KFI = [0,9 / 1,0 / 1,1] iht. DS/EN 1990 DK NA tabel A1.2(B) DK NA.\n\n"
        "Saerlige forhold der kan pavirke KK-klassen: [ingen / angiv forhold]]"
    ),
    _tbl(
        headers=["Konsekvensklasse", "Konstruktionsklasse", "Kontrolniveau", "Eksempel"],
        rows=[
            ["CC1", "KK1", "Reduceret egenkontrol",             "Enfamiliehus, udhus"],
            ["CC2", "KK2", "Normal / udvidet egenkontrol",      "Etageboliger, kontorer"],
            ["CC3", "KK3", "Tredjeparts kontrol",               "Forsamlingslokale, skole"],
            ["CC4", "KK4", "Saerlig kontrol",                   "Bro, beredskabsbygning"],
        ],
        caption="Tabel 3 -- Konstruktionsklasse og kontrolniveau (DS/INF 1990:2021)",
    ),

    _h("A1.2.3 Sikkerhedsklasse og ansvar"),
    _t(
        "Kontrolklasse: Alle bygningsdele henfoeres til normal kontrolklasse.\n"
        "Miljoeklasse: Fastlaegges for de enkelte bygningsdele under hensyn til placering.\n"
        "Levetid: Kategori 4, forventet levetid 50 aar (DS/EN 1990 tabel 2.1).\n"
        "Udfoerelsesklasse: Fastlaegges pr. konstruktionsdel -- se Tabel 4.3."
    ),

    _h("A1.2.4 IKT og beregningssoftware"),
    _n(
        "[Udfyldes: Angiv software og versioner der er anvendt til beregninger:\n\n"
        "  Statiske beregninger:   [RFEM 6 / Tekla Tedds / Excel / Mathcad / Python]\n"
        "  FEM-modeller:           [RFEM 6, version X.X / SCIA Engineer X]\n"
        "  Tegninger:              [Revit / AutoCAD version XX]\n"
        "  Dokumentation:          OMKREDS Structural Calc\n\n"
        "Beregningsresultater er gyldige under forudsaetning af de angivne inputvaerdier.]"
    ),

    _h("A1.2.5 Projektspecifikke referencer"),
    _n(
        "[Udfyldes: Anfoor projektspecifikke referencer:\n\n"
        "  [1] Bygningsreglement BR18\n"
        "  [2] SBi-anvisning 271, 3. udgave\n"
        "  [3] Geoteknisk rapport, [raadgiver], [dato], rapport nr. [xx]\n"
        "  [4] Brandstrategi, [raadgiver], [dato]\n"
        "  [5] Teknisk Staabi, seneste udgave\n"
        "  [6] [Andre projektspecifikke noter, leverandoerdok. m.m.]]"
    ),

    # -- A1.3 Forundersoegelser -------------------------------------------------
    _h("A1.3 Forundersoegelser"),

    _h("A1.3.1 Grunden og lokale forhold"),
    _n(
        "[Udfyldes: Beliggenhed og matrikelforhold.\n\n"
        "Terraenkarakter og terraenkategori iht. DS/EN 1991-1-4 DK NA tabel 4.1:\n"
        "  0   -- Hav, soe, kystomraadet\n"
        "  I   -- Lavtliggende landjord (agre, moser)\n"
        "  II  -- Omraader med lav vegetation, buskads, spredte bebyggelser (typisk Danmark)\n"
        "  III -- Taetvokset skov, forstaeder, industriomraader\n"
        "  IV  -- Mindst 15 % af arealet er bebygget med huse over 15 m\n\n"
        "=> Terraenkategori: [0 / I / II / III / IV] -- begrundelse: [?]\n\n"
        "Terraenkoter: Eksisterende terraen: [?] m DVR90. Reguleret terraen: [?] m DVR90.\n"
        "Grundvandsstand: [?] m DVR90 (kilde: [borearkiv / geoteknisk rapport]).\n"
        "Vindzone: [1 / 2 / 3 / 4 / 5] iht. DS/EN 1991-1-4 DK NA figur DK.1.]"
    ),
    _f("Figur 3.1 -- Oversigtskort, 1 km radius (terraenkategori-vurdering)"),

    _h("A1.3.2 Geotekniske forhold"),
    _n(
        "[Udfyldes: Henvis til geoteknisk rapport (bilag).\n\n"
        "Jordbundsforhold: Beskriv jordbundsopbygning fra boringer / tryksonderinger.\n"
        "Funderingsmetode: [Direkte fundament / Paele / Pilotering]\n"
        "Frostfri dybde: Min. 0,9 m under fremtidigt terraen (terraenfrostklasse F1/F2).\n"
        "Grundvand: [Over / Under] funderingsniveau. Hensyn til vandtryk: [Ja / Nej]\n\n"
        "Karakteristiske jordparametre fremgaar af tabel nedenfor -- tilpas til rapporten.]"
    ),
    _f("Figur 3.2 -- Boringsplan / sondeplan"),
    _tbl(
        headers=["Parameter", "Symbol", "Vaerdi", "Enhed", "Kilde"],
        rows=[
            ["Friktionsvinkel (karakteristisk)",      "phi_k",  "",    "grader", "Geot. rapport"],
            ["Udraenet forskydningsstyrke",            "c_u,k",  "",    "kPa",    "Geot. rapport"],
            ["Rumvaegt, jord over GV",                "gamma",  "18",  "kN/m3",  "Anslaaet"],
            ["Rumvaegt, jord under GV (opdrift)",     "gamma'", "8",   "kN/m3",  "Anslaaet"],
            ["Tilladt jordtryk / baereevne",          "q_adm",  "",    "kPa",    "Geot. rapport"],
        ],
        caption="Tabel 3.1 -- Geotekniske parametre",
    ),

    _h("A1.3.3-3.4 Miljoetekniske og eksisterende forhold"),
    _n(
        "[Udfyldes:\n\n"
        "Miljoetekniske forhold:\n"
        "Grunden er [ikke] forureningsklassificeret. [Angiv forureningsklasse og haandtering.]\n\n"
        "Eksisterende konstruktioner paa matriklen:\n"
        "[Ingen eksisterende baerende konstruktioner paa matriklen.]\n"
        "-- eller --\n"
        "[Angiv eksisterende konstruktioner: type, materiale, tilstand og eventuel nedrivning.]]"
    ),

    _h("A1.3.5-3.6 Tilstodende bygvaerker"),
    _t("Tilstodende bygvaerker er ikke paavirket af de planlagte anlaegsarbejder."),
    _n("[Erstat med beskrivelse hvis nabobygninger kan pavirkes (udgravning, vibrationer m.m.).]"),

    # -- A1.4 Konstruktioner ---------------------------------------------------
    _h("A1.4 Konstruktioner"),

    _h("A1.4.1 Statisk virkemaade"),
    _n(
        "[Udfyldes: Beskriv lodret og vandret lastnedfoering med reference til figurerne nedenfor.\n\n"
        "Lodret lastnedfoering:\n"
        "Laster fra tag og etageadskillelser overfoeres til baerende vaegge / soejler og videre "
        "til fundamenter. [Beskriv den specifikke kraft-vej for dette projekt.]\n\n"
        "Vandret lastnedfoering (stabilitet):\n"
        "Vandrette laster (vind, seismik, imperfektioner) optages af [skivevirkende etageadskillelser, "
        "stabiliserende vaegge / kerner / facaderammer] og overfoeres til fundament.\n"
        "Stabiliserende vaegge er placeret i [x- og y-retning / alle retninger].\n"
        "Torsion: [Tjek at resultanten passerer naer stivhedscentrum -- eller angiv ekscentritet.]]"
    ),
    _f("Figur 4.1 -- Lodret lastnedfoering, udvendigt snit"),
    _f("Figur 4.2 -- Lodret lastnedfoering, indvendigt snit"),
    _f("Figur 4.3 -- Vandret lastnedfoering, facade (x-retning)"),
    _f("Figur 4.4 -- Vandret lastnedfoering, gavl (y-retning)"),

    _h("A1.4.2 Deformationer og vibrationer"),
    _t(
        "Graensevaerdier for nedbojning iht. nationale annekser (midtspansnedbojning):\n"
        "  Beton:  L / 250  (kvasi-permanent)  |  L / 400  (variabel last alene)\n"
        "  Staal:  L / 400  (kvasi-permanent)  |  L / 400  (variabel, etageadskillelse)\n"
        "  Trae:   L / 400  (G + Q, inst.)     |  L / 250  (karakteristisk vindlast)\n\n"
        "Vandret flytning (topforskydning):\n"
        "  h / 500  (udvendige vaegge, fuger)\n"
        "  h / 300  (generel stabilitetsgrense)"
    ),
    _tbl(
        headers=["Konstruktionsdel", "Retning", "Tilladelig", "Beregnede", "Opfyldt"],
        rows=[
            ["Etagedaek",          "Lodret",   "L / 400",  "", ""],
            ["Etagedaek",          "Lodret",   "L / 250",  "", ""],
            ["Tag",                "Lodret",   "L / 250",  "", ""],
            ["Stabiliserende vaeg", "Vandret", "H / 500",  "", ""],
            ["Bygning (top)",      "Vandret",  "H / 300",  "", ""],
        ],
        caption="Tabel 4.1 -- Graensevaerdier og beregnede deformationer",
    ),
    _tbl(
        headers=["Konstruktionsdel", "Egenfrekvens [Hz]", "Krav [Hz]", "Opfyldt"],
        rows=[
            ["Etagedaek (boliger)",    "",  "> 8",  ""],
            ["Etagedaek (kontorer)",   "",  "> 8",  ""],
            ["Trappe",                 "",  "> 5",  ""],
        ],
        caption="Tabel 4.2 -- Vibrationskontrol (DS/EN 1990 DK NA tabel A1.4)",
    ),

    _h("A1.4.3 Funktionskrav"),
    _n(
        "[Udfyldes: Angiv projektspecifikke funktionskrav ud over normerne:\n\n"
        "  Lydisolation: [dB-krav pr. bygningsdel -- reference til akustiknote]\n"
        "  Brand: Brandklasse [BK1 / BK2 / BK3 / BK4] iht. brandstrategi. "
        "Brandmodstandskrav: [REI xx / R xx] jf. BR18 kap. 3.\n"
        "  Saetninger: Totalsaetning <= [?] mm, diffentialsaetning <= [?] mm.\n"
        "  Vandintraengning: [krav til konstruktioner under grundvand / frostfri konstruktion]]"
    ),

    _h("A1.4.4 Robusthed"),
    _t(
        "Bygvaerket er dimensioneret for robusthed iht. DS/EN 1990 DK NA:2024 Anneks E.\n\n"
        "CC2-krav:\n"
        "  Maks. kollapsomfang:  240 m2 pr. etage  /  360 m2 samlet.\n"
        "  Eller konstruktiv kontinuitet (traekkraefter) der sikrer alternativ kraftvej.\n\n"
        "Traekforbindelser iht. DS/EN 1992-1-1:\n"
        "  Vandret (peripheral):  Ftie,per = li x 7,5 kN/m  (min. 8 kN)\n"
        "  Vandret (internal):    Ftie,int = 0,6 x li x 7,5 kN/m  (min. 8 kN)\n"
        "  Lodret:                Ftie,ver = 2 x Nsd (soejler), 3 x Nsd (vaegge)"
    ),
    _n(
        "[Udfyldes: Beregn og dokumenter traekkraefter i A2 Statiske beregninger.\n"
        "Angiv reference til tegning der viser traekforboindelser og armeringsoverlap.\n\n"
        "Ulykkeskollaps: Vurder om nogen enkeltdel er 'key element' der kraever saerlig "
        "dimensionering for ulykkeslast (spragningstryk 34 kPa).]"
    ),
    _f("Figur 4.5 -- Robusthed: tilladte kollapsomraader (CC2)"),
    _f("Figur 4.6 -- Traekforbindelser: principskitse"),

    _h("A1.4.5 Levetid og holdbarhed"),
    _t(
        "Konstruktionerne er dimensioneret for kategori 4 levetid: 50 aar (DS/EN 1990 tabel 2.1).\n\n"
        "Holdbarhed sikres ved korrekt miljoeklasse og daeklag for armeret beton, "
        "korrekt staalklasse og overfladebehandling for staalkonstruktioner samt "
        "korrekt anvendelsesklasse for traekonstruktioner."
    ),
    _n("[Udfyldes: Anfoor saerlige holdbarhedskrav (aggressive miljoeer, marin eksponering m.m.).]"),
    _f("Figur 4.7 -- Levetid og vedligehold: principskitse"),

    _h("A1.4.6 Brand"),
    _t(
        "Brandklasse fastsaettes af brandstrategi udarbejdet iht. BR18 kap. 3.\n"
        "Konstruktiv brandmodstand for baerende bygningsdele:\n"
        "  Bjaalker og soejler:   R [xx] min.\n"
        "  Etagedaek (bjaelke/plade): REI [xx] min.\n"
        "  Brandvaegge:           EI [xx] min.\n\n"
        "Dimensionering foretages iht. DS/EN 1992-1-2 / 1993-1-2 / 1995-1-2."
    ),
    _n("[Udfyldes: Indfoer brandmodstandskrav fra brandstrategi. Reference: [brandstrategi, dato].]"),
    _f("Figur 4.8 -- Brandceller og brandsektioner, plan"),

    _h("A1.4.7 Udfoerelsesklasser"),
    _t(
        "Udfoerelsesklasse (EXC) fastlaegges pr. konstruktionsdel iht. DS/EN 1090-2 og "
        "DS/EN 1990 FU:2021, og er styret af konstruktionsklasse (KK) og materialerisiko."
    ),
    _tbl(
        headers=["Konstruktionsdel", "CC", "KK", "EXC", "Bemaerkning"],
        rows=[
            ["Staalsamlinger, prim. baerende", "CC2", "KK2", "EXC2", ""],
            ["Staalsamlinger, sekund.",         "CC2", "KK2", "EXC2", ""],
            ["Betonkonstruktioner",             "CC2", "KK2", "EXC2 / KS2", ""],
            ["Fundament",                       "CC2", "KK2", "EXC2 / KS2", ""],
        ],
        caption="Tabel 4.3 -- Udfoerelsesklasser pr. konstruktionsdel",
    ),

    _h("A1.4.8 Drift og vedligehold"),
    _n(
        "[Udfyldes: Angiv faerdige konstruktioners drifts- og vedligeholdsforudsaetninger:\n\n"
        "  Efterspandte konstruktioner: Inspektion og retespaending hvert [xx] aar.\n"
        "  Staaloverflader: [maling, galvanisering] -- forventet vedligeholdsinterval: [xx] aar.\n"
        "  Traekonstruktioner: Kontrol af fugtindhold og raat-/svampeskader hvert [xx] aar.\n"
        "  Generelt: Konstruktionerne er ikke dimensioneret for paavirkninger ud over "
        "dem der er specificeret i dette dokument. Aendret anvendelse kraever ny statisk vurdering.]"
    ),

    # -- A1.5 Konstruktionsmaterialer ------------------------------------------
    _h("A1.5 Konstruktionsmaterialer"),

    _h("A1.5.1 Grund og jord"),
    _t(
        "Geoteknik: Alle permanente konstruktioner henfoeres til geoteknisk kategori 2 (GK2), "
        "modelfaktor gamma_s = 1,0.\n"
        "Partialkoefficienter iht. saet M1 i DS/EN 1997-1 DK NA tabel A-4:\n"
        "  Friktionsvinkel:               gamma_phi = 1,2\n"
        "  Effektiv kohaesion:            gamma_c   = 1,2\n"
        "  Udraenet forskydningsstyrke:   gamma_cu  = 1,8\n"
        "  Rumvaegt:                      gamma_r   = 1,0"
    ),

    _h("A1.5.2 Beton og armering"),
    _t(
        "Beton dimensioneres iht. DS/EN 1992-1-1 DK NA:2021.\n"
        "Armering: B500NX (fyk = 500 MPa, Es = 200 GPa).\n"
        "Betondaekkrav: Vaelges iht. eksponeringsklasse og dmax."
    ),
    _tbl(
        headers=["Konstruktionsdel", "Betonklasse", "dmax [mm]", "Eksponeringsklasse", "Daeklag cnom [mm]"],
        rows=[
            ["Fundament",          "C25/30, N", "32", "XC2",  "50"],
            ["Kaelder / stubbvaegge", "C30/37, N", "32", "XC2", "40"],
            ["Baerende vaegge",     "C30/37, N", "32", "XC1",  "25"],
            ["Etagedaek",           "C30/37, N", "32", "XC1",  "25"],
            ["Daekelementkant",     "C35/45, N", "16", "XC3",  "30"],
        ],
        caption="Tabel 5.1 -- Betonparametre pr. konstruktionsdel",
    ),
    _tbl(
        headers=["Parameter", "Symbol", "Vaerdi", "Enhed"],
        rows=[
            ["Karakteristisk trykstyrke (C30/37)", "fck",    "30",    "MPa"],
            ["Designtrykstyrke",                   "fcd",    "20,0",  "MPa"],
            ["Karakteristisk boejetraekstyrke",     "fctk,0.05", "2,0", "MPa"],
            ["E-modul (kortvarig)",                "Ecm",    "33",    "GPa"],
            ["Partialkoefficient",                  "gamma_c", "1,5",  "-"],
        ],
        caption="Tabel 5.2 -- Betonparametre C30/37 iht. DS/EN 1992-1-1 tabel 3.1",
    ),

    _h("A1.5.3 Staal"),
    _tbl(
        headers=["Konstruktionsdel", "Staalsortering", "fyk [MPa]", "fuk [MPa]", "EXC-klasse"],
        rows=[
            ["Prim. baerende staal (t <= 40 mm)", "S355 JR/J0", "355", "510", "EXC2"],
            ["Sekundaere staalelem. (t <= 40 mm)", "S235 JR",   "235", "360", "EXC2"],
            ["Bolte (6.8)",                        "A307 / 8.8", "480", "800", ""],
            ["Svejsemateriale",                    "E42/E50",    "",   "",    "ISO 3834-3"],
        ],
        caption="Tabel 5.3 -- Staalmaterialer iht. DS/EN 1993-1-1",
    ),
    _n(
        "[Tilpas til projektets staalsorter -- tilfoej rustfrit staal / varmegalvaniserede "
        "profiler hvis relevant. Angiv korrosionsbeskyttelse og overfladebehandlingsklasse.]"
    ),

    _h("A1.5.4 Trae"),
    _t(
        "Traekonstruktioner dimensioneres iht. DS/EN 1995-1-1 DK NA:2019.\n"
        "Modifikationsfaktor: kmod (lasttid x anvendelsesklasse).\n"
        "Krybningsfaktor: kdef (vaestning x anvendelsesklasse).\n"
        "Partialkoefficient: gamma_M = 1,3 (konstruktionstrae og limtrae)."
    ),
    _tbl(
        headers=["Lastklasse", "Varighed", "kmod (AK1)", "kmod (AK2)", "kmod (AK3)"],
        rows=[
            ["Permanent",    "> 10 aar",        "0,60", "0,60", "0,50"],
            ["Langtids",     "6 mdr -- 10 aar", "0,70", "0,70", "0,55"],
            ["Mellemlangt",  "1 uge -- 6 mdr",  "0,80", "0,80", "0,65"],
            ["Korttids",     "< 1 uge",         "0,90", "0,90", "0,70"],
            ["Momentan",     "Vind / ulykke",   "1,10", "1,10", "0,90"],
        ],
        caption="Tabel 5.4 -- Modifikationsfaktor kmod (DS/EN 1995-1-1 tabel 3.1)",
    ),
    _tbl(
        headers=["Traetype", "Klasse", "fc0k [MPa]", "ft0k [MPa]", "fmk [MPa]", "E0mean [GPa]"],
        rows=[
            ["Konstruktionstrae",  "C24",   "21",  "14",  "24",  "11,0"],
            ["Limtrae",            "GL24h", "24",  "16,5","24",  "11,6"],
            ["Limtrae",            "GL28h", "28",  "19,5","28",  "12,6"],
        ],
        caption="Tabel 5.5 -- Karakteristiske styrker, traekonstruktioner",
    ),
    _n("[Anfoor anvendelsesklasse (AK) for hvert konstruktionselement (AK1=inde toer / AK2=inde fugtig / AK3=ude).]"),

    # -- A1.6 Laster -----------------------------------------------------------
    _h("A1.6 Laster"),

    _h("A1.6.1 Lastkombinationer"),
    _t(_LOAD_COMB),

    _h("A1.6.2 Egenlaster"),
    _n(
        "[Udfyldes: Anfoor egenlaster for alle konstruktionsdele (kN/m2 eller kN/m):\n\n"
        "  Tagkonstruktion:         [?] kN/m2\n"
        "    heraf: spaer / bialk:  [?] kN/m2\n"
        "    heraf: tagbeklaedn.:   [?] kN/m2\n"
        "    heraf: isolering:      [?] kN/m2\n"
        "    heraf: undertag:       [?] kN/m2\n\n"
        "  Etagedaek (inkl. gulvopbygning):  [?] kN/m2\n"
        "    heraf: konstrukt. daek:         [?] kN/m2\n"
        "    heraf: gulvopbygning:           [?] kN/m2\n\n"
        "  Ydervaegsopbygning:      [?] kN/m2\n"
        "  Lette skillevagge (ekv. fladelast): 0,5 kN/m2  (DS/EN 1991-1-1 cl. 6.3.1.2)]"
    ),

    _h("A1.6.3 Konstruktionslaster"),
    _n(
        "[Udfyldes: Angiv specielle bygge-/monteringslaster, midlertidige laster og "
        "lagringsbelastning under udfoersel. "
        "Angiv stilladslaster og kraanlaster hvis relevant.]"
    ),

    _h("A1.6.4 Nyttelaster"),
    _t("Nyttelaster iht. DS/EN 1991-1-1 DK NA:2024 og tabel nedenfor."),
    _tbl(
        headers=["Kategori", "Anvendelse", "qk [kN/m2]", "Qk [kN]", "psi_0", "psi_1", "psi_2"],
        rows=[
            ["A1", "Boliger, adgangsveje",    "1,5",  "2,0", "0,7", "0,5", "0,3"],
            ["A4", "Trapper",                 "3,0",  "2,0", "0,7", "0,5", "0,3"],
            ["A5", "Balkoner",                "2,5",  "2,0", "0,7", "0,5", "0,3"],
            ["B1", "Kontorer",                "2,5",  "4,5", "0,7", "0,5", "0,3"],
            ["H",  "Tag (utilgaengeligt)",    "0,4",  "1,5", "0,0", "0,0", "0,0"],
            ["--", "Vandret, vaern kat. A",   "0,5",  "--",  "0,7", "0,5", "0,3"],
        ],
        caption="Tabel 6.1 -- Nyttelaster og psi-vaerdier (DS/EN 1991-1-1 DK NA)",
    ),
    _tbl(
        headers=["Kategori", "Anvendelse", "Vandret qk [kN/m]", "Vandret Qk [kN/m]"],
        rows=[
            ["A", "Boliger, trapper",       "0,5", "1,0"],
            ["B", "Kontorer",               "0,5", "1,0"],
            ["C", "Forsamling",             "1,0", "3,0"],
            ["--", "Parkeringsdaek (biler)", "1,5", "3,0"],
        ],
        caption="Tabel 6.2 -- Vandrette raekvaeerkslaster (DS/EN 1991-1-1 DK NA tabel 6.12 DK NA)",
    ),

    _h("A1.6.5 Vindlast"),
    _t(
        "Vindlast iht. DS/EN 1991-1-4 DK NA:2015:\n"
        "  Basishastighed:   vb,0 = 24 m/s (hele Danmark undtagen Zone 1 og 2)\n"
        "  Ruhedslaengde:    z0 og zmin afhaenger af terraenkategori\n"
        "  Middelvindhastighed:   vm(z) = cr(z) x co x vb\n"
        "  Turbolensintensitet:   Iv(z) = kI / (co x ln(z/z0))\n"
        "  Vindtryk:              qp(z) = [1 + 7 x Iv(z)] x 0,5 x rho x vm^2(z)"
    ),
    _n(
        "[Udfyldes:\n"
        "  Terraenkategori: [II / III] -- jf. A1.3.1\n"
        "  Bygningshoejde:  h = [?] m\n"
        "  qp(h) = [?] kN/m2\n\n"
        "Angiv formfaktorer cpe,10 for facader og tag fra DS/EN 1991-1-4 figur 7.4 / 7.6.\n"
        "Interne tryk: cpi = +0,2 / -0,3 (1 dominerende aabning) eller +/- 0,2 (tathed).\n"
        "Nettovindlast pr. facade: we = qp x (cpe - cpi)  [kN/m2].]"
    ),
    _f("Figur 6.1 -- Vindinddeeling, vindretning 0 grader (facade)"),
    _f("Figur 6.2 -- Vindinddeeling, vindretning 90 grader (gavl)"),

    _h("A1.6.6 Snelast"),
    _t(
        "Snelast iht. DS/EN 1991-1-3 DK NA:2015:\n"
        "  Karakteristisk snelast paa jord:  sk = 1,0 kN/m2 (hele Danmark)\n"
        "  Formskoefficient:                 mu_1 = 0,8 (tag heldning alpha <= 30 grader)\n"
        "  Snelast paa tag:                  s = mu_i x Ce x Ct x sk\n"
        "  Eksponierthedsfaktor:             Ce = 1,0 (normalt eksponeret)\n"
        "  Termisk faktor:                   Ct = 1,0\n\n"
        "Undersog tilfaelde (i), (ii) og (iii) jf. DS/EN 1991-1-3 figur 5.3 for usymmetrisk sne."
    ),
    _f("Figur 6.3 -- Sneformskoefficienter, tagform"),

    _h("A1.6.7-6.9 Imperfektioner og seismisk last"),
    _t(_IMPERFECTIONS + "\n\n" + _SEISMIC),
    _n(
        "[Udfyldes: Beregn theta_i for dette projekt:\n"
        "  l = [?] m (hoejde af det stabiliserede system)\n"
        "  m = [?] (antal stabiliserede soejler/vaegge)\n"
        "  alpha_h = [?],  alpha_m = [?],  theta_i = [?]\n"
        "Aekv. vandret last: Hi = theta_i x sum(Vi)]"
    ),
    _f("Figur 6.4 -- Imperfektioner og aekvivalente vandrette laster"),

    # -- A1.7 Bilag ------------------------------------------------------------
    _h("A1.7 Bilag"),
    _n(
        "[Udfyldes: Anfoor bilag med fulde referencer:\n\n"
        "  Bilag A -- Geoteknisk rapport, [Firma], rapport nr. [xx], [dato]\n"
        "  Bilag B -- Brandstrategi, [Firma], [dato]\n"
        "  Bilag C -- Akustiknotat, [Firma], [dato]\n"
        "  Bilag D -- Leverandoerberegning, [Leverandoer], [komponent], [dato]\n"
        "  Bilag E -- [Andre relevante bilag]]"
    ),
]


# -- A2 -- Statiske beregninger -----------------------------------------------

A2 = [
    _n(
        "A2 Statiske beregninger\n\n"
        "Dette dokument indeholder de statiske beregninger for konstruktionsafsnittene "
        "beskrevet i A1.1.3. Beregningsgrundlag, normer, laster og materialeparametre "
        "fremgaar af A1 Konstruktionsgrundlag."
    ),
    _h("Fundament og geoteknik"),
    _n("[Indsaet beregningsblokke for fundament -- brug + Calculation block nedenfor.]"),
    _h("Baerende vaegge og daek"),
    _n("[Indsaet beregningsblokke for vaegge og daek.]"),
    _h("Tagkonstruktion"),
    _n("[Indsaet beregningsblokke for tagkonstruktion.]"),
    _h("Stabilitet"),
    _n("[Indsaet beregningsblokke for vandret stabilitet, skiver og samlinger.]"),
]


# -- A3 -- Konstruktionstegninger og modeller ---------------------------------

A3 = [
    _n(
        "A3 Konstruktionstegninger og modeller\n\n"
        "Dette dokument udgoor dokumentfortegnelsen over konstruktionstegninger og modeller."
    ),
    _h("Dokumentfortegnelse"),
    _n(
        "[Udfyldes: Anfoor alle konstruktionstegninger:\n"
        "  Tegnings-nr. | Titel | Revision | Dato | Ansvarlig\n\n"
        "  K001 -- Fundering, plan og detaljer | Rev. A | [dato]\n"
        "  K002 -- Baerende konstruktioner, plan stue | Rev. A | [dato]\n"
        "  K003 -- Baerende konstruktioner, plan 1. sal | Rev. A | [dato]\n"
        "  K004 -- Baerende konstruktioner, snit | Rev. A | [dato]\n"
        "  K100 -- Generel note, materialer | Rev. A | [dato]]"
    ),
    _h("Beregningsmodeller"),
    _n("[Angiv FEM-modeller og andre beregningsmodeller med filnavn og dato.]"),
]


# -- A4 -- Konstruktionsaendringer --------------------------------------------

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


# -- B1 -- Statisk projekteringsrapport ---------------------------------------

B1 = [
    _n(
        "B1 Statisk Projekteringsrapport\n\n"
        "Rapporten samler de vaesentligste konklusioner fra den statiske projektering "
        "og henvender sig til bygherre og myndigheder."
    ),
    _h("Projektbeskrivelse og statisk system"),
    _n(
        "[Udfyldes: Kort ikke-teknisk beskrivelse af bygvaerket.\n"
        "Beskriv det baerende og stabiliserende system -- materialer, "
        "spaendvidderne og de vaesentligste konstruktionsdele.]"
    ),
    _h("Konsekvensklasse, konstruktionsklasse og laster"),
    _n(
        "[Udfyldes: Angiv CC og KK med begrundelse (se A1.2.2).\n"
        "Opsummeer styrende laster: egenlast, nyttelast, vindlast, snelast.]"
    ),
    _h("Fundamentering og materialeparametre"),
    _n(
        "[Udfyldes: Funderingsprincip og geotekniske forudsaetninger.\n"
        "Opsummeer konstruktionsmaterialer med styrker og klasser.]"
    ),
    _h("Kontrol, godkendelse og konklusion"),
    _n(
        "[Udfyldes: Beskriv kontrolniveau iht. KK-klasse. Angiv beregnet / kontrolleret / godkendt af.\n\n"
        "Konklusion: Konstruktionerne er dimensioneret iht. gaeldende normer og BR18 og er "
        "tilstraekkelig sikre og robuste til den paataenkte anvendelse.]"
    ),
]


# -- B2 -- Statisk kontrolplan ------------------------------------------------

B2 = [
    _n(
        "B2 Statisk Kontrolplan\n\n"
        "Kontrolplanen beskriver, hvordan den statiske dokumentation kontrolleres "
        "iht. konstruktionsklasse og krav i BR18 / SBi 271."
    ),
    _h("Kontrolomfang og -organisation"),
    _n(
        "[Udfyldes: Angiv KK-klasse og kraevet kontrolniveau:\n"
        "  KK2 -- Udvidet egenkontrol\n"
        "  KK3 -- Tredjeparts kontrol\n"
        "  KK4 -- Saerlig kontrol\n\n"
        "  Beregnet af:     [navn / initialer]\n"
        "  Kontrolleret af: [navn / initialer]\n"
        "  Godkendt af:     [navn / initialer]\n"
        "  Tredjepart:      [firmanavn] (kun KK3/KK4)]"
    ),
    _h("Kontrolplan -- projektering"),
    _n(
        "[Udfyldes: Dokument | Kontroltype | Ansvarlig | Dato | Udfoert\n\n"
        "  A1 Konstruktionsgrundlag      | Gennemlaesning       | [ini.] | [dato] | Ja/Nej\n"
        "  A2 Statiske beregninger       | Stikproevekontrol    | [ini.] | [dato] | Ja/Nej\n"
        "  A3 Konstruktionstegninger     | Gennemlaesning       | [ini.] | [dato] | Ja/Nej]"
    ),
    _h("Kontrolplan -- udforelse"),
    _n(
        "[Udfyldes: Tilsynsaktiviteter paa byggepladsen:\n"
        "  - Fundament: kontrol af udgravning og betonstoebning\n"
        "  - Elementmontage: kontrol af samlinger og afstivning\n"
        "  - Slutkontrol: kontrol af faerdigmelding]"
    ),
]


# -- B3 -- Statisk kontrolrapport ---------------------------------------------

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


# -- Registry -----------------------------------------------------------------

DOC_TEMPLATES = {
    "A1": A1,
    "A2": A2,
    "A3": A3,
    "A4": A4,
    "B1": B1,
    "B2": B2,
    "B3": B3,
}
