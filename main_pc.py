import time
import logging
import cv2
from camera import IPCamera
from classifier import classify_image

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# URL de la cámara IP (reemplaza con la de tu celular con IP Webcam)
CAMERA_URL = "http://192.168.1.29:8080/video"
FRAME_DELAY = 0.5  # segundos

def main():
    camera = IPCamera(CAMERA_URL)

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                logging.warning("No se pudo capturar imagen.")
                time.sleep(FRAME_DELAY)
                continue

            # Clasificar el frame
            results = classify_image(frame, top=3)
            logging.info(f"Detecciones: {results}")

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
