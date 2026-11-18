# data/

Acá van los PDFs que se indexan. **No se versionan** (`data/*` está en `.gitignore`).

## Libro de cátedra (se descarga solo)

*Tecnologías para el análisis de datos basadas en software libre. Guía de desarrollo y aplicación.*
Díaz, F. J.; Osorio, M. A.; Amadeo, A. P. (comps.), 2019. SEDICI, UNLP: <https://sedici.unlp.edu.ar/handle/10915/78652>
Licencia [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

```bash
make data    # lo baja a data/ si falta (make index también lo hace)
```

## Otro material

Cualquier otro PDF de la cátedra o propio: copialo en esta carpeta y corré `make reindex`. El material que no sea abierto hay que pedirlo en la cátedra.
Por ejemplo, el manifiesto de Kimball es una página de kimballgroup.com impresa a PDF: opcional, solo local.
