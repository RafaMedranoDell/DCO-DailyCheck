import argparse
from datetime import datetime
import getpass
import json
import os
import pathlib
import sys

from common.password_manager import PasswordManager
from common.functions import get_certificate_fingerprint

def parse_args():
    parser = argparse.ArgumentParser(description='Configuration management tool')

    # Group 1: File-related options (not mutually exclusive)
    file_group = parser.add_argument_group('File Options')
    file_group.add_argument('--cfg', type=str, metavar='FILENAME', default='config_encrypted.json',
                           help='Configuration file')
    file_group.add_argument('--template', type=str, metavar='FILENAME', default='TEMPLATEconfig.json',
                           help='Template file')
    file_group.add_argument('-n', '--no-backup', action='store_true',
                           help='Do not create a backup file before making changes.')

    # Mutually exclusive group for other options
    exclusive_group = parser.add_mutually_exclusive_group()

    # Group 2: Instance management options (mutually exclusive)
    instance_group = parser.add_argument_group('Instance Management Options')
    list_arg = instance_group.add_argument('-l', '--list', action='store_true', dest='list',
                                         help='List the instances')
    add_arg = instance_group.add_argument('--add', type=str, metavar='INSTANCE',
                                        help='Add an instance')
    remove_arg = instance_group.add_argument('--remove', type=str, metavar='INSTANCE',
                                           help='Remove an instance')
    modify_arg = instance_group.add_argument('--modify', type=str, metavar='INSTANCE',
                                             help='Modify the username or password of an instance')
    getcerts_arg = instance_group.add_argument('--certs', choices=["get", "update", "check"],
                                             help='Retrieve the certificate signature of each instance')

    # Group 3: Template comparison options (mutually exclusive, except --values)
    template_group = parser.add_argument_group('Template Comparison Options')
    init_arg = template_group.add_argument('--init', action='store_true',
                                         help='Copies the basic configuration')
    interactive_arg = template_group.add_argument('--interactive', action='store_true',
                                         help='Configures interactively the global settings')
    compare_arg = template_group.add_argument('-c', '--compare', action='store_true',
                                            help='Compare configuration keys with the template')
    values_arg = template_group.add_argument('-v', '--values', action='store_true',
                                           help='When comparing, show also changed values (only valid with --compare)')
    update_arg = template_group.add_argument('-u', '--update', action='store_true',
                                           help='Update configuration keys from the template')

    # Group 4: Key/value  options (mutually exclusive) (undocumented)
    keyvalue = parser.add_argument_group('Key/value')
    kv_dump_arg = keyvalue.add_argument('--dump', nargs='?', metavar='PATH', const='-',
                                      help=argparse.SUPPRESS)
    kv_set_arg = keyvalue.add_argument('--set', nargs=2, type=str, metavar=('KEY', 'VALUE'),
                                             help=argparse.SUPPRESS)

    # Add arguments to the mutually exclusive group (without redefining them)
    exclusive_group._group_actions.extend([
        list_arg, add_arg, remove_arg, modify_arg, getcerts_arg,
        init_arg, interactive_arg, compare_arg, update_arg,
        kv_dump_arg, kv_set_arg
    ])

    # Parse arguments
    args = parser.parse_args()

    # Custom validation for --values
    if args.values and not args.compare:
        parser.error('--values can only be used with --compare')

    return args

def load_cfg(fname):
    # Load a json/config file. Exit with an error if there is any issue
    try:
        with open(fname,  "rt") as f:
            js = json.load(f)
    except json.decoder.JSONDecodeError as e:
        print(f'{fname} JSON malformed: {e}')
        sys.exit(1)
    except OSError  as e:
        print(f'Unable to open file {fname}: {e}')
        sys.exit(1)
    return js

def scalar_first(d):
    # Separate scalar and nested dict items at first level
    scalars = {k: v for k, v in d.items() if not isinstance(v, dict)}
    nested = {k: v for k, v in d.items() if isinstance(v, dict)}
    # Combine, scalars first, then nested, no recursive sorting
    return {**scalars, **nested}

def save_cfg(cfg, fname):
    # Save a json/config into a file name
    try:
        with open(fname, "wt") as f:
            json.dump(scalar_first(cfg), f, indent=4)
        print(f'New config saved in {fname}')
    except OSError  as e:
        print(f'Error: {e}')
        sys.exit(1)

def backup_cfg(fname, no_backup):
    # Rename a filename to adding a the date/time as subfix
    CFGBCK = "cfgbck"
    if no_backup:
        return
    try:
        os.makedirs(CFGBCK, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bck_fname = os.path.join(CFGBCK, f'{args.cfg}.{timestamp}.bck')
        os.rename(args.cfg, bck_fname)
        print(f'Backup file {bck_fname}')
    except OSError  as e:
        print(f'Error: {e}')
        sys.exit(1)

def list_instances(cfg):
    for system_name in cfg["systems"].keys():
        for instance in cfg["systems"][system_name]["instances"]:
            alias = f' ({instance["alias"]})' if instance.get("alias") else ""
            print(f'{system_name}/{instance["hostname"]}{alias}')

def get_instance(cfg, system_name, instance_name):
    instance_found = None
    if system_name in cfg["systems"]:
        for instance in cfg["systems"][system_name]["instances"][:]:
            if instance["hostname"] == instance_name:
                instance_found = instance
    return instance_found

def validate_sys_instance(sys_instance):
    system_name, _, instance_name = sys_instance.partition("/")
    if system_name and instance_name:
        return (system_name, instance_name)
    else:
        print(f'Invalid system/instance: {sys_instance}')
        sys.exit(1)

def add_instance(cfg, template, sys_instance):
    # Locate the instance in the template
    system_name, instance_name = validate_sys_instance(sys_instance)
    if system_name not in template["systems"]:
        print(f'System {system_name} not found in template file.')
        return False

    if system_name not in cfg["systems"]:
        # Copy the system
        cfg["systems"][system_name] = template["systems"][system_name]
        # Delete example instance from the template
        cfg["systems"][system_name]["instances"] = []
        print(f'Adding system {system_name} to the configuration.')

    if get_instance(cfg, system_name, instance_name):
        print(f'Instance {sys_instance} already exists!')
        return False
    else:
        print(f'Provide username/password for {sys_instance}')
        try:
            alias = input("Alias [optional]: ").strip() or ""
            username = input("User name: ")
            instance = {
                "hostname": instance_name, 
                "username": username, 
                "encrypted_password": "",
                "alias": alias
            }
            set_password(system_name, instance)
            cfg["systems"][system_name]["instances"].append(instance)
        except KeyboardInterrupt:
            print("Exiting without changes!")
            sys.exit(0)
        return True

def ask_new_value(item_name, current_value):
    try:
        new_value = input(f'Enter {item_name} [{current_value}]:').strip()
        if new_value == "":
            return current_value, False  # No cambio
        return new_value, True  # Cambio detectado
    except KeyboardInterrupt:
        print("Exiting without changes!")
        sys.exit(0)

def modify_instance(cfg, sys_instance):
    system_name, instance_name = validate_sys_instance(sys_instance)

    instance = get_instance(cfg, system_name, instance_name)
    if instance:
        # Handle alias modification
        current_alias = instance.get("alias", "")
        new_alias, changed_alias = ask_new_value("new alias", current_alias)
        if changed_alias:
            instance["alias"] = new_alias

        new_username, changed_user = ask_new_value("new user name", instance["username"])
        if changed_user:
            instance["username"] = new_username
        
        set_password(system_name, instance)
        return True
    else:
        print(f'{sys_instance} not found in the configuration.')
        return False

def set_password(system_name, instance):
    pm = PasswordManager()
    passwd = getpass.getpass(f'Set password for {instance["username"]} in {system_name}/{instance["hostname"]}: ')
    instance["encrypted_password"] = pm.encrypt_password(passwd)

def remove_instance(cfg, sys_instance):
    system_name, instance_name = validate_sys_instance(sys_instance)
    instance_found = False
    instance = get_instance(cfg, system_name, instance_name)
    if instance:
        cfg["systems"][system_name]["instances"].remove(instance)
        if not cfg["systems"][system_name]["instances"]:
            cfg["systems"].pop(system_name)
        print(f'{sys_instance} removed from the configuration.')
        return True
    else:
        print(f'{sys_instance} not found in the configuration.')
        return False

def configure_interactive_settings(orig_cfg, prefix=""):
    any_changed = False
    # Ask for global configuration paths/settings
    for item_name in orig_cfg.keys():
        if not isinstance(orig_cfg[item_name], dict):
            show_item_name = f'{prefix} {item_name}' if prefix else item_name
            new_value, changed = ask_new_value(show_item_name, orig_cfg[item_name])
            if changed:
                orig_cfg[item_name] = new_value
                any_changed = True

    # Ask for specific customer/email settings
    if "customer" in orig_cfg:
        if configure_interactive_settings(orig_cfg["customer"], "customer"):
            any_changed = True
    return any_changed

def cfg_sync(dict_a, dict_b, cmp_values=False, path="", skip_list=[]):
    """
    Compare an update dict_b with the info found in dict_a.
    Copies missing keys from dict_a to dict_b.
    Deletes not needed keys in dict_b not present in dict_a.
    Do not process keys present in the skip_list.
    Recursively processes nested dictionaries.
    """

    # Format the string to show when there are changes
    def show_str(key, key_path, dict_x, dict_y=None):
        if dict_y:
            return f'"{key_path}": "{dict_x[key]}" -> "{dict_y[key]}"'
        else:
            return f'"{key_path}": "{dict_x[key]}"' if cmp_values else f'"{key_path}"'

    modified = False
    # Compare keys that are in the dict_a
    for key in dict_a.keys():
        if key in skip_list:
            continue
        key_path = f'{path}.{key}' if path else key
        if isinstance(dict_a[key], dict):
            if key in dict_b:
                # Compare the nested dictionaries
                children_modified = cfg_sync(dict_a[key], dict_b[key], cmp_values=cmp_values, path=key_path)
                modified |= children_modified
            else:
                # Copy the missing dictionary
                print(f'Copy missing dict {show_str(key, key_path, dict_a)}')
                dict_b[key] = dict_a[key]
                modified = True
        elif isinstance(dict_a[key], list):
            # Ignore the lists
            pass
        else:
            if key not in dict_b:
                # Copy missing scalar
                print(f'Copy missing key {show_str(key, key_path, dict_a)}')
                dict_b[key] = dict_a[key]
                modified = True
            elif cmp_values:
                # Compare existing scalars in both dictionaries
                if dict_a[key] != dict_b[key]:
                    print(f'Value change {show_str(key, key_path, dict_a, dict_b)}')

    # Delete keys that are not in the dict_a
    for key in list(dict_b.keys()):
        if key in skip_list:
            continue
        key_path = f'{path}.{key}' if path else key
        if key not in dict_a:
            print(f'Removing key {show_str(key, key_path, dict_b)}')
            dict_b.pop(key)
            modified = True

    return modified

def flat_json(json, separator = '.'):
    # Generate a list with pairs key and value from a JSON
    # The keys are the path of the item in the json, separated by separator.

    json_list = []
    def gen_key(parent, key):
        if parent == '':
            return key
        else:
            return separator.join([parent, str(key)])

    def walk(d, path=''):
        if type(d) is list:
            for idx, value in enumerate(d):
                walk(value, gen_key(path, idx))
        elif type(d) is dict:
            for key, value in d.items():
                walk(value, gen_key(path, key))
        else:
            json_list.append((path, d))
    walk(json, '')
    return json_list

def set_value_by_path(data, path, value):
    keys = path.split(".")
    current = data
    for i, key in enumerate(keys):
        # Convert the key to a number
        if key.isdigit():
            key = int(key)
        # In the last element we assing the value
        if i == len(keys) - 1:
            if key in current:
                current[key] = value
            else:
                raise KeyError
        else:
            current = current[key]

if __name__ == "__main__":
    args = parse_args()

    template_cfg = load_cfg(args.template)

    if args.init:
        if os.path.exists(args.cfg):
            print(f'Error: Refusing to initialize an existing config file: {args.cfg}')
            sys.exit(1)
        # Set the basePath to the current working directory
        template_cfg['basePath'] = os.getcwd()
        # Remove all the systems
        template_cfg["systems"] = {}
        save_cfg(template_cfg, args.cfg)
        sys.exit(0)

    orig_cfg = load_cfg(args.cfg)
    if args.list:
        list_instances(orig_cfg)
    elif args.interactive:
        if configure_interactive_settings(orig_cfg):
            backup_cfg(args.cfg, args.no_backup)
            save_cfg(orig_cfg, args.cfg)
    elif args.add:
        if add_instance(orig_cfg, template_cfg, args.add):
            backup_cfg(args.cfg, args.no_backup)
            save_cfg(orig_cfg, args.cfg)
    elif args.remove:
        if remove_instance(orig_cfg, args.remove):
            backup_cfg(args.cfg, args.no_backup)
            save_cfg(orig_cfg, args.cfg)
    elif args.modify:
        if modify_instance(orig_cfg, args.modify):
            backup_cfg(args.cfg, args.no_backup)
            save_cfg(orig_cfg, args.cfg)
    elif args.compare or args.update:
        print(f'Comparing: {args.cfg} -> {args.template}')

        # Compare base items in the root of the config (skipping "systems")
        modified = cfg_sync(template_cfg, orig_cfg, cmp_values=args.values, skip_list=['systems'])

        # Compare systems only if they have instances in the target
        for system_type in orig_cfg['systems'].keys():
            if system_type not in template_cfg['systems']:
                print(f'Error: system "{system_type}" not found in template!')
                sys.exit(1)
            if len(orig_cfg['systems'][system_type]['instances']):
                modified |= cfg_sync(
                    template_cfg['systems'][system_type],
                    orig_cfg['systems'][system_type],
                    cmp_values=args.values,
                    path=f'systems.{system_type}')

        # Save the new file if needed
        if modified and args.update:
            backup_cfg(args.cfg, args.no_backup)
            save_cfg(orig_cfg, args.cfg)
    elif args.certs:
        for system_name in orig_cfg['systems'].keys():
            for instance in orig_cfg['systems'][system_name]['instances']:
                hostname = instance['hostname']
                api_port = orig_cfg['systems'][system_name]['cfg']['api_port']
                cert_hash = get_certificate_fingerprint(hostname, api_port)
                if args.certs == "get":
                    print(f'{system_name}/{hostname} -> {cert_hash}')
                elif args.certs == "update":
                    if cert_hash:
                        instance['certHash'] = cert_hash
                elif args.certs == "check":
                    stored_hash = instance.get('certHash', '')
                    if stored_hash == cert_hash:
                        print(f'{system_name}/{hostname} hash matches [{cert_hash}]')
                    else:
                        print(f'{system_name}/{hostname} hash do not match')
                        print(f'\t   stored: {stored_hash}')
                        print(f'\tretrieved: {cert_hash}')
        if args.certs == "update":
            backup_cfg(args.cfg, args.no_backup)
            save_cfg(orig_cfg, args.cfg)
    elif args.dump:
        for key, value in flat_json(orig_cfg):
            if key.startswith(args.dump) or args.dump == "-":
                print(f'{key} -> {value}')
    elif args.set:
        try:
            set_value_by_path(orig_cfg, args.set[0],  args.set[1])
            backup_cfg(args.cfg, args.no_backup)
            save_cfg(orig_cfg, args.cfg)
        except (KeyError, IndexError):
            print(f'Key {args.set[0]} not found')


