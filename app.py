import streamlit as st
import json, os, io, re, shutil
from datetime import date, datetime
from pathlib import Path
from groq import Groq
import pdfplumber
from PIL import Image

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

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
CHK_FILE   = DATA_DIR / "checklists.json"

for d in [PDF_DIR, DATA_DIR, ASSETS_DIR]: d.mkdir(exist_ok=True)

AZUL     = "#1a1e8f"
AMARILLO = "#f5a800"
AZUL_RL  = colors.HexColor("#1a1e8f")
AMAR_RL  = colors.HexColor("#f5a800")

# ── Configuración página ──────────────────────────────────────────────────────
st.set_page_config(page_title="Castillo RRHH", page_icon="🏢",
                   layout="wide", initial_sidebar_state="collapsed")

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
.badge-rrhh{{background:{AMARILLO};color:{AZUL};font-size:11px;font-weight:800;padding:5px 14px;border-radius:20px;letter-spacing:1px}}
.badge-comercial{{background:#fff;color:{AZUL};font-size:11px;font-weight:800;padding:5px 14px;border-radius:20px;letter-spacing:1px}}
.stat-box{{background:#fff;border:1px solid #e0e0f0;border-radius:12px;padding:14px 18px;text-align:center}}
.stat-box.azul{{background:{AZUL}}}
.stat-num{{font-size:26px;font-weight:800;color:{AZUL}}}
.stat-box.azul .stat-num{{color:{AMARILLO}}}
.stat-label{{font-size:10px;color:#6b6b8a;text-transform:uppercase;letter-spacing:1px}}
.stat-box.azul .stat-label{{color:rgba(255,255,255,.6)}}
.avatar{{width:46px;height:46px;border-radius:50%;background:{AZUL};color:{AMARILLO};font-size:17px;font-weight:800;display:flex;align-items:center;justify-content:center}}
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
/* Chat */
.chat-msg-rrhh{{background:#eef0ff;border-radius:12px 12px 12px 2px;padding:10px 14px;margin-bottom:8px;max-width:85%}}
.chat-msg-comercial{{background:#fff8e1;border-radius:12px 12px 2px 12px;padding:10px 14px;margin-bottom:8px;max-width:85%;margin-left:auto}}
.chat-autor{{font-size:10px;font-weight:800;color:{AZUL};margin-bottom:2px}}
.chat-autor-com{{font-size:10px;font-weight:800;color:#e65100;margin-bottom:2px;text-align:right}}
.chat-texto{{font-size:13px;line-height:1.5}}
.chat-fecha{{font-size:10px;color:#aaa;margin-top:2px}}
/* Checklist */
.chk-seccion{{background:#fff;border:1px solid #e0e0f0;border-radius:10px;padding:14px 16px;margin-bottom:10px}}
.chk-titulo{{font-weight:800;color:{AZUL};font-size:13px;margin-bottom:8px}}
.chk-item-ok{{font-size:12px;color:#2e7d32;text-decoration:line-through;opacity:0.7}}
.chk-item-pend{{font-size:12px;color:#333}}
/* Nota pineada */
.nota-pin{{background:#fffde7;border:1px solid #ffe082;border-left:4px solid {AMARILLO};border-radius:8px;padding:10px 14px;margin-bottom:8px}}
.nota-pin-texto{{font-size:13px;font-weight:600;color:#555}}
/* Score */
.score-card{{background:#fff;border:1px solid #e0e0f0;border-radius:10px;padding:14px;text-align:center}}
.score-num{{font-size:32px;font-weight:800;color:{AZUL}}}
.score-label{{font-size:10px;color:#6b6b8a;text-transform:uppercase;letter-spacing:1px;margin-top:2px}}
/* Directiva Comercial */
.directiva-card{{background:#fff8e1;border:1px solid #ffe082;border-left:4px solid #e65100;border-radius:8px;padding:12px 16px;margin-bottom:8px}}
/* Timeline */
.tl-item{{display:flex;gap:12px;margin-bottom:14px;align-items:flex-start}}
.tl-dot{{width:12px;height:12px;border-radius:50%;flex-shrink:0;margin-top:4px}}
.tl-linea{{border-left:2px solid #e0e0f0;margin-left:5px;padding-left:15px}}
/* Selector rol */
.rol-card{{background:#fff;border:2px solid #e0e0f0;border-radius:16px;padding:32px;text-align:center;cursor:pointer;transition:all .2s}}
.rol-card:hover{{border-color:{AZUL};box-shadow:0 4px 20px rgba(26,30,143,.1)}}
.rol-card.rrhh{{border-top:5px solid {AMARILLO}}}
.rol-card.comercial{{border-top:5px solid #e65100}}
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
def get_checklists():  return load_json(CHK_FILE).get("plantillas",[])

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

def fmt_datetime(f):
    try: return datetime.strptime(f,"%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except: return fmt_fecha(f)

def pdf_dir_emp(eid):
    d=PDF_DIR/str(eid); d.mkdir(exist_ok=True); return d

def tipo_info(codigo,tipos):
    for t in tipos:
        if t["codigo"]==codigo: return t
    return {"codigo":codigo,"label":codigo,"emoji":"📄","color_bg":"#f5f5f5","color_text":"#555"}

def dias_hasta(fecha_str):
    try: return (datetime.strptime(fecha_str,"%Y-%m-%d").date()-date.today()).days
    except: return None

def foto_path(emp_id):
    for ext in ["jpg","jpeg","png","webp"]:
        p=ASSETS_DIR/f"foto_{emp_id}.{ext}"
        if p.exists(): return p
    return None

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
            "Configurá `GROQ_API_KEY` en `.streamlit/secrets.toml`\n"
            "Obtenés tu clave gratis en https://console.groq.com")
    return Groq(api_key=api_key),None

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ── Buscar plantilla checklist por puesto ─────────────────────────────────────
def buscar_plantilla_checklist(puesto):
    plantillas = get_checklists()
    puesto_lower = puesto.lower()
    for p in plantillas:
        if p["puesto_clave"] in puesto_lower or puesto_lower in p["puesto_clave"]:
            return p
    return None

def checklist_progreso(checklist):
    """Retorna (completados, total, porcentaje)"""
    total = sum(len(s["items"]) for s in checklist.get("secciones",[]))
    completados = sum(
        1 for s in checklist.get("secciones",[])
        for item in s["items"]
        if checklist.get("estado",{}).get(f"{s['titulo']}::{item}",{}).get("ok", False)
    )
    pct = int(completados/total*100) if total else 0
    return completados, total, pct

def score_color(val):
    if val is None: return "#aaa"
    if val >= 8: return "#2e7d32"
    if val >= 6: return "#f57c00"
    return "#c62828"

# ── Exportar PDF ──────────────────────────────────────────────────────────────
def exportar_ficha_pdf(emp, tipos):
    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4
    MARGIN_X = 2.0*cm
    MARGIN_Y  = 1.5*cm
    HEADER_H = PAGE_W*(285/2482)
    FOOTER_H = PAGE_W*(79/2482)
    TOP_MARGIN    = HEADER_H + 0.5*cm + MARGIN_Y
    BOTTOM_MARGIN = FOOTER_H + 0.4*cm + MARGIN_Y
    CONTENT_W = PAGE_W - MARGIN_X*2

    AZ  = AZUL_RL; AM = AMAR_RL
    GRI = colors.HexColor("#6b6b8a")
    LIG = colors.HexColor("#f0f2ff")
    BOR = colors.HexColor("#e0e0f0")

    s_nombre  = ParagraphStyle("nombre", fontName="Helvetica-Bold",   fontSize=18, textColor=AZ,  spaceAfter=2)
    s_puesto  = ParagraphStyle("puesto", fontName="Helvetica",        fontSize=11, textColor=GRI, spaceAfter=14)
    s_sec     = ParagraphStyle("sec",    fontName="Helvetica-Bold",   fontSize=11, textColor=AZ,  spaceBefore=14, spaceAfter=5)
    s_label   = ParagraphStyle("label",  fontName="Helvetica-Bold",   fontSize=8,  textColor=GRI)
    s_valor   = ParagraphStyle("valor",  fontName="Helvetica",        fontSize=9,  leading=13)
    s_body    = ParagraphStyle("body",   fontName="Helvetica",        fontSize=9,  leading=14, spaceAfter=3)
    s_body_b  = ParagraphStyle("bodyb",  fontName="Helvetica-Bold",   fontSize=9,  leading=14)
    s_ia_t    = ParagraphStyle("iat",    fontName="Helvetica-Bold",   fontSize=9,  textColor=AZ,  leading=14, spaceAfter=2)
    s_ia_b    = ParagraphStyle("iab",    fontName="Helvetica",        fontSize=9,  textColor=colors.HexColor("#1a1a3e"), leading=14, spaceAfter=3)
    s_small   = ParagraphStyle("small",  fontName="Helvetica",        fontSize=7,  textColor=GRI)
    s_obs     = ParagraphStyle("obs",    fontName="Helvetica-Oblique",fontSize=8,  textColor=GRI, leading=12)

    dias = dias_en_empresa(emp.get("fecha_ingreso",""))
    membrete_p = ASSETS_DIR/"membrete.png"
    pie_p      = ASSETS_DIR/"pie.png"

    def draw_bg(canvas, doc):
        canvas.saveState()
        if membrete_p.exists():
            canvas.drawImage(str(membrete_p),0,PAGE_H-HEADER_H,width=PAGE_W,height=HEADER_H,preserveAspectRatio=False,mask="auto")
        if pie_p.exists():
            canvas.drawImage(str(pie_p),0,0,width=PAGE_W,height=FOOTER_H,preserveAspectRatio=False,mask="auto")
        canvas.setFont("Helvetica",7); canvas.setFillColor(colors.white)
        canvas.drawRightString(PAGE_W-MARGIN_X,FOOTER_H/2-4,f"Pág. {doc.page}  ·  {date.today().strftime('%d/%m/%Y')}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf,pagesize=A4,leftMargin=MARGIN_X,rightMargin=MARGIN_X,
                             topMargin=TOP_MARGIN,bottomMargin=BOTTOM_MARGIN)
    story = []
    fp = foto_path(emp["id"])
    nombre_bloque = [Paragraph(emp["nombre"],s_nombre),
                     Paragraph(f"{emp.get('puesto','—')}  ·  {emp.get('centro_costo','—')}",s_puesto)]
    if fp:
        img_rl=RLImage(str(fp),width=2.2*cm,height=2.2*cm)
        ht=Table([[img_rl,nombre_bloque]],colWidths=[2.6*cm,CONTENT_W-2.6*cm])
        ht.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(1,0),(1,0),10)]))
        story.append(ht)
    else:
        for p in nombre_bloque: story.append(p)
    story.append(HRFlowable(width="100%",thickness=2.5,color=AM,spaceAfter=10,spaceBefore=2))

    CW=CONTENT_W/4
    def dato(label,valor):
        return [Paragraph(label,s_label),Paragraph(str(valor) if valor else "—",s_valor)]
    filas=[
        dato("CENTRO DE COSTOS",emp.get("centro_costo","—"))+dato("LÍDER RESPONSABLE",emp.get("lider_responsable","—") or "—"),
        dato("TIPO",emp.get("tipo","—"))+dato("MOTIVO DE INGRESO",emp.get("motivo_ingreso","—")),
        dato("FECHA DE INGRESO",fmt_fecha(emp.get("fecha_ingreso","")))+dato("DÍAS EN EMPRESA",f"{dias} días"),
        dato("REMUNERACIÓN",emp.get("remuneracion","—"))+dato("ESTADO",emp.get("estado","Activo")),
    ]
    story.append(Paragraph("DATOS DEL EMPLEADO",s_sec))
    td=Table(filas,colWidths=[CW*.6,CW*1.4,CW*.6,CW*1.4])
    td.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),LIG),("BACKGROUND",(2,0),(2,-1),LIG),
        ("GRID",(0,0),(-1,-1),.3,BOR),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8)]))
    story.append(td)
    if emp.get("observaciones"):
        story.append(Spacer(1,5))
        story.append(Paragraph(f"<i>Observaciones: {emp['observaciones']}</i>",s_obs))

    # Scores
    scores = emp.get("scores",[])
    if scores:
        ultimo_score = scores[-1]
        story.append(Paragraph("INDICADORES DE DESEMPEÑO",s_sec))
        score_items = [
            ("Gestión comercial",   ultimo_score.get("comercial")),
            ("Liderazgo",           ultimo_score.get("liderazgo")),
            ("Procesos operativos", ultimo_score.get("operativo")),
            ("Comunicación",        ultimo_score.get("comunicacion")),
        ]
        score_rows = [[Paragraph(l,s_label),Paragraph(f"{v}/10" if v else "—",s_valor)] for l,v in score_items]
        ts=Table(score_rows,colWidths=[CONTENT_W/2,CONTENT_W/2])
        ts.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.3,BOR),("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(0,0),(-1,-1),8),
            ("BACKGROUND",(0,0),(0,-1),LIG)]))
        story.append(ts)
        story.append(Paragraph(f"Registrado el {fmt_fecha(ultimo_score.get('fecha',''))} · {ultimo_score.get('observacion','')}",s_small))

    # Checklist progreso
    checklist = emp.get("checklist")
    if checklist:
        comp, total, pct = checklist_progreso(checklist)
        story.append(Paragraph("CHECKLIST DE INDUCCIÓN",s_sec))
        story.append(Paragraph(f"Progreso: {comp}/{total} ítems completados ({pct}%)",s_body))

    # Directivas comerciales
    directivas = emp.get("directivas",[])
    if directivas:
        story.append(Paragraph(f"DIRECTIVAS COMERCIALES ({len(directivas)})",s_sec))
        for d in directivas[-3:]:  # últimas 3
            story.append(Paragraph(f"<b>{d.get('titulo','—')}</b>  ·  {fmt_fecha(d.get('fecha',''))}",s_body_b))
            story.append(Paragraph(d.get("texto",""),s_body))
            story.append(Spacer(1,4))

    # Informes
    informes=emp.get("informes",[])
    if informes:
        story.append(HRFlowable(width="100%",thickness=.5,color=BOR,spaceBefore=8,spaceAfter=2))
        story.append(Paragraph(f"HISTORIAL DE INFORMES ({len(informes)})",s_sec))
        for inf in informes:
            ti=tipo_info(inf.get("tipo",""),get_tipos_informe())
            contenido=inf.get("contenido","")
            if inf.get("tiene_texto_pdf"):
                partes=contenido.split("[NOTAS ADICIONALES]")
                contenido=partes[0].replace("[CONTENIDO DEL PDF]","").strip()[:800]
            else:
                contenido=contenido[:800]
            bloque=KeepTogether([
                Table([[Paragraph(f"{ti['emoji']} {inf.get('titulo','—')}",s_body_b),
                        Paragraph(fmt_fecha(inf.get("fecha","")),s_small),
                        Paragraph(ti["label"],s_small)]],
                      colWidths=[CONTENT_W*.55,CONTENT_W*.22,CONTENT_W*.23],
                      style=TableStyle([("BACKGROUND",(0,0),(-1,-1),LIG),
                        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                        ("LEFTPADDING",(0,0),(0,0),8),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                        ("ALIGN",(1,0),(-1,-1),"RIGHT"),("RIGHTPADDING",(2,0),(2,0),8)])),
                Paragraph(contenido.replace("\n","<br/>"),s_body),
                Spacer(1,4),HRFlowable(width="100%",thickness=.3,color=BOR,spaceAfter=3),
            ])
            story.append(bloque)

    # Resumen IA
    resumenes=emp.get("resumenes_ia",[])
    if resumenes:
        ultimo=resumenes[-1]
        story.append(HRFlowable(width="100%",thickness=.5,color=BOR,spaceBefore=8,spaceAfter=2))
        story.append(Paragraph("RESUMEN IA DE TRAYECTORIA",s_sec))
        story.append(Paragraph(f"Generado el {fmt_fecha(ultimo['fecha'])} · {ultimo.get('informes_analizados',0)} informes analizados",s_small))
        story.append(Spacer(1,6))
        for linea in ultimo["texto"].split("\n"):
            linea=linea.strip()
            if not linea: continue
            es_titulo=re.match(r'^\*?\*?(\d+\.\s+[A-ZÁÉÍÓÚÑ].{3,})\*?\*?$',linea)
            if es_titulo or re.match(r'^\*\*\d+\.',linea):
                story.append(Paragraph(re.sub(r'\*+','',linea).strip(),s_ia_t))
            elif linea.startswith("- "):
                tl=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',linea[2:].replace("&","&amp;").replace("<","&lt;"))
                story.append(Paragraph(f"• {tl}",s_ia_b))
            else:
                tl=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',linea.replace("&","&amp;").replace("<","&lt;"))
                story.append(Paragraph(tl,s_ia_b))

    doc.build(story,onFirstPage=draw_bg,onLaterPages=draw_bg)
    buf.seek(0); return buf.read()

# ══════════════════════════════════════════════════════════════════════════════
# INIT SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
def _init():
    defaults = {
        "rol": None,          # "rrhh" | "comercial"
        "vista": "dashboard",
        "emp_id": None,
        "busqueda": "",
        "filtro_suc": "Todas",
        "filtro_est": "Activos",
    }
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
_init()

def nav(vista, emp_id=None):
    st.session_state.vista=vista
    if emp_id is not None: st.session_state.emp_id=emp_id
    st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
rol = st.session_state.get("rol")
badge = f'<span class="badge-{"rrhh" if rol=="rrhh" else "comercial"}">{"RRHH" if rol=="rrhh" else "COMERCIAL"}</span>' if rol else ""
cambiar_rol = ""
if rol:
    cambiar_rol = ""  # lo ponemos en columna

st.markdown(f"""
<div class="castillo-header">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="castillo-logo">Castillo</div>
    <div>
      <div class="castillo-title">Sistema de Seguimiento RRHH</div>
      <div class="castillo-subtitle">DESDE 1924</div>
    </div>
  </div>
  <div style="margin-left:auto;display:flex;align-items:center;gap:10px">
    {badge}
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SELECTOR DE ROL
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.rol:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;margin-bottom:24px'><h2 style='color:#1a1e8f'>¿Con qué perfil ingresás?</h2></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.markdown(f"""
        <div class="rol-card rrhh">
          <div style="font-size:48px;margin-bottom:12px">🏢</div>
          <div style="font-size:18px;font-weight:800;color:{AZUL};margin-bottom:8px">RRHH</div>
          <div style="font-size:13px;color:#6b6b8a">Acceso completo: empleados, informes, checklists, resúmenes IA, configuración.</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Entrar como RRHH", type="primary", use_container_width=True):
            st.session_state.rol="rrhh"; st.rerun()
    with c3:
        st.markdown(f"""
        <div class="rol-card comercial">
          <div style="font-size:48px;margin-bottom:12px">💼</div>
          <div style="font-size:18px;font-weight:800;color:#e65100;margin-bottom:8px">Comercial</div>
          <div style="font-size:13px;color:#6b6b8a">Cargá directivas, comentá informes y hacé seguimiento de los líderes de tu área.</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Entrar como Comercial", use_container_width=True):
            st.session_state.rol="comercial"; st.rerun()
    st.stop()

# Botón cambiar rol en sidebar
with st.sidebar:
    st.markdown(f"**Rol activo:** {'🏢 RRHH' if rol=='rrhh' else '💼 Comercial'}")
    if st.button("🔄 Cambiar rol"):
        st.session_state.rol=None; st.session_state.vista="dashboard"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.vista=="dashboard":
    empleados=get_empleados()
    activos=[e for e in empleados if e.get("estado","Activo")=="Activo"]
    tipos=get_tipos_informe()

    vencidos=[(e,r) for e in activos for r in e.get("proximos_reportes",[])
              if not r.get("completado") and dias_hasta(r.get("fecha","")) is not None and dias_hasta(r.get("fecha",""))<0]
    hoy_rep=[(e,r) for e in activos for r in e.get("proximos_reportes",[])
             if not r.get("completado") and dias_hasta(r.get("fecha",""))==0]
    proximos7=[(e,r) for e in activos for r in e.get("proximos_reportes",[])
               if not r.get("completado") and dias_hasta(r.get("fecha","")) is not None and 0<dias_hasta(r.get("fecha",""))<=7]
    sin_inf=[e for e in activos if not e.get("informes") and dias_en_empresa(e.get("fecha_ingreso",""))>14]
    chk_incompletos=[e for e in activos if e.get("checklist") and checklist_progreso(e["checklist"])[2]<100]

    c1,c2,c3,c4,c5=st.columns(5)
    for col,(lbl,val,dest) in zip([c1,c2,c3,c4,c5],[
        ("Empleados activos",  len(activos), True),
        ("Reportes vencidos",  len(vencidos), False),
        ("Reportes hoy",       len(hoy_rep), False),
        ("Sin informes >14d",  len(sin_inf), False),
        ("Checklists abiertos",len(chk_incompletos), False),
    ]):
        with col:
            st.markdown(f'<div class="stat-box {"azul" if dest else ""}"><div class="stat-num">{val}</div><div class="stat-label">{lbl}</div></div>',unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)

    if rol=="rrhh":
        col_n1,col_n2,col_n3,col_n4=st.columns(4)
        with col_n1:
            if st.button("👥 Empleados",use_container_width=True): nav("lista")
        with col_n2:
            if st.button("👑 Líderes",use_container_width=True): nav("lista_lideres")
        with col_n3:
            if st.button("➕ Nuevo empleado",type="primary",use_container_width=True): nav("nuevo_empleado")
        with col_n4:
            if st.button("⚙️ Configuración",use_container_width=True): nav("config")
    else:
        col_n1,col_n2=st.columns(2)
        with col_n1:
            if st.button("👑 Ver líderes de mi área",use_container_width=True): nav("lista_lideres")
        with col_n2:
            if st.button("👥 Ver todos los empleados",use_container_width=True): nav("lista")

    # Alertas
    if vencidos or hoy_rep:
        st.markdown("---")
        st.markdown("### ⚠️ Alertas")
        if hoy_rep:
            st.markdown('<div class="alerta-box">',unsafe_allow_html=True)
            st.markdown(f"**🟢 {len(hoy_rep)} reporte/s para HOY:**")
            for emp,r in hoy_rep:
                ti=tipo_info(r.get("tipo",""),tipos)
                if st.button(f"→ {emp['nombre']} — {ti['emoji']} {r.get('titulo','—')}",key=f"ah_{r['id']}"):
                    nav("ficha",emp["id"])
            st.markdown('</div>',unsafe_allow_html=True)
        if vencidos:
            st.markdown('<div class="alerta-box" style="background:#fce4ec;border-color:#ef9a9a">',unsafe_allow_html=True)
            st.markdown(f"**🔴 {len(vencidos)} reporte/s VENCIDO/S:**")
            for emp,r in vencidos:
                ti=tipo_info(r.get("tipo",""),tipos)
                delta=dias_hasta(r.get("fecha",""))
                if st.button(f"→ {emp['nombre']} — {ti['emoji']} {r.get('titulo','—')} (hace {abs(delta)}d)",key=f"av_{r['id']}"):
                    nav("ficha",emp["id"])
            st.markdown('</div>',unsafe_allow_html=True)

    if sin_inf and rol=="rrhh":
        st.markdown("---")
        st.markdown(f"### 📋 Sin informes hace más de 14 días ({len(sin_inf)})")
        for e in sin_inf:
            d=dias_en_empresa(e.get("fecha_ingreso",""))
            if st.button(f"→ {e['nombre']} — {e.get('puesto','—')} ({d} días)",key=f"si_{e['id']}"):
                nav("ficha",e["id"])

    if chk_incompletos and rol=="rrhh":
        st.markdown("---")
        st.markdown(f"### ✅ Checklists de inducción incompletos ({len(chk_incompletos)})")
        for e in chk_incompletos:
            _,_,pct=checklist_progreso(e["checklist"])
            if st.button(f"→ {e['nombre']} — {pct}% completado",key=f"chk_{e['id']}"):
                nav("ficha",e["id"])

# ══════════════════════════════════════════════════════════════════════════════
# LISTA
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista in ("lista","lista_lideres"):
    es_lider=st.session_state.vista=="lista_lideres"
    empleados=get_empleados(); sucursales=get_sucursales(); tipos=get_tipos_informe()
    if st.button("← Dashboard"): nav("dashboard")

    lista_base=[e for e in empleados if (e.get("tipo")=="Líder de área")==es_lider]
    cs,cf1,cf2,cb=st.columns([3,1.5,1.5,1])
    with cs:
        busqueda=st.text_input("🔍 Buscar",value=st.session_state.busqueda,placeholder="Nombre o puesto...",label_visibility="collapsed")
        st.session_state.busqueda=busqueda
    with cf1:
        filtro_suc=st.selectbox("Sucursal",["Todas"]+sucursales,label_visibility="collapsed")
    with cf2:
        filtro_est=st.selectbox("Estado",["Activos","Inactivos","Todos"],label_visibility="collapsed")
    with cb:
        if rol=="rrhh" and st.button("➕ Nuevo",type="primary"): nav("nuevo_empleado")

    lista=lista_base
    if busqueda:
        q=busqueda.lower(); lista=[e for e in lista if q in e.get("nombre","").lower() or q in e.get("puesto","").lower()]
    if filtro_suc!="Todas": lista=[e for e in lista if e.get("centro_costo","")==filtro_suc]
    if filtro_est=="Activos": lista=[e for e in lista if e.get("estado","Activo")=="Activo"]
    elif filtro_est=="Inactivos": lista=[e for e in lista if e.get("estado","Activo")!="Activo"]

    st.markdown("<br>",unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    prox_urg=sum(1 for e in lista for r in e.get("proximos_reportes",[])
                 if not r.get("completado") and dias_hasta(r.get("fecha","")) is not None and dias_hasta(r.get("fecha",""))<=7)
    for col,(lbl,val,dest) in zip([c1,c2,c3,c4],[
        (f"{'Líderes' if es_lider else 'Empleados'}",len(lista),True),
        ("Sin informes",sum(1 for e in lista if not e.get("informes")),False),
        ("Con seguimiento",sum(1 for e in lista if e.get("informes")),False),
        ("Reportes ≤7d",prox_urg,False),
    ]):
        with col:
            st.markdown(f'<div class="stat-box {"azul" if dest else ""}"><div class="stat-num">{val}</div><div class="stat-label">{lbl}</div></div>',unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    if not lista:
        st.info("No hay registros con esos filtros.")
    else:
        for emp in lista:
            fp=foto_path(emp["id"]); ninf=len(emp.get("informes",[]))
            nprox=[r for r in emp.get("proximos_reportes",[]) if not r.get("completado")]
            urgentes=[r for r in nprox if dias_hasta(r.get("fecha","")) is not None and dias_hasta(r.get("fecha",""))<=7]
            estado=emp.get("estado","Activo")
            tag_text="Líder" if es_lider else ("Sin informes" if not ninf else "Con seguimiento")
            tag_class="tag-lider" if es_lider else ("tag-nuevo" if not ninf else "tag-activo")
            if estado!="Activo": tag_class="tag-inactivo"; tag_text=estado
            chk=emp.get("checklist"); chk_pct=checklist_progreso(chk)[2] if chk else None

            ca,cb2,cc=st.columns([0.6,4,1.5])
            with ca:
                if fp:
                    try: st.image(str(fp),width=46)
                    except: st.markdown(f'<div class="avatar">{iniciales(emp["nombre"])}</div>',unsafe_allow_html=True)
                else: st.markdown(f'<div class="avatar">{iniciales(emp["nombre"])}</div>',unsafe_allow_html=True)
            with cb2:
                alerta=f'<span style="color:#e53935;font-size:11px;margin-left:8px">⚠️ {len(urgentes)} próx.</span>' if urgentes else ""
                chk_html=f'<span style="font-size:11px;color:#6b6b8a;margin-left:8px">📋 Checklist: {chk_pct}%</span>' if chk_pct is not None else ""
                score_html=""
                if emp.get("scores"):
                    s=emp["scores"][-1]; avg=round(sum(v for v in [s.get("comercial"),s.get("liderazgo"),s.get("operativo"),s.get("comunicacion")] if v)/max(1,sum(1 for v in [s.get("comercial"),s.get("liderazgo"),s.get("operativo"),s.get("comunicacion")] if v)),1)
                    score_html=f'<span style="font-size:11px;font-weight:700;color:{score_color(avg)};margin-left:8px">★ {avg}/10</span>'
                st.markdown(f"""
                <div style="padding:3px 0">
                  <strong style="color:{AZUL};font-size:15px">{emp['nombre']}</strong><br>
                  <span style="color:#6b6b8a;font-size:12px">{emp.get('puesto','—')} · {emp.get('centro_costo','—')}</span><br>
                  <span class="tag {tag_class}">{tag_text}</span>
                  <span style="font-size:11px;color:#6b6b8a;margin-left:8px">Ingreso: {fmt_fecha(emp.get('fecha_ingreso',''))} · {ninf} informe{'s' if ninf!=1 else ''}</span>
                  {chk_html}{score_html}{alerta}
                </div>""",unsafe_allow_html=True)
            with cc:
                if st.button("Ver ficha →",key=f"ver_{emp['id']}"): nav("ficha",emp["id"])
            st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# NUEVO / EDITAR EMPLEADO (solo RRHH)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista in ("nuevo_empleado","editar_empleado"):
    if rol!="rrhh": nav("dashboard")
    editando=st.session_state.vista=="editar_empleado"
    empleados=get_empleados(); sucursales=get_sucursales(); lideres=get_lideres()
    emp_orig=next((e for e in empleados if e["id"]==st.session_state.emp_id),{}) if editando else {}
    if st.button("← Volver"): nav("ficha" if editando else "dashboard",st.session_state.emp_id if editando else None)
    st.markdown(f"## {'Editar empleado' if editando else 'Registrar nuevo empleado'}"); st.divider()
    MOTIVOS=["Puesto nuevo","Reemplazo","Cobertura temporal","Promoción interna","Reingreso"]
    with st.form("form_emp"):
        c1,c2=st.columns(2)
        with c1:
            nombre=st.text_input("Nombre completo *",value=emp_orig.get("nombre",""))
            puesto=st.text_input("Puesto / Cargo",value=emp_orig.get("puesto",""))
            fecha_ing=st.date_input("Fecha de ingreso",value=datetime.strptime(emp_orig["fecha_ingreso"],"%Y-%m-%d").date() if emp_orig.get("fecha_ingreso") else date.today())
            remuneracion=st.text_input("Remuneración acordada",value=emp_orig.get("remuneracion",""),placeholder="Ej: $480.000")
            motivo=st.selectbox("Motivo de ingreso",MOTIVOS,index=MOTIVOS.index(emp_orig.get("motivo_ingreso","Puesto nuevo")) if emp_orig.get("motivo_ingreso") in MOTIVOS else 0)
        with c2:
            tipo=st.selectbox("Tipo",["Empleado nuevo","Líder de área","Pasante"],index=["Empleado nuevo","Líder de área","Pasante"].index(emp_orig.get("tipo","Empleado nuevo")) if emp_orig.get("tipo") in ["Empleado nuevo","Líder de área","Pasante"] else 0)
            suc_opts=["— Seleccioná —"]+sucursales
            suc_idx=suc_opts.index(emp_orig.get("centro_costo","— Seleccioná —")) if emp_orig.get("centro_costo") in suc_opts else 0
            suc_sel=st.selectbox("Centro de costos *",suc_opts,index=suc_idx)
            lid_opts=["— Sin asignar —"]+lideres
            lid_idx=lid_opts.index(emp_orig.get("lider_responsable","— Sin asignar —")) if emp_orig.get("lider_responsable") in lid_opts else 0
            lid_sel=st.selectbox("Líder responsable directo",lid_opts,index=lid_idx)
            if editando:
                estado=st.selectbox("Estado",["Activo","Inactivo","Desvinculado"],index=["Activo","Inactivo","Desvinculado"].index(emp_orig.get("estado","Activo")) if emp_orig.get("estado") in ["Activo","Inactivo","Desvinculado"] else 0)
                fecha_egreso=st.date_input("Fecha de egreso",value=datetime.strptime(emp_orig["fecha_egreso"],"%Y-%m-%d").date() if emp_orig.get("fecha_egreso") else date.today()) if estado!="Activo" else None
            else:
                estado="Activo"; fecha_egreso=None
        obs=st.text_area("Observaciones iniciales",value=emp_orig.get("observaciones",""),height=80)
        generar_checklist=st.checkbox("Generar checklist de inducción automáticamente",value=True) if not editando else False

        if st.form_submit_button("💾 Guardar",type="primary"):
            if not nombre.strip(): st.error("El nombre es obligatorio."); st.stop()
            if suc_sel=="— Seleccioná —": st.error("Seleccioná un centro de costos."); st.stop()
            datos={
                "nombre":nombre.strip(),"puesto":puesto.strip(),"tipo":tipo,
                "fecha_ingreso":str(fecha_ing),"remuneracion":remuneracion.strip(),
                "centro_costo":suc_sel,"lider_responsable":lid_sel if lid_sel!="— Sin asignar —" else None,
                "motivo_ingreso":motivo,"estado":estado,
                "fecha_egreso":str(fecha_egreso) if fecha_egreso else None,"observaciones":obs.strip(),
            }
            if editando:
                for e in empleados:
                    if e["id"]==emp_orig["id"]: e.update(datos)
                save_empleados(empleados)
                st.success("✅ Actualizado."); nav("ficha",emp_orig["id"])
            else:
                nvo_id=max((e["id"] for e in empleados),default=0)+1
                nuevo={"id":nvo_id,"informes":[],"proximos_reportes":[],"resumenes_ia":[],
                       "directivas":[],"chat":[],"notas_pin":[],"scores":[],"checklist":None,**datos}
                # Asignar checklist
                if generar_checklist:
                    plantilla=buscar_plantilla_checklist(puesto.strip())
                    if plantilla:
                        nuevo["checklist"]={"puesto_nombre":plantilla["nombre"],"secciones":plantilla["secciones"],"estado":{},"generado_con_ia":False}
                empleados.append(nuevo)
                save_empleados(empleados)
                st.success(f"✅ {nombre} registrado.")
                nav("ficha",nvo_id)

    if editando:
        st.markdown("#### Foto del empleado")
        fp=foto_path(emp_orig["id"])
        co1,co2=st.columns([1,3])
        with co1:
            if fp: st.image(str(fp),width=100)
            else: st.markdown(f'<div class="avatar" style="width:80px;height:80px;font-size:28px">{iniciales(emp_orig.get("nombre",""))}</div>',unsafe_allow_html=True)
        with co2:
            foto_up=st.file_uploader("Subir foto",type=["jpg","jpeg","png","webp"],key="foto_up")
            if foto_up:
                for ext in ["jpg","jpeg","png","webp"]:
                    old_p=ASSETS_DIR/f"foto_{emp_orig['id']}.{ext}"
                    if old_p.exists(): old_p.unlink()
                ext=foto_up.name.split(".")[-1].lower()
                img=Image.open(foto_up); img.thumbnail((300,300))
                img.save(ASSETS_DIR/f"foto_{emp_orig['id']}.{ext}")
                st.success("✅ Foto guardada."); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FICHA EMPLEADO
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista=="ficha":
    empleados=get_empleados()
    emp=next((e for e in empleados if e["id"]==st.session_state.emp_id),None)
    tipos=get_tipos_informe()
    if not emp: nav("dashboard")

    # Barra superior
    col_back,col_ed,col_pdf,col_est=st.columns([2,1,1,1])
    with col_back:
        if st.button("← Volver"): nav("lista" if emp.get("tipo")!="Líder de área" else "lista_lideres")
    with col_ed:
        if rol=="rrhh" and st.button("✏️ Editar ficha"): nav("editar_empleado",emp["id"])
    with col_pdf:
        pdf_b=exportar_ficha_pdf(emp,tipos)
        st.download_button("📄 Exportar PDF",data=pdf_b,
                           file_name=f"ficha_{emp['nombre'].replace(' ','_')}.pdf",
                           mime="application/pdf")
    with col_est:
        estado=emp.get("estado","Activo")
        color_est={"Activo":"#2e7d32","Inactivo":"#e65100","Desvinculado":"#b71c1c"}.get(estado,"#555")
        st.markdown(f'<div style="text-align:center;padding-top:8px"><span style="background:{color_est}22;color:{color_est};font-weight:700;padding:4px 14px;border-radius:10px;font-size:12px">{estado}</span></div>',unsafe_allow_html=True)

    ini=iniciales(emp["nombre"]); dias=dias_en_empresa(emp.get("fecha_ingreso",""))
    fp=foto_path(emp["id"])

    col_p,col_m=st.columns([1,2.5])
    with col_p:
        if fp:
            import base64
            with open(fp,"rb") as img_f: b64=base64.b64encode(img_f.read()).decode()
            ext=str(fp).split(".")[-1]
            foto_html=f'<img src="data:image/{ext};base64,{b64}" class="ficha-avatar-big-img"/>'
        else:
            foto_html=f'<div class="ficha-avatar-big">{ini}</div>'

        # Scores resumen
        scores=emp.get("scores",[])
        score_html_sidebar=""
        if scores:
            s=scores[-1]
            vals=[v for v in [s.get("comercial"),s.get("liderazgo"),s.get("operativo"),s.get("comunicacion")] if v]
            avg=round(sum(vals)/len(vals),1) if vals else None
            sc=score_color(avg)
            score_html_sidebar=f'<div style="background:{sc}22;border-radius:8px;padding:8px;text-align:center;margin-top:10px"><div style="font-size:22px;font-weight:800;color:{sc}">{avg}/10</div><div style="font-size:10px;color:#6b6b8a;text-transform:uppercase;letter-spacing:1px">Score promedio</div></div>'

        # Checklist mini
        chk=emp.get("checklist")
        chk_html_sidebar=""
        if chk:
            comp,total,pct=checklist_progreso(chk)
            bar_color=AMARILLO if pct<100 else "#43a047"
            chk_html_sidebar=f'''<div style="margin-top:10px">
              <div style="font-size:11px;color:#6b6b8a;margin-bottom:4px">Checklist inducción: {comp}/{total}</div>
              <div style="background:#e0e0f0;border-radius:4px;height:6px">
                <div style="background:{bar_color};width:{pct}%;height:6px;border-radius:4px"></div>
              </div>
              <div style="font-size:10px;color:#6b6b8a;margin-top:2px">{pct}% completado</div>
            </div>'''

        egreso_row=f'<tr><td style="color:#6b6b8a;padding:5px 0">Egreso</td><td style="font-weight:700;text-align:right;color:#e53935">{fmt_fecha(emp.get("fecha_egreso",""))}</td></tr>' if emp.get("fecha_egreso") else ""
        rem_row=f'<div class="rem-box"><span>Remuneración</span><span class="rem-valor">{emp.get("remuneracion","—")}</span></div>' if rol=="rrhh" else ""

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
            {egreso_row}
          </table>
          {rem_row}
          {score_html_sidebar}
          {chk_html_sidebar}
          {f'<div style="margin-top:10px;font-size:12px;color:#6b6b8a;line-height:1.5;border-top:1px solid #e0e0f0;padding-top:10px">{emp["observaciones"]}</div>' if emp.get("observaciones") else ''}
        </div>""",unsafe_allow_html=True)

    with col_m:
        # Tabs según rol
        if rol=="rrhh":
            tab_inf,tab_chk,tab_seg,tab_dir,tab_score,tab_ia=st.tabs([
                "📋 Informes","✅ Checklist","💬 Seguimiento","📢 Directivas Comercial","📊 Scores","🤖 Resumen IA"])
        else:
            tab_inf,tab_chk,tab_seg,tab_dir,tab_score,tab_ia=st.tabs([
                "📋 Informes","✅ Checklist","💬 Seguimiento","📢 Mis directivas","📊 Scores","🤖 Resumen IA"])

        # ── INFORMES ──────────────────────────────────────────────────────────
        with tab_inf:
            ct,cb2=st.columns([2,1])
            with ct: st.markdown("#### Historial de informes")
            with cb2:
                if rol=="rrhh" and st.button("＋ Cargar informe",key="btn_inf"): nav("nuevo_informe",emp["id"])
            informes=emp.get("informes",[])
            if not informes:
                st.info("Sin informes cargados aún.")
            else:
                for inf in reversed(informes):
                    ti=tipo_info(inf.get("tipo",""),tipos)
                    pp=pdf_dir_emp(emp["id"])/inf.get("pdf_filename","__")
                    tiene_pdf=bool(inf.get("pdf_filename")) and pp.exists()
                    comentarios_inf=[c for c in emp.get("chat",[]) if c.get("ref_informe")==inf.get("id")]
                    n_com=len(comentarios_inf)
                    with st.expander(f"{ti['emoji']} {inf['titulo']}  —  {fmt_fecha(inf.get('fecha',''))}  {'💬'+str(n_com) if n_com else ''}"):
                        cA,cB=st.columns([3,1])
                        with cA:
                            st.markdown(f'<span style="background:{ti["color_bg"]};color:{ti["color_text"]};padding:2px 10px;border-radius:8px;font-size:11px;font-weight:700">{ti["label"]}</span>{"  📎" if tiene_pdf else ""}',unsafe_allow_html=True)
                            contenido_show=inf.get("contenido","")
                            if inf.get("tiene_texto_pdf"):
                                partes=contenido_show.split("[NOTAS ADICIONALES]")
                                st.markdown(f"<p style='margin-top:8px;font-size:12px;line-height:1.6'>{partes[0].replace('[CONTENIDO DEL PDF]','').strip()[:600]}{'...' if len(partes[0])>600 else ''}</p>",unsafe_allow_html=True)
                                if len(partes)>1 and partes[1].strip(): st.caption(f"Notas: {partes[1].strip()}")
                            else:
                                st.markdown(f"<p style='margin-top:8px;font-size:13px;line-height:1.7'>{contenido_show}</p>",unsafe_allow_html=True)
                            # Comentarios del informe
                            if comentarios_inf:
                                st.markdown("**Comentarios:**")
                                for c in comentarios_inf:
                                    autor_color=AZUL if c.get("rol")=="rrhh" else "#e65100"
                                    st.markdown(f'<div style="background:#f8f9ff;border-left:3px solid {autor_color};padding:6px 10px;border-radius:4px;margin-bottom:4px;font-size:12px"><b style="color:{autor_color}">{c.get("autor","—")}</b> · {fmt_datetime(c.get("fecha",""))}<br>{c.get("texto","")}</div>',unsafe_allow_html=True)
                            # Agregar comentario
                            with st.form(f"com_inf_{inf.get('id')}"):
                                txt_com=st.text_input("Agregar comentario sobre este informe",placeholder="Tu comentario...",label_visibility="collapsed")
                                if st.form_submit_button("Comentar"):
                                    if txt_com.strip():
                                        emps=get_empleados()
                                        for e in emps:
                                            if e["id"]==emp["id"]:
                                                e.setdefault("chat",[]).append({"id":int(datetime.now().timestamp()*1000),"rol":rol,"autor":"RRHH" if rol=="rrhh" else "Comercial","texto":txt_com.strip(),"fecha":now_str(),"ref_informe":inf.get("id"),"tipo":"comentario_informe"})
                                                break
                                        save_empleados(emps); st.rerun()
                        with cB:
                            if tiene_pdf:
                                with open(pp,"rb") as f2: st.download_button("⬇ PDF",data=f2.read(),file_name=inf["pdf_filename"],mime="application/pdf",key=f"dl_{inf['id']}")

        # ── CHECKLIST ─────────────────────────────────────────────────────────
        with tab_chk:
            st.markdown("#### Checklist de inducción")
            chk=emp.get("checklist")

            if not chk:
                st.info("No hay checklist asignado a este empleado.")
                col_g1,col_g2=st.columns(2)
                with col_g1:
                    plantilla=buscar_plantilla_checklist(emp.get("puesto",""))
                    if plantilla and rol=="rrhh":
                        if st.button(f"📋 Usar plantilla: {plantilla['nombre']}",type="primary"):
                            emps=get_empleados()
                            for e in emps:
                                if e["id"]==emp["id"]:
                                    e["checklist"]={"puesto_nombre":plantilla["nombre"],"secciones":plantilla["secciones"],"estado":{},"generado_con_ia":False}
                                    break
                            save_empleados(emps); st.rerun()
                    elif rol=="rrhh":
                        st.caption("No hay plantilla para este puesto.")
                with col_g2:
                    if rol=="rrhh":
                        with st.expander("🤖 Generar checklist con IA (subí el descriptivo del puesto)"):
                            pdf_desc=st.file_uploader("PDF del descriptivo de puesto",type=["pdf"],key="desc_pdf")
                            if pdf_desc and st.button("Generar checklist con IA",type="primary"):
                                texto_desc=extraer_texto_pdf(pdf_desc.read())
                                if texto_desc:
                                    with st.spinner("La IA está generando el checklist..."):
                                        client,err=get_groq_client()
                                        if err: st.warning(err)
                                        else:
                                            try:
                                                resp=client.chat.completions.create(
                                                    model="llama-3.3-70b-versatile",max_tokens=2000,
                                                    messages=[
                                                        {"role":"system","content":"Sos un especialista en RRHH de Castillo Argentina. Generás checklists de inducción detallados basados en descriptivos de puesto. Respondés SOLO en JSON válido, sin texto adicional, sin markdown."},
                                                        {"role":"user","content":f"""Basándote en este descriptivo de puesto, generá un checklist de inducción completo en JSON con este formato exacto:
{{"puesto_nombre": "Nombre del puesto", "secciones": [{{"titulo": "Nombre sección", "items": ["item 1", "item 2"]}}]}}

Incluí entre 5 y 7 secciones temáticas con 4-6 ítems cada una. Secciones sugeridas: Bienvenida, Sistemas y accesos, Normas y procesos, Objetivos y gestión, Liderazgo del equipo (si aplica), Imagen institucional.

Descriptivo del puesto:
{texto_desc[:3000]}"""}
                                                    ]
                                                )
                                                raw=resp.choices[0].message.content.strip()
                                                raw=re.sub(r'^```json\s*','',raw); raw=re.sub(r'\s*```$','',raw)
                                                data=json.loads(raw)
                                                emps=get_empleados()
                                                for e in emps:
                                                    if e["id"]==emp["id"]:
                                                        e["checklist"]={"puesto_nombre":data.get("puesto_nombre",""),"secciones":data.get("secciones",[]),"estado":{},"generado_con_ia":True}
                                                        break
                                                save_empleados(emps)
                                                st.success("✅ Checklist generado con IA."); st.rerun()
                                            except Exception as ex:
                                                st.error(f"Error: {ex}")
                                else:
                                    st.warning("No se pudo leer el PDF.")
            else:
                comp,total,pct=checklist_progreso(chk)
                bar_color=AMARILLO if pct<100 else "#43a047"
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #e0e0f0;border-radius:10px;padding:14px;margin-bottom:14px">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:800;color:{AZUL}">{chk.get('puesto_nombre','Inducción')}{'  🤖' if chk.get('generado_con_ia') else ''}</span>
                    <span style="font-weight:700;color:{bar_color}">{pct}% — {comp}/{total} ítems</span>
                  </div>
                  <div style="background:#e0e0f0;border-radius:4px;height:8px">
                    <div style="background:{bar_color};width:{pct}%;height:8px;border-radius:4px;transition:width .3s"></div>
                  </div>
                </div>""",unsafe_allow_html=True)

                for sec in chk.get("secciones",[]):
                    sec_key=sec["titulo"]
                    items_ok=sum(1 for item in sec["items"] if chk.get("estado",{}).get(f"{sec_key}::{item}",{}).get("ok",False))
                    with st.expander(f"**{sec_key}** — {items_ok}/{len(sec['items'])}"):
                        for item in sec["items"]:
                            estado_item=chk.get("estado",{}).get(f"{sec_key}::{item}",{})
                            ok=estado_item.get("ok",False)
                            fecha_ok=estado_item.get("fecha","")
                            quien_ok=estado_item.get("quien","")
                            col_chk,col_info=st.columns([0.8,3.2])
                            with col_chk:
                                checked=st.checkbox("",value=ok,key=f"chk_{emp['id']}_{sec_key}_{item}",disabled=(rol!="rrhh"))
                                if checked!=ok and rol=="rrhh":
                                    emps=get_empleados()
                                    for e in emps:
                                        if e["id"]==emp["id"]:
                                            if not e.get("checklist"): break
                                            e["checklist"].setdefault("estado",{})[f"{sec_key}::{item}"]={"ok":checked,"fecha":str(date.today()) if checked else "","quien":"RRHH"}
                                            break
                                    save_empleados(emps); st.rerun()
                            with col_info:
                                if ok:
                                    st.markdown(f'<span class="chk-item-ok">✓ {item}</span><br><span style="font-size:10px;color:#aaa">{fmt_fecha(fecha_ok)} · {quien_ok}</span>',unsafe_allow_html=True)
                                else:
                                    st.markdown(f'<span class="chk-item-pend">{item}</span>',unsafe_allow_html=True)

        # ── SEGUIMIENTO (chat + notas pin) ────────────────────────────────────
        with tab_seg:
            st.markdown("#### Seguimiento conjunto RRHH ↔ Comercial")

            # Notas pineadas
            notas=emp.get("notas_pin",[])
            if notas:
                st.markdown("**📌 Cosas a tener en cuenta:**")
                for nota in notas:
                    cn1,cn2=st.columns([5,1])
                    with cn1:
                        st.markdown(f'<div class="nota-pin"><div class="nota-pin-texto">📌 {nota.get("texto","")}</div><div style="font-size:10px;color:#aaa;margin-top:4px">{nota.get("autor","")} · {fmt_fecha(nota.get("fecha",""))}</div></div>',unsafe_allow_html=True)
                    with cn2:
                        if st.button("✕",key=f"delnota_{nota.get('id')}",help="Quitar nota"):
                            emps=get_empleados()
                            for e in emps:
                                if e["id"]==emp["id"]:
                                    e["notas_pin"]=[n for n in e.get("notas_pin",[]) if n.get("id")!=nota.get("id")]
                                    break
                            save_empleados(emps); st.rerun()

            # Agregar nota pineada
            with st.expander("📌 Agregar nota importante (pineada)"):
                with st.form("form_pin"):
                    txt_pin=st.text_input("Nota importante a tener en cuenta",placeholder="Ej: Conversación salarial pendiente...")
                    if st.form_submit_button("📌 Pinear",type="primary"):
                        if txt_pin.strip():
                            emps=get_empleados()
                            for e in emps:
                                if e["id"]==emp["id"]:
                                    e.setdefault("notas_pin",[]).append({"id":int(datetime.now().timestamp()*1000),"texto":txt_pin.strip(),"autor":"RRHH" if rol=="rrhh" else "Comercial","fecha":str(date.today())})
                                    break
                            save_empleados(emps); st.success("✅ Nota pineada."); st.rerun()

            st.markdown("---")

            # Chat conversación
            chat=emp.get("chat",[])
            msgs_seg=[m for m in chat if m.get("tipo","conversacion")=="conversacion"]
            st.markdown("**💬 Conversación:**")
            if not msgs_seg:
                st.caption("Sin mensajes aún. Iniciá la conversación.")
            else:
                for msg in msgs_seg:
                    es_rrhh=msg.get("rol")=="rrhh"
                    if es_rrhh:
                        st.markdown(f'<div class="chat-msg-rrhh"><div class="chat-autor">🏢 {msg.get("autor","RRHH")}</div><div class="chat-texto">{msg.get("texto","")}</div><div class="chat-fecha">{fmt_datetime(msg.get("fecha",""))}</div></div>',unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="display:flex;justify-content:flex-end"><div class="chat-msg-comercial"><div class="chat-autor-com">💼 {msg.get("autor","Comercial")}</div><div class="chat-texto">{msg.get("texto","")}</div><div class="chat-fecha" style="text-align:right">{fmt_datetime(msg.get("fecha",""))}</div></div></div>',unsafe_allow_html=True)

            with st.form("form_chat",clear_on_submit=True):
                txt_chat=st.text_area("Escribí tu mensaje",height=80,placeholder=f"Mensaje de {'RRHH' if rol=='rrhh' else 'Comercial'}...",label_visibility="collapsed")
                if st.form_submit_button("Enviar 💬",type="primary"):
                    if txt_chat.strip():
                        emps=get_empleados()
                        for e in emps:
                            if e["id"]==emp["id"]:
                                e.setdefault("chat",[]).append({"id":int(datetime.now().timestamp()*1000),"rol":rol,"autor":"RRHH" if rol=="rrhh" else "Comercial","texto":txt_chat.strip(),"fecha":now_str(),"tipo":"conversacion"})
                                break
                        save_empleados(emps); st.rerun()

        # ── DIRECTIVAS COMERCIAL ──────────────────────────────────────────────
        with tab_dir:
            st.markdown("#### Directivas y notas de Comercial")
            directivas=emp.get("directivas",[])

            if directivas:
                for d in reversed(directivas):
                    with st.expander(f"📢 {d.get('titulo','—')}  —  {fmt_fecha(d.get('fecha',''))}"):
                        st.markdown(d.get("texto",""))
                        st.caption(f"Cargado por: {d.get('autor','Comercial')} · {fmt_fecha(d.get('fecha',''))}")
                        if d.get("importante"):
                            st.warning("⚠️ Marcada como importante")
            else:
                st.info("Sin directivas cargadas aún.")

            st.markdown("---")
            st.markdown("**Nueva directiva / nota:**")
            with st.form("form_dir",clear_on_submit=True):
                titulo_dir=st.text_input("Título *",placeholder="Ej: Objetivo Q2 — aumentar ticket promedio")
                texto_dir=st.text_area("Contenido",height=120,placeholder="Detallá la directiva, instrucción o nota para RRHH...")
                importante=st.checkbox("⚠️ Marcar como importante")
                if st.form_submit_button("📢 Publicar directiva",type="primary"):
                    if titulo_dir.strip() and texto_dir.strip():
                        emps=get_empleados()
                        for e in emps:
                            if e["id"]==emp["id"]:
                                e.setdefault("directivas",[]).append({"id":int(datetime.now().timestamp()*1000),"titulo":titulo_dir.strip(),"texto":texto_dir.strip(),"fecha":str(date.today()),"autor":"RRHH" if rol=="rrhh" else "Comercial","importante":importante})
                                break
                        save_empleados(emps); st.success("✅ Directiva publicada."); st.rerun()
                    else:
                        st.error("Completá título y contenido.")

        # ── SCORES / INDICADORES ──────────────────────────────────────────────
        with tab_score:
            st.markdown("#### Indicadores de desempeño")
            scores=emp.get("scores",[])

            if scores:
                ultimo=scores[-1]
                c1s,c2s,c3s,c4s=st.columns(4)
                for col,(lbl,key) in zip([c1s,c2s,c3s,c4s],[
                    ("Gestión Comercial","comercial"),("Liderazgo","liderazgo"),
                    ("Procesos Operativos","operativo"),("Comunicación","comunicacion")]):
                    with col:
                        v=ultimo.get(key)
                        sc=score_color(v)
                        st.markdown(f'<div class="score-card"><div class="score-num" style="color:{sc}">{v if v else "—"}</div><div style="font-size:8px">/ 10</div><div class="score-label">{lbl}</div></div>',unsafe_allow_html=True)

                if ultimo.get("observacion"):
                    st.markdown(f"<div style='margin-top:10px;font-size:13px;color:#555;font-style:italic'>📝 {ultimo['observacion']}</div>",unsafe_allow_html=True)
                st.caption(f"Última evaluación: {fmt_fecha(ultimo.get('fecha',''))}")

                if len(scores)>1:
                    with st.expander(f"📈 Historial de evaluaciones ({len(scores)})"):
                        for s in reversed(scores):
                            vals=[v for v in [s.get("comercial"),s.get("liderazgo"),s.get("operativo"),s.get("comunicacion")] if v]
                            avg=round(sum(vals)/len(vals),1) if vals else None
                            sc=score_color(avg)
                            st.markdown(f"**{fmt_fecha(s.get('fecha',''))}** · Promedio: <span style='color:{sc};font-weight:700'>{avg}/10</span> · Comercial:{s.get('comercial','—')} Liderazgo:{s.get('liderazgo','—')} Operativo:{s.get('operativo','—')} Comunicación:{s.get('comunicacion','—')}",unsafe_allow_html=True)
                            if s.get("observacion"): st.caption(f"  {s['observacion']}")
            else:
                st.info("Sin evaluaciones registradas aún.")

            st.markdown("---")
            st.markdown("**Registrar nueva evaluación:**")
            with st.form("form_score",clear_on_submit=True):
                cs1,cs2=st.columns(2)
                with cs1:
                    v_com=st.slider("Gestión Comercial",1,10,7)
                    v_lid=st.slider("Liderazgo",1,10,7)
                with cs2:
                    v_op=st.slider("Procesos Operativos",1,10,7)
                    v_com2=st.slider("Comunicación",1,10,7)
                obs_score=st.text_area("Observaciones de la evaluación",height=70,placeholder="Contexto, logros destacados, áreas de mejora...")
                if st.form_submit_button("💾 Guardar evaluación",type="primary"):
                    emps=get_empleados()
                    for e in emps:
                        if e["id"]==emp["id"]:
                            e.setdefault("scores",[]).append({"id":int(datetime.now().timestamp()*1000),"fecha":str(date.today()),"comercial":v_com,"liderazgo":v_lid,"operativo":v_op,"comunicacion":v_com2,"observacion":obs_score.strip(),"autor":"RRHH" if rol=="rrhh" else "Comercial"})
                            break
                    save_empleados(emps); st.success("✅ Evaluación guardada."); st.rerun()

        # ── RESUMEN IA ────────────────────────────────────────────────────────
        with tab_ia:
            st.markdown("#### Resumen de trayectoria generado por IA")
            informes=emp.get("informes",[])
            directivas=emp.get("directivas",[])
            scores=emp.get("scores",[])
            chat_msgs=emp.get("chat",[])
            chk=emp.get("checklist")

            LIMITE=60000
            encabezado=(f"Empleado: {emp['nombre']}\nPuesto: {emp.get('puesto','—')} | CC: {emp.get('centro_costo','—')} | Tipo: {emp.get('tipo','—')}\n"
                f"Líder responsable: {emp.get('lider_responsable') or '—'} | Motivo ingreso: {emp.get('motivo_ingreso','—')}\n"
                f"Fecha de ingreso: {fmt_fecha(emp.get('fecha_ingreso',''))} ({dias} días en la empresa)\n"
                f"Remuneración: {emp.get('remuneracion','—') if rol=='rrhh' else '[confidencial]'}\n"
                f"Observaciones: {emp.get('observaciones') or 'Ninguna'}\n\n")

            bloques=[]; chars=len(encabezado); trunc=0
            for i,inf in enumerate(informes):
                c_inf=inf.get("contenido","")
                disp=min(6000,LIMITE-chars-200)
                if disp<=0: trunc+=1; continue
                if len(c_inf)>disp: c_inf=c_inf[:disp]+"[...recortado]"; trunc+=1
                bloques.append(f"INFORME {i+1} [{tipo_info(inf.get('tipo',''),tipos)['label'].upper()}] \"{inf['titulo']}\" — {fmt_fecha(inf.get('fecha',''))}\n{c_inf}")
                chars+=len(bloques[-1])

            if scores:
                s=scores[-1]; vals=[v for v in [s.get("comercial"),s.get("liderazgo"),s.get("operativo"),s.get("comunicacion")] if v]
                avg=round(sum(vals)/len(vals),1) if vals else None
                bloques.append(f"\nÚLTIMOS SCORES: Comercial={s.get('comercial')} Liderazgo={s.get('liderazgo')} Operativo={s.get('operativo')} Comunicación={s.get('comunicacion')} Promedio={avg}/10\n{s.get('observacion','')}")

            if directivas:
                txt_dir="\n".join(f"- {d.get('titulo','')}: {d.get('texto','')[:200]}" for d in directivas[-3:])
                bloques.append(f"\nDIRECTIVAS COMERCIALES RECIENTES:\n{txt_dir}")

            if chk:
                comp,total,pct=checklist_progreso(chk)
                bloques.append(f"\nCHECKLIST DE INDUCCIÓN: {comp}/{total} ítems completados ({pct}%)")

            if chat_msgs:
                ultimos=[m for m in chat_msgs if m.get("tipo","conversacion")=="conversacion"][-5:]
                if ultimos:
                    txt_chat="\n".join(f"{m.get('autor','')}: {m.get('texto','')}" for m in ultimos)
                    bloques.append(f"\nCONVERSACIÓN RECIENTE RRHH-COMERCIAL:\n{txt_chat}")

            contexto=encabezado+f"HISTORIAL DE INFORMES ({len(informes)}):\n"+"\n\n".join(bloques)

            cx1,cx2=st.columns(2)
            with cx1: st.caption(f"📊 Contexto: **{len(contexto):,} chars**")
            with cx2:
                if trunc: st.caption(f"⚠️ {trunc} informe/s recortados")
                else: st.caption("✅ Todos los informes incluidos")

            resumenes_guardados=emp.get("resumenes_ia",[])
            if resumenes_guardados:
                ultimo=resumenes_guardados[-1]
                st.markdown(f"""
                <div class="ia-result">
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                    <div style="background:{AMARILLO};width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px">✨</div>
                    <div>
                      <div style="font-weight:800;font-size:14px">Último resumen IA</div>
                      <div style="font-size:11px;opacity:.6">Generado el {fmt_fecha(ultimo['fecha'])} · {ultimo.get('informes_analizados',0)} informes · scores incluidos: {'sí' if ultimo.get('con_scores') else 'no'}</div>
                    </div>
                  </div>
                  <div style="font-size:13px;line-height:1.8;white-space:pre-wrap">{ultimo['texto']}</div>
                </div>""",unsafe_allow_html=True)
                if len(resumenes_guardados)>1:
                    with st.expander(f"📚 Historial ({len(resumenes_guardados)} resúmenes)"):
                        for r in reversed(resumenes_guardados[:-1]):
                            st.markdown(f"**{fmt_fecha(r['fecha'])}** · {r.get('informes_analizados',0)} informes")
                            st.markdown(f"<div style='font-size:12px;white-space:pre-wrap;background:#f8f8f8;padding:10px;border-radius:8px;margin-bottom:10px'>{r['texto']}</div>",unsafe_allow_html=True)
            else:
                st.info("No hay resúmenes generados aún.")

            st.markdown("---")
            btn_lbl="🔄 Actualizar resumen" if resumenes_guardados else "✨ Generar resumen con IA"
            if st.button(btn_lbl,type="primary"):
                with st.spinner("Analizando trayectoria completa..."):
                    client,err=get_groq_client()
                    if err: st.warning(err)
                    else:
                        try:
                            resp=client.chat.completions.create(
                                model="llama-3.3-70b-versatile",max_tokens=1200,
                                messages=[
                                    {"role":"system","content":"Sos un especialista senior en RRHH de Castillo, empresa argentina de distribución con más de 100 años de historia. Analizás fichas de empleados incluyendo informes, scores de desempeño, directivas comerciales y conversaciones de seguimiento. Generás resúmenes profesionales en español rioplatense con estas 4 secciones:\n**1. Estado general**\n**2. Puntos positivos observados**\n**3. Áreas a desarrollar**\n**4. Recomendación para RRHH**"},
                                    {"role":"user","content":f"Generá un resumen de trayectoria completo considerando todos los datos disponibles:\n\n{contexto}"}
                                ]
                            )
                            resumen=resp.choices[0].message.content
                            emps=get_empleados()
                            for e in emps:
                                if e["id"]==emp["id"]:
                                    e.setdefault("resumenes_ia",[]).append({"id":int(datetime.now().timestamp()),"fecha":str(date.today()),"texto":resumen,"informes_analizados":len(informes),"chars_contexto":len(contexto),"con_scores":bool(scores),"con_directivas":bool(directivas)})
                                    break
                            save_empleados(emps); st.success("✅ Resumen guardado."); st.rerun()
                        except Exception as ex:
                            st.error(f"Error al llamar a la IA: {ex}")

# ══════════════════════════════════════════════════════════════════════════════
# NUEVO INFORME
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista=="nuevo_informe":
    if rol!="rrhh": nav("dashboard")
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
            with st.expander("📄 Vista previa texto extraído"): st.text(texto_pdf[:1500]+("..." if len(texto_pdf)>1500 else ""))
            st.success(f"✅ PDF leído: {len(texto_pdf):,} caracteres.")
        else:
            st.warning("⚠️ No se pudo extraer texto. Escribí el contenido manualmente.")
    with st.form("form_informe"):
        c1,c2=st.columns(2)
        with c1:
            tipo_sel=st.selectbox("Tipo de informe",list(tipos_opc.keys()))
            titulo=st.text_input("Título *",placeholder="Ej: Inducción semana 1")
            fecha_inf=st.date_input("Fecha",value=date.today())
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            st.caption("📎 PDF: "+("✅ con texto" if texto_pdf else ("⚠️ sin texto" if pdf_bytes_ok else "ninguno")))
        contenido_manual=st.text_area("Notas adicionales / Contenido manual",height=160,
            placeholder="El texto del PDF se usará automáticamente..." if texto_pdf else "Escribí el detalle del informe...")
        if st.form_submit_button("💾 Guardar informe",type="primary"):
            partes=[]
            if texto_pdf: partes.append(f"[CONTENIDO DEL PDF]\n{texto_pdf}")
            if contenido_manual.strip(): partes.append(f"[NOTAS ADICIONALES]\n{contenido_manual.strip()}")
            contenido_final="\n\n".join(partes)
            if not titulo.strip(): st.error("El título es obligatorio."); st.stop()
            if not contenido_final: st.error("Subí un PDF o escribí el contenido."); st.stop()
            pdf_filename=None
            if pdf_bytes_ok:
                pdf_filename=f"{emp['id']}_{int(datetime.now().timestamp())}_{pdf_file.name}"
                with open(pdf_dir_emp(emp["id"])/pdf_filename,"wb") as f2: f2.write(pdf_bytes_ok)
            emps=get_empleados()
            for e in emps:
                if e["id"]==emp["id"]:
                    e.setdefault("informes",[]).append({"id":int(datetime.now().timestamp()),"tipo":tipos_opc[tipo_sel],"titulo":titulo.strip(),"fecha":str(fecha_inf),"contenido":contenido_final,"pdf_filename":pdf_filename,"tiene_texto_pdf":bool(texto_pdf)})
                    break
            save_empleados(emps); st.success("✅ Informe guardado."); nav("ficha",emp["id"])

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN (solo RRHH)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.vista=="config":
    if rol!="rrhh": nav("dashboard")
    if st.button("← Dashboard"): nav("dashboard")
    st.markdown("## ⚙️ Configuración del sistema"); st.divider()
    tab_img,tab_tipos,tab_chk=st.tabs(["🖼️ Membrete y pie","📋 Tipos de informe","✅ Checklists"])

    with tab_img:
        st.markdown("#### Imágenes para el PDF exportado")
        c1,c2=st.columns(2)
        for col,nombre,archivo,lbl in [(c1,"Membrete","membrete.png","encabezado"),(c2,"Pie de página","pie.png","pie")]:
            with col:
                st.markdown(f"**{nombre}**")
                p=ASSETS_DIR/archivo
                if p.exists(): st.image(str(p),use_container_width=True); st.caption("✅ Cargado")
                else: st.info(f"Sin {lbl} cargado.")
                up=st.file_uploader(f"Subir {nombre}",type=["png","jpg","jpeg"],key=f"up_{archivo}")
                if up:
                    img=Image.open(up); img.save(ASSETS_DIR/archivo)
                    st.success(f"✅ {nombre} guardado."); st.rerun()
                if p.exists():
                    if st.button(f"🗑 Eliminar {nombre}",key=f"del_{archivo}"): p.unlink(); st.rerun()

    with tab_tipos:
        st.markdown("#### Tipos de informe")
        for t in get_tipos_informe():
            st.markdown(f"**{t['emoji']} {t['label']}** — `{t['codigo']}`")
        st.info("Para modificar, editá `data/tipos_informe.json` con el Bloc de notas.")

    with tab_chk:
        st.markdown("#### Plantillas de checklist por puesto")
        plantillas=get_checklists()
        for p in plantillas:
            with st.expander(f"📋 {p['nombre']}"):
                for sec in p.get("secciones",[]):
                    st.markdown(f"**{sec['titulo']}** ({len(sec['items'])} ítems)")
                    for item in sec["items"]: st.markdown(f"  · {item}")
        st.info("Para agregar plantillas, editá `data/checklists.json`.")
