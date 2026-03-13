import logging
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
import urllib3
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "IDRAC"

# Configure module logger
logger = fn.get_module_logger(__name__)

# Disable wargnings: InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disable urllib3 from logging their messages
l = logging.getLogger('urllib3')
l.propagate = False


class iDRACapi():
    def __init__(self, instance, api_port, username, password, cert_hash):
        self.instance = instance
        self.username = username
        self.password = password
        self.base_url = f'https://{self.instance}:{api_port}'
        self.endpoint_list = {}
        # Get system id and chassis id
        self.system_id = self.discover_id("Systems")
        self.chassis_id = self.discover_id("Chassis")

    def get_json(self, endpoint):
        full_url = f"{self.base_url}{endpoint}"
        logger.debug(f'GET {full_url}')
        response = requests.get(full_url, verify=False, auth=HTTPBasicAuth(self.username, self.password), timeout=15)
        logger.debug(f'status_code: {response.status_code}')
        response.raise_for_status()
        self.endpoint_list[full_url] = response.json()
        return response.json()

    def recurse_get(self, endpoint):
        # Recursively find "@odata.id" keys that alone in the dictionary and retrieve the info to fill it
        def recurse_odata_id(data):
            nonlocal retrieved_url
            if isinstance(data, dict):
                if len(data.keys()) == 1 and "@odata.id" in data:
                    url = data["@odata.id"]
                    if url not in retrieved_url:
                        retrieved_url.append(url)
                        try:
                            new_data = self.get_json(url)
                            data.update(new_data)
                        except requests.exceptions.RequestException as e:
                            logger.error(f'Error while retrieving {url}: {e}')

                for key in data.keys():
                    # Skip "Links" and "Assembly" keys to avoid recursion loops
                    if key not in ("Links", "Assembly"):
                        recurse_odata_id(data[key])
            elif isinstance(data, list):
                for item in data:
                    recurse_odata_id(item)

        # Avoid recursion urls
        retrieved_url = []
        root_data = self.get_json(endpoint)
        recurse_odata_id(root_data)
        return root_data

    def discover_id(self, resource):
        root = self.get_json("/redfish/v1/")
        url = fn.get_nested(root, [resource, "@odata.id"], f"/redfish/v1/{resource}")
        data = self.get_json(url)
        if data.get("Members"):
            return data["Members"][0]["@odata.id"].split("/")[-1]
        return "System.Embedded.1"

    def get_system(self):
        return self.get_json(f"/redfish/v1/Systems/{self.system_id}")

    def get_chassis(self):
        return self.get_json(f"/redfish/v1/Chassis/{self.chassis_id}")

    def get_thermal(self):
        return self.get_json(f"/redfish/v1/Chassis/{self.chassis_id}/Thermal")

    def get_power(self):
        return self.get_json(f"/redfish/v1/Chassis/{self.chassis_id}/Power")

    def get_log(self):
        return self.recurse_get("/redfish/v1/Managers/iDRAC.Embedded.1/LogServices")

    def get_storage(self):
        return self.recurse_get(f"/redfish/v1/Systems/{self.system_id}/Storage")

    def get_processors(self):
        return self.recurse_get(f"/redfish/v1/Systems/{self.system_id}/Processors")

# La función extract_memory ha sido eliminada

def getinfo(dcocfg, **kwargs):
    logger.info(f'Getting info from {system} systems')

    # Process each instance in the system
    for instance in dcocfg.instances(system):
        logger.info(f'{system}: getting info from "{instance}"')

        # Get login info
        api_port, username, password, cert_hash = dcocfg.loginInfo(system, instance)

        # Check the certificate hash
        if not fn.valid_certificate_fingerprint(instance, api_port, cert_hash):
            continue

        try:
            idrac = iDRACapi(instance, api_port, username, password, cert_hash)

            # PowerState, Status.Health, general info
            logger.info(f"{system}/{instance}: System general and power state")
            data = idrac.get_system()
            dcocfg.save_json(data, system, instance, "system")

            # Chassis status/health
            logger.info(f"{system}/{instance}: Chassis / General status")
            data = idrac.get_chassis()
            dcocfg.save_json(data, system, instance, "chassis")

            # Temperatures, fans
            logger.info(f"{system}/{instance}: Thermal (temperature and fans)")
            data = idrac.get_thermal()
            dcocfg.save_json(data, system, instance, "thermal")

            # PSU, voltages, currents, power consumption
            logger.info(f"{system}/{instance}: Power (PSU and consumption)")
            data = idrac.get_power()
            dcocfg.save_json(data, system, instance, "power")

            logger.info(f"{system}/{instance}: Event logs")
            data = idrac.get_log()
            dcocfg.save_json(data, system, instance, "logs")

            logger.info(f"{system}/{instance}: Storage")
            data = idrac.get_storage()
            dcocfg.save_json(data, system, instance, "storage")

            logger.info(f"{system}/{instance}: Processors")
            data = idrac.get_processors()
            dcocfg.save_json(data, system, instance, "processors")

            # Save endpoint_list for testing (remove on producction)
            dcocfg.save_json(idrac.endpoint_list, system, instance, "endpoints")
        except RequestException as e:
            logger.error(f'{system}/{instance}: error retrieving information.{e}')

if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    getinfo(dcocfg)