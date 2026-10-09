# asset-schedule-py

Calendarios mensuales de depreciación lineal con aritmética entera, una API tipada y una CLI con salida JSON. Sin dependencias de ejecución.

[English documentation](docs/README.en.md)

## Alcance

Esta biblioteca resuelve un cálculo genérico: distribuir el importe depreciable de un activo entre un número explícito de meses completos. El costo, el valor residual y cada resultado usan la misma unidad monetaria menor, elegida por quien llama a la API. Por ejemplo, `100_000` puede representar 1.000,00 en una moneda con dos decimales; la biblioteca no fija moneda ni cantidad de decimales.

No determina vidas útiles, tasas fiscales ni criterios de reconocimiento. No calcula meses parciales, deterioro, revaluaciones, cambios de estimación, bajas o asientos contables. Su resultado no acredita cumplimiento contable, tributario ni legal.

## Instalación local

Requiere Python 3.12 o posterior. La versión incluida es `0.1.0`; estos comandos instalan el código de este repositorio, no una publicación en PyPI.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
```

En Windows, activa el entorno con `.venv\Scripts\Activate.ps1`. Si usas uv:

```bash
uv venv
uv pip install .
```

La construcción del paquete utiliza setuptools. Esto no añade dependencias de ejecución.

## API

```python
from asset_schedule import straight_line_schedule

rows = straight_line_schedule(
    cost_minor=100_000,
    residual_minor=10_000,
    periods=3,
    start_year=2026,
    start_month=11,
)

assert [row.depreciation_minor for row in rows] == [30_000, 30_000, 30_000]
assert rows[-1].accumulated_depreciation_minor == 90_000
assert rows[-1].carrying_value_minor == 10_000
assert (rows[-1].year, rows[-1].month) == (2027, 1)
```

Todos los argumentos son obligatorios y se pasan por nombre. El resultado es una tupla de objetos `ScheduleRow` inmutables:

| Campo | Significado |
| --- | --- |
| `period` | Número de período, empezando en 1 |
| `year`, `month` | Mes calendario del período |
| `depreciation_minor` | Depreciación del período |
| `accumulated_depreciation_minor` | Depreciación acumulada, incluido el período actual |
| `carrying_value_minor` | Costo menos depreciación acumulada al cierre del período |

El primer período es el mes indicado por `start_year` y `start_month`. Cada fila representa un mes completo, independientemente de sus días. La salida termina después de exactamente `periods` filas; no genera períodos posteriores a la vida útil.

### Política de reparto del resto

Se calcula `base, resto = divmod(cost_minor - residual_minor, periods)`. Los primeros `resto` períodos reciben `base + 1`; los demás reciben `base`. No se utilizan números de coma flotante.

- Un importe depreciable de 10 entre 3 meses produce `4, 3, 3`.
- Un importe depreciable de 11 entre 3 meses produce `4, 4, 3`.
- Una unidad menor entre 4 meses produce `1, 0, 0, 0`.

La política es determinista. Las cuotas difieren como máximo en una unidad menor. Su suma es exactamente `cost_minor - residual_minor`, el valor final es exactamente `residual_minor` y ningún valor en libros queda por debajo del residual. Cuando el costo y el residual son iguales, se generan los meses solicitados con depreciación cero.

### Validaciones y límites

- Solo se aceptan valores cuyo tipo sea el `int` incorporado de Python. Se rechazan `bool`, `float`, `Decimal`, cadenas y subclases de `int`; no hay conversiones implícitas.
- El costo y el residual deben ser no negativos, y el residual no puede superar el costo.
- `periods` debe ser positivo; `start_month` debe estar entre 1 y 12.
- Tanto el inicio como el final deben estar entre enero del año 1 y diciembre del año 9999. La validación del horizonte ocurre antes de crear filas.
- Los tipos incorrectos producen `TypeError`; los rangos incorrectos producen `ValueError`.
- La API usa enteros de precisión arbitraria. La CLI conserva enteros en JSON, pero está sujeta al límite de conversión decimal del intérprete. El consumidor del JSON también debe preservar enteros grandes; un `Number` de JavaScript puede perder precisión por encima de `2**53 - 1`.
- Se materializa el calendario completo. Tiempo y memoria son lineales en el número de períodos; el calendario admite como máximo 119.988 meses.

## CLI

```bash
asset-schedule \
  --cost-minor 100000 \
  --residual-minor 10000 \
  --periods 3 \
  --start-year 2026 \
  --start-month 11
```

También puede ejecutarse con `python -m asset_schedule`. Todos los importes y parámetros se suministran como enteros; `1.0` y `true` son entradas inválidas.

La salida es un documento JSON con `schema_version`, `method`, `remainder_allocation`, `inputs`, `total_depreciation_minor` y `schedule`. Consulta el [ejemplo completo de salida](examples/schedule.json). `schema_version` vale `1`, `method` vale `straight-line` y `remainder_allocation` vale `earliest-periods`.

Opciones adicionales:

- `--compact`: JSON en una sola línea
- `--help`: ayuda de uso
- `--version`: versión del paquete

Los cálculos correctos escriben JSON en stdout y terminan con código 0. Las entradas inválidas escriben el diagnóstico en stderr, dejan stdout vacío y terminan con código 2. La ayuda y la versión son salidas de texto, no JSON.

## Desarrollo y comprobación

Después de instalar el paquete:

```bash
python -m unittest discover -s tests -v
python examples/basic.py
```

Para comprobar el código directamente, sin instalar dependencias ni el paquete:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python examples/basic.py
```

La suite usa únicamente `unittest` e incluye casos de redondeo, cambio de año, límites de calendario, repetición determinista, enteros grandes, entradas inválidas, CLI y 10.710 calendarios de un dominio pequeño exhaustivo para comprobar invariantes.

Para construir una distribución con uv:

```bash
uv build
```

No se incluyen workflows de CI. Las comprobaciones se ejecutan localmente y no consumen minutos de GitHub Actions.

## Estado y licencia

Primera versión funcional, con alcance deliberadamente limitado. Consulta el [historial de cambios](CHANGELOG.md).

La licencia de distribución está pendiente de decisión del titular. Este repositorio todavía no declara una licencia de código abierto.
