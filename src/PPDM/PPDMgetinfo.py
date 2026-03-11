import json
import logging
import requests
import urllib3
import warnings
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime, timedelta
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "PPDM"

# Configure module logger
logger = fn.get_module_logger(__name__)


def get_current_time():
    """
    Gets the current UTC time in ISO 8601 format.

    Returns:
        str: Current UTC time formatted as 'YYYY-MM-DDTHH:MM:SSZ'
    """
    # Get the current UTC time and format it as a string
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def get_hours_ago(hours):
    """
    Calculates a timestamp from a specified number of hours in the past.

    Args:
        hours (int): Number of hours to subtract from current time

    Returns:
        str: Past UTC time formatted as 'YYYY-MM-DDTHH:MM:SSZ'
    """
    # Get the current UTC time
    now = datetime.utcnow()

    # Subtract the specified number of hours to get the time in the past
    time_ago = now - timedelta(hours=hours)

    # Return the calculated time formatted as a string
    return time_ago.strftime("%Y-%m-%dT%H:%M:%SZ")



def get_filtered_results(url, headers, params, fields, cert_file):
    """
    Retrieves and filters paginated results from a PPDM API endpoint.

    Handles pagination automatically by fetching all available pages and
    filtering the results based on specified fields.

    Args:
        url (str): Base API endpoint URL
        headers (dict): Request headers including authentication
        params (dict): Query parameters for filtering results
        fields (list): List of field names to extract from each result
        cert_file (str): Path to SSL certificate file for verification

    Returns:
        list: Filtered results from all pages containing only specified fields
    """
    all_filtered_results = []  # Initialize list to store all filtered results
    page = 1  # Start with the first page
    total_pages = None  # Initialize the total pages variable

    # Loop through pages while there are still pages to fetch
    while total_pages is None or page <= total_pages:
        # Fetch data from the API endpoint for the current page
        response_data = requests.get(f"{url}?page={page}", headers=headers, params=params, verify=cert_file)
        response_data_json = response_data.json()  # Parse the response as JSON

        # Check if the request was successful (status code 200)
        if response_data.status_code != 200:
            logger.error(f"{response_data.status_code}")
            logger.error(response_data.text)  # Print error details
            break

        # Set the total number of pages after the first successful request
        if total_pages is None:
            total_pages = response_data_json['page']['totalPages']
            logger.info(f'TOTAL PAGES = {total_pages}')

        # Retrieve the content entries from the JSON response
        content_entries = response_data_json.get('content', [])

        # Filter the content entries based on the specified fields
        filtered_results = fn.filter_entries(content_entries, fields)

        # Add the filtered results to the list of all results
        all_filtered_results.extend(filtered_results)

        page += 1  # Increment the page number for the next iteration

    return all_filtered_results



def get_token_PPDM(instance, api_port, username, password, cert_file):
    """
    Authenticates with a PPDM system and retrieves access tokens.

    Uses the provided credentials to obtain both access and refresh tokens
    through the PPDM authentication API.

    Args:
        instance (str): PPDM hostname or IP address
        username (str): Authentication username
        encrypted_password (str): Encrypted password (will be decrypted before use)
        cert_file (str): Path to SSL certificate file

    Returns:
        tuple[str | None, str | None]: Tuple containing (access_token, refresh_token)
            Returns (None, None) if authentication fails
    """

    url = f'https://{instance}:{api_port}/api/v2/login'  # URL for the login API endpoint
    headers = {
        'Content-Type': 'application/json'  # Set content type as JSON for the POST request
    }

    # Prepare the data for authentication (username and decrypted password)
    data = {
        "username": username,
        "password": password
    }

    # Send POST request to the login API
    response = requests.post(url, headers=headers, data=json.dumps(data), verify=cert_file)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        response_json = response.json()  # Parse the JSON response
        access_token = response_json.get('access_token')  # Extract access token
        refresh_token = response_json.get('refresh_token')  # Extract refresh token
        return access_token, refresh_token
    elif response.status_code == 423:
        logger.error(f"{response.status_code}")  # Print error if authentication fails
        logger.error("Account is locked due to multiple unsucessfull login attempts. Please try again in 5 minutes or contact your administrator")
    elif response.status_code == 401:
        logger.error(f"{response.status_code}")  # Print error if authentication fails
        logger.error("Unauthorized login request. Check that the login credentials are correct.")
    else:
        logger.error(f"{response.status_code}")  # Print error if authentication fails
    return None, None  # Return None if the authentication fails



def get_health_issues(instance, api_port, access_token, cert_file):
    """
    Retrieves system health issues from a PPDM instance.

    Fetches and filters health-related issues including their categories,
    severity levels, and impact on system health score.

    Args:
        instance (str): PPDM hostname or IP address
        access_token (str): Valid authentication token
        cert_file (str): Path to SSL certificate file

    Returns:
        list[dict]: Filtered health issues with relevant details
    """

    url = f'https://{instance}:{api_port}/api/v2/system-health-issues'  # URL for the health issues API endpoint
    headers = {
        'Authorization': access_token  # Include the access token in the header for authentication
    }
    params = {}  # No additional parameters needed for the request
    fields = [
        "healthCategory",
        "severity",
        "scoreDeduction",
        "componentType",
        "componentName",
        "messageID",
        "detailedDescription",
        "responseAction"
    ]
    return get_filtered_results(url, headers, params, fields, cert_file)  # Call the helper function to get filtered results



def get_job_group_activities(instance, api_port, access_token, cert_file, today, time_ago):
    """
    Retrieves job group activities from a PPDM instance within a specified time range.

    Fetches activities of type "JOB_GROUP" that occurred between the specified
    time range, including their status and timing information.

    Args:
        instance (str): PPDM hostname or IP address
        access_token (str): Valid authentication token
        cert_file (str): Path to SSL certificate file
        today (str): End time in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        time_ago (str): Start time in ISO format (YYYY-MM-DDTHH:MM:SSZ)

    Returns:
        list[dict]: Filtered job group activities within the specified time range
    """

    url = f'https://{instance}:{api_port}/api/v2/activities'  # URL for the activities API endpoint

    headers = {
        'Authorization': access_token  # Include the access token in the header for authentication
    }

    filter_expression = (
        f'createTime ge "{time_ago}" and createTime lt "{today}" and classType eq "JOB_GROUP"'
    )  # Filtering activities by create time and class type (JOB_GROUP)

    params = {
        'filter': filter_expression  # Adding filter parameters to the API request
    }

    fields = [
        "category",
        "classType",  # The class type of the activity (JOB_GROUP)
        "result.status",
        "createTime",  # The creation time of the activity
        "endTime"  # The end time of the activity
    ]
    return get_filtered_results(url, headers, params, fields, cert_file)  # Get filtered results using the helper function



def get_activities_not_ok(instance, api_port, access_token, cert_file, today, time_ago):
    """
    Retrieves failed or problematic activities from a PPDM instance.

    Fetches activities that meet the following criteria:
    - Status is not "OK"
    - Has an associated protection policy
    - Contains error details, host information, or asset information
    - Occurred within the specified time range

    Args:
        instance (str): PPDM hostname or IP address
        access_token (str): Valid authentication token
        cert_file (str): Path to SSL certificate file
        today (str): End time in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        time_ago (str): Start time in ISO format (YYYY-MM-DDTHH:MM:SSZ)

    Returns:
        list[dict]: Filtered problematic activities with detailed error information
    """

    url = f'https://{instance}:{api_port}/api/v2/activities'  # URL for the activities API endpoint
    headers = {
        'Authorization': access_token  # Include the access token in the header for authentication
    }
    filter_expression = (
        f'createTime ge "{time_ago}" and createTime lt "{today}" '  # Filter activities by creation time range
        f'and result.status ne "OK" '  # Exclude activities where status is "OK"
        f'and protectionPolicy.name ne null '  # Ensure protection policy name is not null
        f'and (result.error.code ne null or host.name ne null or asset.name ne null)'  # Ensure certain error or asset details are present
    )
    params = {
        'filter': filter_expression  # Adding filter parameters to the API request
    }
    fields = [
        "category",
        "classType",
        "activityInitiatedType",
        "result.status",
        "result.error.code",
        "result.error.detailedDescription",
        "result.error.extendedReason",
        "result.error.reason",
        "result.error.remediation",
        "asset.name",
        "asset.type",
        "host.name",
        "host.type",
        "inventorySource.type",
        "protectionPolicy.name",
        "protectionPolicy.type",
        "createTime",
        "endTime"
    ]
    return get_filtered_results(url, headers, params, fields, cert_file)  # Get filtered results using the helper function



def get_storage_systems(instance, api_port, access_token, cert_file):
    """
    Retrieves storage system information from a PPDM instance.

    Fetches details about all storage systems including their type,
    name, operational readiness, and additional configuration details.

    Args:
        instance (str): PPDM hostname or IP address
        access_token (str): Valid authentication token
        cert_file (str): Path to SSL certificate file

    Returns:
        list[dict]: Storage systems information including readiness status
    """

    url = f'https://{instance}:{api_port}/api/v2/storage-systems'  # URL for the storage systems API endpoint
    headers = {
        'Authorization': access_token  # Include the access token in the header for authentication
    }
    params = {}  # No specific parameters are set for this API call
    fields = [
        "type",  # The type of the storage system
        "name",  # The name of the storage system
        "readiness",  # The readiness status of the storage system
        "details"  # Additional details about the storage system
    ]

    return get_filtered_results(url, headers, params, fields, cert_file)  # Get filtered results using the helper function



def getinfo(dcocfg, hours_ago=24):
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

        # Check the certificate hash (Security Pinning)
        if not fn.valid_certificate_fingerprint(instance, api_port, cert_hash):
            continue

        # Obtain the authentication token and fetch data
        # We use a context manager to silence the InsecureRequestWarning only for PPDM calls
        # This keeps the logs clean without a global silence, as we've already verified the hash.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsecureRequestWarning)
            
            access_token, _ = get_token_PPDM(instance, api_port, username, password, False)

            if not access_token:
                logger.error(f'Unable to get token for "{instance}".')
                continue

            # Get the current time and the time range for filtering activities
            today = get_current_time()
            time_ago = get_hours_ago(hours_ago)

            # Fetch health issues and save to the specified JSON file
            logger.info("Fetching health issues...")
            data = get_health_issues(instance, api_port, access_token, False)
            dcocfg.save_json(data, system, instance, "systemHealthIssues")

            # Fetch job group activities and save to the specified JSON file
            logger.info("Fetching job group activities...")
            data = get_job_group_activities(instance, api_port, access_token, False, today, time_ago)
            dcocfg.save_json(data, system, instance, "jobGroupActivitiesSummary")

            # Fetch activities that are not OK and save to the specified JSON file
            logger.info("Fetching activities that are not OK...")
            data = get_activities_not_ok(instance, api_port, access_token, False, today, time_ago)
            dcocfg.save_json(data, system, instance, "activitiesNotOK")

            # Fetch storage systems info and save to the specified JSON file
            logger.info("Fetching storage systems...")
            data = get_storage_systems(instance, api_port, access_token, False)
            dcocfg.save_json(data, system, instance, "storageSystems")


if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    getinfo(dcocfg)
