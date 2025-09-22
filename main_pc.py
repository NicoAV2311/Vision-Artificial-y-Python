

"""
main_pc.py
Script principal para la detección de objetos y control de la paletizadora desde PC.
Captura imágenes de una cámara IP, clasifica objetos y envía comandos al EV3.
"""

import time
import logging
import cv2
import socket
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
    Realiza un intento rápido (timeout manual de 1 segundo por IP).
    :param urls: Lista de URLs de cámara IP.
    :return: Objeto IPCamera conectado.
    :raises RuntimeError: Si ninguna cámara responde.
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


# Dirección IP y puerto del EV3 (modificar según configuración de red)
EV3_HOST = "192.168.137.3"
EV3_PORT = 9999


# Diccionario de objetos objetivo y su configuración (velocidad base, altura)
OBJETIVOS_MAP = {
    "bottle": (25, 0.6),
    "banana": (25, 0.6),
    "monitor": (30, 0.6),
    "carton": (30, 0.6),
    "water_bottle": (25, 0.6)
}

# Umbral de confianza mínima para considerar una detección válida
CONF_THRESHOLD = 0.5


def send_palletize(host, port, velocidad, altura):
    """
    Envía el comando PALLETIZE al EV3 y retorna la respuesta.
    Maneja errores de conexión y reporta el estado.
    :param host: IP o hostname del EV3.
    :param port: Puerto TCP del EV3.
    :param velocidad: Velocidad base para la rutina de paletizado.
    :param altura: Altura para la rutina de paletizado.
    :return: Respuesta del EV3 (str) o None si hay error.
    """
    try:
        with socket.create_connection((host, port), timeout=20) as sock:
            cmd = f"PALLETIZE {velocidad} {altura}\n"
            logging.info(f"Enviando comando: {cmd.strip()} a {host}:{port}")
            sock.sendall(cmd.encode("utf-8"))
            response = sock.recv(1024).decode("utf-8").strip()
            logging.info(f"Respuesta recibida del EV3: {response}")
            return response
    except Exception as e:
        logging.error(f"Error al enviar comando al EV3: {e}")
        return None


def main():
    """
    Función principal: captura frames, clasifica objetos y envía comandos al EV3 si corresponde.
    """
    camera = get_working_camera(CAMERA_URLS)
    last_sent = None
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
