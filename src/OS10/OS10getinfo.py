import logging
import os
import requests
import urllib3
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "OS10"

# Configure module logger
logger = fn.get_module_logger(__name__)

# Disable wargnings: InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disable urllib3 from logging their messages
l = logging.getLogger('urllib3')
l.propagate = False

"""
    Possible usefull queries:
    "dell-system:system": System info
    "dell-alarm:alarm-info": Alarms info
    "dell-equipment:system": Equipment info
    "dell-equipment:system/environment": Environment info
    "dell-port:ports": Ports info
    "dell-port:ports/ports-state": Ports state
"""

class OS10api():
    def __init__(self, instance, api_port, username, password, cert_hash):
        # Switch details
        self.base_url = f"https://{instance}:{api_port}/restconf/data"
        self.instance = instance

        # Disable SSL warnings
        requests.packages.urllib3.disable_warnings()

        # Create session for authentication
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = False  # Disable SSL verification

        # Set headers for JSON
        headers = {
            "Content-Type": "application/yang-data+json",
            "Accept": "application/yang-data+json"
        }
        self.session.headers.update(headers)

    def log(self, level, msg):
        logger.log(level, f'{system}/{self.instance}: {msg}')

    def command(self, method, url, **kwargs):
        """
        Send a REST API command to the switch

        Parameters:
        - method (str): Type of REST API call (GET, POST, PUT, DELETE, PATCH)
        - url (str): last part of the URL endpoint for the call (removing the "/restconf/data")
        - **kwargs (kwargs): Additional named parameters to be passed to the request

        Returns:
        - HTTP response: the full HTTP response of the call
        """
        full_url = '/'.join((self.base_url, url.strip('/')))
        self.log(logging.DEBUG, f'{method} {full_url}')
        response = self.session.request(method, full_url, **kwargs)
        self.log(logging.DEBUG, f'status_code: {response.status_code}')
        return response

    def sysinfo(self):
        """
        Get the basic switch information (hostname, users...)

        Returns:
        - System information if was able to connect, empy list if there was an error.
        """
        response = self.command("GET", "dell-system:system")

        if response.status_code != requests.codes.ok:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')
            return {}

        response_json = response.json()
        return response_json

    def alerts(self):
        response = self.command("GET", "dell-alarm:alarm-info")

        if response.status_code != requests.codes.ok:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')
            return {}

        response_json = response.json()
        return response_json["dell-alarm:alarm-info"]

    def equipment(self):
        response = self.command("GET", "dell-equipment:system")

        if response.status_code != requests.codes.ok:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')
            return {}

        response_json = response.json()
        return response_json

    def ports(self):
        response = self.command("GET", "dell-port:ports")

        if response.status_code != requests.codes.ok:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')
            return {}

        response_json = response.json()
        return response_json

def getinfo(dcocfg):
    logger.info(f'Getting info from {system} systems')

    # Iterate through each system defined in the configuration
    for instance in dcocfg.instances(system):
        logger.info(f'{system}: getting info from "{instance}"')

        # Get login info
        api_port, username, password, cert_hash = dcocfg.loginInfo(system, instance)

        # Check the certificate hash
        if not fn.valid_certificate_fingerprint(instance, api_port, cert_hash):
            continue

        # Obtain the authentication token
        os10instance = OS10api(instance, api_port, username, password, cert_hash)

        if not os10instance.sysinfo():
            logger.error(f'ERROR: Unable to get token for "{instance}".')
            continue

        # Fetch alerts and save to the specified JSON file
        logger.info(f"{system}/{instance}: Fetching alerts")
        data = os10instance.alerts()
        dcocfg.save_json(data.get("alarm-summary", []), system, instance, "alarm-summary")
        dcocfg.save_json(data.get("event-history", []), system, instance, "event-history")

        # Fetch hardware status
        logger.info(f"{system}/{instance}: Fetching equipment/environment")
        data = os10instance.equipment()
        environment_unit = fn.get_nested(data, ["dell-equipment:system", "environment", "unit"], [])
        thermal_sensor = fn.get_nested(data, ["dell-equipment:system", "environment", "thermal-sensor"], [])
        dcocfg.save_json(data, system, instance, "equipment")

        # Fetch switch port info
        logger.info(f"{system}/{instance}: Fetching port info")
        data = os10instance.ports()
        dcocfg.save_json(data, system, instance, "ports")

if __name__ == "__main__":
    # Load configuration data from the encrypted config file
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), "{system}debug", level=logging.DEBUG)
    getinfo(dcocfg)

