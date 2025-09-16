"""
camera.py
Módulo para capturar frames desde una cámara IP usando OpenCV.
Compatible con EV3 y sistemas de visión artificial en tiempo real.
"""


import logging
import cv2
import time


class IPCamera:
    def __init__(self, url, reconnect_delay=2):
        """
        Inicializa la cámara IP.
        :param url: URL del stream de video (ej. http://192.168.1.29:8080/video)
        :param reconnect_delay: Tiempo en segundos para reintentar conexión
        """
        if not isinstance(url, str) or not url.startswith("http"):
            logging.error("URL de cámara inválida: %s", url)
            raise ValueError("URL de cámara inválida")

        self.url = url
        self.reconnect_delay = reconnect_delay
        self.cap = None
        self.connect()

    def connect(self):
        """Conecta a la cámara IP."""
        if self.cap is not None:
            self.release()
        self.cap = cv2.VideoCapture(self.url)
        if not self.cap.isOpened():
            logging.error(f"No se puede conectar con la cámara en {self.url}")
            raise RuntimeError(f"No se puede conectar con la cámara en {self.url}")

    def get_frame(self):
        """
        Obtiene un frame de la cámara IP.
        :return: Frame capturado o None si falla.
        """
        try:
            if self.cap is None or not self.cap.isOpened():
                logging.warning("Cámara desconectada, reintentando...")
                time.sleep(self.reconnect_delay)
                self.connect()

            if self.cap is None:
                logging.error("El recurso de la cámara no está disponible.")
                return None

            ret, frame = self.cap.read()
            if not ret or frame is None:
                logging.warning("No se pudo leer el frame")
                return None
            return frame
        except Exception as e:
            logging.error(f"Error al obtener frame de la cámara: {e}")
            return None

    def release(self):
        """Libera el recurso de la cámara."""
        try:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
        except Exception as e:
            logging.error(f"Error al liberar la cámara: {e}")
