#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app_gui.py

Interfaz gráfica mínima con PyQt6 para mostrar el stream de la cámara,
el log del sistema y las predicciones del clasificador.

Requisitos: PyQt6 (pip install PyQt6)

Arquitectura:
- VideoThread: captura frames con IPCamera y emite frames (obj)
- ClassifierThread: recibe frames (cola) y ejecuta classify_image en hilo
- LogHandler -> cola: los logs se encolan y un QTimer los muestra en el QTextEdit
- SSH: invocación a send_palletize en hilo para no bloquear GUI

Nota: el modelo se carga dentro del thread de clasificación para evitar bloquear
la inicialización de la interfaz hasta que el usuario inicie la clasificación.
"""

from __future__ import annotations

import sys
import time
import logging
import traceback
import queue
import threading
from typing import Any

import cv2
import numpy as np

# Workaround: on Windows, importing Qt (PyQt6) before TensorFlow can change DLL
# loading behavior and cause "Failed to load the native TensorFlow runtime"
# (ImportError: _pywrap_tensorflow_internal). To avoid this, try to import
# TensorFlow (only the native runtime) early in the process. We do this in a
# guarded way so the GUI can still start even if TF is not available.
try:
    import tensorflow as _tf  # type: ignore
    logging.info(f"TensorFlow pre-import OK: {_tf.__version__}")
except Exception as _e:
    # Don't block GUI startup; we'll surface errors in logs when the classifier
    # thread attempts to import the model. This warning helps debugging.
    logging.debug(f"TensorFlow pre-import failed or not present: {_e}")

from PyQt6 import QtCore, QtGui, QtWidgets

from camera import IPCamera

# Import send_palletize desde main_pc para realizar la llamada por SSH
try:
    # preferimos NO importar send_palletize aquí para no sobrescribir la
    # implementación local ni forzar efectos secundarios al importar main_pc.
    from main_pc import CAMERA_URLS as _CAMERA_URLS
    CAMERA_URLS = _CAMERA_URLS
except Exception:
    # si no se puede importar main_pc (por alguna razón), definir valores por defecto
    CAMERA_URLS = ["http://192.168.1.28:8080/video", "http://192.168.1.29:8080/video"]

# Umbral de confianza para disparar acciones automáticas desde la GUI
CONF_THRESHOLD = 0.5

# Mapa local de objetivos -> (velocidad, altura). Mantener sincronizado con
# `OBJETIVOS_MAP` en main_pc.py. Se define localmente para evitar importar
# main_pc al iniciar la GUI (evita cargar TF u otros efectos secundarios).
OBJETIVOS_MAP = {
    "bottle": (25, 0.6),
    "banana": (25, 0.6),
    "monitor": (30, 0.6),
    "water_bottle": (25, 0.6),
    "joystick": (20, 0.6),
    "carton": (20, 1.0),
}

# Configuración EV3 para invocación por SSH (misma lógica que en main_pc.py)
EV3_USER = "robot"
EV3_HOST = "ev3dev.local"
EV3_SCRIPT = "/home/robot/rutina_botella.py"

import subprocess
import signal
import traceback as _traceback

# Module-level shutdown flag set by signal handlers or closeEvent
MODULE_SHUTTING_DOWN = False


def _handle_signal(signum, frame):
    global MODULE_SHUTTING_DOWN
    MODULE_SHUTTING_DOWN = True
    logging.info(f"Signal received {signum}, marking module as shutting down")
    try:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.quit()
    except Exception:
        pass


# Register signal handlers for graceful shutdown (SIGINT/SIGTERM)
try:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
except Exception:
    # some platforms (Windows GUI) may restrict signals; ignore failures
    pass


def send_palletize(velocidad, altura):
    """
    Ejecuta el script de motores en el EV3 vía SSH con los parámetros dados.
    Retorna "OK" si la ejecución remota devolvió código 0, o None en caso de error.
    """
    try:
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            f"{EV3_USER}@{EV3_HOST}",
            f"{EV3_SCRIPT} {velocidad} {altura}"
        ]
        logging.info(f"Ejecutando en EV3: {' '.join(cmd)} (thread={threading.current_thread().name})")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        # Loguear la salida del EV3 (stdout y stderr) para que aparezca en la GUI
        if result.stdout:
            logging.info(f"Salida EV3:\n{result.stdout}")
        if result.stderr:
            logging.error(f"Error EV3:\n{result.stderr}")
        if result.returncode == 0:
            logging.info("Comando SSH completado con returncode 0")
            return "OK"
        else:
            logging.error(f"Error en EV3: returncode={result.returncode}")
            return None
    except Exception as e:
        logging.error(f"Error al ejecutar rutina en EV3: {e}\n{_traceback.format_exc()}")
        return None


def send_stop_motors():
    """
    Envía un comando SSH para detener los motores en el EV3 en caso de que
    queden girando tras la rutina. Ejecuta un pequeño comando Python remoto
    que detiene los motores conectados a OUTPUT_A y OUTPUT_B.
    """
    try:
        pycmd = (
            "python3 -c \"from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B;"
            "LargeMotor(OUTPUT_A).stop(); LargeMotor(OUTPUT_B).stop()\""
        )
        cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{EV3_USER}@{EV3_HOST}", pycmd]
        logging.info(f"Enviando comando de parada de motores al EV3: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.stdout:
            logging.info(f"Salida stop EV3:\n{result.stdout}")
        if result.stderr:
            logging.error(f"Error stop EV3:\n{result.stderr}")
        if result.returncode == 0:
            logging.info("Parada remota de motores completada (returncode 0)")
            return True
        else:
            logging.error(f"Parada remota de motores falló: returncode={result.returncode}")
            return False
    except Exception as e:
        logging.error(f"Error al enviar parada de motores por SSH: {e}")
        return False


def check_ev3_via_ssh(timeout: int = 10) -> bool:
    """
    Ejecuta un pequeño script remoto vía SSH que intenta inicializar los
    componentes EV3 (motores y sensor de toque). Retorna True si la
    inicialización es correcta (imprime OK), False en caso contrario.
    """
    # Primera estrategia: intentar ejecutar un pequeño snippet Python remoto
    # que importa ev3dev2 e instancia motores/sensor. Si funciona, devolvemos OK.
    # Try several possible python executables on the EV3 (env differences)
    # Try a broader set of possible python executables on the EV3. Some
    # systems have only 'python' available, or different env setups.
    python_candidates = ["python", "python3", "/usr/bin/python3", "/usr/bin/env python", "/usr/bin/env python3"]
    py_snip = (
        'from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B;'
        'from ev3dev2.sensor import INPUT_1;'
        'from ev3dev2.sensor.lego import TouchSensor;'
        'LargeMotor(OUTPUT_A); LargeMotor(OUTPUT_B); TouchSensor(INPUT_1);'
        'print("OK")'
    )
    for py_exec in python_candidates:
        try:
            # Use single quotes around the -c payload to reduce quoting issues
            # when passed through ssh -> remote shell. The payload itself uses
            # double quotes for the print() call which is safe here.
            pycmd = f"{py_exec} -c '{py_snip}'"
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{EV3_USER}@{EV3_HOST}", pycmd]
            logging.info(f"Verificando EV3 vía SSH (python import) usando '{py_exec}'...")
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            out = (res.stdout or "").strip()
            err = (res.stderr or "").strip()
            logging.debug(f"SSH stdout (via {py_exec}): {out}")
            logging.debug(f"SSH stderr (via {py_exec}): {err}")
            logging.debug(f"SSH returncode: {res.returncode}")
            if out and "OK" in out:
                logging.info(f"Verificación EV3 vía SSH: OK (python import via {py_exec})")
                return True
        except Exception as e:
            logging.debug(f"Intento de import ev3dev2 vía SSH con {py_exec} falló: {e}")

    # Segunda estrategia: comprobar los nodos de sysfs que exponen motores
    try:
        ls_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{EV3_USER}@{EV3_HOST}", "ls /sys/class/tacho-motor"]
        logging.info("Verificando EV3 vía SSH (ls /sys/class/tacho-motor) ...")
        res2 = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=timeout)
        out2 = (res2.stdout or "").strip()
        err2 = (res2.stderr or "").strip()
        logging.debug(f"SSH ls stdout: {out2}")
        logging.debug(f"SSH ls stderr: {err2}")
        if res2.returncode == 0 and out2:
            logging.info("Verificación EV3 vía SSH: OK (sysfs motors detected)")
            return True
        logging.error(f"Verificación EV3 vía SSH fallida (sysfs). stdout: {out2} stderr: {err2}")
        return False
    except Exception as e:
        logging.error(f"Error verificando EV3 por SSH (sysfs): {e}")
        return False


def verify_ev3_connected() -> bool:
    """Verifica si los motores y el sensor de toque están disponibles.
    - Si la GUI corre en el EV3, intenta inicializar hardware local.
    - Si no, intenta una verificación vía SSH en el brick.
    """
    if LOCAL_EV3_AVAILABLE:
        try:
            _init_ev3_hardware()
            logging.info("Verificación EV3 local: hardware inicializado correctamente.")
            return True
        except Exception as e:
            logging.error(f"Verificación EV3 local falló: {e}")
            return False
    else:
        return check_ev3_via_ssh()


# Intento de soporte local para EV3 usando ev3dev2 (si la GUI corre en el brick)
LOCAL_EV3_AVAILABLE = False
try:
    from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B
    from ev3dev2.sensor import INPUT_1
    from ev3dev2.sensor.lego import TouchSensor
    import time as _time

    # inicializar componentes en primer uso
    _motor_vinilo = None
    _motor_base = None
    _sensor_presion = None

    def _init_ev3_hardware():
        global _motor_vinilo, _motor_base, _sensor_presion
        if _motor_vinilo is None:
            _motor_vinilo = LargeMotor(OUTPUT_A)
        if _motor_base is None:
            _motor_base = LargeMotor(OUTPUT_B)
        if _sensor_presion is None:
            _sensor_presion = TouchSensor(INPUT_1)
        return _motor_vinilo, _motor_base, _sensor_presion

    def rutina_paletizadora_local(velocidad_base=25, altura=0.6):
        """
        Rutina local de paletizado usando ev3dev2. Diseñada para ejecutarse
        si la GUI corre directamente en el EV3.
        """
        try:
            motor_vinilo, motor_base, sensor_presion = _init_ev3_hardware()
            logging.info(f"Iniciando rutina local de paletizado (vel={velocidad_base}, altura={altura})")

            # Bajar hasta sensor o timeout
            motor_vinilo.on(15)
            start = _time.time()
            while not sensor_presion.is_pressed:
                _time.sleep(0.1)
                if _time.time() - start > 10.0:
                    logging.error("Timeout bajando vinilo (sensor no presionado)")
                    break
            motor_vinilo.stop()

            motor_base.on(velocidad_base)
            for i in range(6):
                logging.info(f"Ciclo {i+1}/6: Subiendo vinilo")
                motor_vinilo.on_for_rotations(-15, altura)
                _time.sleep(0.5)
                motor_vinilo.stop()
                _time.sleep(0.5)
                logging.info(f"Ciclo {i+1}/6: Bajando vinilo")
                motor_vinilo.on_for_rotations(15, altura)
                _time.sleep(0.5)
                motor_vinilo.stop()

            motor_base.stop()
            logging.info("Rutina local completada")
            return "OK"
        except Exception as e:
            logging.error(f"Error en rutina local de paletizado: {e}")
            try:
                motor_vinilo.stop()
                motor_base.stop()
            except Exception:
                pass
            return None

    # Probe hardware now: try to instantiate components once to ensure the
    # process is actually running on an EV3 brick with motors connected.
    try:
        _init_ev3_hardware()
        LOCAL_EV3_AVAILABLE = True
        logging.info("ev3dev2 disponible y hardware local detectado: usando rutina local cuando corresponda.")
    except Exception as e:
        # Import succeeded but hardware not connected (likely running on PC)
        LOCAL_EV3_AVAILABLE = False
        logging.warning(f"ev3dev2 importado pero hardware local no disponible: {e}. Se usará SSH para controlar el EV3.")
except Exception:
    # ev3dev2 no disponible: la GUI está en PC; continuaremos usando SSH
    LOCAL_EV3_AVAILABLE = False


LOG_QUEUE: queue.Queue[str] = queue.Queue()


class QueueLogHandler(logging.Handler):
    """Logging handler que escribe mensajes en una cola thread-safe."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            LOG_QUEUE.put_nowait(msg)
        except Exception:
            # no raise desde handler
            pass


class VideoThread(QtCore.QThread):
    """Hilo que captura frames desde IPCamera y los emite como objetos."""

    frame_ready = QtCore.pyqtSignal(object)  # emit numpy array (BGR)

    def __init__(self, camera_urls, fps: float = 10.0, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self.camera_urls = camera_urls
        self.fps = fps
        self._stopped = threading.Event()

    def run(self) -> None:
        cam = None
        try:
            # intentar encontrar cámara funcional
            for url in self.camera_urls:
                try:
                    cam = IPCamera(url)
                    break
                except Exception:
                    continue
            if cam is None:
                logging.error("No se pudo conectar a ninguna cámara desde GUI.")
                return

            period = 1.0 / max(1.0, self.fps)
            while not self._stopped.is_set():
                frame = cam.get_frame()
                if frame is not None:
                    self.frame_ready.emit(frame)
                time.sleep(period)
        except Exception:
            logging.error("Error en VideoThread:\n" + traceback.format_exc())
        finally:
            try:
                if cam is not None:
                    cam.release()
            except Exception:
                pass

    def stop(self) -> None:
        self._stopped.set()
        self.wait(1000)


class ClassifierThread(QtCore.QThread):
    """Hilo que consume frames desde una cola y emite predicciones."""

    prediction_ready = QtCore.pyqtSignal(object)  # emit list of tuples

    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self._stopped = threading.Event()
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=2)

    def enqueue(self, frame: np.ndarray) -> None:
        # si la cola está llena, descartar frame anterior para priorizar frescura
        try:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except Exception:
                    pass
            self._queue.put_nowait(frame)
        except Exception:
            pass

    def run(self) -> None:
        # importar el clasificador aquí para que la carga del modelo ocurra en este hilo
        try:
            from classifier import classify_image
        except Exception as e:
            logging.error(f"No se pudo importar classifier: {e}")
            return

        while not self._stopped.is_set():
            try:
                frame = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                preds = classify_image(frame, top=3)
                self.prediction_ready.emit(preds)
            except Exception as e:
                logging.error(f"Error en clasificación: {e}")

    def stop(self) -> None:
        self._stopped.set()
        self.wait(1000)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paletizadora - Monitor")
        self.resize(1100, 700)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        # Layout principal
        h = QtWidgets.QHBoxLayout(central)

        # Panel izquierdo: video
        left = QtWidgets.QVBoxLayout()
        self.video_label = QtWidgets.QLabel()
        self.video_label.setFixedSize(720, 480)
        self.video_label.setStyleSheet("background-color: black;")
        left.addWidget(self.video_label)

        # Botones
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("Start")
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_ssh = QtWidgets.QPushButton("Test SSH")
        self.btn_check = QtWidgets.QPushButton("Re-Check EV3")
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_ssh)
        btn_layout.addWidget(self.btn_check)
        left.addLayout(btn_layout)

        h.addLayout(left)

        # Panel derecho: logs + predicciones
        right = QtWidgets.QVBoxLayout()

        self.pred_list = QtWidgets.QListWidget()
        self.pred_list.setFixedHeight(150)
        self.pred_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        right.addWidget(QtWidgets.QLabel("Predicciones (top 3):"))
        right.addWidget(self.pred_list)

        right.addWidget(QtWidgets.QLabel("Log:"))
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        right.addWidget(self.log_text)

        h.addLayout(right)

        # Threads
        self.video_thread = VideoThread(CAMERA_URLS, fps=10.0)
        self.class_thread = ClassifierThread()

        # Conexiones
        self.video_thread.frame_ready.connect(self.on_frame)
        self.class_thread.prediction_ready.connect(self.on_prediction)
        self.btn_start.clicked.connect(self.start_all)
        self.btn_stop.clicked.connect(self.stop_all)
        self.btn_ssh.clicked.connect(self.on_test_ssh)
        self.btn_check.clicked.connect(self.on_recheck_ev3)

        # Timer para vaciar cola de logs
        self.log_timer = QtCore.QTimer(self)
        self.log_timer.setInterval(200)
        self.log_timer.timeout.connect(self.flush_logs)
        self.log_timer.start()

        # Install logging handler local
        handler = QueueLogHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(handler)

        # Estado
        self._running = False
        # Flag que indica que la rutina principal ya se ejecutó y el sistema debe
        # permanecer detenido (cámara y detección apagadas) aunque la GUI siga abierta.
        self._finished = False
        # Flag que indica que la GUI está en proceso de apagado para evitar
        # lanzar nuevas rutinas mientras los hilos se desmontan.
        self._shutting_down = False
        # Flag para indicar que ya se lanzó la rutina una vez (one-shot)
        self._trigger_launched = False

    def start_all(self) -> None:
        if self._running:
            return
        if getattr(self, "_finished", False):
            logging.warning("El sistema está marcado como finalizado: no se puede reiniciar la detección.")
            return
        # NOTE: main_pc.py no realiza una verificación previa por SSH antes de
        # iniciar la captura; para reproducir su comportamiento (y evitar
        # diferencias entre entornos remotos que hacían fallar el check), no
        # bloqueamos el inicio aquí. Mantendremos el botón "Re-Check EV3"
        # para diagnósticos, pero la detección arrancará inmediatamente.

        logging.info("Iniciando captura y clasificación desde GUI")
        self.class_thread.start()
        self.video_thread.start()
        self._running = True

    def stop_all(self) -> None:
        if not self._running:
            return
        logging.info("Deteniendo captura y clasificación desde GUI")
        try:
            self.video_thread.stop()
        except Exception:
            pass
        try:
            self.class_thread.stop()
        except Exception:
            pass
        self._running = False

    @QtCore.pyqtSlot(object)
    def on_frame(self, frame: np.ndarray) -> None:
        # mostrar en QLabel
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QtGui.QImage(rgb.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(qimg).scaled(self.video_label.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            self.video_label.setPixmap(pix)
        except Exception as e:
            logging.error(f"Error mostrando frame: {e}")

        # enviar frame a clasificador (no bloqueante)
        try:
            self.class_thread.enqueue(frame)
        except Exception:
            pass

    @QtCore.pyqtSlot(object)
    def on_prediction(self, preds: list[tuple[str, float]]) -> None:
        # actualizar lista
        try:
            self.pred_list.clear()
            for label, conf in preds:
                item = QtWidgets.QListWidgetItem(f"{label}: {conf:.2f}")
                self.pred_list.addItem(item)
            logging.info(f"Predicciones: {preds}")
        except Exception as e:
            logging.error(f"Error actualizando predicciones: {e}")

        # Automático: si alguna predicción coincide con nuestros objetivos y
        # supera el umbral, lanzar la rutina en EV3 (en hilo) y aplicar cooldown.
        try:
            # evitar disparos demasiado frecuentes
            if not hasattr(self, "_last_trigger"):
                self._last_trigger = 0.0
                self._cooldown = 10.0  # segundos entre triggers

            now = time.time()
            if now - self._last_trigger < getattr(self, "_cooldown", 10.0):
                return

            # buscar objetivo en predicciones
            objetivo_encontrado = None
            for label, conf in preds:
                ll = label.lower()
                if conf >= CONF_THRESHOLD:
                    for objetivo, (vel, altura) in OBJETIVOS_MAP.items():
                        if objetivo in ll:
                            objetivo_encontrado = (objetivo, vel, altura)
                            break
                if objetivo_encontrado:
                    break

            if objetivo_encontrado is None:
                return

            # Lanzar la llamada SSH en hilo separado y actualizar cooldown
            def trigger_thread(obj, v, h):
                # Ensure we reference module-level flag correctly
                global MODULE_SHUTTING_DOWN
                # No ejecutar si estamos en proceso de cierre
                # NOTE: we intentionally do NOT check self._finished here because
                # the on_prediction caller will set a one-shot flag to avoid
                # launching multiple concurrent routines; trigger_thread must
                # still run once it was started.
                if MODULE_SHUTTING_DOWN or getattr(self, "_shutting_down", False):
                    logging.warning("Ignorando trigger: GUI en cierre o sistema finalizado.")
                    return
                try:
                    # preferir la función local send_palletize (implementada en
                    # este módulo). Si no está disponible, intentar importarla
                    # desde main_pc de forma perezosa.
                    try:
                        _send_palletize = send_palletize
                    except NameError:
                        from main_pc import send_palletize as _send_palletize
                except Exception as _ie:
                    logging.error(f"No se pudo importar send_palletize para ejecutar rutina: {_ie}")
                    return
                try:
                    logging.info(f"Objetivo detectado '{obj}' -> ejecutando rutina EV3 (vel={v}, altura={h})")

                    # Ejecutar la rutina; si existe rutina local, usarla
                    res = None
                    try:
                        if LOCAL_EV3_AVAILABLE:
                            res = rutina_paletizadora_local(v, h)
                        else:
                            res = _send_palletize(v, h)
                    except Exception as e:
                        logging.error(f"Error durante la ejecución de la rutina: {e}")

                    if res == "OK":
                        logging.info("Rutina EV3 completada: OK")
                    else:
                        logging.error("Rutina EV3 falló o no respondió correctamente")

                except Exception as e:
                    logging.error(f"Error ejecutando rutina EV3: {e}")
                finally:
                    # Asegurarse de que los motores queden detenidos (medida de seguridad)
                    try:
                        if not LOCAL_EV3_AVAILABLE:
                            send_stop_motors()
                        else:
                            # también intentar un stop remoto por si queda algo
                            send_stop_motors()
                    except Exception:
                        pass

                    # Detener la captura y la clasificación para evitar nuevos triggers
                    try:
                        # marcar estado terminado para evitar restarts accidentales
                        self._finished = True
                        # desactivar botones
                        try:
                            self.btn_start.setEnabled(False)
                        except Exception:
                            pass
                        self.stop_all()
                        logging.info("Detenido el sistema de detección tras completar la rutina.")
                    except Exception as e:
                        logging.error(f"Error deteniendo hilos tras rutina: {e}")
                    # also set module-level flag to avoid any remaining triggers
                    MODULE_SHUTTING_DOWN = True

            # One-shot: mark that we've launched the routine so subsequent
            # predictions won't start it again.
            if getattr(self, "_trigger_launched", False):
                logging.info("Rutina ya lanzada previamente: ignorando nuevo trigger.")
                return
            self._trigger_launched = True
            threading.Thread(target=trigger_thread, args=objetivo_encontrado, daemon=True).start()
            self._last_trigger = now
        except Exception as e:
            logging.error(f"Error en lógica automática de disparo: {e}")

    def flush_logs(self) -> None:
        appended = False
        while True:
            try:
                msg = LOG_QUEUE.get_nowait()
            except queue.Empty:
                break
            self.log_text.append(msg)
            appended = True
        if appended:
            # auto-scroll (guard verticalScrollBar in case static analysis
            # or runtime returns None)
            vsb = self.log_text.verticalScrollBar()
            if vsb is not None:
                try:
                    vsb.setValue(vsb.maximum())
                except Exception:
                    pass

    def on_test_ssh(self) -> None:
        # lanzar send_palletize en hilo separado y mostrar resultado
        def runner():
            try:
                # Import lazily so GUI can start even if main_pc import fails at
                # module import time (avoid static None call issues and make
                # import errors visible here).
                try:
                    _send_palletize = send_palletize
                except NameError:
                    from main_pc import send_palletize as _send_palletize

                logging.info("Prueba SSH: ejecutando rutina en EV3...")
                res = _send_palletize(25, 0.6)
                if res == "OK":
                    logging.info("Prueba SSH completada: OK")
                else:
                    logging.error("Prueba SSH: fallo o sin respuesta")
            except Exception as e:
                logging.error(f"Error al ejecutar prueba SSH: {e}")

        threading.Thread(target=runner, daemon=True).start()

    def on_recheck_ev3(self) -> None:
        """Run the EV3 verification checks and log stdout/stderr for debugging."""
        def runner():
            try:
                logging.info("Re-Check EV3: iniciando comprobaciones detalladas via SSH...")
                # Run the python import attempts and the sysfs check and log outputs
                python_candidates = ["python", "python3", "/usr/bin/python3", "/usr/bin/env python", "/usr/bin/env python3"]
                py_snip = (
                    'from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B;'
                    'from ev3dev2.sensor import INPUT_1;'
                    'from ev3dev2.sensor.lego import TouchSensor;'
                    'LargeMotor(OUTPUT_A); LargeMotor(OUTPUT_B); TouchSensor(INPUT_1);'
                    'print("OK")'
                )
                for py_exec in python_candidates:
                    try:
                        pycmd = f"{py_exec} -c '{py_snip}'"
                        cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{EV3_USER}@{EV3_HOST}", pycmd]
                        logging.info(f"Ejecutando: {' '.join(cmd)}")
                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                        logging.info(f"[{py_exec}] stdout:\n{res.stdout}")
                        if res.stderr:
                            logging.error(f"[{py_exec}] stderr:\n{res.stderr}")
                        logging.info(f"[{py_exec}] returncode: {res.returncode}")
                    except Exception as e:
                        logging.error(f"Error ejecutando {py_exec} via SSH: {e}")

                # sysfs check
                ls_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{EV3_USER}@{EV3_HOST}", "ls -la /sys/class/tacho-motor"]
                logging.info(f"Ejecutando: {' '.join(ls_cmd)}")
                res2 = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=15)
                logging.info(f"[sysfs] stdout:\n{res2.stdout}")
                if res2.stderr:
                    logging.error(f"[sysfs] stderr:\n{res2.stderr}")
                logging.info(f"[sysfs] returncode: {res2.returncode}")

                logging.info("Re-Check EV3: comprobaciones finalizadas. Copia los logs si necesitas soporte adicional.")
            except Exception as e:
                logging.error(f"Error en Re-Check EV3: {e}")

        threading.Thread(target=runner, daemon=True).start()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        # Marcar que estamos cerrando para evitar triggers concurrentes
        try:
            self._shutting_down = True
        except Exception:
            pass
        try:
            global MODULE_SHUTTING_DOWN
            MODULE_SHUTTING_DOWN = True
        except Exception:
            pass
        # Vaciar cola del clasificador para evitar que procese frames residuales
        try:
            q = getattr(self.class_thread, "_queue", None)
            if q is not None:
                try:
                    while True:
                        q.get_nowait()
                except Exception:
                    pass
        except Exception:
            pass

        self.stop_all()
        super().closeEvent(event)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
