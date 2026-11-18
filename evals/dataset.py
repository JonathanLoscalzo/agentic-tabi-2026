from strands_evals import Case

OFF = "Fuera de tema: debe rechazar la pregunta o decir que no está en los documentos, sin inventar."

CASES = [
    Case(name="kimball", input="¿Quién es Ralph Kimball?",
         expected_output="Referente del data warehousing y el modelado dimensional; propone el enfoque bottom-up con data marts."),
    Case(name="dimension", input="¿Qué es una dimensión en un modelo dimensional?",
         expected_output="Tabla con atributos descriptivos (quién, qué, dónde, cuándo) usados para filtrar y agrupar los hechos."),
    Case(name="hechos", input="¿Qué es una tabla de hechos?",
         expected_output="Tabla central con las medidas numéricas de un proceso de negocio, con claves foráneas a las dimensiones."),
    Case(name="estrella", input="¿Qué es un esquema en estrella?",
         expected_output="Una tabla de hechos rodeada de tablas de dimensiones desnormalizadas conectadas directamente."),
    Case(name="copo", input="¿En qué se diferencia el copo de nieve del esquema en estrella?",
         expected_output="El copo de nieve normaliza las dimensiones en subtablas; la estrella las deja desnormalizadas."),
    Case(name="cubo", input="¿Qué es un cubo OLAP?",
         expected_output="Estructura multidimensional que permite analizar medidas según varias dimensiones (slice, dice, roll-up, drill-down)."),
    Case(name="bi", input="¿Qué es el Business Intelligence?",
         expected_output="Conjunto de procesos y tecnologías para convertir datos en información útil para la toma de decisiones."),
    Case(name="etl", input="¿Qué es un proceso ETL?",
         expected_output="Extracción, transformación y carga de datos desde fuentes hacia el data warehouse."),
    Case(name="opensource", input="¿Qué ventajas tiene el software libre para el análisis de datos?",
         expected_output="Sin costo de licencia, código auditable y modificable, comunidad y ausencia de dependencia de un proveedor."),
    Case(name="ml", input="¿Qué es machine learning?",
         expected_output="Rama de la IA en la que los modelos aprenden patrones a partir de datos para predecir o decidir sin reglas explícitas."),
    Case(name="off_receta", input="¿Cómo hago una tarta de manzana?", expected_output=OFF),
    Case(name="off_futbol", input="¿Quién ganó el último mundial de fútbol?", expected_output=OFF),
]
