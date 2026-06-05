# Sistema Experto ZN 📚
Sistema inteligente de apartado de paquetes escolares para Papelería ZN.

## Descripción
Asistente virtual con inteligencia artificial que automatiza el proceso de 
apartado de útiles escolares. Permite a padres de familia registrar a sus 
hijos, seleccionar montos de anticipo y obtener un folio de comprobante.

## Tecnologías utilizadas
- Python 3.10
- Streamlit (interfaz de usuario)
- OpenRouter API (inteligencia artificial)
- SQLite (base de datos)
- LangChain

## Arquitectura de agentes
- **Agente 1:** Atención al cliente — recolecta datos conversacionalmente
- **Agente 2:** Procesador — valida datos y aplica reglas de negocio
- **Agente 3:** Supervisor — genera resúmenes y explica decisiones

## Instalación
1. Clona el repositorio
2. Crea un entorno virtual: `python -m venv venv`
3. Actívalo: `venv\Scripts\activate`
4. Instala dependencias: `pip install -r requirements.txt`
5. Crea un archivo `.env` con tu API Key de OpenRouter:
   OPENROUTER_API_KEY=tu_clave_aqui
6. Ejecuta: `streamlit run main.py`

## Reglas de inferencia implementadas
- `REGLA_DUPLICADO` — Detecta registros duplicados
- `REGLA_MONTO_INVALIDO` — Valida montos de anticipo
- `REGLA_DATOS_INCOMPLETOS` — Verifica campos obligatorios
- `REGLA_CORRECCION_GRADO` — Corrige errores de escritura en grado
- `REGLA_FRUSTRACION` — Detecta frustración del usuario
- `REGLA_FOLIO_GENERADO` — Genera folio único al completar registro
- `REGLA_PAGO_EFECTIVO` — Maneja pagos en efectivo
- `REGLA_CALCULO_SALDO` — Calcula saldo pendiente

## Panel de administrador
Accede en: `http://localhost:8501/admin`  
Contraseña: (configurada internamente)

## Autor
Juan Pablo García Sánchez  
CETI — Sistemas Expertos 2026
