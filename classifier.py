"""
classifier.py
Módulo para clasificación de imágenes usando EfficientNetV2B0 preentrenado en ImageNet.
Compatible con integración en visión artificial en tiempo real.
"""


import logging
import tensorflow as tf
import numpy as np
import cv2


# Configuración del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Configuración del modelo
MODEL_INPUT_SIZE = (224, 224)  # Tamaño estándar para EfficientNetV2B0

# Cargar modelo al importar módulo (una sola vez)
model = None
preprocess = None
decode = None
try:
    model = tf.keras.applications.EfficientNetV2B0(
        weights="imagenet",
        include_top=True,
        input_shape=(224, 224, 3)  # Fuerza entrada RGB
    )
    preprocess = tf.keras.applications.efficientnet_v2.preprocess_input
    decode = tf.keras.applications.efficientnet_v2.decode_predictions
    logging.info("EfficientNetV2B0 cargado correctamente.")
except Exception as e:
    logging.error(f"No se pudo cargar el modelo EfficientNetV2B0: {e}")
    raise RuntimeError(f"No se pudo cargar el modelo EfficientNetV2B0: {e}")


def classify_image(frame, top=1):
    """
    Clasifica un frame usando EfficientNetV2B0.
    :param frame: Imagen en formato BGR (numpy array).
    :param top: Número de predicciones a retornar.
    :return: Lista de tuplas (etiqueta, confianza) ordenadas por confianza.
    """
    if model is None or preprocess is None or decode is None:
        logging.error("El modelo EfficientNetV2B0 no está cargado.")
        raise RuntimeError("El modelo EfficientNetV2B0 no está cargado.")

    if frame is None or not hasattr(frame, "shape"):
        logging.error("Frame inválido o vacío para clasificación")
        raise ValueError("Frame inválido o vacío para clasificación")

    try:
        # Convertir de BGR (OpenCV) a RGB (modelo)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized_image = cv2.resize(frame_rgb, MODEL_INPUT_SIZE, interpolation=cv2.INTER_AREA)
        input_tensor = preprocess(np.expand_dims(resized_image.astype(np.float32), axis=0))
        predictions = model.predict(input_tensor, verbose=0)
        decoded = decode(predictions, top=top)[0]
        result = [(label, float(conf)) for (_, label, conf) in decoded]
        logging.debug(f"Predicciones: {result}")
        return result
    except Exception as e:
        logging.error(f"Error en la clasificación: {e}")
        raise RuntimeError(f"Error en la clasificación: {e}")
