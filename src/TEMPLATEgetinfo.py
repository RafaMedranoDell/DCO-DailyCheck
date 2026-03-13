import json
import logging
import requests
import urllib3
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "product"

# Configure module logger
logger = fn.get_module_logger(__name__)

# Disable wargnings: InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disable urllib3 from logging their messages
l = logging.getLogger('urllib3')
l.propagate = False

class PRODUCTapi():
    def __init__(self, instance, api_port, username, password, cert_hash):
        self.instance = instance
        self.base_url = f'https://{instance}:{api_port}'
        self.access_token = None
        self.refresh_token = None

        self.session = requests.Session()
        self.session.headers.update({'content-type': 'application/json'})
        # Avoid SSL certificate validation
        self.session.verify = False

        # Prepare the data for authentication (username and decrypted password)
        auth_data = { "username": username, "password": password }

        # Send POST request to the login API
        response = self.command("POST", 'auth/url', data=json.dumps(auth_data))

        # Check if the request was successful
        if response.status_code in (requests.codes.created, requests.codes.ok):
            response_json = response.json()  # Parse the JSON response
            self.access_token = response_json.get('accessToken')  # Extract access token
            self.session.headers.update({'X-CR-AUTH-TOKEN': response_json.get('accessToken')})
        else:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')

    def log(self, level, msg):
        logger.log(level, f'{system}/{self.instance}: {msg}')

    def connected(self):
        return (self.access_token != None)

    def command(self, method, url, **kwargs):
        full_url = '/'.join((self.base_url, url.strip('/')))
        self.log(logging.DEBUG, f'{method} {full_url}')
        response = self.session.request(method, full_url, **kwargs)
        self.log(logging.DEBUG, f'status_code: {response.status_code}')
        return response

    def get_alerts(self):
        """
        Fetch active alerts from a Cyber Recovery instance.

        Fetches and filters health-related issues including their categories,
        severity levels, and impact on system health score.

        Returns:
        - list: A list of filtered alerts with relevant fields, or an empty list if no alerts are found or on error.
        """

        response = self.command("GET", "v8/notifications/alerts")
        # Check if the request was successful (status code 200)
        # Check if the request was successful (status code 200)
        if response_data.status_code != requests.codes.ok:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')
            return []

        return response_data.json()  # Parse the response as JSON
        # Return filtered alert list with the relevant fields
        fields = [
            "field1",
            "field2",
            "field3",
            "field4",
        ]
        return fn.filter_entries(response_data_json.get('items', []), fields)


def getinfo(dcocfg, **kwargs):
    """

    """
    hours_ago = kwargs.get('hours_ago', 24)
    logger.info(f'Getting info from {system} systems')

    # Process each instance in the system
    for instance in dcocfg.instances(system):
        logger.info(f'{system}: getting info from "{instance}"')

        # Get login info
        api_port, username, password, cert_hash = dcocfg.loginInfo(system, instance)

        # Check the certificate hash
        if not fn.valid_certificate_fingerprint(instance, api_port, cert_hash):
            continue

        # Obtain the authentication token
        ProductAPI = ProductAPIclass(instance, api_port, username, password, cert_hash)

        if not ProductAPI.connected():
            logger.error(f'Unable to get token for "{instance}".')
            continue

        # Fetch alerts and save to the specified JSON file
        logger.info(f"{system}/{instance}: fecching alerts")
        data = ProductAPI.alerts()
        if data:
            fields = [
                "field1",
                "field2",
                "field3"
            ]
            # Filter fields and data by date
            data = fn.filter_entries(data.get('items', []), fields)
            dcocfg.save_json(data, system, instance, "data1")

if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    getinfo(dcocfg)

