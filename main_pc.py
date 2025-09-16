import time
import logging
import cv2
import socket
from camera import IPCamera
from classifier import classify_image

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# Lista de posibles URLs de la cámara IP
CAMERA_URLS = [
    "http://192.168.1.28:8080/video",
    "http://192.168.1.29:8080/video"
]
FRAME_DELAY = 0.5  # segundos

def get_working_camera(urls):
    for url in urls:
        try:
            cam = IPCamera(url)
            logging.info(f"Cámara conectada exitosamente a {url}")
            return cam
        except Exception as e:
            logging.warning(f"No se pudo conectar a {url}: {e}")
    raise RuntimeError("No se pudo conectar a ninguna cámara IP.")

# Dirección del EV3 (pon la IP real de tu EV3 aquí)
EV3_HOST = "192.168.0.1"
EV3_PORT = 9999

# Objetos que disparan la paletizadora y su configuración (velocidad base, altura)
OBJETIVOS_MAP = {
    "bottle": (25, 0.3),
    "banana": (25, 0.6),
    "monitor": (30, 0.6),
    "carton": (30, 0.6),
    "water_bottle": (25, 0.3)
}
CONF_THRESHOLD = 0.6  # confianza mínima



def send_palletize(host, port, velocidad, altura):
    """
    Envía el comando PALLETIZE al EV3 y retorna la respuesta.
    Maneja errores de conexión y reporta el estado.
    """
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            cmd = f"PALLETIZE {velocidad} {altura}\n"
            logging.info(f"Enviando comando: {cmd.strip()} a {host}:{port}")
            sock.sendall(cmd.encode("utf-8"))
            response = sock.recv(1024).decode("utf-8").strip()
            logging.info(f"Respuesta recibida del EV3: {response}")
            return response
    except Exception as e:
        logging.error(f"Error al enviar comando al EV3: {e}")
        return None





    camera = get_working_camera(CAMERA_URLS)
    last_sent = None
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                logging.warning("No se pudo capturar imagen.")
                time.sleep(FRAME_DELAY)
                continue

            # Clasificar el frame
            resultados = classify_image(frame, top=3)
            logging.info(f"Detecciones: {resultados}")

            # Revisar si hay un objetivo con confianza suficiente
            objetivo_detectado = False
            for etiqueta, confianza in resultados:
                etiqueta_l = etiqueta.lower()
                for objetivo, (vel, altura) in OBJETIVOS_MAP.items():
                    if objetivo in etiqueta_l and confianza >= CONF_THRESHOLD:
                        logging.info("Detectado %s (%.2f). Enviando comando a EV3...", etiqueta, confianza)
                        resp = send_palletize(EV3_HOST, EV3_PORT, vel, altura)
                        if resp == "BUSY":
                            logging.warning("EV3 ocupado, esperando para reintentar...")
                            time.sleep(1.0)
                        elif resp == "STARTED" or resp == "OK":
                            logging.info("Rutina iniciada correctamente en EV3.")
                            last_sent = (objetivo, time.time())
                            time.sleep(1.0)  # evitar disparos múltiples seguidos
                        elif resp is None:
                            logging.error("No se recibió respuesta del EV3.")
                        else:
                            logging.info(f"Respuesta inesperada del EV3: {resp}")
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
