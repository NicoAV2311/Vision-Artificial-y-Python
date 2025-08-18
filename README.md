# Proyecto: Reconocimiento de Objetos con Cámara IP y Control de LEGO EV3 (EV3DEV)
## Este proyecto implementa un sistema de visión artificial que utiliza la cámara de un celular como fuente de video para detectar objetos y controlar un robot LEGO EV3 con EV3DEV (basado en Debian). El procesamiento de imágenes se realiza en Python usando OpenCV y TensorFlow (o TensorFlow Lite para optimización en EV3). La arquitectura es modular para facilitar mantenimiento, pruebas y escalabilidad.

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

[Cámara IP del celular] → [OpenCV - camera.py] → [TensorFlow/TFLite - classifier.py] → [main.py - lógica] → [Motor EV3 - ev3_controller.py]

#### Requisitos
# Hardware:
- LEGO Mindstorms EV3 con EV3DEV instalado
- Motor conectado al puerto OUTPUT_B
- Celular Android con IP Webcam
- EV3 y celular en la misma red WiFi
# Software:
- Python 3.8+ en EV3DEV
- Librerías listadas en requirements_ev3.txt o requirements_pc.txt

#### Instalación
En EV3 (producción):

pip3 install --no-cache-dir -r requirements_ev3.txt
En PC (desarrollo/pruebas):

pip install -r requirements_pc.txt

#### Configuración
En main.py debes definir:

CAMERA_URL = "http://<IP_DEL_CELULAR>:8080/video"
TARGET_OBJECT = "banana"
CONFIDENCE_THRESHOLD = 0.5
FRAME_DELAY = 0.5

Configura IP Webcam en el celular, inicia el servidor y copia la URL.

#### Ejecución
En el EV3:

python3 main.py

Detener con Ctrl + C.

#### Descripción de módulos
- camera.py → Captura frames desde cámara IP.
- classifier.py → Clasifica imágenes con MobileNetV2/TFLite.
- ev3_controller.py → Controla motor EV3.
- main.py → Coordina todo el flujo.

#### Calidad y pruebas
- Cumplir con PEP8 (flake8 o ruff).
- Probar classifier.py con imágenes estáticas.
- Simular cortes de red para probar camera.py.
- Usar mock del motor en PC para validar ev3_controller.py.

#### Solución de problemas
No conecta a la cámara: Verificar URL y red.
Rendimiento bajo en EV3: Usar TensorFlow Lite.
Motor no responde: Revisar puerto y permisos.
Memoria insuficiente: Usar tflite-runtime en lugar de TensorFlow completo.

#### Licencia
MIT — Libre uso, modificación y distribución con atribución.

#### Archivos de requisitos
requirements_ev3.txt:
opencv-python>=4.5.0
numpy>=1.21.0,<1.24.0
tflite-runtime>=2.5.0
python-ev3dev2
Pillow>=8.0.0
requirements_pc.txt:
opencv-python>=4.5.0
numpy>=1.21.0
tensorflow>=2.10.0
Pillow>=8.0.0
