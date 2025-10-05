#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_pc.py
Script principal para la detección de objetos y control de la paletizadora desde PC.
Captura imágenes de una cámara IP, clasifica objetos y envía comandos al EV3 vía SSH.
"""

import time
import logging
import cv2
import subprocess
from camera import IPCamera
from classifier import classify_image

# Configuración de logging global
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Lista de posibles URLs de la cámara IP (probar en orden)
CAMERA_URLS = [
    "http://192.168.1.28:8080/video",
    "http://192.168.1.29:8080/video"
    ]

# Tiempo de espera entre frames (segundos)
FRAME_DELAY = 0.5

def get_working_camera(urls):
    """
    Intenta conectar con una lista de URLs de cámara IP y retorna la primera que funcione.
    """
    for url in urls:
        try:
            cam = IPCamera(url)
            # Intentar leer un frame con timeout manual (1 segundo)
            start = time.time()
            frame = None
            while time.time() - start < 1.0:
                frame = cam.get_frame()
                if frame is not None:
                    break
                time.sleep(0.05)
            if frame is not None:
                logging.info(f"Cámara conectada exitosamente a {url}")
                return cam
            else:
                logging.warning(f"No se pudo obtener frame de {url} en 1 segundo")
                cam.release()
        except Exception as e:
            logging.warning(f"No se pudo conectar a {url}: {e}")
    raise RuntimeError("No se pudo conectar a ninguna cámara IP.")

# Datos de conexión al EV3
EV3_USER = "robot"                 # usuario por defecto de ev3dev
EV3_HOST = "ev3dev.local"          # o IP del EV3, ej. "192.168.137.3"
EV3_SCRIPT = "/home/robot/mover_motores.py"  # ruta absoluta al script en el EV3

# Diccionario de objetos objetivo y su configuración (velocidad base, altura)
OBJETIVOS_MAP = {
    "bottle": (25, 0.6),
    "banana": (25, 0.6),
    "monitor": (30, 0.6),
    "water_bottle": (25, 0.6),
    "joystick": (20, 0.6),
    "carton": (20, 1.0)
}

# Umbral de confianza mínima para considerar una detección válida
CONF_THRESHOLD = 0.5

def send_palletize(velocidad, altura):
    """
    Ejecuta el script de motores en el EV3 vía SSH con los parámetros dados.
    """
    try:
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            f"{EV3_USER}@{EV3_HOST}",
            f"{EV3_SCRIPT} {velocidad} {altura}"
        ]
        logging.info(f"Ejecutando en EV3: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        logging.info(f"Salida EV3:\n{result.stdout}")
        if result.returncode == 0:
            return "OK"
        else:
            logging.error(f"Error en EV3: {result.stderr}")
            return None
    except Exception as e:
        logging.error(f"Error al ejecutar rutina en EV3: {e}")
        return None

def main():
    """
    Función principal: captura frames, clasifica objetos y envía comandos al EV3 si corresponde.
    """
    camera = get_working_camera(CAMERA_URLS)
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                logging.warning("No se pudo capturar imagen.")
                time.sleep(FRAME_DELAY)
                continue

            # Clasificar el frame (top=3)
            resultados = classify_image(frame, top=3)
            logging.info(f"Detecciones: {resultados}")

            # Revisar si hay un objetivo con confianza suficiente
            objetivo_detectado = False
            for etiqueta, confianza in resultados:
                etiqueta_l = etiqueta.lower()
                for objetivo, (vel, altura) in OBJETIVOS_MAP.items():
                    if objetivo in etiqueta_l and confianza >= CONF_THRESHOLD:
                        logging.info("Detectado %s (%.2f). Ejecutando rutina en EV3...", etiqueta, confianza)
                        resp = send_palletize(vel, altura)
                        if resp == "OK":
                            logging.info("Rutina ejecutada correctamente en EV3.")
                            time.sleep(10.0)  # evitar disparos múltiples seguidos
                        else:
                            logging.error("Falló la ejecución en EV3.")
                        objetivo_detectado = True
                        break
                if objetivo_detectado:
                    break

            # Mostrar la cámara en ventana
            cv2.imshow("Cámara IP", frame)

            # Salir con la tecla 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(FRAME_DELAY)
    except KeyboardInterrupt:
        logging.info("Ejecución interrumpida por el usuario.")
    finally:
        camera.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
