import logging
import requests
from requests.auth import HTTPBasicAuth
import urllib3
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "ECS"

# Configure module logger
logger = fn.get_module_logger(__name__)

# Disable wargnings: InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disable urllib3 from logging their messages
l = logging.getLogger('urllib3')
l.propagate = False


def get_token_ECS(instance, api_port, username, password, cert_hash):
    """
    Retrieve an authentication token from an ECS instance.

    Args:
        instance (str): The hostname or IP address of the ECS instance.
        username (str): The username for authentication.
        password (str): The password for authentication.
        cert_hash (str): Path to the certificate file for SSL validation (not currently used).

    Returns:
        str: The authentication token if successful, otherwise None.
    """

    # Define the API endpoint for login
    endpoint = f'https://{instance}:{api_port}/login'

    # Define headers for the request
    headers = {
        'Accept': 'application/json'  # Indicate that JSON responses are expected
    }

    # Prepare authentication credentials
    auth_credentials = {
        "username": username,
        "password": password
    }

    # Create an HTTPBasicAuth object for the request
    auth_credentials_BasicAuth = HTTPBasicAuth(
        auth_credentials["username"],
        auth_credentials["password"]
    )

    try:
        # Perform a GET request to the login endpoint with basic authentication
        response = requests.get(
            endpoint,
            headers=headers,
            auth=auth_credentials_BasicAuth,
            verify=False  # SSL verification is disabled for this request
        )

        # Check if the response indicates a successful authentication
        if response.status_code == 200:
            access_token = response.headers.get('X-SDS-AUTH-TOKEN')  # Retrieve the token from response headers
            logger.info("INFO: TOKEN generated successfully")
            return access_token  # Return the token
        else:
            logger.error(f"Error: {response.status_code}")  # Log the error status code if authentication fails
    except requests.exceptions.RequestException as e:
            # Handle other exceptions such as connection errores
            logger.error(f'ERROR: Unable to connect to the ECS instance. Details:{e}')


    return None  # Return None if token retrieval is unsuccessful



def ecs_get_alerts(instance, api_port, access_token, cert_hash):
    """
    Retrieve alerts from an ECS instance.

    Args:
        instance (str): The hostname or IP address of the ECS instance.
        access_token (str): The authentication token for accessing the ECS API.
        cert_hash (str): Path to the certificate file for SSL validation (not currently used).

    Returns:
        list: A list of filtered alert entries if successful, otherwise None.
    """

    # Define the API endpoint for alerts
    endpoint = f'https://{instance}:{api_port}/vdc/alerts'

    # Set up request headers with the access token
    headers = {
        "Accept": "application/json",  # Expect JSON responses
        "X-SDS-AUTH-TOKEN": access_token  # Include the authentication token in headers
    }

    # Perform a GET request to the alerts endpoint
    response_data = requests.get(
        endpoint,
        headers=headers,
        verify=False  # SSL verification is disabled for this request
    )

    # Handle non-successful responses
    if response_data.status_code != 200:
        logger.error(f'ERROR: Failed to access {endpoint}')
        logger.error(f"Error: {response_data.status_code}")  # Print HTTP status code
        logger.error(response_data.text)  # Print detailed error message from the response
        return None

    # Parse the JSON response if the request is successful
    response_data_json = response_data.json()

    # Define the fields to filter from the alert data
    fields = [
        "severity",
        "timestamp",
        "namespace",
        "description",
        "symptomCode",
        "acknowledged",
        "type"
    ]

    # Retrieve alert entries from the response and filter the relevant fields
    # The structure can be {"alerts": {"alert": [...]}} or just {"alert": [...]}
    content_entries = response_data_json.get('alert')
    if content_entries is None:
        content_entries = response_data_json.get('alerts', {}).get('alert', [])

    filtered_results = fn.filter_entries(content_entries, fields)  # Apply field filtering

    return filtered_results  # Return the filtered alert entries


def ecs_get_localzone(instance, api_port, access_token, cert_hash):
    """
    Retrieve information about the local zone from an ECS instance.

    Args:
        instance (str): The hostname or IP address of the ECS instance.
        access_token (str): The authentication token for accessing the ECS API.
        cert_hash (str): Path to the certificate file for SSL validation (not currently used).

    Returns:
        list: A list of filtered and processed local zone entries if successful, otherwise None.
    """

    # Define the API endpoint for the local zone
    endpoint = f'https://{instance}:{api_port}/dashboard/zones/localzone'

    # Set up request headers with the access token
    headers = {
        "Accept": "application/json",  # Expect JSON responses
        "X-SDS-AUTH-TOKEN": access_token  # Include the authentication token in headers
    }

    # Perform a GET request to retrieve local zone data
    response_data = requests.get(
        endpoint,
        headers=headers,
        verify=False  # SSL verification is disabled for this request
    )

    # Handle non-successful responses
    if response_data.status_code != 200:
        logger.error(f'ERROR: Failed to access {endpoint}')
        logger.error(f"Error: {response_data.status_code}")  # Print HTTP status code
        logger.error(response_data.text)  # Print detailed error message from the response
        return None

    # Parse the JSON response if the request is successful
    response_data_json = response_data.json()

    # Define the fields to filter from the local zone data
    fields = [
        "id", "name", "numNodes", "numGoodNodes", "numBadNodes",
        "numMaintenanceNodes", "numDisks", "numGoodDisks", "numBadDisks",
        "numMaintenanceDisks", "alertsNumUnackCritical", "alertsNumUnackError",
        "alertsNumUnackInfo", "alertsNumUnackWarning", "diskSpaceTotalCurrent",
        "diskSpaceFreeCurrent", "diskSpaceAllocatedCurrent",
        "diskSpaceAllocatedUserDataCurrent", "diskSpaceAllocatedGeoCacheCurrent",
        "diskSpaceAllocatedLocalProtectionCurrent", "diskSpaceAllocatedSystemMetadataCurrent",
        "diskSpaceAllocatedGeoCopyCurrent"
    ]

    # Filter the relevant fields from the response data
    content_entries = [response_data_json]
    filtered_results = fn.filter_entries(content_entries, fields)

    # Process the filtered results to extract detailed metrics (Count, Space, and Capacity)
    for entry in filtered_results:
        # Extract 'Count' from alert fields
        for alert_field in ['alertsNumUnackCritical', 'alertsNumUnackError',
                            'alertsNumUnackInfo', 'alertsNumUnackWarning']:
            if entry[alert_field] and len(entry[alert_field]) > 0:
                entry[f"{alert_field}.Count"] = entry[alert_field][0]['Count']
                del entry[alert_field]  # Remove original field after processing

        # Extract 'Space' from disk space fields
        for alert_field in ['diskSpaceTotalCurrent', 'diskSpaceFreeCurrent',
                            'diskSpaceAllocatedCurrent']:
            if entry[alert_field] and len(entry[alert_field]) > 0:
                entry[f"{alert_field}.Space"] = entry[alert_field][0]['Space']
                del entry[alert_field]  # Remove original field after processing

        # Extract 'Capacity' from specific disk space allocation fields
        for alert_field in ['diskSpaceAllocatedUserDataCurrent', 'diskSpaceAllocatedGeoCacheCurrent',
                            'diskSpaceAllocatedLocalProtectionCurrent', 'diskSpaceAllocatedSystemMetadataCurrent',
                            'diskSpaceAllocatedGeoCopyCurrent']:
            if entry[alert_field] and len(entry[alert_field]) > 0:
                entry[f"{alert_field}.Capacity"] = entry[alert_field][0]['Capacity']
                del entry[alert_field]  # Remove original field after processing

    return filtered_results  # Return the processed and filtered local zone data


def getinfo(dcocfg):
    """
    Main function to process data from systems specified in the configuration file.
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

        access_token = get_token_ECS(instance, api_port, username, password, cert_hash)

        if not access_token:
            logger.error(f'Unable to connect {system}/{instance}')
            continue

        # Fetch active alerts from the ECS instance and save it to a JSON file
        logger.info(f"{system}/{instance}: fetching active alerts")
        data = ecs_get_alerts(instance, api_port, access_token, cert_hash)
        dcocfg.save_json(data, system, instance, "alerts")

        # Fetch policies jobs and save to the specified JSON file

        # Fetch local zone information from the ECS instance and save it to a JSON file
        logger.info(f"{system}/{instance}: fetching info of Localzone")
        data = ecs_get_localzone(instance, api_port, access_token, cert_hash)
        dcocfg.save_json(data, system, instance, "localzoneInfo")

if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    getinfo(dcocfg)