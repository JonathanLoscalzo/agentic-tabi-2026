# Evals con Strands Evals

Sirven para comparar las técnicas con números en vez de opiniones: los mismos casos pasan por cada técnica y se puntúan igual.

## Cómo funciona

> Cada pregunta del dataset se responde con la técnica elegida y después se evalúa la respuesta.

1. **Dataset** (`evals/dataset.py`): 12 `Case` con pregunta y respuesta esperada. 10 son preguntas del dominio (Kimball, dimensión, tabla de hechos, estrella, copo de nieve, cubo OLAP, BI, ETL, software libre, machine learning) y 2 son **fuera de tema** (una receta y fútbol). En estas dos lo correcto es rechazar la pregunta o decir que no está en los documentos, sin inventar.
2. **Task** (`evals/run.py`): para cada caso llama a la técnica y devuelve la respuesta más la lista de tools que usó el agente (la "trayectoria").
3. **Evaluadores**: puntúan lo que devolvió el task. Hay cuatro, descritos abajo.
4. **Reporte**: promedio por evaluador y técnica, y un JSON con el detalle de cada caso.

## Las métricas

| Métrica | Qué mide | Cómo | Se aplica a |
|---|---|---|---|
| `correctness` | Si la respuesta es consistente con la esperada, en español y sin inventar | **LLM juez** (`OutputEvaluator`) con una rúbrica | Todas las técnicas |
| `faithfulness` | Si la respuesta es fiel a lo que hay en la conversación (contexto recuperado, resultados de tools) | **LLM juez** (`FaithfulnessEvaluator`), escala 0 a 1 en cinco niveles | Todas las técnicas |
| `relevance` | Si la respuesta atiende lo que se preguntó | **LLM juez** (`ResponseRelevanceEvaluator`) | Todas las técnicas |
| `tool_called` | Si el agente usó la tool esperada | **Determinística** (`ToolCalled`): mira la trayectoria | Solo `agent` (`search_docs`) y `multi` (`classify_relevance`) |

- **El juez:** es un LLM de OpenRouter, configurado con `TABI_JUDGE_LLM` (por defecto `anthropic/claude-haiku-5.5`). Recibe la pregunta, la respuesta de la técnica y la esperada, y devuelve un puntaje entre 0 y 1 con una explicación. La rúbrica lo orienta a 1 = correcta, 0.5 = parcial, 0 = incorrecta o inventada, aunque puede devolver valores intermedios como 0.9.
- **Fuera de tema:** rechazar o decir que no hay información cuenta como correcto.
- **`tool_called` vacío:** para las técnicas sin agente la métrica no aplica y aparece como `nan`.

## Resumen de resultados

Corrida completa con `claude-haiku-5.5` como modelo y como juez, 12 casos por técnica (2026-11-18):

| Técnica | correctness | faithfulness | relevance | tool_called |
|---|---:|---:|---:|---:|
| `no_context` | 0.86 | 1.00 | 1.00 | – |
| `bm25` | 0.75 | 0.98 | 0.94 | – |
| `vector` | 0.83 | 0.98 | 0.96 | – |
| `ensemble` | 0.82 | 1.00 | 0.92 | – |
| `agent` | 0.80 | 0.94 | 0.94 | 1.00 |
| `multi` | 0.86 | 0.90 | 0.98 | 1.00 |

Cómo leerla:

- **Casi todas quedan entre 0.75 y 0.86 en `correctness`.** Con 12 casos y puntajes que varían entre corridas, esas diferencias no alcanzan para decir que una técnica es mejor que otra.
- **`no_context` puntúa alto en `correctness`.** Las preguntas del dataset son definiciones generales (qué es un cubo OLAP, qué es ETL) que un modelo conoce sin los libros. Esta métrica no premia que la respuesta cite o se apoye en los documentos, que es lo que aportan las técnicas con contexto.
- **`faithfulness` de `no_context` (1.00) no significa que esté anclada a los libros.** La métrica mide si la respuesta contradice lo que hay en la conversación, y sin contexto no hay nada contra qué contradecir.
- **`multi` tiene la menor `faithfulness` (0.90).** Es la única que mezcla documentos y web, y el juez ve varios agentes. No investigué la causa: se puede mirar en `tmp/conversations/` y en las razones del JSON de cada caso.
- **`tool_called` es 1.00 en `agent` y `multi`:** siempre usaron la tool esperada.

## Cómo se corre

```bash
make eval                         # todas las técnicas, modelo por defecto
make eval M=openai/gpt-5-mini     # evalúa otro modelo (el juez no cambia)
uv run python evals/run.py -t bm25 -t agent -w 8   # técnicas puntuales, 8 casos en paralelo
```

- Imprime una línea por caso apenas termina, con el tiempo y si salió `ok` o con error.
- Un caso que falla (por ejemplo un error del modelo) no tumba la corrida: queda como `ERROR ...` y puntúa 0.
- Los resultados se guardan en `evals/results/<modelo>__<técnica>.json`. Cambiar de modelo no pisa corridas anteriores.
- `evals/smoke.py` prueba que el flujo funciona sin red ni modelos, con una técnica falsa y evaluadores determinísticos.

## Qué tener en cuenta al leer los números

- **12 casos es poco.** Una diferencia de pocas décimas entre técnicas puede ser ruido. Una misma técnica da puntajes algo distintos entre corridas.
- **El juez también es un modelo.** Tiene sesgos, y si es de la misma familia que el modelo evaluado puede favorecerlo.
- **`correctness` no distingue de dónde salió la respuesta:** si del contexto recuperado o del conocimiento previo del modelo. Por eso se mira junto con `faithfulness`, y aun así no prueba que haya usado los libros.
- **Telemetría:** `faithfulness` y `relevance` leen las trazas OpenTelemetry de cada caso (mensajes, contexto, tool calls). `evals/run.py` las captura en memoria y las filtra por caso, así que funciona con casos en paralelo.
- **No incluye** `TrajectoryEvaluator`: la trayectoria se verifica solo con `tool_called`.
