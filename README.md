
# Proyecto: Reconocimiento de Objetos con Cámara IP y Control de LEGO EV3 (EV3DEV)

## Descripción General
Este proyecto implementa un sistema de visión artificial que utiliza la cámara de un celular como fuente de video para detectar objetos y controlar un robot LEGO EV3 con EV3DEV (basado en Debian). El procesamiento de imágenes se realiza en Python usando OpenCV y TensorFlow (o TensorFlow Lite para optimización en EV3). La arquitectura es modular para facilitar mantenimiento, pruebas y escalabilidad.

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
2. **Clasificación de imagen:** Los frames capturados se envían al clasificador (`classifier.py`), que utiliza un modelo de IA preentrenado (MobileNetV2) para identificar objetos en la imagen.
3. **Lógica de decisión:** El módulo principal (`main.py`) procesa los resultados de la clasificación y decide si se debe activar el robot EV3, en función de la presencia y confianza del objeto objetivo.
4. **Control del robot:** Si el objeto objetivo es detectado con suficiente confianza, el sistema envía una orden al controlador del EV3 (`ev3_controller.py`), que acciona los motores del robot.

Todo el proceso es cíclico y en tiempo real, permitiendo una respuesta rápida ante la detección de objetos.

**Diagrama de flujo general:**

```
[Cámara IP del celular]
	│
	▼
[camera.py] --captura imagen--> [classifier.py] --detecta objeto-->
	│                                               │
	▼                                               ▼
[main.py] --decide acción--> [ev3_controller.py (solo en EV3)]
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
**En el EV3:**
```bash
python3 main.py
```
Detener con Ctrl + C.


#### Descripción de módulos
- **camera.py:** Captura frames desde cámara IP. Gestiona la conexión y reconexión automática, y proporciona una interfaz sencilla para obtener imágenes en tiempo real.
- **classifier.py:** Clasifica imágenes con MobileNetV2/TFLite. Preprocesa los frames y utiliza IA para identificar objetos, devolviendo etiquetas y niveles de confianza.
- **ev3_controller.py:** Controla el motor EV3. Inicializa los motores y permite su activación/desactivación según las órdenes recibidas.
- **main.py:** Coordina todo el flujo. Orquesta la captura, clasificación y control del robot, implementando la lógica de decisión central del sistema.


#### Calidad y pruebas
- Cumplir con PEP8 (flake8 o ruff) para mantener la calidad del código.
- Probar `classifier.py` con imágenes estáticas para validar la precisión del modelo.
- Simular cortes de red para probar la robustez de `camera.py`.
- Usar mocks del motor en PC para validar `ev3_controller.py` sin hardware real.
- Implementar pruebas unitarias y de integración usando `unittest` o `pytest`.
- Registrar logs detallados para facilitar la depuración y el monitoreo del sistema.


#### Solución de problemas
- **No conecta a la cámara:** Verificar URL, red y configuración de la cámara IP. Probar la conexión desde un navegador web.
- **Rendimiento bajo en EV3:** Usar TensorFlow Lite para optimizar el uso de recursos.
- **Motor no responde:** Revisar el puerto de conexión, permisos y estado del hardware.
- **Memoria insuficiente:** Usar `tflite-runtime` en lugar de TensorFlow completo para reducir el consumo de memoria.
- **Errores de clasificación:** Verificar la calidad de la imagen y ajustar el umbral de confianza.


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