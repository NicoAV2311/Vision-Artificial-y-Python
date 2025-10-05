# Proyecto: Reconocimiento de Objetos con Cámara IP y Control de LEGO EV3 (EV3DEV)

Descripción
-----------
Este repositorio contiene una solución modular para detectar objetos desde una cámara IP y accionar una paletizadora construida con LEGO EV3 (ejecutando EV3DEV) mediante comandos remotos (SSH). Está orientado a desarrollo en PC (clasificación con TensorFlow/OpenCV) y despliegue en el brick EV3 (control de motores con python-ev3dev2).

Resumen de mejoras y estado actual
----------------------------------
- Añadida interfaz gráfica PyQt6 (`app_gui.py`) para monitorizar el stream de la cámara, ver predicciones y logs en tiempo real, y lanzar rutinas de paletizado por SSH.
- Integración segura con EV3:
	- Invocación por SSH para ejecutar `mover_motores.py` en el brick (método por defecto para la ejecución desde PC).
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

Estructura de archivos
----------------------
- `app_gui.py` — Nueva GUI PyQt6 que muestra cámara, predicciones y logs; integra llamadas SSH y rutinas locales según disponibilidad.
- `main_pc.py` — Script CLI que captura frames, clasifica y ejecuta la rutina en el EV3 vía SSH (flujo clásico usado en producción/pruebas automatizadas).
- `camera.py` — Manejo robusto de captura desde cámara IP con reconexión.
- `classifier.py` — Clasificador basado en EfficientNetV2B0 (TensorFlow). Carga el modelo al import; ver sección 'TensorFlow en Windows' si da errores.
- `mover_motores.py` — Script que reside en el EV3 y ejecuta la rutina de paletizado cuando se le invoca por SSH.
- `ev3_controller.py`, `logica_paletizadora.py`, `motor_server.py` — Módulos auxiliares con variantes y utilidades (control local, servidor TCP alternativo, rutinas).

Requisitos
----------
- PC (desarrollo): Python 3.10+ recomendado, OpenCV, numpy, TensorFlow (o TensorFlow-lite si prefieres), PyQt6.
- EV3 (brick): EV3DEV Linux con `python3` y `python-ev3dev2` instalado.

Recomendado (ejemplo):
- En PC (virtualenv/venv):

```powershell
python -m venv .venv; .\\.venv\\Scripts\\Activate.ps1
pip install -r requirements_pc.txt
```

- En EV3 (ssh al brick):

```bash
pip3 install -r requirements_ev3.txt
```

Notas sobre TensorFlow en Windows
---------------------------------
En Windows existe un problema común con la carga del runtime nativo de TensorFlow cuando se importan ciertas librerías (Qt/PyQt) en un orden que provoca conflictos de DLL. Para mitigar esto el archivo `app_gui.py` intenta una "pre-import" de TensorFlow antes de importar PyQt6; esto reduce la probabilidad de error, pero si aún aparece 'Failed to load the native TensorFlow runtime' considera:
- Usar un entorno virtual limpio (venv/conda) con una versión compatible de Python (3.10/3.11).
- Instalar la versión de TensorFlow adecuada para tu CPU/GPU y el Microsoft Visual C++ Redistributable (2015-2019/2022).
- Alternativa: ejecutar la inferencia en un proceso separado (p. ej. `main_pc.py`) y comunicar los resultados a la GUI por socket o archivos temporales.

Cómo ejecutar
-------------
Flujo típico (PC + EV3 por SSH):

1. Enciende el EV3 con EV3DEV y asegúrate de que `mover_motores.py` esté en `/home/robot/` y tenga permisos de ejecución.
2. En la PC, activa tu entorno y lanza:

```powershell
python app_gui.py
```

3. En la GUI: presiona `Start` para iniciar captura y clasificación.
4. Al detectar un objetivo (según `OBJETIVOS_MAP` y `CONF_THRESHOLD`), la GUI lanzará la rutina remota por SSH. La GUI también mostrará en el panel de logs stdout/stderr del brick cuando la llamada SSH se complete.

Nota: si prefieres la versión de consola, `python main_pc.py` realiza el mismo flujo sin interfaz gráfica, y en `main_pc.py` se respeta un `time.sleep(10)` tras ejecutar la rutina para evitar disparos múltiples seguidos.

Diagnóstico EV3 (Re-Check EV3)
------------------------------
Si la GUI no detecta el EV3, usa el botón "Re-Check EV3" para ejecutar comprobaciones remotas (prueba varios interpretadores Python en el brick y verifica `/sys/class/tacho-motor`). Los resultados salen en el panel de logs y ayudan a decidir si el brick tiene `ev3dev2` instalado o si hay diferencias en el PATH remoto.

Comportamiento en entornos mixtos
---------------------------------
- Si `app_gui.py` corre en el propio EV3 y la inicialización del hardware local es satisfactoria, el programa usará la rutina local basada en `ev3dev2` para evitar la latencia de SSH.
- Si corre en PC (o la inicialización local falla), la GUI usará SSH para invocar `mover_motores.py` en el brick.

Seguridad y stop de emergencia
------------------------------
- `send_stop_motors()` envía un comando remoto para detener los motores en caso de emergencia.
- En la finalización de la rutina la GUI intenta detener los motores y marca el estado para evitar relanzamientos accidentales (flag one-shot `_trigger_launched`).

Sugerencias de mejora futuras
-----------------------------
- Añadir un botón "Reset" en la GUI para permitir re-ejecutar la rutina (actualmente es one-shot por sesión).
- Registrar automáticamente los logs del Re-Check en un archivo para análisis remoto.
- Desacoplar la inferencia en un proceso independiente para evitar problemas de carga de TensorFlow y mejorar estabilidad en Windows.
- Implementar autenticación/llaves SSH dedicadas y comprobaciones de conexión más explícitas.

Solución de problemas comunes
-----------------------------
- "Failed to load the native TensorFlow runtime": usar un entorno limpio, instalar redistribuible VC++ y verificar la compatibilidad de la versión de TensorFlow.
- "LargeMotor(outA) is not connected": significa que se intentó ejecutar la rutina local en una máquina que no tiene motores físicos; la GUI ahora detecta esto y preferirá SSH.
- "No se puede conectar con la cámara": revisa la URL de la cámara IP, que el teléfono y la PC estén en la misma red y que la app IP Webcam esté corriendo.

Contribuciones
--------------
Pull requests y issues son bienvenidos. Para cambios funcionales importantes, abre un issue primero describiendo el caso de uso y la prueba propuesta.

Licencia
--------
MIT

Autores
-------
- Nicolas Arango Vergara
- Miguel Angel Muñoz


***

README actualizado para reflejar las mejoras de la GUI, la estrategia SSH y las medidas de robustez y diagnóstico.

# Proyecto: Reconocimiento de Objetos con Cámara IP y Control de LEGO EV3 (EV3DEV)


## Descripción General
Este proyecto implementa un sistema de visión artificial que utiliza la cámara de un celular como fuente de video para detectar objetos y controlar un robot LEGO EV3 con EV3DEV (basado en Debian). El procesamiento de imágenes se realiza en Python usando OpenCV y TensorFlow (o TensorFlow Lite para optimización en EV3). La arquitectura es modular para facilitar mantenimiento, pruebas y escalabilidad.

**Mejoras recientes:**
- Todos los módulos principales (`main_pc.py`, `motor_server.py`, `camera.py`, `ev3_controller.py`, `logica_paletizadora.py`) han sido completamente documentados con docstrings y comentarios detallados.
- Se corrigieron y estandarizaron los estilos de código según PEP8.
- Se robusteció el manejo de errores y validaciones en la inicialización de hardware, cámaras y recursos críticos.
- Se mejoró la estructura y claridad de los scripts para facilitar el mantenimiento y la comprensión.
- Se reforzó la reconexión automática y la gestión de recursos en la captura de frames y control de motores.
- Se mantuvo la compatibilidad y modularidad para pruebas y despliegue en EV3 y PC.

El sistema está diseñado para ser robusto, flexible y educativo, permitiendo experimentar con conceptos de inteligencia artificial, visión por computadora y robótica de manera integrada y práctica.

### Índice
•	Estructura de carpetas
•	Arquitectura del sistema
•	Requisitos
•	Instalación
•	Configuración
•	Ejecución
•	Descripción de módulos
•	Calidad y pruebas
•	Solución de problemas
•	Licencia
•	Archivos de requisitos

#### Estructura de carpetas
.
├── main.py               # Código principal que orquesta la ejecución
├── camera.py             # Captura de frames desde cámara IP
├── classifier.py         # Clasificador de imágenes
├── ev3_controller.py     # Control del EV3 con python-ev3dev2
├── requirements_ev3.txt  # Dependencias para EV3 (ligeras)
├── requirements_pc.txt   # Dependencias para desarrollo en PC
└── README.md             # Este documento


#### Arquitectura del sistema

El sistema sigue una arquitectura modular donde cada componente tiene una responsabilidad clara y definida. El flujo de datos y control es el siguiente:

1. **Captura de imagen:** La cámara IP (por ejemplo, un celular con IP Webcam) transmite imágenes en tiempo real. El módulo `camera.py` gestiona la conexión, reconexión y obtención de frames, asegurando robustez ante fallos de red.
2. **Clasificación de imagen:** Los frames capturados se envían al clasificador (`classifier.py`), que utiliza un modelo de IA preentrenado (EfficientNetV2B0) para identificar objetos en la imagen.
3. **Lógica de decisión:** El módulo principal (`main.py`) procesa los resultados de la clasificación y decide si se debe activar el robot EV3, en función de la presencia y confianza del objeto objetivo.
4. **Control del robot:** Si el objeto objetivo es detectado con suficiente confianza, el sistema envía una orden al controlador del EV3 (`ev3_controller.py`), que acciona los motores del robot.

Todo el proceso es cíclico y en tiempo real, permitiendo una respuesta rápida ante la detección de objetos.

**Diagrama de flujo general (flujo por SSH):**

```
[Cámara IP del celular]
	│
	▼
[camera.py] --captura imagen--> [classifier.py] --detecta objeto-->
	│                                               │
	▼                                               ▼
[main_pc.py] --decide acción--> [SSH] --> [mover_motores.py (EV3)]
```


#### Requisitos
**Hardware:**
- LEGO Mindstorms EV3 con EV3DEV instalado
- Motor conectado al puerto OUTPUT_B
- Celular Android con IP Webcam (o cualquier cámara IP compatible)
- EV3 y celular en la misma red WiFi

**Software:**
- Python 3.8+ en EV3DEV
- Librerías listadas en requirements_ev3.txt o requirements_pc.txt

pip3 install --no-cache-dir -r requirements_ev3.txt
pip install -r requirements_pc.txt

#### Instalación
**En EV3 (producción):**
```bash
pip3 install --no-cache-dir -r requirements_ev3.txt
```

**En PC (desarrollo/pruebas):**
```bash
pip install -r requirements_pc.txt
```


#### Configuración
En `main.py` debes definir los siguientes parámetros:

```python
CAMERA_URL = "http://<IP_DEL_CELULAR>:8080/video"  # URL de la cámara IP
TARGET_OBJECT = "banana"                            # Objeto a detectar, se pone este como ejemplo, pero el usuario puede detectar cuantos objetos necesite, o clases de objetos
CONFIDENCE_THRESHOLD = 0.5                          # Umbral de confianza
FRAME_DELAY = 0.5                                   # Retardo entre frames (segundos)
```

Configura IP Webcam en el celular, inicia el servidor y copia la URL. Estos parámetros permiten adaptar el sistema a diferentes objetos y condiciones de red sin modificar el código fuente.


#### Ejecución

Flujo recomendado (PC + EV3 usando SSH):

1. En la PC (clasificación y control):

```bash
python3 main_pc.py
```

2. `main_pc.py` invoca la rutina en el EV3 mediante SSH, ejecutando `mover_motores.py` en el brick. Asegúrate de que el usuario `robot` exista y tenga permisos, y que el EV3 sea accesible por nombre (o coloca la IP en `EV3_HOST`).

3. Para probar la invocación SSH manualmente desde la PC:

```powershell
ssh robot@ev3dev.local "python3 /home/robot/mover_motores.py 25 0.6"
```

Detener con Ctrl + C en la PC para interrumpir `main_pc.py`.



#### Descripción de módulos
- **main_pc.py:** Script principal para la detección de objetos y control de la paletizadora desde PC. Captura imágenes de una cámara IP, clasifica objetos y envía comandos al EV3. Ahora incluye documentación completa, manejo robusto de errores y validaciones.
- **motor_server.py (opcional/no usado en el flujo actual):** Implementa un servidor TCP para recibir comandos desde la PC. Está disponible como alternativa, pero en este proyecto se decidió usar invocación por SSH a `mover_motores.py`. Si en el futuro prefieres una conexión persistente y baja latencia, `motor_server.py` puede activarse en el EV3 y adaptarse al cliente en la PC.
- **camera.py:** Captura frames desde cámara IP. Gestiona la conexión y reconexión automática, y proporciona una interfaz sencilla y robusta para obtener imágenes en tiempo real. Documentación y manejo de errores mejorados.
- **classifier.py:** Clasifica imágenes con EfficientNetV2B0/TensorFlow. Preprocesa los frames y utiliza IA para identificar objetos, devolviendo etiquetas y niveles de confianza. (No modificado por problemas de compatibilidad documentados).
- **ev3_controller.py:** Controla el motor EV3. Inicializa los motores y permite su activación/desactivación según las órdenes recibidas. Incluye validaciones, logs y documentación mejorada.
- **logica_paletizadora.py:** Script autónomo para control de la paletizadora con visión artificial y EV3. Incluye robustecimiento, documentación y manejo de errores en la lógica de paletizado.



#### Calidad y pruebas
- Todo el código principal cumple con PEP8 y buenas prácticas de documentación.
- Se han reforzado los logs y el manejo de excepciones para facilitar la depuración y el monitoreo.
- Se recomienda probar `classifier.py` con imágenes estáticas para validar la precisión del modelo.
- Simular cortes de red para probar la robustez de `camera.py`.
- Usar mocks del motor en PC para validar `ev3_controller.py` sin hardware real.
- Implementar pruebas unitarias y de integración usando `unittest` o `pytest`.



#### Solución de problemas
- **No conecta a la cámara:** Verificar URL, red y configuración de la cámara IP. Probar la conexión desde un navegador web. El sistema ahora reconecta automáticamente y reporta fallos detallados por log.
- **Rendimiento bajo en EV3:** Usar TensorFlow Lite para optimizar el uso de recursos.
- **Motor no responde:** Revisar el puerto de conexión, permisos y estado del hardware. El sistema ahora valida y reporta errores de inicialización y ejecución de motores.
- **Memoria insuficiente:** Usar `tflite-runtime` en lugar de TensorFlow completo para reducir el consumo de memoria.
- **Errores de clasificación:** Verificar la calidad de la imagen y ajustar el umbral de confianza. El sistema reporta errores de clasificación y permite ajustar el umbral fácilmente.


#### Licencia
MIT — Libre uso, modificación y distribución con atribución.


#### Archivos de requisitos
**requirements_ev3.txt:**
```
opencv-python>=4.5.0
numpy>=1.21.0,<1.24.0
tflite-runtime>=2.5.0
python-ev3dev2
Pillow>=8.0.0
```
**requirements_pc.txt:**
```
opencv-python>=4.5.0
numpy>=1.21.0
tensorflow>=2.10.0
Pillow>=8.0.0
```

---

### Funcionamiento detallado y lógica del sistema

El núcleo del sistema es un bucle que, en cada iteración, realiza los siguientes pasos:
1. Captura un frame de la cámara IP.
2. Clasifica el frame para identificar objetos presentes.
3. Evalúa si el objeto objetivo está presente y si la confianza de la predicción supera un umbral configurable.
4. Si la condición se cumple, activa el motor del EV3 durante un tiempo determinado.

Este enfoque permite adaptar el sistema a diferentes objetos y escenarios simplemente cambiando los parámetros de configuración, sin necesidad de modificar el código fuente. La modularidad facilita la extensión y el mantenimiento del sistema.

#### Ejemplo de flujo de trabajo

1. El usuario configura la cámara IP en su celular y ajusta los parámetros en `main.py`.
2. Inicia el script en el EV3 o PC.
3. El sistema comienza a capturar imágenes y a clasificarlas en tiempo real.
4. Cuando el sistema detecta una banana (ejemplo de objeto) en la imagen con alta confianza, activa el motor del robot, que puede realizar una acción como avanzar o girar.
5. El proceso se repite hasta que el usuario detiene el programa.

#### Valor y aplicaciones prácticas

Este desarrollo tiene aplicaciones en robótica educativa, automatización y prototipado rápido de sistemas de visión artificial. Permite experimentar con IA y robótica de manera accesible, usando hardware común (celular, EV3) y software libre. La modularidad facilita la extensión del sistema para tareas como seguimiento de objetos, clasificación múltiple, o integración con otros sensores y actuadores.

#### Detalles técnicos y buenas prácticas

- El uso de TensorFlow Lite en EV3 permite ejecutar modelos de IA en hardware limitado, optimizando el rendimiento y el consumo de memoria.
- El sistema de logging proporciona trazabilidad y facilita la depuración de errores.
- La separación de requisitos para PC y EV3 permite un desarrollo eficiente y portable.
- El código sigue buenas prácticas de Python y es fácilmente extensible.

#### Ideas para futuras mejoras

- **Manejo avanzado de errores:** Reconexión automática más inteligente, logs detallados y alertas si la cámara o el robot fallan repetidamente.
- **Interfaz gráfica (GUI):** Crear una interfaz simple en PC para visualizar resultados, cambiar parámetros y controlar el robot manualmente.
- **Configuración externa:** Permitir cargar parámetros desde un archivo `.ini` o `.json`.
- **Optimización con TensorFlow Lite:** Usar TFLite en PC y EV3 para reducir consumo de memoria y acelerar la inferencia.
- **Filtrado de resultados:** Aplicar un filtro temporal (ej. mayoría en 3 frames) para evitar falsos positivos.
- **Soporte para múltiples objetos:** Definir una lista de objetos objetivo y diferentes acciones para cada uno.
- **Control remoto:** Agregar un servidor web o API para controlar el robot y ver el video en tiempo real desde otro dispositivo.
- **Navegación autónoma:** Integrar sensores adicionales (ultrasónicos, color) y lógica para que el robot navegue y busque objetos por sí mismo.
- **Documentación técnica y de usuario:** Agregar ejemplos de uso, diagramas de arquitectura y guías de solución de problemas.
- **Tests automáticos:** Implementar pruebas unitarias para cada módulo y tests de integración para el flujo completo.
- **Soporte multiplataforma:** Asegurarse de que el código funcione en Windows, Linux y EV3DEV sin cambios.
- **Soporte para otras cámaras:** Permitir usar cámaras USB o la cámara del EV3.
- **Integración con servicios en la nube:** Enviar imágenes o resultados a una base de datos o dashboard online.
- **Aprendizaje personalizado:** Permitir al usuario entrenar su propio modelo con nuevas clases de objetos.


### Realizado por:
### - Nicolas Arango Vergara
### - Miguel Angel Muñoz