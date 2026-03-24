import json
import logging
import requests
import urllib3
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "PPCR"

# Configure module logger
logger = fn.get_module_logger(__name__)

# Disable wargnings: InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disable urllib3 from logging their messages
l = logging.getLogger('urllib3')
l.propagate = False

API_ENDPOINTS = {
    'v7': { # Endpoints for 19.x
        'login': '/v7/login',
        'logout': '/v7/logout/{}'
    },
    'v9': { # Endpoints for 19.21 and 19.22
        'login': '/v9/auth/login',
        'logout': '/v9/auth/logout'
    }
}

class PPCRapi():
    def __init__(self, instance, api_port, username, password, cert_hash):
        self.instance = instance
        self.base_url = f'https://{instance}:{api_port}/cr'
        self._connected = False
        self.api_ver = None
        # Force username to lowercase to handle PPCR 19.22+ case sensitivity
        self.username = username.lower()

        self.session = requests.Session()
        self.session.headers.update({'content-type': 'application/json'})
        # Avoid SSL certificate validation
        self.session.verify = False

        # Prepare the data for authentication (username and decrypted password)
        auth_data = { "username": self.username, "password": password }

        try:
            for api_ver in API_ENDPOINTS:
                auth_endpoint = API_ENDPOINTS[api_ver]['login']
                response = self.command("POST", auth_endpoint, data=json.dumps(auth_data), timeout=5)
                if response.status_code == requests.codes.not_found:
                    # If not found try other auth login endpoint
                    continue
                elif response.status_code == requests.codes.ok:
                    response_json = response.json()  # Parse the JSON response

                    if api_ver == 'v7':
                        auth_token = response_json.get('accessToken')
                    else: # api_ver == 'v9'
                        auth_token = response_json.get('access_token')
                    self.session.headers.update({'X-CR-AUTH-TOKEN': auth_token})
                    self.api_ver = api_ver
                    self._connected = True
                    break
                elif response.status_code == requests.codes.unauthorized:
                    self.log(logging.ERROR, f'Error 401: Authentication failed for user "{username}". Check credentials or if the account is locked (Error: {response.text})')
                else:
                    self.log(logging.ERROR, f'{response.status_code}:{response.text}')
        except requests.exceptions.ConnectionError as e:
            self.log(logging.ERROR, f'Unable to connect: {e}')
        except requests.exceptions.ConnectTimeout as e:
            self.log(logging.ERROR, f'Connection timeout: {e}')

    def __del__(self):
        self.close()

    def close(self):
        if self._connected:
            logout_endpoint = API_ENDPOINTS[self.api_ver]["logout"]
            # API v7 needs the username to logout
            if self.api_ver == 'v7':
                logout_endpoint = logout_endpoint.format(self.username)
            self.command("POST", logout_endpoint)
            self._connected = False
            self.log(logging.DEBUG, "Connection closed.")

    def log(self, level, msg):
        logger.log(level, f'{system}/{self.instance}: {msg}')

    def connected(self):
        return self._connected

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
        if response.status_code != requests.codes.ok:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')
            return {}

        return response.json()  # Parse the response as JSON

    def get_jobs(self):
        """
        Fetch active alerts from a Cyber Recovery instance.

        Fetches and filters health-related issues including their categories,
        severity levels, and impact on system health score.

        Returns:
        - list: A list of filtered alerts with relevant fields, or an empty list if no alerts are found or on error.
        """
        response = self.command("GET", "v8/policies/jobs")

        # Check if the request was successful (status code 200)
        if response.status_code != requests.codes.ok:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')
            return {}

        return response.json()  # Parse the response as JSON

    def get_policies(self):
        """
        Fetch active alerts from a Cyber Recovery instance.

        Fetches and filters health-related issues including their categories,
        severity levels, and impact on system health score.

        Returns:
        - list: A list of filtered alerts with relevant fields, or an empty list if no alerts are found or on error.
        """
        response = self.command("GET", "v8/policies")

        # Check if the request was successful (status code 200)
        if response.status_code != requests.codes.ok:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')
            return {}

        return response.json()  # Parse the response as JSON

    def get_reports(self):
        """
        Fetch the reports

        Returns:
        - dict: response with the reports
        """
        response = self.command("GET", "v8/reporting/reports")

        # Check if the request was successful (status code 200)
        if response.status_code != requests.codes.ok:
            self.log(logging.ERROR, f'{response.status_code}:{response.text}')
            return {}

        return response.json()

def getinfo(dcocfg, **kwargs):
    """
    Main execution function for the PPDM monitoring script.

    Processes each configured PPDM instance to collect and store:
    - System health issues
    - Job group activities
    - Failed/problematic activities
    - Storage system information

    The collected data is saved to JSON files in the configured output directory.
    """

    # Process each instance in the system
    logger.info(f'Getting info from {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'{system}/{instance}: getting info')

        # Get login info
        api_port, username, password, cert_hash = dcocfg.loginInfo(system, instance)

        # Check the certificate hash
        if not fn.valid_certificate_fingerprint(instance, api_port, cert_hash):
            continue

        # Connect to the PPCR instance
        ppcr = PPCRapi(instance, api_port, username, password, cert_hash)

        if not ppcr.connected():
            continue

        # Fetch alerts and save to the specified JSON file
        logger.info(f"{system}/{instance}: fetching alerts")
        data = ppcr.get_alerts()

        fields = [
            "category",
            "createdByService",
            "creationDate",
            "acknowledged",
            "severity",
            "summary",
            "description",
            "remedy"
        ]
        filtered_data = fn.filter_entries(data.get('items', []), fields) if data.get("count", 0) else []
        dcocfg.save_json(filtered_data, system, instance, "alerts")

        # Fetch policies and save to the specified JSON file
        logger.info(f"{system}/{instance}: fetching policies")
        data = ppcr.get_policies()
        dcocfg.save_json(data.get('items', []), system, instance, "policies")

        # Fetch policies jobs and save to the specified JSON file
        logger.info(f"{system}/{instance}: fetching policies jobs")
        data = ppcr.get_jobs()

        fields = [
            "id",
            "jobName",
            "jobType",
            "policyName",
            "progress",
            "status",
            "statusDetail",
            "startTime",
            "elapsedTime",
            "endTime",
            "tasks"
        ]
        filtered_data = fn.filter_entries(data.get('items', []), fields) if data.get("count", 0) else []
        dcocfg.save_json(filtered_data, system, instance, "policies_jobs")

        # Fetch CyberSense license utilizatión reports
        logger.info(f"{system}/{instance}: fetching CS reports")
        data = ppcr.get_reports()

        # Filter CS license utilization reports
        reports = [
            rpt for rpt in data.get('items', [])
            if rpt.get("status") == "Success"
            and fn.get_nested(rpt, ['config', 'family']) == "Capacity & Utilization"
            and "cs_license_utilization" in fn.get_nested(rpt, ['config', 'components'], [])
        ]
        # Get the most recent report
        last_report = max(reports, key=lambda rpt: int(rpt["creationDate"]), default={})

        dcocfg.save_json(last_report, system, instance, "cs_report")

        ppcr.close()

if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    getinfo(dcocfg)
