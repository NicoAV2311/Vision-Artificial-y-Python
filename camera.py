"""
camera.py
Módulo para capturar frames desde una cámara IP usando OpenCV.
Compatible con EV3 y sistemas de visión artificial en tiempo real.
"""

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
            raise ValueError("URL de cámara inválida")

        self.url = url
        self.reconnect_delay = reconnect_delay
        self.cap = None
        self.connect()

    def connect(self):
        """Conecta a la cámara IP."""
        self.cap = cv2.VideoCapture(self.url)
        if not self.cap.isOpened():
            raise RuntimeError(f"No se puede conectar con la cámara en {self.url}")

    def get_frame(self):
        """
        Obtiene un frame de la cámara IP.
        :return: Frame capturado o None si falla.
        """
        if self.cap is None or not self.cap.isOpened():
            print("[WARN] Cámara desconectada, reintentando...")
            time.sleep(self.reconnect_delay)
            self.connect()

        if self.cap is None:
            print("[ERROR] El recurso de la cámara no está disponible.")
            return None

        ret, frame = self.cap.read()
        if not ret:
            print("[WARN] No se pudo leer el frame")
            return None
        return frame

    def release(self):
        """Libera el recurso de la cámara."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
