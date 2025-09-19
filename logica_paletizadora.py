#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logica_paletizadora.py
Script para control de paletizadora automática usando visión artificial y EV3.
Detecta objetos en tiempo real y ejecuta rutina de paletizado si se detecta un objetivo.

Autores: [Nicolas Arango Vergara, Miguel Angel Muñoz]
Fecha: 2025-09-14
"""


import logging
import time
import cv2
from camera import IPCamera
from classifier import classify_image
from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B
from ev3dev2.sensor import INPUT_1
from ev3dev2.sensor.lego import TouchSensor


# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Inicialización de motores y sensor de presión
try:
    motor_vinilo = LargeMotor(OUTPUT_A)
    motor_base = LargeMotor(OUTPUT_B)
    sensor_presion = TouchSensor(INPUT_1)
    logging.info("Motores y sensor inicializados correctamente.")
except Exception as e:
    logging.error(f"Error inicializando hardware EV3: {e}")
    raise


# Configuración de la cámara IP (varias posibles IPs)
CAMERA_URLS = [
    "http://192.168.1.29:8080/video",
    "http://192.168.1.28:8080/video"
]
FRAME_DELAY = 0.5  # segundos entre frames

def get_working_camera(urls):
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

# Objetos que disparan la paletizadora
OBJETIVOS = {"bottle", "banana"}


def rutina_paletizadora(velocidad_base=25, altura=0.6):
    """
    Ejecuta la rutina de paletizado.
    """
    logging.info(f"Iniciando rutina de paletizado (velocidad={velocidad_base}, altura={altura})")
    try:
        motor_vinilo.on(15)
        start = time.time()
        while not sensor_presion.is_pressed:
            time.sleep(0.1)
            if time.time() - start > 10.0:
                logging.error("Timeout bajando vinilo (sensor no presionado)")
                break
        motor_vinilo.stop()

        motor_base.on(velocidad_base)

        for i in range(6):
            logging.info(f"Ciclo {i+1}/6: Subiendo vinilo")
            motor_vinilo.on_for_rotations(-15, altura)
            time.sleep(0.5)
            motor_vinilo.stop()
            time.sleep(0.5)
            logging.info(f"Ciclo {i+1}/6: Bajando vinilo")
            motor_vinilo.on_for_rotations(15, altura)
            time.sleep(0.5)
            motor_vinilo.stop()

        motor_base.stop()
        logging.info("Rutina completada")
    except Exception as e:
        logging.error(f"Error en rutina de paletizado: {e}")
        try:
            motor_vinilo.stop()
            motor_base.stop()
        except Exception:
            pass

def main():

    camera = None
    while camera is None:
        try:
            camera = get_working_camera(CAMERA_URLS)
        except Exception as e:
            logging.error(f"No se pudo inicializar la cámara: {e}. Reintentando en 2 segundos...")
            time.sleep(2)

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                logging.warning("No se pudo capturar imagen. Reintentando cámara...")
                camera.release()
                camera = None
                # Reintentar obtener cámara
                while camera is None:
                    try:
                        camera = get_working_camera(CAMERA_URLS)
                    except Exception as e:
                        logging.error(f"No se pudo reconectar la cámara: {e}. Reintentando en 2 segundos...")
                        time.sleep(2)
                continue

            resultados = classify_image(frame, top=3)
            logging.info(f"Detecciones: {resultados}")

            for etiqueta, confianza in resultados:
                if etiqueta in OBJETIVOS and confianza > 0.6:
                    logging.info(f"¡Objeto detectado! Ejecutando rutina de paletizado para {etiqueta} (confianza={confianza:.2f})")
                    rutina_paletizadora()
                    break

            cv2.imshow("Cámara IP", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(FRAME_DELAY)

    except KeyboardInterrupt:
        logging.info("Interrumpido por el usuario.")
    except Exception as e:
        logging.error(f"Error en el bucle principal: {e}")
    finally:
        try:
            if camera:
                camera.release()
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            motor_vinilo.stop()
            motor_base.stop()
        except Exception:
            pass