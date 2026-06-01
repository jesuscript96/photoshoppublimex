import os
import requests
import json
import re

# Table IDs
T_RESERVACIONES = "tbluUAzNFSuaqMrYX"
T_ESPACIOS      = "tblQ9Z0KW0XheaHRc"
T_CLIENTES      = "tblkKHa9CNt285uv1"

# Load secrets from Streamlit secrets file
secrets = {}
secrets_path = "/Users/jvch/Desktop/PUBLIMEX/PUBLIMEX APP/.streamlit/secrets.toml"
if os.path.exists(secrets_path):
    with open(secrets_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                secrets[k.strip()] = v.strip().strip('"').strip("'")

TOKEN = secrets.get("AIRTABLE_TOKEN")
BASE = "appW4QjUOV9nXQkx9"

if not TOKEN:
    print("Error: AIRTABLE_TOKEN not found in secrets.toml")
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# SQL DATA DECLARATIONS
sql_clientes = [
    (1, 'TECATE'), (2, 'TELCEL'), (3, 'COPPEL'), (4, 'FARMACIAS SIMILARES'), 
    (5, 'AMERICAN EAGLE / AE'), (6, 'VARIOS / SPOT DIGITAL'), (7, 'REVISTA EJERCE'), 
    (8, 'COCA-COLA'), (9, 'AEROMEXICO'), (10, 'PLATA CARD'), (11, 'ALPURA'), 
    (12, 'PORFIRIOS'), (13, 'BUS BUS'), (14, 'IMPERQUIMIA'), (15, 'IMPACTO CAPITAL'), 
    (16, 'OCESA'), (17, 'PARAMOUNT'), (18, 'LA COSTEÑA'), (19, 'JBL')
]

sql_sitios = [
    ('PUB-CDMX-001', 'CDMX', 'VIAD. RIO PIEDAD N° 108', 'CELOSIA', 85000.00, 'NATURAL', 10.50, 7.20, '19.408965, -99.093093'),
    ('PUB-CDMX-002', 'CDMX', 'AV. RÍO CHURUBUSCO, ESQ. BIÓGRAFOS NO. 1', 'UNIPOLAR', 110000.00, 'NATURAL', 12.90, 7.20, '19.370166, -99.108800'),
    ('PUB-CDMX-003', 'CDMX', 'CARR. MEXICO - CUERNAVACA N° 51', 'UNIPOLAR', 130000.00, 'NATURAL', 12.90, 7.20, '19.262143, -99.166215'),
    ('PUB-CDMX-004', 'CDMX', 'CARR. MEXICO - CUERNAVACA N° 51', 'UNIPOLAR', 130000.00, 'CRUZADA', 12.90, 7.20, '19.262143, -99.166215'),
    ('PUB-CDMX-005', 'CDMX', 'VIADUCTO - COYUYA N° 149', 'UNIPOLAR', 300000.00, 'NATURAL', 12.90, 16.50, '19.405501, -99.119447'),
    ('PUB-CDMX-006', 'CDMX', 'VIADUCTO - COYUYA N° 149', 'UNIPOLAR', 75000.00, 'CRUZADA', 12.90, 7.20, '19.405501, -99.119447'),
    ('PUB-CDMX-007', 'CDMX', 'INSURGENTES SUR N° 568 - MURO XOLA', 'MURO', 480000.00, 'NATURAL', 12.60, 20.00, '19.399073, -99.170626'),
    ('PUB-CDMX-008', 'CDMX', 'INSURGENTES SUR N° 568 - MURO VIADUCTO', 'MURO', 350000.00, 'CRUZADA', 15.10, 13.60, '19.399073, -99.170626'),
    ('PUB-CDMX-009', 'CDMX', 'MONTERREY N° 172', 'MURO', 90000.00, 'NATURAL', 12.90, 7.20, '19.414194, -99.163271'),
    ('PUB-CDMX-010', 'CDMX', 'PERIFERICO BLD. A.LOPEZ MATEOS N° 2799', 'UNIPOLAR', 150000.00, 'CRUZADA', 12.90, 7.20, '19.336074, -99.206681'),
    ('PUB-CDMX-011', 'CDMX', 'PERIFERICO N° 30', 'PANTALLA DIGITAL', 120000.00, 'CRUZADA', 12.90, 7.20, '19.373832, -99.192430'),
    ('PUB-CDMX-012', 'CDMX', 'SUPER VIA PONIENTE, DIRECCION SANTA FE', 'UNIPOLAR', 145000.00, 'NATURAL', 12.90, 7.20, '19.34545, -99.24708'),
    ('PUB-CDMX-013', 'CDMX', 'SUPER VIA PONIENTE, DIRECCION SAN JERONIMO', 'UNIPOLAR', 145000.00, 'CRUZADA', 12.90, 7.20, '19.34545, -99.24708'),
    ('PUB-CDMX-014', 'CDMX', 'INSURGENTES, ESQ. POPOCATEPETL N° 14', 'MURO', 1300000.00, 'NATURAL', 14.00, 25.00, '19.41516, -99.16609'),
    ('PUB-CDMX-015', 'CDMX', 'HORACIO N° 604', 'MURO', 650000.00, 'NATURAL', 12.20, 17.00, '19.43349, -99.19095'),
    ('PUB-CDMX-016', 'CDMX', 'BLVD. ADOLFO LÓPEZ MATEOS N° 1803', 'MURO', 500000.00, 'NATURAL', 14.50, 10.00, '19.36599, -99.19107'),
    ('PUB-CDMX-017', 'CDMX', 'RIO CHURUBUSCO N° 342, ESQ. AV. UNIVERSIDAD', 'MURO', 650000.00, 'NATURAL', 30.00, 14.00, '19.360317, -99.172164'),
    ('PUB-CDMX-018', 'CDMX', 'AV. UNIVERSIDAD N° 1883, COYOACÁN', 'MURO', 350000.00, 'CRUZADA', 20.00, 12.00, '19.34229, -99.18173'),
    ('PUB-CDMX-019', 'CDMX', 'EJERCITO NACIONAL N° 436', 'MURO', 480000.00, 'NATURAL', 11.00, 17.00, '19.438258, -99.188302'),
    ('PUB-CDMX-020', 'CDMX', 'VIADUCTO N°936, COL. NAPOLES', 'MURO', 350000.00, 'NATURAL', 5.40, 14.00, '19.39776, -99.17575'),
    ('PUB-CDMX-021', 'CDMX', 'NUEVO LEON N°202, ESQ. BAJA CALIFORNIA', 'MURO', 550000.00, 'NATURAL', 9.65, 22.30, '19.405493, -99.171375'),
    ('PUB-CDMX-022', 'CDMX', 'PERIFERICO SUR N°3380, COL. JARDINES DEL PEDREGAL', 'MURO', 800000.00, 'CRUZADA', 9.40, 15.20, '19.322720, -99.217763'),
    ('PUB-CDMX-023', 'CDMX', 'PERIFERICO SUR N°3380, COL. JARDINES DEL PEDREGAL', 'UNIPOLAR', 150000.00, 'NATURAL', 12.90, 7.20, '19.322720, -99.217763'),
    ('PUB-CDMX-024', 'CDMX', 'PERIFERICO SUR N°3380, COL. JARDINES DEL PEDREGAL', 'UNIPOLAR', 150000.00, 'CRUZADA', 12.90, 7.20, '19.322720, -99.217763'),
    ('PUB-CDMX-025', 'CDMX', 'PERIFERICO MANUEL AVILA CAMACHO N° 131 (ESPECTACULAR)', 'UNIPOLAR', 150000.00, 'NATURAL', 12.90, 7.20, '19.432722, -99.208978'),
    ('PUB-CDMX-026', 'CDMX', 'PERIFERICO MANUEL AVILA CAMACHO N° 131 (PANTALLA DIGITAL)', 'PANTALLA DIGITAL', None, None, None, None, '19.432722, -99.208978'),
    ('PUB-CDMX-027', 'CDMX', 'PERIFERICO MANUEL AVILA CAMACHO N° 131 (VISTA PALMAS)', 'MURO', 485000.00, 'NATURAL', 9.90, 11.00, '19.432722, -99.208978'),
    ('PUB-CDMX-028', 'CDMX', 'PERIFERICO MANUEL AVILA CAMACHO N° 131 (VISTA PERIFERICO)', 'MURO', 600000.00, 'CRUZADA', 14.50, 19.50, '19.432722, -99.208978'),
    ('PUB-CDMX-029', 'CDMX', 'AV. UNIVERSIDAD N° 1770', 'CELOSIA', 115000.00, 'CRUZADA', 12.90, 10.80, '19.346147, -99.180660'),
    ('PUB-CDMX-030', 'CDMX', 'AV. MONTERREY N°150, COL. ROMA', 'MURO', 600000.00, 'NATURAL', 33.50, 13.50, '19.415612, -99.163541'),
    ('PUB-CDMX-031', 'CDMX', 'AV. REVOLUCIÓN N°1348, GUADALUPE INN', 'MURO', 600000.00, 'NATURAL', 15.00, 25.00, '19.358150, -99.190099'),
    ('PUB-CDMX-032', 'CDMX', 'BLVD. ADOLFO LÓPEZ MATEOS 1817 (TORREO NEO)', 'MURO', 1600000.00, 'NATURAL', 19.00, 29.00, '19.36599, -99.19107'),
    ('PUB-CDMX-033', 'CDMX', 'BLVD. ADOLFO LÓPEZ MATEOS 1817 (TORREO NEO)', 'MURO', 1500000.00, 'CRUZADA', 19.00, 29.00, '19.36599, -99.19107'),
    ('PUB-CDMX-034', 'CDMX', 'PERIFERICO SUR N°5185', 'UNIPOLAR', 150000.00, 'CRUZADA', 12.90, 7.20, '19.303111, -99.175724'),
    ('PUB-CDMX-035', 'CDMX', 'PERIFERICO SUR N°5185', 'UNIPOLAR', None, 'NATURAL', 12.90, 7.20, '19.303111, -99.175724'),
    ('PUB-CDMX-036', 'CDMX', 'VIADUCTO MIGUEL ALEMÁN NO. 35 ESQ. HÉROES DE CHURUBUSCO', 'UNIPOLAR', 145000.00, 'NATURAL', 12.90, 7.20, '19.399823, -99.190225'),
    ('PUB-CDMX-037', 'CDMX', 'VIADUCTO MIGUEL ALEMÁN NO. 35 ESQ. HÉROES DE CHURUBUSCO', 'UNIPOLAR', 145000.00, 'CRUZADA', 12.90, 7.20, '19.399823, -99.190225'),
    ('PUB-CDMX-038', 'CDMX', 'HEGEL N°228', 'MURO', 550000.00, 'NATURAL', 12.10, 16.50, '19.434097, -99.188031'),
    ('PUB-CDMX-039', 'CDMX', 'JALAPA 15, ROMA NTE., CUAUH. GLORIETA DE INSURGENTES', 'MURO', 1800000.00, 'CRUZADA', 25.00, 19.00, '19.423165, -99.162474'),
    ('PUB-CDMX-040', 'CDMX', 'AV. ALVARO OBREGÓN N°52, COL. ROMA NORTE', 'MURO', 250000.00, 'NATURAL', 9.00, 13.00, '19.418740, -99.157161'),
    ('PUB-CDMX-041', 'CDMX', 'AV. INSURGENTES N° 377, COL. ROMA', 'MURO', 370000.00, 'NATURAL', 24.00, 10.00, '19.409566, -99.167441'),
    ('PUB-CDMX-042', 'CDMX', 'PERIFÉRICO, ESQ. GUITIERREZ DE MENDOZA N° 13', 'UNIPOLAR', 150000.00, 'NATURAL', 12.90, 7.20, '19.447053, -99.219894'),
    ('PUB-CDMX-043', 'CDMX', 'PERIFÉRICO, ESQ. GUITIERREZ DE MENDOZA N° 13', 'UNIPOLAR', 150000.00, 'CRUZADA', 12.90, 7.20, '19.447053, -99.219894'),
    ('PUB-CDMX-044', 'CDMX', 'AV. P.º DE LA REFORMA 80, JUÁREZ, CUAUHTÉMOC', 'MURO', 800000.00, 'NATURAL', 19.00, 35.00, '19.432459, -99.154797'),
    ('PUB-CDMX-045', 'CDMX', 'ALFONSO REYES N° 152, HIPÓDROMO CONDESA', 'MURO', 1900000.00, 'NATURAL', 8.00, 13.00, '19.409078, -99.176721'),
    ('PUB-CDMX-046', 'CDMX', 'AV CONSTITUYENTES N°345, DANIEL GARZA', 'MURO', 700000.00, 'CRUZADA', 12.00, 25.00, '19.408691, -99.197808'),
    ('PUB-CDMX-047', 'CDMX', 'AV. PATRIOTISMO N°483, SAN PEDRO DE LOS PINOS', 'UNIPOLAR', 130000.00, 'NATURAL', 12.90, 7.20, '19.386997, -99.182448'),
    ('PUB-CDMX-048', 'CDMX', 'AV. PATRIOTISMO N°483, SAN PEDRO DE LOS PINOS', 'UNIPOLAR', 130000.00, 'CRUZADA', 12.90, 7.20, '19.386997, -99.182448'),
    ('PUB-CDMX-049', 'CDMX', 'QUERÉTARO 147, ROMA NTE.', 'MURO', 450000.00, 'NATURAL', 27.00, 11.00, '19.414921, -99.161312'),
    ('PUB-CDMX-050', 'CDMX', 'VIADUCTO RÍO BECERRA N°451, NÁPOLES', 'MURO', 350000.00, 'CRUZADA', 4.60, 11.00, '19.386657, -99.181519'),
    ('PUB-CDMX-051', 'CDMX', 'AV CONSTITUYENTES N°643, COL.16 DE SEPT', 'MURO', 380000.00, 'NATURAL', 10.00, 17.00, '19.401410, -99.209704'),
    ('PUB-CDMX-052', 'CDMX', 'AV. INSURGENTES SUR N° 586, DEL VALLE', 'MURO', 200000.00, 'CRUZADA', 12.00, 7.00, '19.398553, -99.171137'),
    ('PUB-CDMX-053', 'CDMX', 'GUTENBERG N°39, VERÓNICA ANZÚRES', 'MURO', 650000.00, 'NATURAL', 10.00, 18.00, '19.433630, -99.172458'),
    ('PUB-CDMX-054', 'CDMX', 'PERIFÉRICO SUR N°5550, EL CARACOL', 'UNIPOLAR', 150000.00, 'NATURAL', 12.90, 7.20, '19.303111, -99.175724'),
    ('PUB-CDMX-055', 'CDMX', 'PERIFÉRICO SUR N°5550, EL CARACOL', 'PANTALLA DIGITAL', 150000.00, 'CRUZADA', 12.90, 7.20, '19.303111, -99.175724'),
    ('PUB-CDMX-056', 'CDMX', 'ANILLO PERIFERICO, ESQ. ESTEPA (PANTALLA)', 'PANTALLA DIGITAL', 120000.00, 'NATURAL', 11.52, 6.72, '19.302390, -99.195615'),
    ('PUB-CDMX-057', 'CDMX', 'ANILLO PERIFERICO, ESQ. ESTEPA (PANTALLA)', 'PANTALLA DIGITAL', 120000.00, 'CRUZADA', 11.52, 6.72, '19.302390, -99.195615'),
    ('PUB-CDMX-058', 'CDMX', 'AEROPUERTO - AICM T1 (EXTERIOR RETORNO P4)', 'PANTALLA DIGITAL', 220000.00, 'NATURAL', 12.00, 5.00, None),
    ('PUB-CDMX-059', 'CDMX', 'AEROPUERTO - AICM T1 (EXTERIOR CALLE P6)', 'PANTALLA DIGITAL', 220000.00, 'NATURAL', 12.00, 8.00, None),
    ('PUB-CDMX-060', 'CDMX', 'AEROPUERTO - AICM T2 - PANTALLA', 'PANTALLA DIGITAL', 250000.00, 'NATURAL', 13.00, 7.00, None),
    ('PUB-CDMX-061A', 'CDMX', 'VALLAS AEROPUERTO - VALLA A', 'VALLA', 600000.00, 'NATURAL', 4.70, 3.30, None),
    ('PUB-CDMX-062A', 'CDMX', 'VALLAS AMSTERDAM N°116 - VALLA A', 'VALLA', 6500.00, 'NATURAL', 5.00, 3.00, '19.414222, -99.166689'),
    ('PUB-CDMX-063A', 'CDMX', 'VALLAS COYUYA - VALLA A', 'VALLA', 6500.00, 'NATURAL', 2.80, 4.80, None),
    ('PUB-CDMX-064A', 'CDMX', 'VALLAS CIRCUITO AZTECA - VALLA A', 'VALLA', 150000.00, 'NATURAL', 4.55, 2.40, None),
    ('PUB-CDMX-065A', 'CDMX', 'VALLAS MELCHOR OCAMPO - VALLA A', 'VALLA', None, 'NATURAL', None, None, None),
    ('PUB-CDMX-066', 'CDMX', 'PERIFERICO N°1795', 'MURO', None, None, None, None, None),
    ('PUB-CDMX-067', 'CDMX', 'PERIFERICO N°1795', 'MURO', None, None, None, None, None),
    ('PUB-CDMX-068', 'CDMX', 'PATRICIO SANZ N°1365', 'MURO', 300000.00, None, 7.50, 18.00, None),
    ('PUB-CDMX-069', 'CDMX', 'BAJIO', 'MURO', 300000.00, None, None, None, None),
    ('PUB-CDMX-070', 'CDMX', 'JOSÉ MARÍA RICO 230', 'MURO', None, None, None, None, None),
    ('PUB-CDMX-071', 'CDMX', 'ARQUIMIDES 184', 'MURO', 650000.00, None, None, None, None),
    ('PUB-CDMX-072', 'CDMX', 'JOSÉ VASCONCELOS', 'MURO', 700000.00, None, None, None, None),
    ('PUB-EDOMX-01', 'EDOMX', 'BLD. A. LÓPEZ PORTILLO, ESQ. CALLE TREINTA TREINTA', 'UNIPOLAR', 45000.00, 'NATURAL', 12.90, 10.80, None),
    ('PUB-EDOMX-02', 'EDOMX', 'BLD. A. LÓPEZ PORTILLO, ESQ. CALLE TREINTA TREINTA', 'UNIPOLAR', 35000.00, 'CRUZADA', 12.90, 10.80, None),
    ('PUB-EDOMX-03', 'EDOMX', 'VIA MORELOS N° 252, COL. SANTA MARÍA TULPETLAC, ECATEPEC', 'UNIPOLAR', 40000.00, 'NATURAL', 12.90, 10.80, None),
    ('PUB-EDOMX-04', 'EDOMX', 'VIA MORELOS N° 252, COL. SANTA MARÍA TULPETLAC, ECATEPEC', 'UNIPOLAR', 35000.00, 'CRUZADA', 12.90, 10.80, None),
    ('PUB-EDOMX-05', 'EDOMX', 'BLVD. MIGUEL ALEMAN. ESQ. CAMINO AL CERRILLO', 'UNIPOLAR', 60000.00, 'NATURAL', 25.00, 7.20, None),
    ('PUB-EDOMX-06', 'EDOMX', 'BLVD. MIGUEL ALEMAN. ESQ. CAMINO AL CERRILLO', 'UNIPOLAR', 55000.00, 'CRUZADA', 25.00, 7.20, None),
    ('PUB-EDOMX-07', 'EDOMX', 'BLD. A. LÓPEZ MATEOS N° 302, COL. SAN PEDRO TOTOLTEPEC', 'UNIPOLAR', 45000.00, 'NATURAL', 12.90, 7.20, None),
    ('PUB-EDOMX-08', 'EDOMX', 'BLD. A. LÓPEZ MATEOS N° 302, COL. SAN PEDRO TOTOLTEPEC', 'UNIPOLAR', 35000.00, 'CRUZADA', 12.90, 7.20, None),
    ('PUB-ACA-01', 'ACA', 'BLD.DE LAS NACIONES KM.14.5 (APTO.AL PUERTO)', 'UNIPOLAR', 45000.00, 'NATURAL', 12.90, 7.20, None),
    ('PUB-ACA-02', 'ACA', 'BLD.DE LAS NACIONES KM.14.5 (PUERTO AL APTO.)', 'UNIPOLAR', 40000.00, 'CRUZADA', 12.90, 7.20, None),
    ('PUB-ACA-03', 'ACA', 'COSTERA M. ALEMAN - MERCADO DALIA', 'UNIPOLAR', 45000.00, 'NATURAL', 12.90, 7.20, None)
]

sql_reservas = [
    ('PUB-CDMX-002', 1, '2026-04-30', '2026-06-29'),
    ('PUB-CDMX-005', 2, '2025-12-01', '2026-07-31'),
    ('PUB-CDMX-006', 2, '2025-12-01', '2026-07-31'),
    ('PUB-CDMX-063A', 2, '2025-12-01', '2026-07-31'),
    ('PUB-CDMX-007', 3, '2026-03-01', '2026-12-31'),
    ('PUB-CDMX-022', 3, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-024', 3, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-033', 3, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-050', 3, '2026-02-01', '2026-12-31'),
    ('PUB-CDMX-008', 4, '2026-01-15', '2026-04-14'),
    ('PUB-CDMX-031', 4, '2026-01-15', '2026-04-14'),
    ('PUB-CDMX-044', 4, '2026-01-15', '2026-04-14'),
    ('PUB-CDMX-054', 4, '2026-05-01', '2027-04-30'),
    ('PUB-CDMX-009', 5, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-027', 5, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-028', 5, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-030', 5, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-045', 5, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-011', 6, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-056', 6, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-057', 6, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-058', 6, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-059', 6, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-060', 6, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-013', 7, '2026-07-01', '2026-07-31'),
    ('PUB-CDMX-025', 7, '2026-07-01', '2026-07-31'),
    ('PUB-CDMX-014', 8, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-016', 8, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-017', 8, '2026-01-01', '2026-07-31'),
    ('PUB-CDMX-032', 8, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-021', 9, '2026-02-01', '2026-04-30'),
    ('PUB-CDMX-021', 10, '2026-04-01', '2026-05-31'),
    ('PUB-CDMX-040', 10, '2026-04-01', '2026-05-31'),
    ('PUB-CDMX-023', 11, '2026-03-01', '2026-12-31'),
    ('PUB-CDMX-029', 12, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-029', 13, '2026-06-01', '2026-06-30'),
    ('PUB-CDMX-036', 13, '2026-06-01', '2026-06-30'),
    ('PUB-CDMX-034', 14, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-035', 14, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-039', 15, '2026-01-01', '2026-12-31'),
    ('PUB-CDMX-049', 16, '2026-05-26', '2026-06-16'),
    ('PUB-CDMX-051', 17, '2026-05-09', '2026-06-09'),
    ('PUB-CDMX-054', 18, '2026-01-14', '2026-02-13'),
    ('PUB-CDMX-043', 19, '2026-03-01', '2026-04-30'),
    ('PUB-CDMX-055', 19, '2026-03-01', '2026-04-30')
]

# EXACT MAPPING DICTIONARY FOR PRESERVING MEDIA & DETAILS
MAPPING = {
    "PUB-CDMX-001": "recKj6Rxh2AHf464M",  # ID 66
    "PUB-CDMX-002": "rechiD2S9u447AHH1",  # ID 64
    "PUB-CDMX-003": "recGvV4wfBWuqb68e",  # ID 58
    "PUB-CDMX-004": "recONXpvzTorPcBub",  # ID 59
    "PUB-CDMX-005": "recx93PX1UTg2CinY",  # ID 41
    "PUB-CDMX-006": "recqTm75FvkIOfMMj",  # ID 67
    "PUB-CDMX-007": "rec8a0IZtZOdhB9XY",  # ID 35
    "PUB-CDMX-008": "recAdGa1A8jYEeBM7",  # ID 36 (will be updated)
    "PUB-CDMX-009": "recRARpinDysIunvs",  # ID 62
    "PUB-CDMX-010": "recKOx90x3N5iHPfA",  # ID 49
    "PUB-CDMX-011": "recr2xdPeMe1m5rEG",  # ID 45
    "PUB-CDMX-012": "recQjIPJoCYmCFwv4",  # ID 60
    "PUB-CDMX-013": "recJQ9eW3UBYn13mo",  # ID 61
    "PUB-CDMX-014": "recZ7I91rxF7JjoHQ",  # ID 13
    "PUB-CDMX-015": "rec2SOWmaSNkKlQ7N",  # ID 10
    "PUB-CDMX-016": "rec6iZXGJM2BRsvuZ",  # ID 4
    "PUB-CDMX-017": "recjzNQMLHqEdWm4Y",  # ID 19
    "PUB-CDMX-018": "recEyTRJ921i3fdZJ",  # ID 30
    "PUB-CDMX-019": "recpLvS3EQwt98fUp",  # ID 31
    "PUB-CDMX-020": "rechmNeRxFh5stJ9a",  # ID 32
    "PUB-CDMX-021": "recl6iUmundPKOanf",  # ID 34
    "PUB-CDMX-022": "recUVfvUYU6MzuCPW",  # ID 38
    "PUB-CDMX-023": "recnV8yPCa9dW9D94",  # ID 51
    "PUB-CDMX-024": "recJpN2qtFOWRstxX",  # ID 50
    "PUB-CDMX-025": "recJ7MQYpVZHy55lR",  # ID 68
    "PUB-CDMX-027": "recDGP5GutwCbUnu1",  # ID 17
    "PUB-CDMX-028": "reccHBev2YZUShAz0",  # ID 16
    "PUB-CDMX-029": "recp71mwYmkcUBdVa",  # ID 65
    "PUB-CDMX-030": "recjaJBIWNmsvg6RP",  # ID 21
    "PUB-CDMX-031": "recDZM7l46fUhGM1s",  # ID 24
    "PUB-CDMX-032": "recBkhJCMaLUvJKq2",  # ID 2
    "PUB-CDMX-033": "recLAaBOstmxRpzon",  # ID 5
    "PUB-CDMX-034": "recAPz1QaMsJMU9eW",  # ID 52
    "PUB-CDMX-036": "recF6kyVFWtQdMf6W",  # ID 56
    "PUB-CDMX-037": "reczGE0IXpmHnOx13",  # ID 57
    "PUB-CDMX-038": "recv0AIVVJWfFr38X",  # ID 20
    "PUB-CDMX-040": "recQ9w7GgmtzklPYs",  # ID 23
    "PUB-CDMX-041": "recVdGR3UWANkhbnX",  # ID 37
    "PUB-CDMX-042": "recxO8uhpnE0lKDZt",  # ID 53
    "PUB-CDMX-043": "recSYev0UDx4KrHSd",  # ID 54
    "PUB-CDMX-044": "recp2DAZB0C8FteEV",  # ID 9
    "PUB-CDMX-045": "recKJ3EdTynyBKM9j",  # ID 1
    "PUB-CDMX-046": "rec86XypcqjYBXt6P",  # ID 12
    "PUB-CDMX-047": "rectuUVomVTZQZQoj",  # ID 63
    "PUB-CDMX-049": "recjcv0mTxVB5xlXT",  # ID 22
    "PUB-CDMX-051": "recNdlRySW53X9YW4",  # ID 15
    "PUB-CDMX-053": "rec67WOOvsuGl6Kh8",  # ID 29
    "PUB-CDMX-054": "recd7sJVTHgRKOe9W",  # ID 55
    "PUB-CDMX-055": "rec7hVhsoZzCLt0Ch",  # ID 48
    "PUB-CDMX-056": "rec7GLjsEJayy87UK",  # ID 46
    "PUB-CDMX-057": "reczqYAtXMauuLOzM",  # ID 47
    "PUB-CDMX-061A": "rechVSUNF9NJXvOmn", # ID 73
    "PUB-CDMX-062A": "reccVZwjLuBGCJqYC", # ID 70
    "PUB-CDMX-063A": "recwlMOIVp9cRgbdU", # ID 71
    "PUB-CDMX-064A": "recjpeHkfgXHSIO1c", # ID 69
    "PUB-CDMX-065A": "recM4iuHoi3YxNnHE", # ID 72
    "PUB-CDMX-068": "rec2sboneUJwqawLU",  # ID 42
    "PUB-CDMX-070": "recq9vRgHj4iaT21H",  # ID 33
    "PUB-CDMX-071": "recpWeuy197hAlXQt",  # ID 44
    "PUB-CDMX-072": "reccVpM8RZ1jIBVpb",  # ID 43
}

def map_category(tipo):
    t = (tipo or "").upper()
    if t == 'CELOSIA':
        return 'Muro'
    elif t == 'UNIPOLAR':
        return 'Muro + Espectacular'
    elif t == 'MURO':
        return 'Muro'
    elif t == 'PANTALLA DIGITAL':
        return 'Pantalla Digital'
    elif t == 'VALLA':
        return 'Valla'
    return 'Muro'

def map_vista(v):
    val = (v or "").upper()
    if val == 'NATURAL':
        return 'Natural'
    elif val == 'CRUZADA':
        return 'Cruzada'
    return 'Por confirmar'

def clean_old_records(table_id):
    print(f"Cleaning records in table {table_id}...")
    url = f"https://api.airtable.com/v0/{BASE}/{table_id}"
    records_to_delete = []
    
    # 1. Fetch all record IDs
    params = {}
    while True:
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        data = r.json()
        for rec in data.get("records", []):
            records_to_delete.append(rec["id"])
        offset = data.get("offset")
        if not offset:
            break
        params = {"offset": offset}
        
    print(f"Deleting {len(records_to_delete)} records...")
    # 2. Delete in batches of 10
    for i in range(0, len(records_to_delete), 10):
        batch = records_to_delete[i:i+10]
        delete_url = f"{url}?" + "&".join([f"records[]={rid}" for rid in batch])
        r = requests.delete(delete_url, headers=HEADERS)
        r.raise_for_status()
    print(f"Cleared table {table_id}.")

def execute_migration():
    # Step 1: Clear existing reservations & clients (to avoid FK errors or orphaned link items)
    clean_old_records(T_RESERVACIONES)
    clean_old_records(T_CLIENTES)
    
    # Step 2: Create Clients
    print("Creating clients...")
    client_sql_to_at = {}
    url_clients = f"https://api.airtable.com/v0/{BASE}/{T_CLIENTES}"
    
    # Create clients one by one or in batches of 10
    client_batches = []
    current_batch = []
    for client_id, nombre in sql_clientes:
        fields = {
            "Empresa": nombre,
            "Contacto": nombre
        }
        current_batch.append({"fields": fields, "id_num": client_id})
        if len(current_batch) == 10:
            client_batches.append(current_batch)
            current_batch = []
    if current_batch:
        client_batches.append(current_batch)
        
    for batch in client_batches:
        payload = {"records": [{"fields": b["fields"]} for b in batch]}
        r = requests.post(url_clients, headers=HEADERS, json=payload)
        r.raise_for_status()
        res_data = r.json()
        for b, rec in zip(batch, res_data["records"]):
            client_sql_to_at[b["id_num"]] = rec["id"]
            
    print(f"Created {len(client_sql_to_at)} clients.")
    
    # Step 3: Fetch existing Spaces to preserve images & map URLs
    print("Fetching spaces...")
    url_spaces = f"https://api.airtable.com/v0/{BASE}/{T_ESPACIOS}"
    existing_spaces = {}
    params = {}
    while True:
        r = requests.get(url_spaces, headers=HEADERS, params=params)
        r.raise_for_status()
        data = r.json()
        for rec in data.get("records", []):
            existing_spaces[rec["id"]] = rec
        offset = data.get("offset")
        if not offset:
            break
        params = {"offset": offset}
        
    print(f"Fetched {len(existing_spaces)} spaces.")
    
    # Step 4: Map and Update Matched Spaces + Create Unmatched Spaces
    space_sql_to_at = {}
    matched_record_ids = set()
    
    spaces_to_create = []
    spaces_to_update = []
    
    # Calculate sequential index (1 to 83) for the sites
    for idx, s in enumerate(sql_sitios):
        sql_index = idx + 1
        id_sitio, region, direccion, tipo, tarifa_publicada, vista, base, alto, coordenadas = s
        
        # Determine category, vista, and dimensions
        category = map_category(tipo)
        clean_vista = map_vista(vista)
        ancho = float(base) if base is not None else None
        alto_val = float(alto) if alto is not None else None
        m2 = (ancho * alto_val) if ancho and alto_val else None
        medida = f"{ancho:.2f} x {alto_val:.2f} M" if ancho and alto_val else "—"
        
        fields = {
            "Direccion": direccion,
            "Categoria": category,
            "Vista": clean_vista,
            "Precio_MXN": int(tarifa_publicada) if tarifa_publicada is not None else None,
            "Ancho_m": ancho,
            "Alto_m": alto_val,
            "M2": m2,
            "Medida": medida,
            "Zona": region,
            "\ufeffID": sql_index,  # Set numeric ID (1-83)
            "Disponible": "Sí"
        }
        
        # Check if matched in our MAPPING dictionary
        if id_sitio in MAPPING:
            at_rec_id = MAPPING[id_sitio]
            if at_rec_id in existing_spaces:
                # Update fields but preserve key ones (like Imagenes, URL_Maps, Referencia, etc.)
                old_fields = existing_spaces[at_rec_id].get("fields", {})
                for preserve_field in ["Imagenes", "URL_Maps", "Referencia"]:
                    if preserve_field in old_fields:
                        fields[preserve_field] = old_fields[preserve_field]
                        
                spaces_to_update.append({"id": at_rec_id, "fields": fields})
                space_sql_to_at[id_sitio] = at_rec_id
                matched_record_ids.add(at_rec_id)
                continue
                
        # Unmatched -> Create new record
        spaces_to_create.append({"fields": fields, "id_sitio": id_sitio})
        
    # Execute Updates (in batches of 10)
    print(f"Updating {len(spaces_to_update)} matched spaces...")
    for i in range(0, len(spaces_to_update), 10):
        batch = spaces_to_update[i:i+10]
        payload = {"records": batch, "typecast": True}
        r = requests.patch(url_spaces, headers=HEADERS, json=payload)
        if r.status_code != 200:
            print(f"PATCH Error: {r.status_code}")
            print(r.text)
            r.raise_for_status()
        
    # Execute Creations (in batches of 10)
    print(f"Creating {len(spaces_to_create)} new spaces...")
    for i in range(0, len(spaces_to_create), 10):
        batch = spaces_to_create[i:i+10]
        payload = {"records": [{"fields": b["fields"]} for b in batch], "typecast": True}
        r = requests.post(url_spaces, headers=HEADERS, json=payload)
        if r.status_code != 200:
            print(f"POST Error: {r.status_code}")
            print(r.text)
            r.raise_for_status()
        res_data = r.json()
        for b, rec in zip(batch, res_data["records"]):
            space_sql_to_at[b["id_sitio"]] = rec["id"]
            
    # Delete unmatched spaces
    spaces_to_delete = [rid for rid in existing_spaces.keys() if rid not in matched_record_ids]
    print(f"Deleting {len(spaces_to_delete)} old unmatched spaces...")
    for i in range(0, len(spaces_to_delete), 10):
        batch = spaces_to_delete[i:i+10]
        delete_url = f"{url_spaces}?" + "&".join([f"records[]={rid}" for rid in batch])
        r = requests.delete(delete_url, headers=HEADERS)
        r.raise_for_status()
        
    print("Spaces migration complete!")
    
    # Step 5: Insert Reservations
    print("Creating reservations...")
    url_res = f"https://api.airtable.com/v0/{BASE}/{T_RESERVACIONES}"
    
    res_batches = []
    current_batch = []
    for idx, r_val in enumerate(sql_reservas):
        id_sitio, id_cliente, fecha_ini, fecha_fin = r_val
        
        # Get linked record IDs
        at_space_id = space_sql_to_at.get(id_sitio)
        at_client_id = client_sql_to_at.get(id_cliente)
        
        if not at_space_id or not at_client_id:
            print(f"Warning: could not find mapping for reservation {id_sitio} / {id_cliente}")
            continue
            
        fields = {
            "Espacio (Nuevo)": [at_space_id],
            "Cliente": [at_client_id],
            "Fecha_Inicio": fecha_ini,
            "Fecha_Fin": fecha_fin,
            "Estado": "Confirmada",
            "Notas": "Migración desde script SQL."
        }
        current_batch.append({"fields": fields})
        if len(current_batch) == 10:
            res_batches.append(current_batch)
            current_batch = []
            
    if current_batch:
        res_batches.append(current_batch)
        
    for batch in res_batches:
        payload = {"records": [{"fields": b["fields"]} for b in batch], "typecast": True}
        r = requests.post(url_res, headers=HEADERS, json=payload)
        if r.status_code != 200:
            print(f"Reservation POST Error: {r.status_code}")
            print(r.text)
            r.raise_for_status()
        
    print(f"Created {len(sql_reservas)} reservations in Airtable.")
    print("\nMigration completed successfully!")

if __name__ == "__main__":
    execute_migration()
