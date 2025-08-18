"""
classifier.py
Módulo para clasificación de imágenes usando MobileNetV2 preentrenado en ImageNet.
Compatible con integración en visión artificial en tiempo real.
"""

import tensorflow as tf
import numpy as np
import cv2

# Configuración del modelo
MODEL_INPUT_SIZE = (224, 224)  # Tamaño estándar para MobileNetV2

# Cargar modelo al importar módulo (una sola vez)
try:
    model = tf.keras.applications.MobileNetV2(weights='imagenet')
    preprocess = tf.keras.applications.mobilenet_v2.preprocess_input
    decode = tf.keras.applications.mobilenet_v2.decode_predictions
except Exception as e:
    raise RuntimeError(f"No se pudo cargar el modelo MobileNetV2: {e}")

def classify_image(frame, top=1):
    """
    Clasifica un frame usando MobileNetV2.
    
    :param frame: Imagen en formato BGR (numpy array).
    :param top: Número de predicciones a retornar.
    :return: Lista de tuplas (etiqueta, confianza) ordenadas por confianza.
    """
    if frame is None or not hasattr(frame, "shape"):
        raise ValueError("Frame inválido o vacío para clasificación")

    resized_image = cv2.resize(frame, MODEL_INPUT_SIZE, interpolation=cv2.INTER_AREA)
    input_tensor = preprocess(np.expand_dims(resized_image.astype(np.float32), axis=0))

    try:
        predictions = model.predict(input_tensor, verbose=0)
        decoded = decode(predictions, top=top)[0]
        return [(label, float(conf)) for (_, label, conf) in decoded]
    except Exception as e:
        raise RuntimeError(f"Error en la clasificación: {e}")
