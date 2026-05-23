# Ejemplo de entrenamiento — clasificador fastText

Tutorial autocontenido para entrenar, evaluar y desplegar el **modelo ligero (capa 1)** del pipeline PiholeBlocker.

## Requisitos

- Python 3.11+
- Entorno virtual del proyecto con dependencias ML:

```bash
cd ..   # raíz del repo
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ml]"
```

## Estructura

```
examples/
├── README.md           # Este fichero
├── train.py            # Entrenamiento + cuantización
├── evaluate.py         # Métricas en test
├── predict.py          # Prueba interactiva de inferencia
├── data/
│   ├── train.txt       # Corpus de entrenamiento (formato fastText)
│   ├── val.txt         # Validación
│   └── test.txt        # Test (no usar en entrenamiento)
└── output/             # Modelos generados (gitignored)
    ├── risk_classifier.ftz   # o .bin si corpus pequeño
    └── metrics.json
```

## Formato de datos

Cada línea sigue el formato supervisado de fastText:

```
__label__<clase> <texto de entrada>
```

Clases del proyecto:

| Etiqueta | Descripción | Ejemplo de input |
|----------|-------------|------------------|
| `safe` | Dominios/contenido legítimo | `google.com`, título Wikipedia |
| `suspicious` | TLD raro, phishing probable | `free-prize-now.xyz` |
| `abusive` | Odio, insultos | URL o snippet con lenguaje abusivo |
| `grooming_risk` | Patrones de acoso/grooming | dominio o texto con señales de riesgo |

El texto de entrada debe parecerse a lo que verá el modelo en producción: **hostnames, URLs y snippets cortos** (no documentos largos).

## Pasos rápidos

### 1. Entrenar (genera corpus si no existe)

```bash
cd examples
python generate_sample_data.py   # opcional; train.py lo hace automáticamente
python train.py
```

Salida esperada:

- `output/risk_classifier.ftz` (cuantizado) o `output/risk_classifier.bin`
- `output/metrics.json` con F1 en validación

### 2. Evaluar en test

```bash
python evaluate.py
```

Muestra precisión, recall y F1 por clase sobre `data/test.txt`.

### 3. Probar inferencia manual

```bash
python predict.py "google.com"
python predict.py "free-crypto-win.xyz"
python predict.py "chat-secreto-no-le-digas-a-nadie.example"
```

### 4. Desplegar en PiholeBlocker

```bash
# Desde la raíz del repo
cp examples/output/risk_classifier.ftz models/risk_classifier.ftz
# o, si solo hay .bin:
cp examples/output/risk_classifier.bin models/risk_classifier.bin

pihole-blocker
```

Asegúrate de que `config/config.yaml` apunte a la ruta correcta:

```yaml
models:
  fasttext_path: models/risk_classifier.ftz
```

## Parámetros de entrenamiento

Editables en `train.py` o vía CLI:

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `--train` | `data/train.txt` | Corpus de entrenamiento |
| `--val` | `data/val.txt` | Validación |
| `--output` | `output/risk_classifier` | Prefijo del modelo (sin extensión) |
| `--epoch` | `50` | Épocas de entrenamiento |
| `--lr` | `0.5` | Learning rate |
| `--wordNgrams` | `2` | N-gramas de palabra |
| `--minCount` | `1` | Frecuencia mínima de token |
| `--no-quantize` | — | Guardar solo `.bin` sin cuantizar |

Ejemplo con parámetros custom:

```bash
python train.py --epoch 80 --lr 0.3 --output output/mi_modelo_v1
```

## Notas importantes

- **No entrenes en la Raspberry Pi** para modelos reales; usa tu PC. Este ejemplo es pequeño y sí puede ejecutarse en Pi solo para prueba.
- El corpus de `data/` es **sintético y educativo** (~585 muestras tras `generate_sample_data.py`). Para producción necesitas miles de muestras reales (ver [Entrenamiento de modelos](../README.md#entrenamiento-de-modelos) en el README principal).
- Si la cuantización falla por vocabulario insuficiente (< 256 n-gramas), el script guarda `.bin` automáticamente. El clasificador del proyecto acepta ambos formatos.
- Requiere `pip install -e "../.[ml]"` (NumPy < 2 por compatibilidad con fastText; ver `pyproject.toml`).
- Tras desplegar, revisa falsos positivos en el panel y exporta feedback para el siguiente ciclo de entrenamiento (Fase 7 del roadmap).

## Siguiente paso

Sustituir `data/*.txt` por un corpus preparado con `scripts/prepare_dataset.py` (Fase 2) usando EXIST, ciberacoso ES y listas de dominios públicas.
