
"""
camera.py

Módulo para capturar frames desde una cámara IP usando OpenCV.
Proporciona la clase IPCamera para gestionar la conexión, obtención de frames y liberación de recursos de una cámara IP.
Pensado para sistemas de visión artificial en tiempo real y uso con EV3.
"""


import logging
import cv2
import time



class IPCamera:
    """
    Clase para gestionar una cámara IP usando OpenCV.
    Permite conectar, obtener frames y liberar el recurso de la cámara de forma robusta.
    """

    def __init__(self, url, reconnect_delay=2):
        """
        Inicializa la cámara IP y realiza la primera conexión.

        Args:
            url (str): URL del stream de video (ej. http://192.168.1.29:8080/video)
            reconnect_delay (int, optional): Tiempo en segundos para reintentar conexión si falla. Default=2.

        Raises:
            ValueError: Si la URL es inválida.
            RuntimeError: Si no se puede conectar a la cámara.
        """
        if not isinstance(url, str) or not url.startswith("http"):
            logging.error("URL de cámara inválida: %s", url)
            raise ValueError("URL de cámara inválida")

        self.url = url
        self.reconnect_delay = reconnect_delay
        self.cap = None
        self.connect()

    def connect(self):
        """
        Conecta a la cámara IP usando OpenCV.
        Si ya existe una conexión previa, la libera antes de reconectar.

        Raises:
            RuntimeError: Si no se puede abrir el stream de la cámara.
        """
        if self.cap is not None:
            self.release()
        self.cap = cv2.VideoCapture(self.url)
        if not self.cap.isOpened():
            logging.error(f"No se puede conectar con la cámara en {self.url}")
            raise RuntimeError(f"No se puede conectar con la cámara en {self.url}")

    def get_frame(self):
        """
        Obtiene un frame de la cámara IP.

        Returns:
            frame (np.ndarray | None): Frame capturado o None si falla.

        Maneja reconexión automática si la cámara se desconecta.
        """
        try:
            # Si la cámara está desconectada, intenta reconectar
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
        """
        Libera el recurso de la cámara y cierra la conexión.
        Es importante llamar a este método al finalizar el uso de la cámara para evitar fugas de recursos.
        """
        try:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
        except Exception as e:
            logging.error(f"Error al liberar la cámara: {e}")
