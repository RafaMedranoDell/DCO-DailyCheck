# DCO Daily Check automation
## Description
Daily Check Report Generation Automation Scripts for the DCO Group## Technologies

## Technologies

### Currently supported
- Data Domain (DD)
- PowerProtect Data Manager (PPDM)
- Elastic Cloud (ECS)
- PowerProtect Cyber Recovery (PPCR)
- Dell Switches (OS10)

## Prerequisites

- Python3 enviroment with the following modules instaled:
   - cryptography
    - openpyxl
    - pandas
    - requests
    - urllib3
    - jinja2
- For Windows systems we advice to use WinPython.

## Installation Instructions

### WynPython
These are the steps to follow to obtain a reduced version of WinPython, but with the needed packages to run your DCO automation scripts.

1. Download the WinPython “dot” version from https://winpython.github.io
2. Unpack the downloaded file in a temporary folder.
3. Using file explorer, execute "WinPython Control Panel.exe". This will open a terminal with an custom environment.
4. Check the python modules included in this version:
    ```
    wppm -ls
    ```
5. Install the modules needed using pip:
    ```
    pip install cryptography
    pip install openpyxl
    pip install pandas
    pip install requests
    pip install urllib3
    pip install jinja2
    pip install pyvmomi
    ```

   > **Note:** if you need to reproduce the validated environment (WinPython with the tested packages), run `pip install -r requirements-verified.txt` from the repo root. This file pins the verified versions (Python 3.12.10 + main dependencies) and is the one used when packaging the scripts.

6. Verify the currently installed packages (optional control check):
   ```
   python.exe -m pip list --path "<WINPYTHON-PATH>\python\Lib\site-packages"
   ```
7. Disable the user site packages before installing:
   ```
   set PYTHONNOUSERSITE=1
   ```
8. Install the dependencies directly into the WinPython bundle site-packages:
   ```
   python.exe -m pip install -r requirements-verified.txt --target "<WINPYTHON-PATH>\python\Lib\site-packages"
   ```
9. Verify again that the modules are present inside the portable environment:
   ```
   python.exe -m pip list --path "<WINPYTHON-PATH>\python\Lib\site-packages"
   ```
10. Check that the python is able to load the downloaded modules(optional)
    - Execute python.exe
    - Type import commands for each of the modules and verify it doesn't fail
   ```
   import <module_name>
   ```
11. Pack/zip the original folder (now with the modules installed).
12. Copy and unzip the file to the customer server.

### DCO scripts
1. Generate the zip file with the scripts to deploy them in the customer server
   1. Retrieve the GitHub repository and switch to the main/test branch
   2. Run the deploy package generator
      ```
      python3 tools/deploy-pack.py
      ```
      The deploy package generato create a zip file in the build subdirectory with:
         - Main script: DCO-DailyCheck.py
         - Libraries: password_manager.py, common/functions.py, common/DCOconfig.py and common/DCOreport.py
         - Config utility tool: config_tool.py
         - Config template example: TEMPLATEconfig.json
         - Product scripts: DD, ECS, PPDM...
         - hashes.txt: sha256 hash of all the files included.
            - We can check if files have been changed after the deployment
               ```
               Get-FileHash -Path "<filename>" -Algorithm SHA256
               ```
         - commit_id.txt: GIT commit ID of the files generated.
            - This allows to track the version of the files deployed.

      The file name will have the date and time: deploypack-YYYYMMDD_hhmm.zip

2. Copy and unzip the file to the customer server.
3. Create, modify or update the configuration file:
   - a) For new deployments
      - Use the config tool to initizlize the configuration file
         1. Open a command / PowerShell window.
         2. Change to the directory where the scripts are unziped.
         3. Initialize the configuration file using the configuration tool:
            ```
            python3 config-tool.py --init
            ```
            - The configuration will set the base path of the scripts to the current path.
            - The default configuration file name is "config_encrypted.json" but we can use any other name using the option "--cfg".

         4. Use config-tool.py to add instances of the products to be monitored.
            ```
            $ python3 config_tool.py --add IDRAC/10.0.0.10
            Adding system IDRAC to the configuration.
            Provide username/password for IDRAC/10.0.0.10
            User name: DCOoper
            Set password for DCOoper in IDRAC/10.0.0.10:
            Backup file cfgbck\config_encrypted.json.20251010_111628.bck
            New config saved in config_encrypted.json
            ```
            - Each time the config tool modifies the configuration file a backup will be saved in the "cfgbck" subdirectory.
            - First time we add a instance to a configuration file, the script will create key file (secret.key) to encrypt the passwords. Do not delete that file!
   - b) For exising deployments
      - Use config-tool.py to compare (and update if needed) the configuration with the template.
         - Comparision
            ```
            $ python3 config_tool.py --compare --values
            Comparing: config_encrypted.json -> TEMPLATEconfig.json
            key removed  ['xlsxPath']
            key removed  ['templatePath']
            value change ['logPath']: "logs" -> "files/logs"
            value change ['basePath']: "/home/nacho/dev/dco/DCO-dailycheck" -> ""
            key added    ['reportPath']
            key removed  ['systems', 'PPCR', 'files', 'templates']
            ```
            The tool compares also the values but it doesn't updates them. If the values of the keys present in the configuration need a mofication it has to be done manually.
         - Updating
            ```
            $ python3 config_tool.py --update
            Comparing: config_encrypted.json -> TEMPLATEconfig.json
            key removed  ['templatePath']
            key removed  ['xlsxPath']
            key added    ['reportPath']
            key removed  ['systems', 'PPCR', 'files', 'templates']
            Backup file cfgbck\config_encrypted.json.20251010_111318.bck
            New config saved in config_encrypted.json
4. Check the product/instances in the configuration file
   ```
   $ python3 config_tool.py --cfg config_encrypted.json.lab1 -l
   PPDM/192.168.1.15
   PPCR/192.168.231.133
   OS10/192.168.231.134
   DD/ddtest01
   ECS/ecstest01
   ```

## Usage

### Execution phases
1. getinfo phase
   - In this phase the script will connect to the REST API of the products present in the "config.json" and retrieve the information in JSON format.
   - This is the only phase that needs network conectivity to the products.
   - No modifications are done to the products in any way.
2. process phase
   - The process phase will take raw JSON files from the products and filter and sumarize the relevant information.
   - This phase will generate a set of CSV files with the results
3. report phase
   - This phase will read the CSV files generated from the previous phase and will format and colorize.
   - This phase can generate two kind of reports:
      - Daily Check (DC) report: sumarized version of the report.
      - Daily Check Investigation (DCI) report: detailed version of the report with the relevant alerts, statuses, jobs and information.
   - The reports can be generated as HTML and/or Excel formats

### Basic usage
- Info retrieval phase
   - Confirm that the "config.json" (config_encrypted.json) have the right format and the complete list of elements to monitor by listing them:
      ```
      python3  DCO-DailyCheck.py --list
      ```
   - Run the information retrieval for a single system/instance:
      ```
      python3  DCO-DailyCheck.py --phase getinfo --scope PPCR/192.168.231.133
      ```
   - Run the information retrieval for all the instances of a system type:
      ```
      python3  DCO-DailyCheck.py --phase getinfo --scope PPCR
      ```
   - Run the information retrieval for all the elements in the "config.json" file:
      ```
      python3  DCO-DailyCheck.py --phase getinfo
      ```
- Info processing phase
   - Process only one system/instance
      ```
      python3 DCO-DailyCheck.py --phase process --scope OS10
      ```
      The reports generated with the --scope option will have the scope (the system / instance) in the report name.
   - Proccess the information fo all the retrieved systems/instances:
      ```
      python3  DCO-DailyCheck.py --phase process
      ```
- Report generation phase
   - Generate the Daily Check (DC) report both in html and xlsx formats:
      ```
      python3 DCO-DailyCheck.py --phase reportDC --fmt all
      ```
   - Generate the Daily Check Investigation (DCI) report both in html and xlsx formats:

      ```
      python3 DCO-DailyCheck.py -p reportDCI -f all
      ```
### Usage additional info
Command line help:
```
$ python3 DCO-DailyCheck.py --help
usage: DCO-DailyCheck.py [-h] [-c CFG] [-l] [-s SCOPE]
                         [-p {getinfo,process,reportDC,reportDCI} [{getinfo,process,reportDC,reportDCI} ...]]
                         [--last LAST] [--email] [-f {html,xls,all}] [--split] [--numbers]
                         [--loglevel {error,warn,info,debug}]

DCO daily report script

options:
  -h, --help            show this help message and exit
  -c CFG, --cfg CFG     Use an alternate configuration file (default=config_encrypted.json).
  -l, --list            List the system/instances in the configuration file.
  -s SCOPE, --scope SCOPE
                        Run the script only for system or system/instance.
  -p {getinfo,process,reportDC,reportDCI} [{getinfo,process,reportDC,reportDCI} ...], --phase {getinfo,process,reportDC,reportDCI} [{getinfo,process,reportDC,reportDCI} ...]
                        Run only one phase of the script.
  --last LAST           Number of hours (or days if followed by 'd') to look back
  --email               Send the report by email.
  -f {html,xls,all}, --fmt {html,xls,all}
                        Save the report in one of the formats (default: html).
  --split               Split DCI report in subreports by system type.
  --numbers             Adds hierarchical numbering to the report.
  --loglevel {error,warn,info,debug}
                        Set the logging level.

```
- Phases

   We can specify several phases separate by spaces with option '--phase'. i.e: we have retrieved the data from all the systems, but we need to generate a report only containing iDRAC info:
   ```
   python3 DCO-DailyCheck.py --scope IDRAC --phase process reportDCI
   ```
- Date filtering

   The script filters by default the logs and events:
   - last 24 hours (Tuesday to Sunday)
   - last 72 hours (Mondays).

   We can override this behaviour with option '--last' followed by the number of hours /days.

   This option only affects process phase.
   ```
   python3 DCO-DailyCheck.py --scope OS10 --phase process reportDCI --last 30d

   python3 DCO-DailyCheck.py --scope OS10 --phase process reportDCI --last 12h
   ```
- Schema numbering

   Option '--numbers' adds a schema numbering to each element/information in the report.
- DCI report split

   Option  '--split' splits the DCI report into subreports for every product. It also generates the report with all the products.

### Other tools
#### config_tool.py
```
$ python3 config_tool.py --help
usage: config_tool.py [-h] [--cfg FILENAME] [--template FILENAME] [-n] [-l] [--add INSTANCE]
                      [--remove INSTANCE] [--password INSTANCE] [--init] [-c] [-v] [-u]
                      [--paths {win,posix}]

Configuration management tool

options:
  -h, --help           show this help message and exit

File Options:
  --cfg FILENAME       Configuration file
  --template FILENAME  Template file
  -n, --no-backup      Do not create a backup file before making changes.

Instance Management Options:
  -l, --list           List the instances
  --add INSTANCE       Add an instance
  --remove INSTANCE    Remove an instance
  --password INSTANCE  Modify the password of an instance

Template Comparison Options:
  --init               Copies the basic configuration
  -c, --compare        Compare configurations with the template
  -v, --values         When comparing, show also changed values (only valid with --compare)
  -u, --update         Update configurations from the template

Path Conversion Options:
  --paths {win,posix}  Convert paths to specified type
```

## Modules

## FAQs
