"""
print_model_summary.py
Imprime el resumen del modelo EfficientNetV2B0 y el número total de parámetros.
Usa el mismo modelo que `classifier.py`.

Ejecución:
    python .\print_model_summary.py

Nota: requiere TensorFlow instalado en el entorno.
"""

import sys

try:
    import tensorflow as tf
    from tensorflow.keras.applications import EfficientNetV2B0
except Exception as e:
    print("ERROR: no se pudo importar TensorFlow:", e)
    sys.exit(2)

try:
    model = EfficientNetV2B0(weights="imagenet", include_top=True, input_shape=(224,224,3))
    model.summary()
    print("Parametros totales:", model.count_params())
    try:
        print("Numero de capas (len(model.layers)):", len(model.layers))
    except Exception:
        # fallback if layers attribute not available for some reason
        print("Numero de capas: (no disponible)")
except Exception as e:
    print("ERROR al construir o cargar el modelo:", e)
    sys.exit(3)
