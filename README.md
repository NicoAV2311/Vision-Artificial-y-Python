# Proyecto: Reconocimiento de Objetos con Cámara IP y Control de LEGO EV3 (EV3DEV)

Descripción
-----------
Este repositorio contiene una solución modular para detectar objetos desde una cámara IP y accionar una paletizadora construida con LEGO EV3 (ejecutando EV3DEV) mediante comandos remotos (SSH). Está orientado a desarrollo en PC (clasificación con TensorFlow/OpenCV) y despliegue en el brick EV3 (control de motores con python-ev3dev2).

Resumen de mejoras y estado actual
----------------------------------
- Añadida interfaz gráfica PyQt6 (`app_gui.py`) para monitorizar el stream de la cámara, ver predicciones y logs en tiempo real, y lanzar rutinas de paletizado por SSH.
- Integración segura con EV3:
	- Invocación por SSH para ejecutar `rutina_botella.py` en el brick (método por defecto para la ejecución desde PC).
	- Soporte para ejecución local con `ev3dev2` si la GUI corre en el brick y la inicialización del hardware es satisfactoria.
	- `send_stop_motors()` para detener motores remotamente en caso de emergencia.
- Robustez y tolerancia a fallos:
	- Reconexión automática de cámara en `camera.py`.
	- Clasificador cargado en un hilo separado (`ClassifierThread`) para evitar bloquear la UI. TensorFlow es pre-cargado de forma guardada al iniciar la app para reducir errores de carga en Windows.
	- Protecciones contra ejecución accidental: shutdown guards (`_shutting_down`, `MODULE_SHUTTING_DOWN`), y una bandera "one-shot" para que la rutina de paletizado sólo se ejecute una vez por sesión (`_trigger_launched`).
- Diagnóstico remoto:
	- Botón "Re-Check EV3" en la GUI que ejecuta checks SSH (varias rutas de python y verificación sysfs) y vuelca stdout/stderr en el panel de logs para facilitar la depuración remota.
- Documentación y limpieza:
	- Comentarios, docstrings y mensajes de log extendidos en módulos principales.
	- Correcciones de errores previos (p. ej. SyntaxError y condiciones de carrera en el init/import).
# Proyecto: Reconocimiento de Objetos con Cámara IP y Control de LEGO EV3 (EV3DEV)

Este repositorio implementa un sistema modular para detectar objetos en imágenes capturadas por una cámara IP (por ejemplo, un celular con IP Webcam) y accionar una paletizadora construida con LEGO EV3 (EV3DEV). El procesamiento principal corre en un PC (OpenCV + TensorFlow) mientras que las rutinas de motor se ejecutan en el brick EV3 (por SSH o localmente con ev3dev2).

Este README ha sido reorganizado para listar los cambios recientes, los archivos añadidos y su función, además de incluir instrucciones de uso y depuración.

Contenido rápido
----------------
- GUI PyQt6: `app_gui.py` (monitor, logs, predicciones, trigger automático)
- CLI: `main_pc.py` (flujo de captura-clasificación-SSH)
- Clasificador: `classifier.py` (EfficientNetV2B0) y `print_model_summary.py` (inspección)
- Routines (EV3): `rutina_botella.py`, `rutina_caja.py` (ajuste de rotación)
- Alternativa de control: `motor_server.py` (servidor TCP en EV3)
- Helpers y utilidades: `camera.py`, `ev3_controller.py`, `logica_paletizadora.py`, `setup_ssh_ev3.ps1` (opcional)

Estructura de archivos y descripción (detallado)
-----------------------------------------------
- `app_gui.py`
	- Interfaz gráfica en PyQt6.
	- Componentes: `VideoThread` (captura), `ClassifierThread` (inferencia en hilo), panel de logs, controles de Start/Stop y Re-Check EV3.
	- Modo de operación: si detecta EV3 local usa `ev3dev2`; si no, lanza rutinas por SSH.

- `main_pc.py`
	- Script de consola que implementa el mismo flujo que la GUI: captura frames desde `IPCamera`, invoca `classify_image`, y ejecuta `send_routine` (SSH) cuando detecta un objetivo.

- `camera.py`
	- Clase `IPCamera` basada en OpenCV (`cv2.VideoCapture`) con reconexión automática y manejo de errores.

- `classifier.py`
	- Usa `tf.keras.applications.EfficientNetV2B0(weights='imagenet', include_top=True)`.
	- Función pública: `classify_image(frame, top=1)`
		- Convierte BGR→RGB, redimensiona a 224×224, aplica `preprocess_input`, llama a `model.predict()` y usa `decode_predictions`.
	- Nota: actualmente carga el modelo al importar el módulo; se recomienda lazy-load para evitar efectos secundarios en entornos GUI/Windows.

- `print_model_summary.py`
	- Script auxiliar que carga EfficientNetV2B0 e imprime `model.summary()`, número total de parámetros y número de capas.

- `rutina_botella.py` y `rutina_caja.py`
	- Scripts diseñados para ejecutarse en el EV3 (/home/robot/). Inicializan motores y sensores con `ev3dev2` y ejecutan la rutina de paletizado.
	- `rutina_caja.py` ajusta el movimiento del vinilo a la mitad de la rotación para objetos de tipo "carton".

- `motor_server.py`
	- Servidor TCP alternativo para ejecutar rutinas en el EV3. Comandos soportados: `PALLETIZE <vel> <altura>`, `STOP`, `STATUS`.
	- Incluye control de concurrencia (lock) para evitar ejecuciones simultáneas.

- `ev3_controller.py`
	- Utilidades para inicializar y mover motores en EV3 con manejo de errores.

- `logica_paletizadora.py`
	- Script monolítico pensado para ejecutar captura + clasificación + rutina directamente en el EV3 si se desea (ejecución local).

- `setup_ssh_ev3.ps1` (opcional)
	- Script PowerShell para copiar la llave pública SSH al brick y facilitar la conexión sin contraseña.

Flujo de datos y control (resumido)
----------------------------------
1. `IPCamera` captura un frame (BGR) con OpenCV.
2. El frame se pasa a `classify_image`:
	 - BGR→RGB, resize a (224,224), `preprocess_input`, `model.predict()`, `decode_predictions`.
	 - Resultado: lista de pares `(label, confidence)` (p. ej. `[('bottle', 0.92)]`).
3. La aplicación compara las etiquetas con `OBJETIVOS_MAP` y, si `confidence >= CONF_THRESHOLD`, lanza la rutina correspondiente:
	 - En PC: `ssh robot@ev3 'python3 /home/robot/rutina_*.py <vel> <altura>'` o petición TCP a `motor_server`.
	 - En EV3 local: ejecuta la rutina que usa `ev3dev2`.

Detalles del modelo (EfficientNetV2B0)
-----------------------------------
- Tipo: EfficientNetV2B0 preentrenada en ImageNet (Keras / TensorFlow).
- Entrada: imagen RGB, tamaño 224×224×3.
- Salida: vector de 1000 clases (ImageNet). `decode_predictions` convierte índices a etiquetas humanas y probabilidades.
- Métricas locales (ejecutadas con `print_model_summary.py`): ~7.2M parámetros totales y ~273 capas (estos números provienen del modelo cargado con `include_top=True`).

Contrato y comportamiento de `classify_image`
--------------------------------------------
- Entrada: `frame` (numpy array BGR), `top` (int).
- Salida: `[(label, confidence), ...]` con `top` items.
- Errores: lanza `ValueError` si el frame es inválido, `RuntimeError` si el modelo no está cargado o falla la inferencia.

Requisitos e instalación rápida
------------------------------
En PC (Windows / Linux):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements_pc.txt
```

En EV3 (si ejecutas rutinas localmente):

```bash
ssh robot@ev3dev.local
pip3 install -r requirements_ev3.txt
```

Cómo ejecutar
--------------
- GUI (PC):

```powershell
python app_gui.py
```

- CLI (PC):

```powershell
python main_pc.py
```

- Ejecutar rutina manual (SSH):

```powershell
ssh robot@ev3dev.local "python3 /home/robot/rutina_botella.py 25 0.6"
```

- Inspeccionar modelo localmente:

```powershell
python print_model_summary.py
```

Notas de depuración y recomendaciones
------------------------------------
- TensorFlow + PyQt en Windows: si ves "Failed to load the native TensorFlow runtime":
	- Usa un entorno virtual limpio (Python 3.10/3.11 recomendados).
	- Instala Microsoft Visual C++ Redistributable (2015-2022) y la versión de TensorFlow compatible.
	- Alternativa segura: implementar lazy-load del modelo en `classifier.py` o ejecutar la inferencia en un proceso separado.

- Evitar ejecuciones duplicadas: la GUI y `main_pc.py` usan una bandera "one-shot" y/o un `sleep` tras ejecutar la rutina para evitar lanzamientos repetidos por ruido en la detección.

- Permisos remotos: si obtienes "Permission denied" al ejecutar scripts por SSH, invoca `python3 /home/robot/rutina_*.py` explícitamente o ajusta permisos con `chmod +x` en el brick.

- Si quieres evitar SSH por completo, despliega `motor_server.py` en el EV3 y envía comandos TCP desde el PC (reduce problemas de exec-bit y permisos).

Próximos pasos recomendados (opcionales)
--------------------------------------
- Implementar lazy‑load en `classifier.py` (cargar el modelo en la primera llamada a `classify_image`) para evitar efectos secundarios al arrancar la GUI en Windows.
- Convertir el modelo a TensorFlow Lite (quantizado) para acelerar inferencia en hardware limitado.
- Añadir tests unitarios para `camera.py` y mocks para `ev3_controller.py`.

Licencia
-------
MIT

Autores
-------
- Nicolas Arango Vergara
- Miguel Angel Muñoz

- **Soporte multiplataforma:** Asegurarse de que el código funcione en Windows, Linux y EV3DEV sin cambios.
- **Soporte para otras cámaras:** Permitir usar cámaras USB o la cámara del EV3.
- **Integración con servicios en la nube:** Enviar imágenes o resultados a una base de datos o dashboard online.
- **Aprendizaje personalizado:** Permitir al usuario entrenar su propio modelo con nuevas clases de objetos.


### Realizado por:
### - Nicolas Arango Vergara
### - Miguel Angel Muñoz