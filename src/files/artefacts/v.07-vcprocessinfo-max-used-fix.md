# Artefacto v.07 - Fix NameError en VCprocessinfo (max_used)

## Contexto
Al ejecutar `DCO-DailyCheck.py -s VC -p process` aparece `name 'max_used' is not defined` en `VCprocessinfo.py`. El cálculo del estado de datastores usa `max_used` sin haberlo definido.

## Cambio propuesto (sin aplicar aún)
- Archivo objetivo: `src/VC/VCprocessinfo.py`
- Se calcula `max_used` inmediatamente después de crear la columna `% Used` en el dataframe de datastores.
- Se usa ese `max_used` para alimentar `DCOreport.rate_num_value`, manteniendo los umbrales existentes `[0, 85, 95, 101]` y ratings `OK/Warning/Critical`.

Pseudodiff:
```
# --- C. Datastores Status & Detail ---
ds_df = pd.DataFrame(datastores)
ds_status = "OK"
if not ds_df.empty:
    # 1. Calculate % Used before unit conversion for precision
    ds_df["% Used"] = ((ds_df["capacity"] - ds_df["free_space"]) / ds_df["capacity"]) * 100
    max_used = ds_df["% Used"].max()

    # 2. Determine aggregate Status using common rating function
    ds_status = DCOreport.rate_num_value(
        max_used,
        rate_intervals=[0, 85, 95, 101],
        rating=["OK", "Warning", "Critical"]
    )
```

## Impacto esperado
- Se elimina el NameError en la fase `process` para VC.
- El estado de datastores refleja el porcentaje máximo de uso calculado desde los datos ya cargados.
- No afecta a otras secciones (hosts, VMs, alerts) ni a la estructura de salida de CSVs.

## Archivos a modificar
- `src/VC/VCprocessinfo.py`

## Pruebas sugeridas tras aplicar
1) Ejecutar `python.exe .\DCO-DailyCheck.py -s VC -p process --loglevel debug` con los JSON recientes del `getinfo`:
   - Confirmar que no aparece NameError.
   - Verificar que se generan/actualizan CSV en `files/csv/` sin errores.
2) Revisar el CSV `VC-<instance>-datastore_status.csv` para verificar el campo `% Used` y que el estado agregado corresponda con los umbrales.

## Pendiente
- Esperar tu aprobación para aplicar el cambio en el código.
