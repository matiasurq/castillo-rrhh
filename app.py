import streamlit as st
import json, os, io, shutil
from datetime import date, datetime
from pathlib import Path
from groq import Groq
import pdfplumber
from PIL import Image

# ── ReportLab ────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
PDF_DIR    = BASE_DIR / "informes_pdf"
ASSETS_DIR = BASE_DIR / "assets"
EMP_FILE   = DATA_DIR / "empleados.json"
SUC_FILE   = DATA_DIR / "sucursales.json"
LID_FILE   = DATA_DIR / "lideres.json"
TIP_FILE   = DATA_DIR / "tipos_informe.json"
CFG_FILE   = DATA_DIR / "config.json"

for d in [PDF_DIR, DATA_DIR, ASSETS_DIR]: d.mkdir(exist_ok=True)

AZUL     = "#1a1e8f"
AMARILLO = "#f5a800"
AZUL_RL  = colors.HexColor("#1a1e8f")
AMAR_RL  = colors.HexColor("#f5a800")

# ── Configuración página ──────────────────────────────────────────────────────
st.set_page_config(page_title="Castillo RRHH", page_icon="🏢", layout="wide",
                   initial_sidebar_state="collapsed")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
html,body,[class*="css"]{{font-family:'Nunito',sans-serif!important}}
.stApp{{background:#f0f2ff}}
.castillo-header{{background:{AZUL};border-bottom:4px solid {AMARILLO};padding:14px 28px;display:flex;align-items:center;gap:16px;margin:-1rem -1rem 1.5rem -1rem}}
.castillo-logo{{border:2px solid {AMARILLO};border-radius:50px;padding:5px 16px;color:{AMARILLO};font-size:20px;font-weight:800;letter-spacing:1px}}
.castillo-subtitle{{color:rgba(255,255,255,.5);font-size:9px;letter-spacing:3px;margin-top:1px}}
.castillo-title{{color:#fff;font-size:17px;font-weight:600}}
.badge-rrhh{{margin-left:auto;background:{AMARILLO};color:{AZUL};font-size:11px;font-weight:800;padding:5px 14px;border-radius:20px;letter-spacing:1px}}
.stat-box{{background:#fff;border:1px solid #e0e0f0;border-radius:12px;padding:14px 18px;text-align:center}}
.stat-box.azul{{background:{AZUL}}}
.stat-num{{font-size:26px;font-weight:800;color:{AZUL}}}
.stat-box.azul .stat-num{{color:{AMARILLO}}}
.stat-label{{font-size:10px;color:#6b6b8a;text-transform:uppercase;letter-spacing:1px}}
.stat-box.azul .stat-label{{color:rgba(255,255,255,.6)}}
.avatar{{width:46px;height:46px;border-radius:50%;background:{AZUL};color:{AMARILLO};font-size:17px;font-weight:800;display:flex;align-items:center;justify-content:center}}
.avatar-img{{width:46px;height:46px;border-radius:50%;object-fit:cover;border:2px solid {AMARILLO}}}
.tag{{display:inline-block;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:700}}
.tag-nuevo{{background:#e8f5e9;color:#2e7d32}}
.tag-activo{{background:#e3f2fd;color:#1565c0}}
.tag-lider{{background:#fff3e0;color:#e65100}}
.tag-inactivo{{background:#fce4ec;color:#b71c1c}}
.ia-result{{background:{AZUL};border-radius:12px;padding:22px;color:#fff;line-height:1.7}}
.ficha-header{{background:{AZUL};border-radius:12px;padding:24px;color:#fff;text-align:center;margin-bottom:14px}}
.ficha-avatar-big{{width:80px;height:80px;border-radius:50%;background:{AMARILLO};color:{AZUL};font-size:28px;font-weight:800;display:flex;align-items:center;justify-content:center;margin:0 auto 10px;border:3px solid rgba(255,255,255,.3)}}
.ficha-avatar-big-img{{width:80px;height:80px;border-radius:50%;object-fit:cover;margin:0 auto 10px;display:block;border:3px solid {AMARILLO}}}
.rem-box{{background:{AZUL};border-radius:8px;padding:10px 14px;display:flex;justify-content:space-between;color:rgba(255,255,255,.6);font-size:12px;margin-top:8px}}
.rem-valor{{color:{AMARILLO};font-size:17px;font-weight:800}}
.proximo-card{{background:#fff;border:1px solid #e0e0f0;border-left:4px solid {AMARILLO};border-radius:8px;padding:11px 14px}}
.proximo-vencido{{border-left-color:#e53935!important}}
.proximo-hoy{{border-left-color:#43a047!important}}
.alerta-box{{background:#fff3e0;border:1px solid #ffe082;border-radius:10px;padding:12px 16px;margin-bottom:16px}}
.search-result-emp{{background:#fff;border:1px solid #e0e0f0;border-radius:10px;padding:12px 16px;margin-bottom:8px;border-top:3px solid {AMARILLO}}}
div[data-testid="stButton"]>button{{border-radius:8px!important;font-weight:700!important;font-family:'Nunito',sans-serif!important}}
hr{{border-color:#e0e0f0!important}}
</style>
""", unsafe_allow_html=True)

# ── Helpers de datos ──────────────────────────────────────────────────────────
def load_json(path):
    if path.exists():
        with open(path,"r",encoding="utf-8") as f: return json.load(f)
    return {}

def save_json(path, data):
    with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

def get_empleados():   return load_json(EMP_FILE).get("empleados",[])
def save_empleados(l): save_json(EMP_FILE,{"empleados":l})
def get_sucursales():  return load_json(SUC_FILE).get("sucursales",[])
def get_lideres():     return load_json(LID_FILE).get("lideres",[])
def get_config():      return load_json(CFG_FILE)
def save_config(d):    save_json(CFG_FILE,d)

def get_tipos_informe():
    default=[
        {"codigo":"induccion","label":"Inducción","emoji":"📋","color_bg":"#e8f5e9","color_text":"#2e7d32"},
        {"codigo":"entrevista_rrhh","label":"Entrevista RRHH","emoji":"🤝","color_bg":"#e3f2fd","color_text":"#1565c0"},
        {"codigo":"entrevista_comercial","label":"Entrevista Comercial","emoji":"💼","color_bg":"#e8eaf6","color_text":"#283593"},
        {"codigo":"desempeno","label":"Evaluación Desempeño","emoji":"📊","color_bg":"#fff3e0","color_text":"#e65100"},
        {"codigo":"seguimiento","label":"Seguimiento","emoji":"🔍","color_bg":"#f3e5f5","color_text":"#6a1b9a"},
    ]
    return load_json(TIP_FILE).get("tipos_informe",default)

def iniciales(nombre):
    p=nombre.strip().split(); return "".join(x[0] for x in p[:2]).upper() if p else "??"

def dias_en_empresa(f):
    try: return (date.today()-datetime.strptime(f,"%Y-%m-%d").date()).days
    except: return 0

def fmt_fecha(f):
    try: return datetime.strptime(f,"%Y-%m-%d").strftime("%d/%m/%Y")
    except: return f or "—"

def fmt_fecha_hora(f):
    try: return datetime.strptime(f,"%Y-%m-%d").strftime("%d/%m/%Y")
    except: return f or "—"

def pdf_dir_emp(eid):
    d=PDF_DIR/str(eid); d.mkdir(exist_ok=True); return d

def tipo_info(codigo,tipos):
    for t in tipos:
        if t["codigo"]==codigo: return t
    return {"codigo":codigo,"label":codigo,"emoji":"📄","color_bg":"#f5f5f5","color_text":"#555"}

def dias_hasta(fecha_str):
    try: return (datetime.strptime(fecha_str,"%Y-%m-%d").date()-date.today()).days
    except: return None

def extraer_texto_pdf(pdf_bytes):
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texto="\n".join(p.extract_text() or "" for p in pdf.pages).strip()
        return texto if texto else None
    except: return None

def get_groq_client():
    api_key=None
    try: api_key=st.secrets["GROQ_API_KEY"]
    except: pass
    if not api_key: api_key=os.environ.get("GROQ_API_KEY")
    if not api_key or api_key=="PEGA-TU-CLAVE-AQUI":
        return None,("⚠️ **Groq API key no configurada.**\n\n"
            "1. Entrá a https://console.groq.com\n"
            "2. Creá cuenta → **API Keys → Create API Key**\n"
            "3. Pegá la clave en `.streamlit/secrets.toml`:\n"
            "```toml\nGROQ_API_KEY = \"gsk_...\"\n```")
    return Groq(api_key=api_key),None

def foto_path(emp_id):
    for ext in ["jpg","jpeg","png","webp"]:
        p=ASSETS_DIR/f"foto_{emp_id}.{ext}"
        if p.exists(): return p
    return None

# ── Exportar ficha a PDF ──────────────────────────────────────────────────────
def md_to_rl(texto):
    """Convierte **bold** de Markdown a XML de ReportLab de forma segura."""
    import re
    # Escapar caracteres especiales XML primero
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Convertir **texto** → <b>texto</b>
    texto = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', texto)
    return texto

def exportar_ficha_pdf(emp, tipos):
    buf = io.BytesIO()

    PAGE_W, PAGE_H = A4
    MARGIN_X = 2.0 * cm
    MARGIN_Y  = 1.5 * cm

    # Alturas reales de las imágenes en la página
    # membrete: 2482x285px → en A4 ancho = PAGE_W → altura proporcional
    HEADER_H = PAGE_W * (285 / 2482)   # ~3.27cm
    FOOTER_H = PAGE_W * (79  / 2482)   # ~0.91cm
    HEADER_GAP = 0.5 * cm
    FOOTER_GAP = 0.4 * cm

    TOP_MARGIN    = HEADER_H + HEADER_GAP + MARGIN_Y
    BOTTOM_MARGIN = FOOTER_H + FOOTER_GAP + MARGIN_Y

    # ── Estilos ───────────────────────────────────────────────────────────────
    AZ  = AZUL_RL
    AM  = AMAR_RL
    GRI = colors.HexColor("#6b6b8a")
    LIG = colors.HexColor("#f0f2ff")
    BOR = colors.HexColor("#e0e0f0")

    s_nombre   = ParagraphStyle("nombre",   fontName="Helvetica-Bold",  fontSize=18, textColor=AZ,  spaceAfter=2)
    s_puesto   = ParagraphStyle("puesto",   fontName="Helvetica",       fontSize=11, textColor=GRI, spaceAfter=14)
    s_seccion  = ParagraphStyle("seccion",  fontName="Helvetica-Bold",  fontSize=11, textColor=AZ,  spaceBefore=14, spaceAfter=5)
    s_label    = ParagraphStyle("label",    fontName="Helvetica-Bold",  fontSize=8,  textColor=GRI)
    s_valor    = ParagraphStyle("valor",    fontName="Helvetica",       fontSize=9,  textColor=colors.black, leading=13)
    s_body     = ParagraphStyle("body",     fontName="Helvetica",       fontSize=9,  textColor=colors.black, leading=14, spaceAfter=3)
    s_body_b   = ParagraphStyle("bodyb",    fontName="Helvetica-Bold",  fontSize=9,  textColor=colors.black, leading=14)
    s_ia_title = ParagraphStyle("iatitle",  fontName="Helvetica-Bold",  fontSize=9,  textColor=AZ,  leading=14, spaceAfter=2)
    s_ia_body  = ParagraphStyle("iabody",   fontName="Helvetica",       fontSize=9,  textColor=colors.HexColor("#1a1a3e"), leading=14, spaceAfter=3)
    s_small    = ParagraphStyle("small",    fontName="Helvetica",       fontSize=7,  textColor=GRI)
    s_inf_tit  = ParagraphStyle("inftit",   fontName="Helvetica-Bold",  fontSize=9,  textColor=AZ,  spaceAfter=1)
    s_obs      = ParagraphStyle("obs",      fontName="Helvetica-Oblique", fontSize=8, textColor=GRI, leading=12)

    dias = dias_en_empresa(emp.get("fecha_ingreso", ""))

    # ── Dibuja membrete y pie en cada página ──────────────────────────────────
    membrete_p = ASSETS_DIR / "membrete.png"
    pie_p      = ASSETS_DIR / "pie.png"

    def draw_bg(canvas, doc):
        canvas.saveState()
        if membrete_p.exists():
            canvas.drawImage(str(membrete_p), 0, PAGE_H - HEADER_H,
                             width=PAGE_W, height=HEADER_H,
                             preserveAspectRatio=False, mask="auto")
        if pie_p.exists():
            canvas.drawImage(str(pie_p), 0, 0,
                             width=PAGE_W, height=FOOTER_H,
                             preserveAspectRatio=False, mask="auto")
        # Número de página
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.white)
        canvas.drawRightString(PAGE_W - MARGIN_X,
                               FOOTER_H / 2 - 4,
                               f"Página {doc.page}  ·  {date.today().strftime('%d/%m/%Y')}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=TOP_MARGIN, bottomMargin=BOTTOM_MARGIN
    )

    story = []
    CONTENT_W = PAGE_W - MARGIN_X * 2

    # ── Encabezado: foto + nombre + puesto ───────────────────────────────────
    fp = foto_path(emp["id"])
    nombre_bloque = [
        Paragraph(emp["nombre"], s_nombre),
        Paragraph(f"{emp.get('puesto','—')}  ·  {emp.get('centro_costo','—')}", s_puesto),
    ]
    if fp:
        img_rl = RLImage(str(fp), width=2.2*cm, height=2.2*cm)
        hdr_tbl = Table([[img_rl, nombre_bloque]],
                        colWidths=[2.6*cm, CONTENT_W - 2.6*cm])
        hdr_tbl.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (1,0), (1,0), 10),
            ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
        story.append(hdr_tbl)
    else:
        for p in nombre_bloque: story.append(p)

    story.append(HRFlowable(width="100%", thickness=2.5, color=AM, spaceAfter=10, spaceBefore=2))

    # ── Datos en tabla de 4 columnas ─────────────────────────────────────────
    story.append(Paragraph("DATOS DEL EMPLEADO", s_seccion))

    CW = CONTENT_W / 4
    def dato(label, valor):
        return [Paragraph(label, s_label), Paragraph(str(valor) if valor else "—", s_valor)]

    filas_datos = [
        dato("CENTRO DE COSTOS", emp.get("centro_costo","—")) +
        dato("LÍDER RESPONSABLE", emp.get("lider_responsable","—") or "—"),
        dato("TIPO", emp.get("tipo","—")) +
        dato("MOTIVO DE INGRESO", emp.get("motivo_ingreso","—")),
        dato("FECHA DE INGRESO", fmt_fecha(emp.get("fecha_ingreso",""))) +
        dato("DÍAS EN EMPRESA", f"{dias} días"),
        dato("REMUNERACIÓN", emp.get("remuneracion","—")) +
        dato("ESTADO", emp.get("estado","Activo")),
    ]
    if emp.get("fecha_egreso"):
        filas_datos.append(dato("FECHA DE EGRESO", fmt_fecha(emp.get("fecha_egreso",""))) + dato("",""))

    tbl_datos = Table(filas_datos, colWidths=[CW*0.6, CW*1.4, CW*0.6, CW*1.4])
    tbl_datos.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LIG),
        ("BACKGROUND",    (2,0), (2,-1), LIG),
        ("GRID",          (0,0), (-1,-1), 0.3, BOR),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
    ]))
    story.append(tbl_datos)

    if emp.get("observaciones"):
        story.append(Spacer(1, 5))
        story.append(Paragraph(f"<i>Observaciones: {emp['observaciones']}</i>", s_obs))

    # ── Historial de informes ─────────────────────────────────────────────────
    informes = emp.get("informes", [])
    if informes:
        story.append(HRFlowable(width="100%", thickness=0.5, color=BOR, spaceBefore=8, spaceAfter=2))
        story.append(Paragraph(f"HISTORIAL DE INFORMES  ({len(informes)} registros)", s_seccion))

        for inf in informes:
            ti = tipo_info(inf.get("tipo",""), tipos)
            contenido = inf.get("contenido","")
            # Si tiene texto de PDF, mostrar solo las notas adicionales + primeras líneas
            if inf.get("tiene_texto_pdf"):
                partes = contenido.split("[NOTAS ADICIONALES]")
                texto_pdf_part = partes[0].replace("[CONTENIDO DEL PDF]","").strip()
                notas_part = partes[1].strip() if len(partes)>1 else ""
                contenido_show = texto_pdf_part[:900] + ("..." if len(texto_pdf_part)>900 else "")
                if notas_part:
                    contenido_show += f"\nNotas: {notas_part}"
            else:
                contenido_show = contenido[:900] + ("..." if len(contenido)>900 else "")

            bloque = KeepTogether([
                Table([[
                    Paragraph(f"{ti['emoji']} {inf.get('titulo','—')}", s_inf_tit),
                    Paragraph(fmt_fecha(inf.get("fecha","")), s_small),
                    Paragraph(ti["label"], s_small),
                ]], colWidths=[CONTENT_W*0.55, CONTENT_W*0.22, CONTENT_W*0.23],
                style=TableStyle([
                    ("BACKGROUND",    (0,0),(-1,-1), LIG),
                    ("TOPPADDING",    (0,0),(-1,-1), 5),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                    ("LEFTPADDING",   (0,0),(0,0),   8),
                    ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                    ("ALIGN",         (1,0),(-1,-1), "RIGHT"),
                    ("RIGHTPADDING",  (2,0),(2,0),   8),
                ])),
                Paragraph(contenido_show.replace("\n","<br/>"), s_body),
                Spacer(1, 4),
                HRFlowable(width="100%", thickness=0.3, color=BOR, spaceAfter=3),
            ])
            story.append(bloque)

    # ── Próximos reportes ─────────────────────────────────────────────────────
    proximos = [r for r in emp.get("proximos_reportes",[]) if not r.get("completado")]
    if proximos:
        story.append(HRFlowable(width="100%", thickness=0.5, color=BOR, spaceBefore=4, spaceAfter=2))
        story.append(Paragraph(f"PRÓXIMOS REPORTES PROGRAMADOS  ({len(proximos)} pendientes)", s_seccion))
        prox_rows = [[
            Paragraph("TIPO", s_label),
            Paragraph("DESCRIPCIÓN", s_label),
            Paragraph("FECHA", s_label),
            Paragraph("ESTADO", s_label),
        ]]
        for r in sorted(proximos, key=lambda x: x.get("fecha","")):
            ti    = tipo_info(r.get("tipo",""), tipos)
            delta = dias_hasta(r.get("fecha",""))
            if delta is None:   est = "—"
            elif delta < 0:     est = f"Vencido ({abs(delta)}d)"
            elif delta == 0:    est = "¡Hoy!"
            elif delta <= 7:    est = f"En {delta} días"
            else:               est = f"En {delta} días"
            prox_rows.append([
                Paragraph(ti["label"], s_body),
                Paragraph(r.get("titulo","—"), s_body),
                Paragraph(fmt_fecha(r.get("fecha","")), s_body),
                Paragraph(est, s_body),
            ])
        tbl_prox = Table(prox_rows, colWidths=[CONTENT_W*0.22, CONTENT_W*0.38, CONTENT_W*0.2, CONTENT_W*0.2])
        tbl_prox.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), AZ),
            ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 8),
            ("GRID",          (0,0),(-1,-1), 0.3, BOR),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, LIG]),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ]))
        story.append(tbl_prox)

    # ── Último resumen IA ─────────────────────────────────────────────────────
    resumenes = emp.get("resumenes_ia",[])
    if resumenes:
        ultimo = resumenes[-1]
        story.append(HRFlowable(width="100%", thickness=0.5, color=BOR, spaceBefore=8, spaceAfter=2))
        story.append(Paragraph("RESUMEN IA DE TRAYECTORIA", s_seccion))
        story.append(Paragraph(
            f"Generado el {fmt_fecha(ultimo['fecha'])}  ·  {ultimo.get('informes_analizados',0)} informes analizados",
            s_small
        ))
        story.append(Spacer(1, 6))

        # Parsear el texto IA: separar por secciones numeradas
        texto_ia = ultimo["texto"]
        import re
        # Dividir por líneas y procesar
        for linea in texto_ia.split("\n"):
            linea = linea.strip()
            if not linea: continue
            # Detectar encabezados tipo "**1. Estado general**" o "1. Estado general"
            es_titulo = re.match(r'^\*?\*?(\d+\.\s+[A-ZÁÉÍÓÚÑ].{3,})\*?\*?$', linea)
            if es_titulo or re.match(r'^\*\*\d+\.', linea):
                texto_limpio = re.sub(r'\*+','',linea).strip()
                story.append(Paragraph(texto_limpio, s_ia_title))
            elif linea.startswith("- "):
                texto_limpio = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', linea[2:].replace("&","&amp;").replace("<","&lt;"))
                story.append(Paragraph(f"• {texto_limpio}", s_ia_body))
            else:
                texto_limpio = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', linea.replace("&","&amp;").replace("<","&lt;"))
                story.append(Paragraph(texto_limpio, s_ia_body))

    doc.build(story, onFirstPage=draw_bg, onLaterPages=draw_bg)
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.vista=="dashboard":
    empleados = get_empleados()
    activos   = [e for e in empleados if e.get("estado","Activo")=="Activo"]
    tipos     = get_tipos_informe()

    # Alertas
    vencidos  = [(e,r) for e in activos for r in e.get("proximos_reportes",[])
                 if not r.get("completado") and dias_hasta(r.get("fecha","")) is not None and dias_hasta(r.get("fecha",""))<0]
    hoy       = [(e,r) for e in activos for r in e.get("proximos_reportes",[])
                 if not r.get("completado") and dias_hasta(r.get("fecha",""))==0]
    proximos7 = [(e,r) for e in activos for r in e.get("proximos_reportes",[])
                 if not r.get("completado") and dias_hasta(r.get("fecha","")) is not None and 0<dias_hasta(r.get("fecha",""))<=7]
    sin_inf   = [e for e in activos if not e.get("informes") and dias_en_empresa(e.get("fecha_ingreso",""))>14]

    # Stats
    c1,c2,c3,c4,c5 = st.columns(5)
    for col,(lbl,val,dest) in zip([c1,c2,c3,c4,c5],[
        ("Empleados activos",   len(activos),      True),
        ("Reportes vencidos",   len(vencidos),     False),
        ("Reportes hoy",        len(hoy),          False),
        ("Próximos 7 días",     len(proximos7),    False),
        ("Sin informes >14d",   len(sin_inf),      False),
    ]):
        with col:
            color_num = "#e53935" if val>0 and not dest and lbl!="Próximos 7 días" else (AZUL if dest else AZUL)
            st.markdown(f'<div class="stat-box {"azul" if dest else ""}"><div class="stat-num" style="color:{"#e53935" if val>0 and "enci" in lbl else ""}">{val}</div><div class="stat-label">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
    with col_nav1:
        if st.button("👥 Ver empleados", use_container_width=True): nav("lista")
    with col_nav2:
        if st.button("👑 Ver líderes", use_container_width=True): nav("lista_lideres")
    with col_nav3:
        if st.button("➕ Nuevo empleado", type="primary", use_container_width=True): nav("nuevo_empleado")
    with col_nav4:
        if st.button("⚙️ Configuración", use_container_width=True): nav("config")

    # Alertas del día
    if vencidos or hoy:
        st.markdown("---")
        st.markdown("### ⚠️ Alertas")
        if hoy:
            st.markdown('<div class="alerta-box">', unsafe_allow_html=True)
            st.markdown(f"**🟢 {len(hoy)} reporte{'s' if len(hoy)>1 else ''} programado{'s' if len(hoy)>1 else ''} para HOY:**")
            for emp,r in hoy:
                ti=tipo_info(r.get("tipo",""),tipos)
                if st.button(f"  → {emp['nombre']} — {ti['emoji']} {r.get('titulo','—')}", key=f"alerta_hoy_{r['id']}"):
                    nav("ficha", emp["id"])
            st.markdown('</div>', unsafe_allow_html=True)
        if vencidos:
            st.markdown('<div class="alerta-box" style="background:#fce4ec;border-color:#ef9a9a">', unsafe_allow_html=True)
            st.markdown(f"**🔴 {len(vencidos)} reporte{'s' if len(vencidos)>1 else ''} VENCIDO{'S' if len(vencidos)>1 else ''}:**")
            for emp,r in vencidos:
                ti=tipo_info(r.get("tipo",""),tipos)
                delta=dias_hasta(r.get("fecha",""))
                if st.button(f"  → {emp['nombre']} — {ti['emoji']} {r.get('titulo','—')} (hace {abs(delta)} días)", key=f"alerta_v_{r['id']}"):
                    nav("ficha", emp["id"])
            st.markdown('</div>', unsafe_allow_html=True)

    if sin_inf:
        st.markdown("---")
        st.markdown(f"### 📋 Sin informes hace más de 14 días ({len(sin_inf)})")
        for emp in sin_inf:
            d=dias_en_empresa(emp.get("fecha_ingreso",""))
            if st.button(f"  → {emp['nombre']} — {emp.get('puesto','—')} ({d} días en la empresa)", key=f"sinf_{emp['id']}"):
                nav("ficha", emp["id"])

# ══════════════════════════════════════════════════════════════════════════════
# LISTA (empleados o líderes)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista in ("lista","lista_lideres"):
    es_lider = st.session_state.vista=="lista_lideres"
    empleados = get_empleados()
    sucursales= get_sucursales()
    tipos     = get_tipos_informe()

    if st.button("← Dashboard"): nav("dashboard")

    lista_base = [e for e in empleados if (e.get("tipo")=="Líder de área")==es_lider]

    # Búsqueda y filtros
    col_s, col_f1, col_f2, col_btn = st.columns([3,1.5,1.5,1])
    with col_s:
        busqueda = st.text_input("🔍 Buscar por nombre o puesto", value=st.session_state.busqueda,
                                  placeholder="Escribí para filtrar...", label_visibility="collapsed")
        st.session_state.busqueda = busqueda
    with col_f1:
        filtro_suc = st.selectbox("Sucursal", ["Todas"]+sucursales, label_visibility="collapsed")
    with col_f2:
        filtro_est = st.selectbox("Estado", ["Activos","Inactivos","Todos"], label_visibility="collapsed")
    with col_btn:
        if st.button("➕ Nuevo", type="primary"): nav("nuevo_empleado")

    # Aplicar filtros
    lista = lista_base
    if busqueda:
        q=busqueda.lower()
        lista=[e for e in lista if q in e.get("nombre","").lower() or q in e.get("puesto","").lower()]
    if filtro_suc!="Todas":
        lista=[e for e in lista if e.get("centro_costo","")==filtro_suc]
    if filtro_est=="Activos":
        lista=[e for e in lista if e.get("estado","Activo")=="Activo"]
    elif filtro_est=="Inactivos":
        lista=[e for e in lista if e.get("estado","Activo")!="Activo"]

    # Stats
    st.markdown("<br>", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    prox_urg = sum(1 for e in lista for r in e.get("proximos_reportes",[])
                   if not r.get("completado") and dias_hasta(r.get("fecha","")) is not None and dias_hasta(r.get("fecha",""))<=7)
    for col,(lbl,val,dest) in zip([c1,c2,c3,c4],[
        (f"{'Líderes' if es_lider else 'Empleados'}", len(lista), True),
        ("Sin informes",   sum(1 for e in lista if not e.get("informes")), False),
        ("Con seguimiento",sum(1 for e in lista if e.get("informes")), False),
        ("Reportes ≤7d",   prox_urg, False),
    ]):
        with col:
            st.markdown(f'<div class="stat-box {"azul" if dest else ""}"><div class="stat-num">{val}</div><div class="stat-label">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not lista:
        st.info("No hay registros con esos filtros.")
    else:
        for emp in lista:
            fp = foto_path(emp["id"])
            ninf  = len(emp.get("informes",[]))
            nprox = [r for r in emp.get("proximos_reportes",[]) if not r.get("completado")]
            urgentes=[r for r in nprox if dias_hasta(r.get("fecha","")) is not None and dias_hasta(r.get("fecha",""))<=7]
            estado = emp.get("estado","Activo")
            tag_text  = "Líder" if es_lider else ("Sin informes" if not ninf else "Con seguimiento")
            tag_class = "tag-lider" if es_lider else ("tag-nuevo" if not ninf else "tag-activo")
            if estado!="Activo": tag_class="tag-inactivo"; tag_text=estado

            ca,cb,cc = st.columns([0.6,4,1.5])
            with ca:
                if fp:
                    try:
                        img=Image.open(fp); img.thumbnail((46,46))
                        st.image(img,width=46)
                    except: st.markdown(f'<div class="avatar">{iniciales(emp["nombre"])}</div>',unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="avatar">{iniciales(emp["nombre"])}</div>',unsafe_allow_html=True)
            with cb:
                alerta=f'<span style="color:#e53935;font-size:11px;margin-left:8px">⚠️ {len(urgentes)} reporte{"s" if len(urgentes)>1 else ""} próx.</span>' if urgentes else ""
                st.markdown(f"""
                <div style="padding:3px 0">
                  <strong style="color:{AZUL};font-size:15px">{emp['nombre']}</strong><br>
                  <span style="color:#6b6b8a;font-size:12px">{emp.get('puesto','—')} · {emp.get('centro_costo','—')}</span><br>
                  <span class="tag {tag_class}">{tag_text}</span>
                  <span style="font-size:11px;color:#6b6b8a;margin-left:8px">
                    Ingreso: {fmt_fecha(emp.get('fecha_ingreso',''))} · {ninf} informe{'s' if ninf!=1 else ''}
                    {f'· {len(nprox)} pendiente{"s" if len(nprox)!=1 else ""}' if nprox else ''}
                  </span>{alerta}
                </div>""",unsafe_allow_html=True)
            with cc:
                if st.button("Ver ficha →", key=f"ver_{emp['id']}"): nav("ficha", emp["id"])
            st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# NUEVO / EDITAR EMPLEADO
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista in ("nuevo_empleado","editar_empleado"):
    editando  = st.session_state.vista=="editar_empleado"
    empleados = get_empleados()
    sucursales= get_sucursales()
    lideres   = get_lideres()

    emp_orig = next((e for e in empleados if e["id"]==st.session_state.emp_id), {}) if editando else {}

    if st.button("← Volver"): nav("ficha" if editando else "dashboard", st.session_state.emp_id if editando else None)

    st.markdown(f"## {'Editar empleado' if editando else 'Registrar nuevo empleado'}")
    st.divider()

    MOTIVOS = ["Puesto nuevo","Reemplazo","Cobertura temporal","Promoción interna","Reingreso"]

    with st.form("form_emp"):
        c1,c2 = st.columns(2)
        with c1:
            nombre       = st.text_input("Nombre completo *",          value=emp_orig.get("nombre",""))
            puesto       = st.text_input("Puesto / Cargo",             value=emp_orig.get("puesto",""))
            fecha_ing    = st.date_input("Fecha de ingreso",           value=datetime.strptime(emp_orig["fecha_ingreso"],"%Y-%m-%d").date() if emp_orig.get("fecha_ingreso") else date.today())
            remuneracion = st.text_input("Remuneración acordada",      value=emp_orig.get("remuneracion",""), placeholder="Ej: $480.000")
            motivo       = st.selectbox("Motivo de ingreso",           MOTIVOS, index=MOTIVOS.index(emp_orig.get("motivo_ingreso","Puesto nuevo")) if emp_orig.get("motivo_ingreso") in MOTIVOS else 0)
        with c2:
            tipo         = st.selectbox("Tipo",                        ["Empleado nuevo","Líder de área","Pasante"],
                                         index=["Empleado nuevo","Líder de área","Pasante"].index(emp_orig.get("tipo","Empleado nuevo")) if emp_orig.get("tipo") in ["Empleado nuevo","Líder de área","Pasante"] else 0)
            suc_opts     = ["— Seleccioná —"]+sucursales
            suc_idx      = suc_opts.index(emp_orig.get("centro_costo","— Seleccioná —")) if emp_orig.get("centro_costo") in suc_opts else 0
            suc_sel      = st.selectbox("Centro de costos *",          suc_opts, index=suc_idx)
            lid_opts     = ["— Sin asignar —"]+lideres
            lid_idx      = lid_opts.index(emp_orig.get("lider_responsable","— Sin asignar —")) if emp_orig.get("lider_responsable") in lid_opts else 0
            lid_sel      = st.selectbox("Líder responsable directo",   lid_opts, index=lid_idx)
            if editando:
                estado   = st.selectbox("Estado",                      ["Activo","Inactivo","Desvinculado"],
                                         index=["Activo","Inactivo","Desvinculado"].index(emp_orig.get("estado","Activo")) if emp_orig.get("estado") in ["Activo","Inactivo","Desvinculado"] else 0)
                if estado!="Activo":
                    fecha_egr_val = datetime.strptime(emp_orig["fecha_egreso"],"%Y-%m-%d").date() if emp_orig.get("fecha_egreso") else date.today()
                    fecha_egreso = st.date_input("Fecha de egreso", value=fecha_egr_val)
                else:
                    fecha_egreso = None
            else:
                estado="Activo"; fecha_egreso=None

        obs = st.text_area("Observaciones iniciales", value=emp_orig.get("observaciones",""), height=90)

        if st.form_submit_button("💾 Guardar", type="primary"):
            if not nombre.strip():                st.error("El nombre es obligatorio."); st.stop()
            if suc_sel=="— Seleccioná —":         st.error("Seleccioná un centro de costos."); st.stop()
            datos_nuevos = {
                "nombre": nombre.strip(), "puesto": puesto.strip(), "tipo": tipo,
                "fecha_ingreso": str(fecha_ing), "remuneracion": remuneracion.strip(),
                "centro_costo": suc_sel,
                "lider_responsable": lid_sel if lid_sel!="— Sin asignar —" else None,
                "motivo_ingreso": motivo, "estado": estado,
                "fecha_egreso": str(fecha_egreso) if fecha_egreso else None,
                "observaciones": obs.strip(),
            }
            if editando:
                for e in empleados:
                    if e["id"]==emp_orig["id"]: e.update(datos_nuevos)
                save_empleados(empleados)
                st.success("✅ Datos actualizados.")
                nav("ficha", emp_orig["id"])
            else:
                nvo_id = max((e["id"] for e in empleados), default=0)+1
                empleados.append({"id":nvo_id,"informes":[],"proximos_reportes":[],"resumenes_ia":[], **datos_nuevos})
                save_empleados(empleados)
                st.success(f"✅ {nombre} registrado.")
                nav("ficha", nvo_id)

    # Foto (fuera del form)
    if editando:
        st.markdown("#### Foto del empleado")
        foto_actual = foto_path(emp_orig["id"])
        col_foto1, col_foto2 = st.columns([1,3])
        with col_foto1:
            if foto_actual:
                st.image(str(foto_actual), width=100)
            else:
                st.markdown(f'<div class="avatar" style="width:80px;height:80px;font-size:28px">{iniciales(emp_orig.get("nombre",""))}</div>', unsafe_allow_html=True)
        with col_foto2:
            foto_up = st.file_uploader("Subir foto (JPG, PNG)", type=["jpg","jpeg","png","webp"], key="foto_up")
            if foto_up:
                # Borrar fotos anteriores
                for ext in ["jpg","jpeg","png","webp"]:
                    old_p = ASSETS_DIR/f"foto_{emp_orig['id']}.{ext}"
                    if old_p.exists(): old_p.unlink()
                ext = foto_up.name.split(".")[-1].lower()
                dest = ASSETS_DIR/f"foto_{emp_orig['id']}.{ext}"
                img = Image.open(foto_up)
                img.thumbnail((300,300))
                img.save(dest)
                st.success("✅ Foto guardada.")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FICHA EMPLEADO
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista=="ficha":
    empleados = get_empleados()
    emp   = next((e for e in empleados if e["id"]==st.session_state.emp_id), None)
    tipos = get_tipos_informe()
    if not emp: nav("dashboard")

    col_back, col_edit, col_pdf, col_estado = st.columns([2,1,1,1])
    with col_back:
        if st.button("← Volver"): nav("lista" if emp.get("tipo")!="Líder de área" else "lista_lideres")
    with col_edit:
        if st.button("✏️ Editar ficha"): nav("editar_empleado", emp["id"])
    with col_pdf:
        pdf_bytes = exportar_ficha_pdf(emp, tipos)
        st.download_button("📄 Exportar PDF", data=pdf_bytes,
                           file_name=f"ficha_{emp['nombre'].replace(' ','_')}.pdf",
                           mime="application/pdf")
    with col_estado:
        estado = emp.get("estado","Activo")
        color_est = {"Activo":"#2e7d32","Inactivo":"#e65100","Desvinculado":"#b71c1c"}.get(estado,"#555")
        st.markdown(f'<div style="text-align:center;padding-top:8px"><span style="background:{color_est}22;color:{color_est};font-weight:700;padding:4px 14px;border-radius:10px;font-size:12px">{estado}</span></div>', unsafe_allow_html=True)

    ini  = iniciales(emp["nombre"])
    dias = dias_en_empresa(emp.get("fecha_ingreso",""))
    fp   = foto_path(emp["id"])

    col_p, col_m = st.columns([1,2.5])

    with col_p:
        foto_html = ""
        if fp:
            import base64
            with open(fp,"rb") as img_f: b64=base64.b64encode(img_f.read()).decode()
            ext=str(fp).split(".")[-1]
            foto_html=f'<img src="data:image/{ext};base64,{b64}" class="ficha-avatar-big-img"/>'
        else:
            foto_html=f'<div class="ficha-avatar-big">{ini}</div>'

        st.markdown(f"""
        <div class="ficha-header">
          {foto_html}
          <div style="font-size:19px;font-weight:800">{emp['nombre']}</div>
          <div style="background:rgba(245,168,0,.2);color:{AMARILLO};font-size:11px;padding:3px 12px;border-radius:10px;display:inline-block;margin-top:5px;border:1px solid rgba(245,168,0,.3)">{emp.get('puesto','—')}</div>
        </div>
        <div style="background:#fff;border:1px solid #e0e0f0;border-radius:12px;padding:14px">
          <table style="width:100%;font-size:13px;border-collapse:collapse">
            <tr><td style="color:#6b6b8a;padding:5px 0">Centro de costos</td><td style="font-weight:700;text-align:right">{emp.get('centro_costo','—')}</td></tr>
            <tr><td style="color:#6b6b8a;padding:5px 0">Líder responsable</td><td style="font-weight:700;text-align:right;font-size:11px">{emp.get('lider_responsable') or '—'}</td></tr>
            <tr><td style="color:#6b6b8a;padding:5px 0">Motivo de ingreso</td><td style="font-weight:700;text-align:right;font-size:11px">{emp.get('motivo_ingreso','—')}</td></tr>
            <tr><td style="color:#6b6b8a;padding:5px 0">Ingreso</td><td style="font-weight:700;text-align:right">{fmt_fecha(emp.get('fecha_ingreso',''))}</td></tr>
            <tr><td style="color:#6b6b8a;padding:5px 0">Días en empresa</td><td style="font-weight:700;text-align:right;color:{AZUL}">{dias} días</td></tr>
            {f'<tr><td style="color:#6b6b8a;padding:5px 0">Egreso</td><td style="font-weight:700;text-align:right;color:#e53935">{fmt_fecha(emp.get("fecha_egreso",""))}</td></tr>' if emp.get("fecha_egreso") else ''}
          </table>
          <div class="rem-box"><span>Remuneración</span><span class="rem-valor">{emp.get('remuneracion','—')}</span></div>
          {f'<div style="margin-top:10px;font-size:12px;color:#6b6b8a;line-height:1.5;border-top:1px solid #e0e0f0;padding-top:10px">{emp["observaciones"]}</div>' if emp.get("observaciones") else ''}
        </div>
        """, unsafe_allow_html=True)

    with col_m:
        tab_inf, tab_prox, tab_ia = st.tabs(["📋  Historial de informes","📅  Próximos reportes","🤖  Resumen IA"])

        # ── INFORMES ──────────────────────────────────────────────────────────
        with tab_inf:
            ct,cb2 = st.columns([2,1])
            with ct: st.markdown("#### Informes cargados")
            with cb2:
                if st.button("＋ Cargar informe", key="btn_inf"): nav("nuevo_informe", emp["id"])
            informes=emp.get("informes",[])
            if not informes:
                st.info("Sin informes cargados aún.")
            else:
                for inf in reversed(informes):
                    ti=tipo_info(inf.get("tipo",""),tipos)
                    pp=pdf_dir_emp(emp["id"])/inf.get("pdf_filename","__")
                    tiene_pdf=bool(inf.get("pdf_filename")) and pp.exists()
                    with st.expander(f"{ti['emoji']} {inf['titulo']}  —  {fmt_fecha(inf.get('fecha',''))}"):
                        cA,cB=st.columns([3,1])
                        with cA:
                            st.markdown(f'<span style="background:{ti["color_bg"]};color:{ti["color_text"]};padding:2px 10px;border-radius:8px;font-size:11px;font-weight:700">{ti["label"]}</span>{"  📎 PDF" if tiene_pdf else ""}', unsafe_allow_html=True)
                            contenido_mostrar=inf.get("contenido","")
                            if inf.get("tiene_texto_pdf"):
                                partes=contenido_mostrar.split("[NOTAS ADICIONALES]")
                                st.markdown(f"<p style='margin-top:8px;font-size:12px;line-height:1.6'>{partes[0].replace('[CONTENIDO DEL PDF]','').strip()[:600]}{'...' if len(partes[0])>600 else ''}</p>", unsafe_allow_html=True)
                                if len(partes)>1 and partes[1].strip():
                                    st.caption(f"Notas: {partes[1].strip()}")
                            else:
                                st.markdown(f"<p style='margin-top:8px;font-size:13px;line-height:1.7'>{contenido_mostrar}</p>", unsafe_allow_html=True)
                        with cB:
                            if tiene_pdf:
                                with open(pp,"rb") as f2:
                                    st.download_button("⬇ PDF", data=f2.read(), file_name=inf["pdf_filename"], mime="application/pdf", key=f"dl_{inf['id']}")

        # ── PRÓXIMOS REPORTES ─────────────────────────────────────────────────
        with tab_prox:
            st.markdown("#### Próximos reportes programados")
            proximos=emp.get("proximos_reportes",[])
            tipos_label={t["label"]:t["codigo"] for t in tipos}

            with st.expander("＋ Agregar reporte"):
                with st.form("form_prox"):
                    pp1,pp2=st.columns(2)
                    with pp1:
                        tipo_prox  =st.selectbox("Tipo",list(tipos_label.keys()))
                        titulo_prox=st.text_input("Descripción",placeholder="Ej: Evaluación mes 2")
                    with pp2:
                        fecha_prox=st.date_input("Fecha programada",value=date.today(),key="dp_prox")
                        nota_prox =st.text_input("Nota interna (opcional)")
                    if st.form_submit_button("📅 Agregar",type="primary"):
                        emps=get_empleados()
                        for e in emps:
                            if e["id"]==emp["id"]:
                                e.setdefault("proximos_reportes",[]).append({
                                    "id":int(datetime.now().timestamp()),
                                    "tipo":tipos_label[tipo_prox],
                                    "titulo":titulo_prox.strip() or tipo_prox,
                                    "fecha":str(fecha_prox),"nota":nota_prox.strip(),"completado":False
                                })
                                emp["proximos_reportes"]=e["proximos_reportes"]; break
                        save_empleados(emps); st.success("✅ Agregado."); st.rerun()

            pendientes =[r for r in proximos if not r.get("completado")]
            completados=[r for r in proximos if r.get("completado")]

            if not pendientes and not completados: st.info("No hay reportes programados.")

            if pendientes:
                st.markdown("**Pendientes**")
                for r in sorted(pendientes,key=lambda x:x.get("fecha","")):
                    ti=tipo_info(r.get("tipo",""),tipos)
                    delta=dias_hasta(r.get("fecha",""))
                    if delta is None:   extra,txt="","—"
                    elif delta<0:       extra,txt="proximo-vencido",f'<span style="color:#e53935;font-weight:700">Vencido hace {abs(delta)}d</span>'
                    elif delta==0:      extra,txt="proximo-hoy",    f'<span style="color:#43a047;font-weight:700">¡Hoy!</span>'
                    elif delta<=7:      extra,txt="",               f'<span style="color:{AMARILLO};font-weight:700">En {delta}d</span>'
                    else:               extra,txt="",               f'<span style="color:#6b6b8a">En {delta}d</span>'
                    cr1,cr2,cr3=st.columns([3,1.5,1])
                    with cr1:
                        nota_html = f'<div style="font-size:11px;color:#888;margin-top:3px">{r["nota"]}</div>' if r.get("nota") else ""
                        st.markdown(
                            f'<div class="proximo-card {extra}" style="margin-bottom:8px">'
                            f'<div style="font-weight:700;font-size:13px">{ti["emoji"]} {r.get("titulo","—")}</div>'
                            f'<div style="font-size:12px;color:#6b6b8a;margin-top:2px">{fmt_fecha(r.get("fecha",""))} · '
                            f'<span style="background:{ti["color_bg"]};color:{ti["color_text"]};padding:1px 8px;border-radius:6px;font-size:11px">{ti["label"]}</span></div>'
                            f'{nota_html}</div>',
                            unsafe_allow_html=True
                        )
                    with cr2:
                        st.markdown(f"<div style='padding-top:16px'>{txt}</div>",unsafe_allow_html=True)
                    with cr3:
                        if st.button("✓ Listo",key=f"done_{r['id']}"):
                            emps=get_empleados()
                            for e in emps:
                                if e["id"]==emp["id"]:
                                    for rep in e.get("proximos_reportes",[]):
                                        if rep["id"]==r["id"]: rep["completado"]=True
                                    emp["proximos_reportes"]=e["proximos_reportes"]; break
                            save_empleados(emps); st.rerun()

            if completados:
                with st.expander(f"✅ Completados ({len(completados)})"):
                    for r in completados:
                        ti=tipo_info(r.get("tipo",""),tipos)
                        st.markdown(f"~~{ti['emoji']} **{r.get('titulo','—')}**~~ — {fmt_fecha(r.get('fecha',''))}")

        # ── RESUMEN IA ────────────────────────────────────────────────────────
        with tab_ia:
            st.markdown("#### Resumen de trayectoria generado por IA")
            informes=emp.get("informes",[])

            LIMITE_POR_INF=8000; LIMITE_TOTAL=60000
            encabezado=(
                f"Empleado: {emp['nombre']}\n"
                f"Puesto: {emp.get('puesto','—')} | Centro de costos: {emp.get('centro_costo','—')} | Tipo: {emp.get('tipo','—')}\n"
                f"Líder responsable: {emp.get('lider_responsable') or '—'}\n"
                f"Motivo de ingreso: {emp.get('motivo_ingreso','—')}\n"
                f"Fecha de ingreso: {fmt_fecha(emp.get('fecha_ingreso',''))} ({dias} días en la empresa)\n"
                f"Remuneración: {emp.get('remuneracion','—')}\n"
                f"Observaciones iniciales: {emp.get('observaciones') or 'Ninguna'}\n\n"
                f"HISTORIAL DE INFORMES ({len(informes)} en total):\n"
            )
            bloques=[]; chars=len(encabezado); trunc=0
            for i,inf in enumerate(informes):
                c_inf=inf.get("contenido","")
                disp=min(LIMITE_POR_INF,LIMITE_TOTAL-chars-200)
                if disp<=0: trunc+=1; continue
                if len(c_inf)>disp: c_inf=c_inf[:disp]+"[...recortado]"; trunc+=1
                bloque=(f"{i+1}. [{tipo_info(inf.get('tipo',''),tipos)['label'].upper()}]"
                        f" \"{inf['titulo']}\" — {fmt_fecha(inf.get('fecha',''))}"
                        f"{'  [PDF]' if inf.get('tiene_texto_pdf') else ''}\n   {c_inf}")
                bloques.append(bloque); chars+=len(bloque)
            contexto=encabezado+("\n\n".join(bloques) if bloques else "(Sin informes)")

            cx1,cx2=st.columns(2)
            with cx1: st.caption(f"📊 Contexto: **{chars:,} chars** (~{chars//4:,} tokens)")
            with cx2:
                if trunc: st.caption(f"⚠️ {trunc} informe/s recortados")
                else:     st.caption("✅ Todos los informes incluidos")

            resumenes_guardados=emp.get("resumenes_ia",[])
            if resumenes_guardados:
                ultimo=resumenes_guardados[-1]
                st.markdown(f"""
                <div class="ia-result">
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                    <div style="background:{AMARILLO};width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px">✨</div>
                    <div>
                      <div style="font-weight:800;font-size:14px">Último resumen IA</div>
                      <div style="font-size:11px;opacity:.6">Generado el {fmt_fecha(ultimo['fecha'])} · {ultimo.get('informes_analizados',0)} informes analizados</div>
                    </div>
                  </div>
                  <div style="font-size:13px;line-height:1.8;white-space:pre-wrap">{ultimo['texto']}</div>
                </div>""", unsafe_allow_html=True)
                if len(resumenes_guardados)>1:
                    with st.expander(f"📚 Historial completo ({len(resumenes_guardados)} resúmenes)"):
                        for r in reversed(resumenes_guardados[:-1]):
                            st.markdown(f"**{fmt_fecha(r['fecha'])}** · {r.get('informes_analizados',0)} informes")
                            st.markdown(f"<div style='font-size:12px;color:#444;white-space:pre-wrap;background:#f8f8f8;padding:10px;border-radius:8px;margin-bottom:10px'>{r['texto']}</div>",unsafe_allow_html=True)
            else:
                st.info("No hay resúmenes generados aún.")

            st.markdown("---")
            btn_lbl="🔄 Actualizar resumen" if resumenes_guardados else "✨ Generar resumen con IA"
            if st.button(btn_lbl, type="primary"):
                with st.spinner("Analizando trayectoria..."):
                    client,err=get_groq_client()
                    if err: st.warning(err)
                    else:
                        try:
                            resp=client.chat.completions.create(
                                model="llama-3.3-70b-versatile", max_tokens=1024,
                                messages=[
                                    {"role":"system","content":"Sos un especialista senior en RRHH de Castillo, empresa argentina de distribución con más de 100 años de historia (desde 1924). Analizás fichas de empleados y generás resúmenes profesionales, concisos y útiles para el equipo de RRHH. Respondés en español rioplatense, de forma directa. Usá estas 4 secciones:\n**1. Estado general**\n**2. Puntos positivos observados**\n**3. Áreas a desarrollar**\n**4. Recomendación para RRHH**"},
                                    {"role":"user","content":f"Generá un resumen de trayectoria:\n\n{contexto}"}
                                ]
                            )
                            resumen=resp.choices[0].message.content
                            emps=get_empleados()
                            for e in emps:
                                if e["id"]==emp["id"]:
                                    e.setdefault("resumenes_ia",[]).append({
                                        "id":int(datetime.now().timestamp()),
                                        "fecha":str(date.today()), "texto":resumen,
                                        "informes_analizados":len(informes), "chars_contexto":chars
                                    })
                                    emp["resumenes_ia"]=e["resumenes_ia"]; break
                            save_empleados(emps)
                            st.success("✅ Resumen guardado."); st.rerun()
                        except Exception as ex:
                            st.error(f"Error al llamar a la IA: {ex}")

# ══════════════════════════════════════════════════════════════════════════════
# NUEVO INFORME
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista=="nuevo_informe":
    empleados=get_empleados()
    emp=next((e for e in empleados if e["id"]==st.session_state.emp_id),None)
    tipos=get_tipos_informe()
    if not emp: nav("dashboard")

    if st.button("← Volver a la ficha"): nav("ficha",emp["id"])
    st.markdown(f"## Cargar informe — {emp['nombre']}"); st.divider()

    tipos_opc={f"{t['emoji']} {t['label']}":t["codigo"] for t in tipos}

    pdf_file=st.file_uploader("Adjuntar PDF del informe (opcional)",type=["pdf"])
    texto_pdf=None; pdf_bytes_ok=None
    if pdf_file:
        pdf_bytes_ok=pdf_file.read()
        texto_pdf=extraer_texto_pdf(pdf_bytes_ok)
        if texto_pdf:
            with st.expander("📄 Vista previa texto extraído del PDF"):
                st.text(texto_pdf[:1500]+("..." if len(texto_pdf)>1500 else ""))
            st.success(f"✅ PDF leído: {len(texto_pdf):,} caracteres. La IA lo usará en el resumen.")
        else:
            st.warning("⚠️ No se pudo extraer texto (PDF escaneado). Escribí el contenido manualmente.")

    with st.form("form_informe"):
        c1,c2=st.columns(2)
        with c1:
            tipo_sel =st.selectbox("Tipo de informe",list(tipos_opc.keys()))
            titulo   =st.text_input("Título *",placeholder="Ej: Inducción semana 1")
            fecha_inf=st.date_input("Fecha",value=date.today())
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            st.caption("📎 PDF: " + ("✅ cargado con texto" if texto_pdf else ("⚠️ sin texto extraíble" if pdf_bytes_ok else "ninguno")))
        contenido_manual=st.text_area(
            "Notas adicionales / Contenido manual",height=160,
            placeholder="El texto del PDF se usará automáticamente. Agregá notas extra acá..." if texto_pdf else "Escribí el detalle del informe..."
        )
        if st.form_submit_button("💾 Guardar informe",type="primary"):
            partes=[]
            if texto_pdf:    partes.append(f"[CONTENIDO DEL PDF]\n{texto_pdf}")
            if contenido_manual.strip(): partes.append(f"[NOTAS ADICIONALES]\n{contenido_manual.strip()}")
            contenido_final="\n\n".join(partes)
            if not titulo.strip():   st.error("El título es obligatorio."); st.stop()
            if not contenido_final:  st.error("Subí un PDF o escribí el contenido."); st.stop()
            pdf_filename=None
            if pdf_bytes_ok:
                pdf_filename=f"{emp['id']}_{int(datetime.now().timestamp())}_{pdf_file.name}"
                with open(pdf_dir_emp(emp["id"])/pdf_filename,"wb") as f2: f2.write(pdf_bytes_ok)
            emps=get_empleados()
            for e in emps:
                if e["id"]==emp["id"]:
                    e.setdefault("informes",[]).append({
                        "id":int(datetime.now().timestamp()),
                        "tipo":tipos_opc[tipo_sel],"titulo":titulo.strip(),
                        "fecha":str(fecha_inf),"contenido":contenido_final,
                        "pdf_filename":pdf_filename,"tiene_texto_pdf":bool(texto_pdf)
                    }); break
            save_empleados(emps)
            st.success("✅ Informe guardado."); nav("ficha",emp["id"])

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista=="config":
    if st.button("← Dashboard"): nav("dashboard")
    st.markdown("## ⚙️ Configuración del sistema"); st.divider()

    cfg=get_config()

    tab_img, tab_tipos = st.tabs(["🖼️  Membrete y pie de página","📋  Tipos de informe"])

    with tab_img:
        st.markdown("#### Imágenes para el PDF exportado")
        st.caption("Estas imágenes se usan como encabezado y pie en todos los PDFs de fichas exportados.")

        c1,c2=st.columns(2)
        with c1:
            st.markdown("**Membrete (encabezado)**")
            header_actual=ASSETS_DIR/"membrete.png"
            if header_actual.exists():
                st.image(str(header_actual),use_container_width=True)
                st.caption("✅ Imagen cargada")
            else:
                st.info("Sin membrete cargado — el PDF no tendrá encabezado.")
            up_header=st.file_uploader("Subir membrete",type=["png","jpg","jpeg"],key="up_header")
            if up_header:
                img=Image.open(up_header)
                img.save(ASSETS_DIR/"membrete.png")
                st.success("✅ Membrete guardado."); st.rerun()
            if header_actual.exists():
                if st.button("🗑 Eliminar membrete"):
                    header_actual.unlink(); st.rerun()

        with c2:
            st.markdown("**Pie de página**")
            footer_actual=ASSETS_DIR/"pie.png"
            if footer_actual.exists():
                st.image(str(footer_actual),use_container_width=True)
                st.caption("✅ Imagen cargada")
            else:
                st.info("Sin pie cargado — el PDF no tendrá pie de página.")
            up_footer=st.file_uploader("Subir pie de página",type=["png","jpg","jpeg"],key="up_footer")
            if up_footer:
                img=Image.open(up_footer)
                img.save(ASSETS_DIR/"pie.png")
                st.success("✅ Pie guardado."); st.rerun()
            if footer_actual.exists():
                if st.button("🗑 Eliminar pie"):
                    footer_actual.unlink(); st.rerun()

        st.markdown("---")
        st.markdown("**Recomendaciones para las imágenes:**")
        st.markdown("- Membrete: ancho completo de hoja A4 (~2480px), alto ~350px, fondo blanco o transparente\n- Pie: mismas dimensiones, alto ~250px\n- Formato PNG para mejor calidad")

    with tab_tipos:
        st.markdown("#### Tipos de informe configurables")
        st.caption("Editá directamente el archivo `data/tipos_informe.json` para agregar, modificar o eliminar tipos.")
        tipos_actuales=get_tipos_informe()
        for t in tipos_actuales:
            st.markdown(f"**{t['emoji']} {t['label']}** — código: `{t['codigo']}`")
        st.markdown("---")
        st.info("Para modificar los tipos, editá el archivo `data/tipos_informe.json` con el Bloc de notas y reiniciá la app.")
