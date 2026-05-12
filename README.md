# 🏢 Castillo RRHH — Sistema de Seguimiento

Sistema interno de seguimiento de empleados y líderes nuevos.  
Desarrollado con **Streamlit + Python**.

---

## 📁 Estructura del proyecto

```
castillo_rrhh/
├── app.py                          ← Aplicación principal
├── requirements.txt                ← Dependencias Python
├── README.md                       ← Este archivo
├── .streamlit/
│   └── secrets.toml                ← ⚠️ CONFIGURAR API KEY AQUÍ
├── data/
│   ├── empleados.json              ← Base de datos de empleados (auto-generado)
│   └── centros_costo.json          ← Centros de costo y gerentes (EDITABLE)
└── informes_pdf/                   ← PDFs adjuntos (auto-generado)
```

---

## 🚀 Instalación

### 1. Instalá Python 3.9 o superior
Descargalo desde [python.org](https://python.org) si no lo tenés.

### 2. Instalá las dependencias
```bash
pip install -r requirements.txt
```

### 3. ⚠️ Configurá tu API key de Anthropic (OBLIGATORIO para la IA)

Abrí el archivo `.streamlit/secrets.toml` con el Bloc de notas y reemplazá la clave:

```toml
ANTHROPIC_API_KEY = "sk-ant-PEGA-TU-CLAVE-AQUI"
```

Obtenés tu clave en: https://console.anthropic.com/  
(Es gratuito registrarse y tiene créditos iniciales)

### 4. Ejecutá la app
```bash
streamlit run app.py
```

Se abre automáticamente en `http://localhost:8501`

---

## ✏️ Editar centros de costo y gerentes

Abrí `data/centros_costo.json` con el Bloc de notas o cualquier editor de texto.

**Formato de cada entrada:**
```json
{"codigo": "ALBERDI", "gerente": "GOMEZ DARIO", "tipo": "sucursal"}
```

- `codigo`: nombre de la sucursal o área
- `gerente`: gerente de la sucursal (se muestra automáticamente al seleccionar el CC)
- `tipo`: `"sucursal"` o `"area"`

El **líder responsable** del empleado es un campo separado: se elige entre los líderes
que ya estén registrados en el sistema (tipo "Líder de área").

---

## 📋 Funcionalidades

- ✅ Registrar empleados nuevos y líderes de área
- ✅ Centro de costos con gerente de sucursal automático
- ✅ Líder responsable directo (campo separado, elegís entre líderes registrados)
- ✅ Cargar informes (inducción, RRHH, comercial, desempeño) con PDF adjunto
- ✅ Ver y descargar PDFs desde la ficha del empleado
- ✅ Resumen de trayectoria generado por IA

---

## 💾 Backup

Hacé backup periódico de estas dos carpetas:
- `data/empleados.json`
- `informes_pdf/`

