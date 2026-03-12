import csv
from datetime import datetime, timedelta
import functools
import glob
import hashlib
import json
import logging
import os
import pandas as pd
import pytz
import tempfile
import time
import socket
import ssl
import webbrowser
import zipfile

def get_module_logger(module_name):
    # Setups a local module logger with the provided module_name
    mod_logger = logging.getLogger(module_name)
    mod_logger.addHandler(logging.NullHandler())
    return mod_logger

# Configure module logger
logger = get_module_logger(__name__)

# Funcion para leer configuracion desde JSON
def load_json_file(json_file):
    with open(json_file, "r") as file:
        return json.load(file)


# Guardar los datos en un archivo JSON
def save_json(data, system, instance, query_name, base_path):
    output_file = os.path.join(base_path, f"{system}-{instance}-{query_name}")
    with open(output_file, "w") as file:
        json.dump(data, file, indent=4)
    logger.error(f'Data saved in: {output_file}')


def save_dataframe_to_csv(df, file_path, header=True):
    """Saves the DataFrame to a CSV file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False, header=header, quoting=csv.QUOTE_ALL, escapechar='\\')

    if os.path.exists(file_path):  # Cambiar 'csv_path' a 'file_path'
        logger.error(f'File saved succesfully: {file_path}')
    else:
        logger.error(f'ERROR: Error saving the file: {file_path}')


def get_value_from_nested_keys(data, keys):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def filter_entries(entries, fields):
    filtered_results = []
    for entry in entries:
        filtered_entry = {}
        for field in fields:
            keys = field.split('.')
            value = get_value_from_nested_keys(entry, keys)
            filtered_entry[field] = value
        filtered_results.append(filtered_entry)
    return filtered_results



def open_html_inBrowser(html_body):
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
        f.write(html_body)
        temp_file_path = f.name

    webbrowser.open(f'file://{temp_file_path}')


def compress_and_delete_files(directory, extension, date):
    # Create the name of the ZIP file with the added extension
    zip_file_name = f'{date}-{extension}.zip'
    # Create the full path of the ZIP file
    zip_file_path = os.path.join(directory, zip_file_name)

    # Create a ZIP file to store the files
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        # Iterate over all files in the specified directory
        for filename in os.listdir(directory):
            # Check if the file hast the desired extension
            if filename.endswith(extension):
                # Get the full path of the file
                file_path = os.path.join(directory, filename)
                # Add the file to the ZIP
                zipf.write(file_path, filename)
                # Delete the original File
                os.remove(file_path)
        logger.error(f'Created compressed file "{zip_file_path}"')
        logger.error(f'Deleted ."{extension}" files in "{directory}"')


def delete_old_files(directory, current_time, days_old):
    current_time = time.time()

    # Calcular el tiempo límite (en segundos)
    time_limit = current_time - (days_old * 86400)  # 86400 segundos en un día

    # Flag to track if any file was deleted
    files_deleted = False

    # Recorrer todos los archivos en el directorio especificado
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        # Verificar si es un archivo y no un directorio
        if os.path.isfile(file_path):
            # Obtener el tiempo de la última modificación del archivo
            file_mod_time = os.path.getmtime(file_path)
            # Si el archivo es más antiguo que el límite de tiempo, eliminarlo
            if file_mod_time < time_limit:
                os.remove(file_path)
                logger.error(f'Delete file "{file_path}"')
                files_deleted = True

    # If no files were deleted, print a message
    if not files_deleted:
        logger.info("No files were deleted")

def mark_files_by_date(path, glob_exp, dt_func, keep_days=30, keep_months=True):
    """
    Marks a list of files for deletion in a given directory based on their associated datetime values.
    The function determines which files should be kept or marked for deletion based on two criteria:
        Files from the last keep_days days.
        The first file of each month (if keep_months is True).

    Parameters:
        path (str): Directory path where the files are located.
        glob_exp (str): Glob expression to match the desired files (e.g., "*.log").
        dt_func (Callable[[str], datetime]): A function that extracts a datetime object from a filename.
        keep_days (int, optional): Number of recent days to retain files. Defaults to 30.
        keep_months (bool, optional): Whether to keep the first file of each month. Defaults to True.

    Returns:
    List[Dict]: A list of dictionaries, each containing:
        'fname': The full path to the file.
        'dt': The datetime associated with the file.
        'delete': A boolean indicating whether the file should be deleted (True) or kept (False).

    Behavior:
        Collects all files matching the glob pattern.
        Extracts the datetime for each file using dt_func.
        Marks files older than keep_days as deletable.
        Identifies the first file of each month and marks it to be kept.
        Returns the annotated list of files.
    """
    file_list = []
    for fname in glob.glob(os.path.join(path, glob_exp)):
        dt = dt_func(fname)
        file_list.append({'fname': fname, 'dt': dt, 'delete': True})
    # Keep 30 last days
    daily_keep_date = datetime.now()+timedelta(days=-keep_days)
    for f_entry in file_list:
        if f_entry['dt'] >= daily_keep_date:
            f_entry['delete'] = False
    # Find the first report of each month
    monthly_first_date = {}
    for f_entry in file_list:
        ym = f_entry['dt'].date().strftime('%Y-%m')
        if ym not in monthly_first_date or monthly_first_date[ym] > f_entry['dt']:
            monthly_first_date[ym] = f_entry['dt']
    if keep_months:
        # Keep the first of each month
        for f_entry in file_list:
            ym = f_entry['dt'].date().strftime('%Y-%m')
            if monthly_first_date[ym] == f_entry['dt']:
                f_entry['delete'] = False
    return sorted(file_list, key=lambda x: x['dt'], reverse=False)

def remove_file(fpath):
    """
    Attempts to remove a file at the given path.
    Logs any exceptions encountered and returns a boolean indicating success.

    Parameters:
        fpath (str): Path to the file to be removed.

    Returns:
        bool: True if the file was successfully deleted, False otherwise.
    """
    try:
        os.remove(fpath)
        logger.debug(f'Deleted {fpath}')
        return True
    except FileNotFoundError as e:
        logger.debug(f'Unable to delete: {fpath}. {e}')
    except OSError as e:
        logger.warning(f'Unable to delete: {fpath}. {e}')
    return False

def setup_logging(log_path, file_prefix, level=logging.DEBUG):
    # Setup the global logging
    logfile = os.path.join(log_path, f"{file_prefix}-DailyCheck.log")
    logging.basicConfig(
        level=level,
        handlers=[
            logging.FileHandler(logfile, encoding='utf-8'),
            logging.StreamHandler()  # Outputs to stderr by default
        ],
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def remove_files(glob_path, glob_exp, dt_func, keep_days=30, keep_months=True):
    marked_list = mark_files_by_date(glob_path, glob_exp, dt_func, keep_days=keep_days, keep_months=keep_months)
    delete_list = [ x['fname'] for x in marked_list if x['delete'] ]
    if delete_list:
        for fname in delete_list:
            # Remove without logging neither reporting errors
            try:
                os.remove(fname)
            except OSError:
                pass

def remove_logs(dcocfg, keep_days=14, keep_months=True):
    def log2dt(full_name):
        # Retrieve the date/time from the zipfile name
        fpath, fname = os.path.split(full_name)
        strtime, _ = fname.split('-')
        return datetime.strptime(strtime, "%Y%m%d_%H%M")
    glob_path = dcocfg.fileTypePath('log')
    remove_files(glob_path, '*-DailyCheck.log', log2dt, keep_days=keep_days, keep_months=keep_months)

def remove_reports(dcocfg, keep_days=14, keep_months=True):
    def rpt2dt(full_name):
        # Retrieve the date/time from the zipfile name
        fpath, fname = os.path.split(full_name)
        parts = fname.split('_')
        return datetime.strptime(parts[2]+parts[3] , "%Y%m%d%H%M")
    glob_path = dcocfg.fileTypePath('html')
    remove_files(glob_path, 'DCO_DCreport_*.html', rpt2dt, keep_days=keep_days, keep_months=keep_months)
    remove_files(glob_path, 'DCO_DCIreport_*.html', rpt2dt, keep_days=keep_days, keep_months=keep_months)

######################################################################################################
# GetInfo helpers
######################################################################################################


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

def get_nested(d, keys, default=None):
    """
    Access a nested dictionary with a list of keys, return default if any key is missing.

    Args:
        d (dict): The dictionary to traverse.
        keys (list): List of keys to access nested value.
        default: Value to return if any key is missing (default: None).

    Returns:
        The value at the nested key path, or default if path doesn't exist.
    """
    current = d
    for key in keys:
        try:
            current = current[key]
        except (KeyError, TypeError):
            return default
    return current

def get_certificate_fingerprint(host, port=443, timeout=5):
    """
    Retrieve the SHA-256 fingerprint of the SSL/TLS certificate from a server using only standard library.

    Args:
        host (str): The IP address or hostname of the server (e.g., 'example.com' or '192.168.1.1').
        port (int): The TCP port to connect to (default: 443 for HTTPS).
        timeout (float): Connection timeout in seconds (default: 10.0).

    Returns:
        str: The SHA-256 fingerprint of the certificate in hexadecimal format (e.g., 'a1b2c3...').
             Returns an empty string if an error occurs.
    """
    try:
        # Create an SSL context with no certificate verification
        context = ssl._create_unverified_context()
        context.check_hostname = False  # Disable hostname verification for IP addresses

        # Create a socket connection
        with socket.create_connection((host, port), timeout=timeout) as sock:
            # Wrap the socket with the SSL context
            with context.wrap_socket(sock) as ssock:
                # Get the server's certificate in DER format
                cert_der = ssock.getpeercert(binary_form=True)
                # Compute the SHA-256 fingerprint using hashlib
                fingerprint = hashlib.sha256(cert_der).hexdigest()
                return fingerprint
    except (ssl.SSLError, socket.gaierror, socket.timeout) as e:
        logger.error(f"Error retrieving certificate from {host}:{port}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return ""

def valid_certificate_fingerprint(host, port, cert_hash):
    api_cert_hash = get_certificate_fingerprint(host, port)
    if cert_hash != api_cert_hash:
        logger.critical(f'{host} certificate hash "{api_cert_hash}" does not match')
        return False
    return True

######################################################################################################
# ProccessInfo helpers
######################################################################################################


def process_if_not_empty(process_function, system, instance, data_type, dcocfg, na_count=1):
    """
    Checks if the JSON data is empty; if not, converts it to a DataFrame and processes it.

    Args:
        process_function (function): Function responsible for processing the resulting DataFrame.
        system (str): Name of the system associated with the data.
        instance (str): Instance of the system associated with the data.
        file_type (str): File type (csv, json) to load for processing.
        data_type (str): Keyword describing data contents.
        dcocfg : DCOconfig object with configuration loaded

    Returns:
        Summary dataframe: sumarized version of the data for this instance (optional)
    """
    #data = dcocfg.load_json(system, instance, data_type)
    try:
        data = dcocfg.load_json(system, instance, data_type)
    except FileNotFoundError:
        data = None

    # Validate if the data is empty or invalid
    if not data:
        file_path = dcocfg.filePath(system, instance, "json", data_type)
        logger.warning(f'The file "{file_path}" does not exist, is empty or contains invalid data. It will be skipped.')

        # If there is no data, return the number of 'N/A' requested
        # For calls expecting 1 or more values
        if na_count == 1:
            return 'N/A'
        else:
            return ['N/A'] * na_count

    # Process the DataFrame using the provided function
    return process_function(data, system, instance, dcocfg)

def filter_by_time(df, dt_column, dt_fmt, start_time, include_nat=False):
    """
    Filter DataFrame to include rows from a specified start time based on a datetime column.

    Parameters:
    df (pd.DataFrame): Input DataFrame
    dt_column (str): Name of the column containing datetime strings or epoch timestamps
    dt_fmt (str): Format of the datetime strings (e.g., '%Y-%m-%d %H:%M:%S') or 'epoch' for seconds since epoch
    start_time (datetime): Datetime to filter from (inclusive)
    include_nat (bool): Include empty (NA) and incorrect dates in the filtered dataframe

    Returns:
    pd.DataFrame: Filtered DataFrame containing only rows from the specified start time
    """
    # Create a copy to avoid SettingWithCopyWarning on the original dataframe
    df = df.copy()
    tmp_dt = '__temp_datetime__'

    if dt_fmt.lower() == 'epoch':
        # Convert to numeric first to avoid FutureWarning with 'unit'
        dt_series = pd.to_numeric(df[dt_column], errors='coerce')
        df[tmp_dt] = pd.to_datetime(dt_series, unit='s', utc=True, errors='coerce')
    else:
        # Convert string datetime using the provided format
        df[tmp_dt] = pd.to_datetime(df[dt_column], format=dt_fmt, utc=True, errors='coerce')

    # Ensure start_time is timezone-aware (if not already)
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=pytz.UTC)

    # Filter rows where the datetime is greater than or equal to the threshold
    row_selector = df[tmp_dt] >= start_time

    # Include empy/incorrect dates if requested
    if include_nat:
        row_selector |= df[tmp_dt].isna()

    filtered_df = df[row_selector].copy()

    # Drop the temporary column to keep original column format
    filtered_df = filtered_df.drop(columns=[tmp_dt])

    # Reset index for clean output
    filtered_df = filtered_df.reset_index(drop=True)

    return filtered_df


def format_duration(seconds):
    """
    Formats a amount of time in seconds to days, hours and minutes

    Examples:
    --------
    >>> format_duration(123456)
    '1d 10h 17m'

    Pandas usage:
    policies['Elapsed time'] = dataframe['elapsed'].apply(format_duration)

    """
    total_minutes = int(seconds // 60)
    days = total_minutes // (24 * 60)
    hours = (total_minutes % (24 * 60)) // 60
    minutes = total_minutes % 60
    return f"{days}d {hours:02d}h {minutes:02d}m"


def get_most_critical(df, column, status_order, default):
    """
    Retrieves the most critical status from a DataFrame column based on a predefined priority order.

    This function examines the specified column in the DataFrame and returns the first status
    from the provided `status_order` list that appears in the column with a non-zero count.
    The `status_order` list defines the priority of statuses, where earlier entries are
    considered more critical. If no statuses from `status_order` are found in the column,
    or if the column is empty, the function returns the specified default value.

    Parameters:
    -----------
    df : pandas.DataFrame
        The DataFrame containing the column to analyze.
    column : str
        The name of the column in the DataFrame to check for status values.
    status_order : list
        A list of status values in order of priority (most critical to least critical).
    default : any
        The value to return if no statuses from `status_order` are found or if the column is empty.

    Returns:
    --------
    any
        The most critical status found in the column based on `status_order`, or the `default`
        value if no matching statuses are present.

    Example:
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'status': ['low', 'high', 'medium', 'low']})
    >>> status_order = ['critical', 'high', 'medium', 'low']
    >>> get_most_critical(df, 'status', status_order, 'unknown')
    'high'
    """
    value_counts = df[column].value_counts()
    if not value_counts.empty:
        for status in status_order:
            if status in value_counts.index and value_counts[status] > 0:
                return status
    return default


def df_timestamps_to_dates(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Converts Unix timestamp columns in a DataFrame to datetime objects, only for existing columns.

    Parameters:
    -----------
    df : pd.DataFrame
        The input DataFrame containing timestamp columns.
    columns : list
        List of column names with Unix timestamps (in seconds) to convert.

    Returns:
    --------
    pd.DataFrame
        A new DataFrame with existing specified columns converted to datetime objects.

    Example:
    --------
    >>> df = pd.DataFrame({'ts': [1697059200], 'other': [1]})
    >>> df_timestamps_to_dates(df, ['ts', 'missing'])
                     ts  other
    0 2023-10-12 00:00:00      1
    """
    valid_columns = [col for col in columns if col in df.columns]
    return df.assign(**{col: df[col].map(lambda x: datetime.fromtimestamp(int(x))) for col in valid_columns})


def reformat_date(fmt_in: str, fmt_out: str, date: str) -> str:
    """
    Reformats a date string from one format to another.

    Parameters:
    -----------
    fmt_in : str
        The input datetime format (e.g., '%Y/%m/%d').
    fmt_out : str
        The desired output datetime format (e.g., '%Y-%m-%d %H:%M:%S').
    date : str
        The date string to reformat.

    Returns:
    --------
    str
        The reformatted date string.

    Example:
    --------
    >>> reformat_date('%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '2023/10/12')
    '2023-10-12 00:00:00'
    """
    try:
        if fmt_in == 'epoch':
            return datetime.fromtimestamp(int(date)).strftime(fmt_out)
        else:
            return datetime.strptime(date, fmt_in).strftime(fmt_out)
    except (ValueError, TypeError) as e:
        #logger.debug(f'Unable to reformat date {date}: {e}')
        return date

DCO_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def df_reformat_dates(df: pd.DataFrame, columns: list, current_fmt: str) -> pd.DataFrame:
    """
    Reformats date strings in specified DataFrame columns to a standard format, only for existing columns.

    Parameters:
    -----------
    df : pd.DataFrame
        The input DataFrame containing date columns.
    current_fmt : str
        The current format of dates in the columns (e.g., '%Y/%m/%d').
    columns : list
        List of column names to reformat; only existing columns are processed.

    Returns:
    --------
    pd.DataFrame
        A new DataFrame with existing specified columns reformatted to DCO_DATETIME_FMT.

    Example:
    --------
    >>> df = pd.DataFrame({'date': ['2023/10/12'], 'other': [1]})
    >>> df_reformat_dates(df, '%Y/%m/%d', ['date', 'missing'])
              date                 other
    0  2023-10-12 00:00:00         1
    """
    # Filter only existing columns
    valid_columns = [col for col in columns if col in df.columns]
    date_formater = functools.partial(reformat_date, current_fmt, DCO_DATETIME_FMT)
    return df.assign(**{col: df[col].map(date_formater) for col in valid_columns})

######################################################################################################
# CreatereportDC / DCI helpers
######################################################################################################

def systemSummary(system, index_key, data_type, dcocfg):
    """
    Generates a dataframe with the sumarized info of all the instances of a system type.

    Parameters:
    -----------
    dcocfg : DCOconfig
        DCOconfig object with the configuration loaded.
    system : str
        System type to sumarize (PPDM, ECS, DD...).
    index_key : str
        First column (index) for the dataframe summaries of this system type.
    data_type : str
        Keyword describing the files that have the summary in the configuration.

    Returns:
    --------
    pd.DataFrame
        DataFrame with the sumary of the instances.
    """
    # Load and return Unified file: DD-unified_data.csv, ECS-unified_data.csv, PPDM-unified_data.csv
    if system in ("PPDM"):
        return dcocfg.load_csv_to_dataframe(system, "", "unifiedData")

    summaryDf = pd.DataFrame()
    for instance in dcocfg.instances(system):
        df = dcocfg.load_csv_to_dataframe(system, instance, data_type)
        if summaryDf.empty:
            # First dataframe loaded: assign
            summaryDf = df
        else:
            # Remaining dataframes: merge if not empty
            if not df.empty:
                summaryDf = summaryDf.merge(df, on=index_key, how='inner')
            else:
                logger.warn(f'Summary dataframe for {system}/{instance} is empty.')
    return summaryDf
