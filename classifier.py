"""
classifier.py
Módulo para clasificación de imágenes usando EfficientNetV2B0 preentrenado en ImageNet.
Compatible con integración en visión artificial en tiempo real.
"""

import tensorflow as tf
import numpy as np
import cv2

# Configuración del modelo
MODEL_INPUT_SIZE = (224, 224)  # Tamaño estándar para EfficientNetV2B0

# Cargar modelo al importar módulo (una sola vez)
try:
    model = tf.keras.applications.EfficientNetV2B0(
        weights="imagenet",
        include_top=True,
        input_shape=(224, 224, 3)  # Fuerza entrada RGB
    )
    preprocess = tf.keras.applications.efficientnet_v2.preprocess_input
    decode = tf.keras.applications.efficientnet_v2.decode_predictions
except Exception as e:
    raise RuntimeError(f"No se pudo cargar el modelo EfficientNetV2B0: {e}")

def classify_image(frame, top=1):
    """
    Clasifica un frame usando EfficientNetV2B0.
    
    :param frame: Imagen en formato BGR (numpy array).
    :param top: Número de predicciones a retornar.
    :return: Lista de tuplas (etiqueta, confianza) ordenadas por confianza.
    """
    if frame is None or not hasattr(frame, "shape"):
        raise ValueError("Frame inválido o vacío para clasificación")

    # Convertir de BGR (OpenCV) a RGB (modelo)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    resized_image = cv2.resize(frame_rgb, MODEL_INPUT_SIZE, interpolation=cv2.INTER_AREA)
    input_tensor = preprocess(np.expand_dims(resized_image.astype(np.float32), axis=0))

    try:
        predictions = model.predict(input_tensor, verbose=0)
        decoded = decode(predictions, top=top)[0]
        return [(label, float(conf)) for (_, label, conf) in decoded]
    except Exception as e:
        raise RuntimeError(f"Error en la clasificación: {e}")
