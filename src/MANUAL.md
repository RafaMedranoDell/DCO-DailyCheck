# 📖 Manual de Uso: DCO DailyCheck Automation

Bienvenidos a la herramienta de Automatización de Validaciones Diarias (DailyChecks). Esta herramienta consta de dos scripts principales:
1. **`config_tool.py`**: Utilizado para configurar y gestionar el inventario de sistemas y contraseñas.
2. **`DCO-DailyCheck.py`**: El motor principal que extrae la información, procesa los datos y genera los reportes ejecutivos.

---

## 🏗️ 1. Arquitectura y Fases del Script

El script principal funciona ejecutando de forma secuencial **4 fases independientes** para cada módulo. Conocerlas es clave para entender cómo actúan los scripts:

1. **`getinfo`**: Se conecta a las APIs/CLI de todos los sistemas definidos, solicita todos los datos crudos (en formato JSON) para volcarlos localmente. 
2. **`process`**: Mastica todos los JSONs raw descargados, aplica filtros (ej. calcula tiempos, elimina alertas irrelevantes) y convierte la información consolidada a tablas limpias (CSV).
3. **`reportDC`**: Genera el **Reporte Ejecutivo (Daily Check - DC)**. Muestra información unificada de alto nivel cruzando los CSV de todas las máquinas en un formato fácil de leer (Ideal para presentar al cliente).
4. **`reportDCI`**: Genera el **Reporte de Investigación (Daily Check Investigation - DCI)**. Ofrece tablas exclusivas e individuales por sistema o instancia indicando *solo* qué elementos están fallando o en riesgo (Ideal para el equipo de Operaciones).

### 🔎 ¿Qué información extrae cada módulo?

La herramienta interactúa con diferentes tecnologías del datacenter. Aquí un resumen general de lo que se plasma en los reportes de cada módulo:

*   🔒 **PowerProtect Cyber Recovery (PPCR) / CyberSense**: Estado del sistema, alertas, detalles de políticas (tiempos y bloqueos), estatus de las copias asiladas, resultados de indexación de CyberSense y licenciamiento.
*   🛡️ **Data Domain (DD)**: Capacidad activa, cloud y combinada, estatus de las réplicas establecidas, operatividad del filesystem general y limpieza.
*   💾 **PowerProtect Data Manager (PPDM)**: Estado de la salud general del sistema, tasa de éxito y resumen de inventario y trabajos de protección agrupados por categoría.
*   📦 **Elastic Cloud Storage (ECS)**: Capacidad total asignada y libre, estatus e integridad de todos los discos y de todos los nodos que componen el virtual data center.
*   🖥️ **vSphere (VC) / ESX Standalone**: Operatividad de clústers/hosts de cómputo desglosada (conexión, VMs apagadas inusualmente, ocupación del datastore y alarmas críticas y de licencia mapeadas en vCenter).
*   🌐 **Networking OS10**: Temperaturas, estatus funcional de cada boca frente a la expectativa, ventiladores, fuentes de poder y alarmas de switches físicos troncales.
*   ⚙️ **Server / iDRAC**: Chequeo nativo del hardware base: estatus del chasis, procesadores, RAM, log de controladora de vida útil (LifeCycle) y el FaultList a nivel de servidor plano.

---

## 🛠️ 2. Guía de Administración: `config_tool.py` 

Esta utilidad centraliza la seguridad y los ficheros de configuración. Nunca edites a mano los archivos `.json` de configuración; utiliza siempre este script.

### 🌟 Inicialización y Configuración Global

*   **1. Primera ejecución / Inicializar el sistema**
    Crea la base limpia de configuración partiendo de las plantillas del repositorio:
    ```bash
    python src/config_tool.py --init
    ```
*   **2. Configurar opciones globales interactivamente**
    Un asistente preguntará por parámetros generales (paths, puertos por defecto, información del cliente y correos asociados para el envío):
    ```bash
    python src/config_tool.py --interactive
    ```

### ➕ Gestión de Sistemas e Instancias

Puedes añadir múltiples sistemas gestionando sus credenciales de manera encriptada. El script preguntará de forma interactiva por **Alias**, **Usuario** y **Contraseña** (que nunca será visible).

*   **Listar inventario actual** (Mostrará los hostnames, y si disponen de Alias, aparecerá junto a ellos):
    ```bash
    python src/config_tool.py --list
    ```
*   **Añadir un sistema** (Formato: `MODULO/IpOHostname`):
    ```bash
    python src/config_tool.py --add IDRAC/192.168.1.15
    python src/config_tool.py --add DD/dd01.mipais.local
    ```
*   **Modificar credenciales o el Alias** de un sistema existente:
    ```bash
    python src/config_tool.py --modify IDRAC/192.168.1.15
    ```
*   **Eliminar un sistema**:
    ```bash
    python src/config_tool.py --remove IDRAC/192.168.1.15
    ```

### 🔐 Validación de Certificados TLS

La herramienta permite integrarse sobre HTTPS asegurado contra las APIs importando automáticamente la firma de los certificados:

*   Descargar y actualizar automáticamente los certificados en todos los sistemas configurados:
    ```bash
    python src/config_tool.py --certs update
    ```
*   Comprobar si los sistemas están respondiendo bien a su firma (ideal aplicarlo periódicamente o tras una actualización en la infraestructura central):
    ```bash
    python src/config_tool.py --certs check
    ```

---

## 🚀 3. Guía de Ejecución: `DCO-DailyCheck.py`

Este es el script que deben programar en los CRONs o disparar de forma manual para realizar el trabajo, generar los reportes en HTML y opcionalmente recibirlos en sus bandejas de entrada.

### Ejecución General Básica

Ejecutar todo (fases de getinfo a reportDC), barriendo absolutamente todos los sistemas configurados:
```bash
python src/DCO-DailyCheck.py
```

### Ejecuciones Avanzadas (Con Parámetros)

Puedes jugar con los parámetros (flags) para ajustar qué comportamiento quieres obtener:

* **1. Filtrar por módulo o inventario exacto (`-s` o `--scope`)**
  Solo sacar reporte de la tecnología vSphere:
  ```bash
  python src/DCO-DailyCheck.py -s VC
  ```
  O de una IP en específico:
  ```bash
  python src/DCO-DailyCheck.py -s IDRAC/192.168.1.15
  ```

* **2. Ejecutar fases parciales del script (`-p` o `--phase`)**
  A veces ya hemos descargado (`getinfo`) toda la inmensa cantidad de datos a disco y solo queremos aplicar filtros y regenerar el `.html`:
  ```bash
  python src/DCO-DailyCheck.py -p process reportDC reportDCI
  ```

* **3. Modificar alcance de revisiones históricas (`--last`)**
  Por defecto el script revisa un diferencial de métricas de las últimas 24 horas (u 72h si es lunes). Si tuvimos algún día sin operar, podemos forzar mirar más atrás en el tiempo:
  ```bash
  python src/DCO-DailyCheck.py --last 48h
  python src/DCO-DailyCheck.py --last 3d
  ```

* **4. Forzar Envío de Correo (`--email`) y estilos (`--numbers`)**
  Desencadena el plan de envío por SMTP a los correos definidos en el `config_tool.py`. Al tiempo, agrega el índice numerado jerárquicamente a los encabezados del propio cuerpo.
  ```bash
  python src/DCO-DailyCheck.py --numbers --email
  ```

* **5. Modo Diagnóstico (Troubleshooting) (`--loglevel debug`)**
  Si el log general (`info`) devuelve advertencias porque alguna API/SO no conectó, elevar la verbosidad permite ver los requests e inspeccionar por qué falla.
  ```bash
  python src/DCO-DailyCheck.py --loglevel debug
  ```

* **6. Comprobar Versión y Modificaciones (`--changelog`)**
  Obtiene la visual de control de versiones y los cambios sin procesar los sistemas.
  ```bash
  python src/DCO-DailyCheck.py --changelog
  ```
