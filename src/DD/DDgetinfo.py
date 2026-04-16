import json
import logging
import requests
import urllib3
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "DD"

# Configure module logger
logger = fn.get_module_logger(__name__)

# Disable wargnings: InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disable urllib3 from logging their messages
l = logging.getLogger('urllib3')
l.propagate = False

def get_token_DD(instance, api_port, username, password, cert_hash):
    """
    Obtain the authentication token from the Data Domain instance.

    Parameters:
    - instance (str): The hostname or IP address of the Data Domain instance.
    - username (str): The username for authentication.
    - password (str): The password for authentication.
    - cert_hash (str): Path to the certificate file for secure connection (unused in the current function).

    Returns:
    - str: The access token if authentication is successful, or None if the authentication fails.
    """

    # Define the URL for the authentication API endpoint on the Data Domain instance
    url = f'https://{instance}:{api_port}/rest/v1.0/auth'
    headers = {
        'Content-Type': 'application/json'
    }

    # Prepare the data to be sent in the POST request
    data = {
        "username": username,
        "password": password
    }

    # Send a POST request to the authentication endpoint with the provided data
    response = requests.post(url, headers=headers, data=json.dumps(data), verify=False)

    # Check if the authentication was successful (HTTP status code 201)
    if response.status_code == 201:
        access_token = response.headers.get('X-DD-AUTH-TOKEN')  # Retrieve the token from the response headers
        return access_token  # Return the access token if successful
    else:
        logger.error(f'{response.status_code}')  # Print an error message if the authentication fails
    return None  # Return None if the token could not be obtained



def dd_get_alerts(instance, api_port, access_token, cert_hash):
    """
    Fetch active alerts from a Data Domain instance.

    Parameters:
    - instance (str): The hostname or IP address of the Data Domain instance.
    - access_token (str): The authentication token used for accessing the Data Domain API.
    - cert_hash (str): Path to the certificate file for secure connection (unused in the current function).

    Returns:
    - list: A list of filtered alerts with relevant fields, or an empty list if no alerts are found or on error.
    """

    # Define the URL for the Data Domain API endpoint to fetch alerts
    url = f'https://{instance}:{api_port}/rest/v2/dd-systems/0/alerts'
    headers = {
        "X-DD-AUTH-TOKEN": access_token  # Include the authentication token in the request headers
    }

    # Define the filter expression and the page size for the alerts to retrieve
    filter_expression = "status = active"  # Filter to only get active alerts
    page_size = "50"  # Retrieve 50 alerts per page

    # Prepare the query parameters for the request
    params = {
        'filter': filter_expression,
        'size': page_size  # Limit the number of results to 50
    }

    # Send a GET request to fetch the alerts
    response_data = requests.get(url, headers=headers, params=params, verify=False)
    response_data_json = response_data.json()  # Parse the response JSON

    # Check if the request was successful
    if response_data.status_code != requests.codes.ok:
        logger.error(f'{response_data.status_code}')  # Print error if request fails
        logger.error(response_data.text)  # Print additional error details from the response

    # Define the fields to be filtered from the alert data
    fields = [
        "id",
        "alert_id",
        "event_id",
        "status",
        "class",
        "severity",
        "name",
        "alert_gen_epoch",
        "description",
        "msg",
        "additional_info",
        "clear_additional_info",
        "action"
    ]

    # Extract and filter the alert list from the response JSON
    content_entries = response_data_json.get('alert_list', [])  # Get alerts or an empty list if no alerts found
    filtered_results = fn.filter_entries(content_entries, fields)  # Filter the relevant fields using a helper function

    return filtered_results  # Return the filtered list of alerts



def dd_get_services(instance, api_port, access_token, cert_hash):
    """
    Fetch specified services from a Data Domain instance.

    Parameters:
    - instance (str): The hostname or IP address of the Data Domain instance.
    - access_token (str): The authentication token used for accessing the Data Domain API.
    - cert_hash (str): Path to the certificate file for secure connection (unused in the current function).

    Returns:
    - list: A list of filtered services with their names and status, or an empty list if no services are found or on error.
    """

    # Define the URL for the Data Domain API endpoint to fetch services
    url = f'https://{instance}:{api_port}/rest/v1.0/dd-systems/0/services'

    headers = {
        "X-DD-AUTH-TOKEN": access_token  # Include the authentication token in the request headers
    }

    # Define the filter expression to retrieve specific services
    filter_expression = "name = filesys|replication|encryption|ddboost|cifs|nfs|ntp|snmp|iscsi|asup|cloud"
    # List of possible services that can be filtered (e.g., ntp, snmp, license-server, iscsi, log, asup, nfs, etc.)

    sort = "name"  # Sort the services by their name
    params = {
        "filter": filter_expression,  # Apply the filter to select specific services
        "sort": sort  # Sort the results by "name"
    }

    # Send a GET request to fetch the services
    response_data = requests.get(url, headers=headers, params=params, verify=False)

    # Check if the request was successful
    if response_data.status_code != requests.codes.ok:
        logger.error(f'{response_data.status_code}')  # Print error if request fails
        logger.error(response_data.text)  # Print additional error details from the response

    # Parse the response JSON to extract services data
    response_data_json = response_data.json()

    # Define the fields to be filtered from the services data
    fields = [
        "name",
        "status"
    ]

    # Extract and filter the services list from the response JSON
    content_entries = response_data_json.get('services', [])  # Get services or an empty list if no services found
    filtered_results = fn.filter_entries(content_entries, fields)  # Filter the relevant fields using a helper function

    return filtered_results  # Return the filtered list of services



def dd_get_replicas(instance, api_port, access_token, cert_hash):
    """
    Fetch MTree replication information from a Data Domain instance.

    Parameters:
    - instance (str): The hostname or IP address of the Data Domain instance.
    - access_token (str): The authentication token used for accessing the Data Domain API.
    - cert_hash (str): Path to the certificate file for secure connection (unused in the current function).

    Returns:
    - list: A list of filtered replication entries with relevant fields, or an empty list if no replications are found or on error.
    """

    # Define the URL for the Data Domain API endpoint to fetch MTree replications
    url = f'https://{instance}:{api_port}/api/v1/dd-systems/0/mtree-replications'

    headers = {
        "X-DD-AUTH-TOKEN": access_token  # Include the authentication token in the request headers
    }

    # Define parameters to increase the result limit (Data Domain default is typically 20)
    params = {
        'size': '100',
        'page': '0'
    }

    # Send a GET request to fetch replication data
    response_data = requests.get(url, headers=headers, params=params, verify=False)

    # Check if the request was successful
    if response_data.status_code != requests.codes.ok:
        logger.error(f'{response_data.status_code}')  # Print error if request fails
        logger.error(response_data.text)  # Print additional error details from the response

    # Parse the response JSON to extract replication data
    response_data_json = response_data.json()

    # Define the fields to be filtered from the replication data
    fields = [
        "id",
        "mode",
        # "state",
        # "enabled",
        # "needResync",
        # "connected",
        # "connHost",
        # "sourceHost",
        # "destinationHost",
        "sourceMtreePath",
        # "destinationMtreePath",
        "connEpoch",
        "syncEpoch",
        # "encryption",
        # "propagateretentionLock",
        # "maxReplStreams",
        # "errorMessage"
    ]

    # Extract and filter the replication context entries from the response JSON
    content_entries = response_data_json.get('contexts', [])  # Get replication contexts or an empty list if not found
    filtered_results = fn.filter_entries(content_entries, fields)  # Filter the relevant fields using a helper function

    return filtered_results  # Return the filtered list of replication entries



def dd_get_tiers(instance, api_port, access_token, cert_hash):
    """
    Fetch tier space information from a Data Domain system.

    Parameters:
    - instance (str): The hostname or IP address of the Data Domain instance.
    - access_token (str): The authentication token used for accessing the Data Domain API.
    - cert_hash (str): Path to the certificate file for secure connection (unused in the current function).

    Returns:
    - list: A list of filtered space information for system tiers, or an empty list if no space information is found or on error.
    """

    # Define the URL for the Data Domain API endpoint to fetch file system space information
    url = f'https://{instance}:{api_port}/rest/v1.0/dd-systems/0/file-systems'

    headers = {
        "X-DD-AUTH-TOKEN": access_token  # Include the authentication token in the request headers
    }

    # Send a GET request to fetch space information for file systems
    response_data = requests.get(url, headers=headers, verify=False)

    # Check if the request was successful
    if response_data.status_code != requests.codes.ok:
        logger.error(f'{response_data.status_code}')  # Print error if request fails
        logger.error(response_data.text)  # Print additional error details from the response

    # Parse the response JSON to extract file system space information
    response_data_json = response_data.json()

    # Extract detailed space info for the file systems from the response JSON
    fs_detailed_space_info = response_data_json.get('fs_detailed_space_info', {})

    # Extract the system tier space information (may be empty if no tiers are found)
    system_tier_space_info = fs_detailed_space_info.get('system_tier_space_info', [])

    # Define the fields to be filtered from the system tier space information
    fields = [
        "tier",
        "dc_total",
        "dc_used",
        "dc_avail"
    ]

    # Filter the system tier space info using the helper function 'filter_entries'
    filtered_results = fn.filter_entries(system_tier_space_info, fields)

    return filtered_results  # Return the filtered space information for the tiers



def dd_get_filesys(instance, api_port, access_token, cert_hash):
    """
    Fetch file system information from a Data Domain instance.

    Parameters:
    - instance (str): The hostname or IP address of the Data Domain instance.
    - access_token (str): The authentication token used for accessing the Data Domain API.
    - cert_hash (str): Path to the certificate file for secure connection (unused in the current function).

    Returns:
    - dict: A dictionary with the file system information, or an empty dictionary on error.
    """

    # Define the URL for the Data Domain API endpoint to fetch file system info
    url = f'https://{instance}:{api_port}/rest/v1.0/dd-systems/0/file-systems'

    headers = {
        "X-DD-AUTH-TOKEN": access_token  # Include the authentication token in the request headers
    }

    # Send a GET request to fetch file system data
    response_data = requests.get(url, headers=headers, verify=False)

    # Check if the request was successful
    if response_data.status_code != requests.codes.ok:
        logger.error(f'{response_data.status_code}')  # Print error if request fails
        logger.error(response_data.text)  # Print additional error details from the response
        return {}

    # Parse and return the response JSON
    return response_data.json()



def getinfo(dcocfg, **kwargs):
    """
    Main function to retrieve information from a Data Domain system using API calls.
    The function reads configuration data, authenticates with the system, and retrieves
    various system details such as alerts, services, replicas, and capacity information.
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

        # Get the access token by calling the get_token_DD function
        access_token = get_token_DD(instance, api_port, username, password, cert_hash)

        # If no token is obtained, skip the instance and move to the next one
        if not access_token:
            logger.error(f"ERROR: Unable to get token for {instance}.")
            continue

        # Fetch active alerts for the instance
        logger.info("INFO: Fetching active alerts...")
        data = dd_get_alerts(instance, api_port, access_token, cert_hash)
        dcocfg.save_json(data, system, instance, "activeAlerts")

        # Fetch the state of services for the instance
        logger.info("INFO: Fetching state of services...")
        data = dd_get_services(instance, api_port, access_token, cert_hash)
        dcocfg.save_json(data, system, instance, "services")

        # Fetch the state of replicas for the instance
        logger.info("INFO: Fetching state of replicas...")
        data = dd_get_replicas(instance, api_port, access_token, cert_hash)
        dcocfg.save_json(data, system, instance, "replicas")

        # Fetch the capacity info for the instance
        logger.info("INFO: Fetching capacity info...")
        data = dd_get_tiers(instance, api_port, access_token, cert_hash)
        dcocfg.save_json(data, system, instance, "tiers")

        # Fetch the file system info for the instance
        logger.info("INFO: Fetching file system info...")
        data = dd_get_filesys(instance, api_port, access_token, cert_hash)
        dcocfg.save_json(data, system, instance, "filesys")

if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    getinfo(dcocfg)
