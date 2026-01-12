# cool-routes 🧊🚶‍♂️

**cool-routes** es un proyecto en desarrollo con un enfoque de **ingeniería de datos / MLOps**, cuyo objetivo final es construir una **aplicación que permita recomendar rutas peatonales “más frescas”**, utilizando información geoespacial y variables ambientales derivadas desde **Google Earth Engine (GEE)**.

Este repositorio documenta un **avance técnico inicial**, centrado en diseñar un flujo **robusto, modular y reproducible** para la generación, exportación y sincronización de datos.

---

## 🎯 Objetivo del proyecto

Desarrollar una aplicación que permita:

* Evaluar rutas peatonales alternativas
* Priorizar recorridos con menor exposición térmica
* Integrar información ambiental (ej. temperatura superficial, cobertura vegetal)
* Servir resultados de forma reproducible y escalable

Este avance se enfoca exclusivamente en la **capa de datos y automatización**, no en la interfaz de usuario.

---

## 🧭 Estado actual (Data / MLOps)

✅ Flujo de datos funcional de extremo a extremo

* Autenticación OAuth 2.0 con Google
* Generación de imágenes y outputs geoespaciales desde GEE
* Exportación automática de resultados a Google Drive
* Sincronización y descarga local incremental

🔧 El énfasis ha estado en **arquitectura, separación de responsabilidades y control del entorno**, más que en optimización de modelos o visualización.

---

## 🧩 Arquitectura del flujo

```text
[ Google Earth Engine ]
           ↓
[ Exportación automatizada ]
           ↓
[ Google Drive ]
           ↓
[ Sincronización local ]
```

Cada bloque está desacoplado y encapsulado en módulos independientes, permitiendo:

* Reejecución parcial del pipeline
* Debugging aislado
* Evolución incremental hacia un pipeline más complejo

---

## 📁 Organización del proyecto

```text
cool_routes/
├── pipelines/                    # Orquestadores para la obtención de la información base
│   ├── gee_bootstrap/            # DAG 0
│   │   ├── export_buildings.py
│   │   ├── export_ndvi.py
|   |   ├── export_lst.py
│   │   ├── sync_drive.py         # Integración con Google Drive API
│   │   └── README.md
├── src/
│   ├── cool_routes/
│   │   ├── __init__.py
│   │   │
│   │   ├── ingest/                
│   │   │   ├── gee.py           # Lógica de extracción y procesamiento en GEE
│   │   ├── utils/                # Funciones auxiliares
|   |                
├── config/                      # Se alojan archivos yaml de configuración          
│   ├── gee/
│   │   ├── export_buildings.yaml
│   │   ├── export_ndvi.yaml
│   │   ├── export_lst.yaml
│   ├── regions/                  # Áreas de interés (ROI)
│   ├── sync_drive/  
|           
│
├── notebooks/                    # Notebooks demostrativos (en construcción)
│
├── pyproject.toml          # Gestión de dependencias (Poetry)
├── README.md

```

---

## 🔐 Autenticación y seguridad

* Autenticación basada en **OAuth 2.0**
* Acceso a Google Drive y GEE
* Las credenciales:

  * No se versionan
  * Se cargan desde archivos locales (`credentials.json`, `token.json`)

Este diseño permite:

* Separar código y secretos
* Facilitar despliegues futuros

---

## 🔄 Sincronización de datos

El mecanismo de sincronización:

1. Genera outputs desde GEE
2. Exporta resultados a una carpeta definida en Google Drive
3. Descarga localmente solo archivos nuevos o faltantes

Este enfoque:

* Evita descargas redundantes
* Permite reiniciar el pipeline sin efectos colaterales
* Es compatible con ejecuciones programadas

---

## 🧪 Testing y validación

* Validación manual del flujo completo
* Ejecuciones repetidas sin inconsistencias
* Tests automatizados aún no implementados

---

## 📌 Próximos pasos (roadmap técnico)

* Parametrización mediante archivos de configuración
* Logging estructurado
* Manejo de errores y retries
* Versionado de outputs
* Integración con modelos de routing
* Preparación para despliegue (CLI / servicio)

---

## ▶️ Cómo ejecutar el pipeline

### 1. Clonar el repositorio

```bash
git clone <repo-url>
cd cool_routes
```

### 2. Crear y activar el entorno (Poetry)

```bash
poetry install
```

Esto instalará todas las dependencias definidas en `pyproject.toml` y utilizará el entorno virtual asociado al proyecto.

### 3. Verificar autenticación

Antes de ejecutar el pipeline, asegúrate de haber configurado correctamente las credenciales OAuth para Google Drive y Google Earth Engine (ver tutorial más abajo).

Archivos esperados (no versionados):

```text
credentials.json
token.json   # se genera automáticamente tras la primera autenticación
```

---

## 🛠️ Stack tecnológico

* Python
* Google Earth Engine API
* Google Drive API
* Poetry (gestión de dependencias)

---

## 📝 Nota

Este avance prioriza **ingeniería y reproducibilidad** sobre rapidez inicial. La fricción en la configuración del entorno es intencionalmente abordada para sentar una base sólida de cara a un sistema más complejo.

✔️ *Pipeline de datos validado y sincronización operativa*
