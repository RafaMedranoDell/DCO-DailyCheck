import argparse
import csv
from datetime import datetime
import glob
import json
import logging
import os
import pandas as pd
import pathlib
import zipfile
import common.functions as fn
from common.password_manager import PasswordManager

# Configure module logger
logger = fn.get_module_logger(__name__)

class DCOconfig:
    """
        Loads the configuration file and simplifies the generation of information based on it.
        Concepts:
            - system: family of components. ie: PPDM, DD, ECS, PPCR...
            - instance: hostname of a specific element of a system type
            - file_type: format of the file used for the scripts: csv, json, xls
            - data_type: keyword describing the kind of contents the file has
    """
    def __init__(self, config_fname):
        with open(config_fname, "rt") as f:
            self.config = json.load(f)
        self.base_path = self.config["basePath"]
        self.params = {}
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())
        self.cfgbck = None

    def set_param(self, key, value):
        logger.debug(f'Param "{key}" set to: "{value}"')
        self.params[key] = value

    def get_param(self, key):
        return self.params.get(key, None)

    def log(self, level, msg):
        self.logger.log(level, msg)

    def _getInstanceData(self, system, instance):
        for instance_data in self.config["systems"][system]["instances"]:
            if instance_data["hostname"] == instance:
                return instance_data

    def remove_limit(self):
        if self.cfgbck:
            self.config = self.cfgbck
            self.cfgbck = None
        else:
            self.log(logging.DEBUG, 'remove_limit() call without limit set.')

    def limit_to(self, selected):
        """
        Removes all but the system or system/instance provided
        Charater neg_char (^) negates the systems
            - ^system1 -> all systems but system1
            - system1/^instance1 -> only system1 systems, all but instance1 instances
        """
        # Make a copy of the configuration
        self.cfgbck = self.config.copy()

        neg_char = '^'
        sel_system, _, sel_instance = selected.partition("/")
        not_system, sel_system = sel_system.startswith(neg_char), sel_system.lstrip(neg_char)
        not_instance, sel_instance = sel_instance.startswith(neg_char), sel_instance.lstrip(neg_char)

        # Validate system exists and instance exists
        if sel_system and sel_system not in self.config['systems']:
            raise ValueError(f'System "{sel_system}" not found in config')
            if sel_instance and sel_instance not in self.config['systems'][sel_system]['instances']:
                raise ValueError(f'Instance "{sel_instance}" not found in system "{sel_system}"')

        # If system is specified, keep/remove only the selected system
        if sel_system:
            if not_system:
                # Remove the system from the config
                self.config['systems'].pop(sel_system, None)
            else:
                self.config['systems'] = {sel_system: self.config['systems'][sel_system]}
                # If an instance is specified, keep/remove only that instance
                if sel_instance:
                    instances = self.config['systems'][sel_system]['instances']
                    if not_instance:
                        # Remove the instance
                        instances[:] = [d for d in instances if d.get("hostname") != sel_instance]
                    else:
                        instances[:] = [self._getInstanceData(sel_system, sel_instance)]

    def systems(self):
        """
        Returns the system types present in the configuration.
        The list is sorted by a predefined priority to ensure consistent reporting order.
        """
        SYSTEM_PRIORITY = ["PPCR", "PPDM", "DD", "ECS", "VC", "IDRAC", "OS10"]
        
        current_systems = list(self.config["systems"].keys())
        
        # Sort current systems based on the priority list. 
        # Systems not in the list are placed at the end.
        current_systems.sort(key=lambda x: SYSTEM_PRIORITY.index(x) if x in SYSTEM_PRIORITY else 999)
        
        return current_systems

    def instances(self, system):
        # Returns the instance names for a system type
        if system in self.config["systems"]:
            return [ instance["hostname"] for instance in self.config["systems"][system]["instances"] ]
        else:
            return []

    def loginInfo(self, system, instance):
        # Returns username, password, REST API port and certificate hash for a system/instance
        instance_data = self._getInstanceData(system, instance)
        pwd_mgnt = PasswordManager()
        password = pwd_mgnt.decrypt_password(instance_data["encrypted_password"])
        # Get specific api_port for this instance if present, get the default one
        api_port = instance_data.get('api_port', self.config['systems'][system]['cfg']['api_port'])
        cert_hash = instance_data.get('certHash', '')
        return api_port, instance_data["username"], password, cert_hash

    def instanceInfo(self, system, instance):
        instance_data = self._getInstanceData(system, instance)
        return instance_data.get("info", {})

    def customerInfo(self):
        return self.config["customer"]

    def fileTypePath(self, file_type):
        # Returns the path of a file type
        if file_type == "json":
            type_path = self.config["jsonPath"]
        elif file_type == "csv":
            type_path = self.config["csvPath"]
        elif file_type == "xlsx":
            type_path = self.config["reportPath"]
        elif file_type == "html":
            type_path = self.config["reportPath"]
        elif file_type == "log":
            type_path = self.config["logPath"]
        else:
            # If not found, store the file in a tmp dir
            type_path = "tmp"
            logger.error(f'Requested file path for unknown file type: {file_type}')
        # Load the path in a PurePath to split in parts and later convert into a native path
        type_purepath = pathlib.PurePath(type_path)
        filePath = os.path.join(self.base_path, *type_purepath.parts)
        # Creates it if doesn't exist
        os.makedirs(filePath, exist_ok=True)
        return filePath

    def filePath(self, system, instance, file_type, data_type):
        # Returns the complete file path and name for a system, instance filetype and data_type
        try:
            # Generate file for exception "unifiedData.csv" (DD, ECS, PPDM)
            if system in ("DD", "PPDM") and file_type == "csv" and data_type == "unifiedData":
                file_name = f"{system}-unified_data.csv"
            else:
                file_subfix = self.config["systems"][system]["files"][file_type][data_type]
                file_name = f"{system}-{instance}-{file_subfix}"
        except KeyError as e:
            self.log(logging.ERROR, f'Key path config["systems"]["{system}"]["files"]["{file_type}"]["{data_type}"] not found')
            raise e

        return os.path.join(self.fileTypePath(file_type), file_name)

    def filePathList(self, system, instance, file_type, data_type):
        # Uses the glob library to locate the real path of a file
        return glob.glob(self.filePath(filePath))

    def _checkFile(self, system, instance, file_type, data_type):
        # Checks the existence of a file (after saving it) and logs the result
        file_path = self.filePath(system, instance, file_type, data_type)
        if os.path.exists(file_path):
            self.log(logging.DEBUG, f"File saved succesfully: {file_path}")
        else:
            self.log(logging.ERROR, f"Error saving the file: {file_path}")

    def save_json(self, data, system, instance, data_type):
        output_file = self.filePath(system, instance, "json", data_type)
        with open(output_file, "w") as file:
            json.dump(data, file, indent=4)
        self._checkFile(system, instance, "json", data_type)

    def load_json(self, system, instance, data_type):
        with open(self.filePath(system, instance, "json", data_type), "r") as file:
            return json.load(file)

    def save_dataframe_to_csv(self, df, system, instance, data_type):
        output_file = self.filePath(system, instance, "csv", data_type)
        df.to_csv(output_file, index=False, header=True, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\")
        self._checkFile(system, instance, "csv", data_type)

    def load_csv_to_dataframe(self, system, instance, data_type):
        try:
            df = pd.read_csv(self.filePath(system, instance, "csv", data_type), keep_default_na=False, na_values=['NA', 'NaN', 'null'])
        except FileNotFoundError:
            df = pd.DataFrame()
        return df

    def cleanup(self, days=30):
        # Remove files by date to asure no files are left behind
        time_limit = datetime.now().timestamp() - (86400 * days)
        for file_type in ['json', 'csv', 'xlsx', 'html']:
            file_type_path = self.fileTypePath(file_type)
            file_list_up = glob.glob(os.path.join(file_type_path, f'*.{file_type.upper()}'))
            file_list_low  = glob.glob(os.path.join(file_type_path, f'*.{file_type.lower()}'))
            cnt = 0
            for file_path in file_list_up + file_list_low:
                if os.path.getmtime(file_path) < time_limit:
                    if fn.remove_file(file_path):
                        cnt += 1
            if cnt:
                logger.info(f'Cleaned up {cnt} {file_type} old files')

    def _file_list_by_type(self, file_type):
        file_list = []
        for system in self.systems():
            for instance in self.instances(system):
                for data_type in self.config["systems"][system]["files"][file_type].keys():
                    file_list.append(self.filePath(system, instance, file_type, data_type))
        return file_list

    def archive_type(self, file_type, current_time):
        file_list = self._file_list_by_type(file_type)
        if file_list:
            time_str = current_time.strftime("%Y%m%d_%H%M%S")
            zip_file_path = os.path.join(self.fileTypePath(file_type), f'{time_str}-{file_type}.zip')
            try:
                with zipfile.ZipFile(zip_file_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in file_list:
                        if os.path.exists(file_path):
                            zipf.write(file_path, os.path.basename(file_path))
                logger.info(f'Archived {file_type} files in {zip_file_path}')
            except Exception as e:
                logger.error(f'Error while archiving {file_type} files: {e}')

    def archive_cleanup(self, file_type):
        def zip2dt(full_name):
            # Retrieve the date/time from the zipfile name
            fpath, fname = os.path.split(full_name)
            strtime, _ = fname.split('-')
            return datetime.strptime(strtime, "%Y%m%d_%H%M%S")

        marked_list = fn.mark_files_by_date(self.fileTypePath(file_type), f'*-{file_type}.zip', zip2dt, keep_days=14)
        delete_list = [ x['fname'] for x in marked_list if x['delete'] ]
        if delete_list:
            logger.info(f'Deleting old {file_type} archive files')
            for fname in delete_list:
                fn.remove_file(fname)

    def delete_type(self, file_type):
        logger.info(f'Deleting {file_type} files')
        for fpath in self._file_list_by_type(file_type):
            fn.remove_file(fpath)

def create_parser():
    parser = argparse.ArgumentParser(description='Command line tool for system operations')
    parser.add_argument('-c', '--config', type=str,
                       default='config_encrypted.json', help='Configuration file path')
    parser.add_argument('action', choices=['archive', 'cleanup', 'instances', 'systems'],
                       help='Action to perform')

    return parser

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()

    dcocfg = DCOconfig(args.config)
    fn.setup_logging(dcocfg.fileTypePath("log"), "{system}debug", level=logging.DEBUG)

    if args.action == 'archive':
        dcocfg.archive()
    elif args.action == 'cleanup':
        dcocfg.cleanup()
    elif args.action == 'systems':
        for system in dcocfg.systems():
            print(system)
    elif args.action == 'instances':
        for system in dcocfg.systems():
            for instance in dcocfg.instances(system):
                print(f'{system},{instance}')
