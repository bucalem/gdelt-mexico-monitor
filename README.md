# Monitor de Tono Mediático — México (GDELT 2.0)

Dashboard que se actualiza solo, cada 15 minutos, midiendo el tono de la
cobertura noticiosa global sobre México usando datos públicos de
[GDELT 2.0](https://www.gdeltproject.org/) (sin API key, sin BigQuery).

```
.
├── index.html                          # Dashboard (lee data/*.json por fetch)
├── data/
│   └── mexico_tone_timeline.json       # Se sobreescribe automáticamente
├── scripts/
│   ├── fetch_gdelt.py                  # Descarga los archivos GKG recientes
│   └── analyze_mexico.py               # Filtra México, calcula tono, fusiona histórico
└── .github/workflows/update-monitor.yml # Corre el pipeline cada 15 min y hace commit
```

## Cómo funciona

1. `fetch_gdelt.py` descarga los últimos archivos GKG públicos de
   `data.gdeltproject.org` (por default, la última hora con redundancia).
2. `analyze_mexico.py` filtra las filas cuyo campo `V2Locations` incluye el
   código de país `MX`, calcula el tono promedio (`V2Tone` / GCAM) por bloque
   de 15 min, y **fusiona** el resultado con el histórico ya guardado en
   `data/mexico_tone_timeline.json` (sin duplicar, recortando a 3 días).
3. El GitHub Action corre ambos scripts cada 15 min y hace `git commit` +
   `git push` del JSON si cambió.
4. `index.html` no tiene datos embebidos: los pide por `fetch()` al propio
   JSON del repo, cada vez que se carga la página y luego cada 5 min.

## Pasos para desplegarlo

1. **Crea un repo nuevo** en GitHub, por ejemplo `gdelt-mexico-monitor`
   (recomendado dejarlo separado de `bucalem.github.io` para no llenar el
   historial de commits de tu portafolio principal con commits automáticos
   cada 15 min — aquí esos commits frecuentes son una *feature*, ahí serían
   ruido).
2. Sube todo el contenido de esta carpeta a la raíz del repo.
3. Ve a **Settings → Actions → General → Workflow permissions** y selecciona
   **"Read and write permissions"**. Sin esto el Action no podrá hacer push
   del JSON actualizado.
4. Ve a **Settings → Pages**, selecciona la rama `main` y carpeta `/ (root)`.
   Tu dashboard quedará en algo como
   `https://bucalem.github.io/gdelt-mexico-monitor/`.
5. Ve a la pestaña **Actions** del repo y corre el workflow
   **"Actualizar monitor GDELT México"** manualmente una vez
   (botón "Run workflow") para generar el primer dato real sin esperar el
   cron.
6. A partir de ahí corre solo, cada 15 minutos.

## Nota sobre el cron

GitHub Actions no garantiza el minuto exacto en `schedule` — en cuentas
gratuitas puede haber unos minutos de retraso, especialmente en horas de
poco uso de la plataforma. El dashboard ya contempla esto: el indicador
"EN VIVO" pasa a "SIN ACTUALIZAR" si han pasado más de 25 minutos desde la
última corrida, en vez de fallar silenciosamente.

## Integrarlo a tu portafolio principal

La forma más simple es una tarjeta de proyecto que enlace a la URL de Pages
de este repo ("Ver monitor en vivo →"). Si prefieres incrustarlo directo en
`bucalem.github.io`, puedes usar un `<iframe src="https://bucalem.github.io/gdelt-mexico-monitor/">`
dentro de la tarjeta correspondiente.

## Ir más allá

- Ampliar `MX_LOC_RE` a una lista de países para comparar tono entre México
  y otros mercados.
- Cruzar el histórico con eventos de coyuntura (conferencia mañanera,
  agenda legislativa) para correlacionar picos de tono con hechos
  específicos.
- Migrar el filtro a BigQuery (`gdelt-bq:gdeltv2.gkg`) para análisis
  histórico más allá de los 3 días que conserva este pipeline ligero.
