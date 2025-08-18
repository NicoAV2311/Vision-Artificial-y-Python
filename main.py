"""
main.py adaptado para EV3 con ev3dev2
"""

import time
import logging
from camera import IPCamera
from classifier import classify_image
from ev3_controller import connect_to_ev3, move_motor  # ← CAMBIO

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CAMERA_URL = "http://192.168.1.28:8080/video"
TARGET_OBJECT = "banana"
CONFIDENCE_THRESHOLD = 0.5
FRAME_DELAY = 0.5  # segundos

def main():
    camera = IPCamera(CAMERA_URL)

    try:
        motor_b = connect_to_ev3()  # ← CAMBIO
        logging.info("Motor EV3 listo.")
    except Exception as e:
        logging.error(f"No se pudo inicializar el motor EV3: {e}")
        return

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                logging.warning("No se pudo capturar imagen.")
                time.sleep(FRAME_DELAY)
                continue

            results = classify_image(frame)
            label, confidence = results[0]
            logging.info(f"Detectado: {label} ({confidence:.2f})")

            if label == TARGET_OBJECT and confidence > CONFIDENCE_THRESHOLD:
                logging.info("¡Objeto detectado! Activando motor...")
                move_motor(motor_b, speed=50, duration=2)

            time.sleep(FRAME_DELAY)

    except KeyboardInterrupt:
        logging.info("Ejecución interrumpida por el usuario.")
    finally:
        camera.release()

if __name__ == "__main__":
    main()
