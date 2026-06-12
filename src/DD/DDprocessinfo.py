import logging
import pandas as pd
import common.functions as fn
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "DD"

# Configure module logger
logger = fn.get_module_logger(__name__)

def process_alerts_detail(data, system, instance, dcocfg):
    """
    Processes the detailed alert data by filtering the desired columns and saving the result as a CSV file.

    Parameters:
    data (str): The data loaded from the file.
    system (str): The system from which the alert data originates.
    instance (str): The instance of the system.
    dcocfg (DCOconfig): Configuration object.
    """
    # Convert JSON data into dataframe
    df = pd.DataFrame(data)

    # Translate timestamps to human readable dates/times
    df = fn.df_timestamps_to_dates(df, ["alert_gen_epoch"])

    selected_columns = {
        'id': "ID",
        'alert_id': "Alert ID",
        'event_id': "Event ID",
        'status': "Status",
        'class': "Class",
        'severity': "Severity",
        'alert_gen_epoch': "Alert Creation Time",
        'description': "Description",
        'msg': "Message"
    }

    # Rename and select columns, and save to the CSV
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    # Save the DataFrame as a CSV
    dcocfg.save_dataframe_to_csv(df, system, instance, "alertsDetail")


def process_replicas_status(data, system, instance, dcocfg):
    """
    Processes the replication status data and saves it as a CSV file.

    Parameters:
    data (str): The data loaded from the file.
    system (str): The system from which the alert data originates.
    instance (str): The instance of the system.
    dcocfg (DCOconfig): Configuration object.
    """
    # Convert JSON data into dataframe
    df = pd.DataFrame(data)

    # Get the current date and time
    current_time = pd.Timestamp.now()

    # Convert syncEpoch to datetime
    df['syncEpoch_datetime'] = pd.to_datetime(df['syncEpoch'].astype(int), unit='s')

    # Calculate the difference in hours and round to the nearest integer
    df['secondsSinceLastSync'] = (current_time - df['syncEpoch_datetime']).dt.total_seconds()

    df['elapsedLastSync'] = df['secondsSinceLastSync'].apply(fn.format_duration)

    # Convert syncEpoch to a readable format
    df['syncEpoch'] = df['syncEpoch_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Convert connEpoch to datetime and to a readable format
    df['connEpoch'] = pd.to_datetime(df['connEpoch'].astype(int), unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')

    selected_columns = {
        "id": "ID",
        "mode": "Mod",
        "sourceMtreePath": "Source Mtree Path",
        "elapsedLastSync": "Time since last sync",
        "secondsSinceLastSync": "secondsSinceLastSync"
    }
    # Rename and select columns, and save to the CSV
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(df, system, instance, "replicasStatus")


def process_tiers_status(data, system, instance, dcocfg):
    """
    Processes the storage tier status data, ensuring all required tiers are present,
    converting fields to TB, calculating usage percentage, and saving the result as a CSV file.

    Parameters:
    data (str): The data loaded from the file.
    system (str): The system from which the alert data originates.
    instance (str): The instance of the system.
    dcocfg (DCOconfig): Configuration object.
    """
    # Convert JSON data into dataframe
    df = pd.DataFrame(data)

    # Set the index to 'tier' to make processing easier
    df_processed = df.set_index('tier')

    # Calculate the occupancy percentage
    df_processed['percent'] = df_processed.apply(
        lambda row: 0.0 if row['dc_total'] == 0 or row['dc_used'] == 0
        else round((row['dc_used'] / row['dc_total']) * 100, 2),
        axis=1
    )

    # Convert fields to TB
    df_processed['total_TB'] = (df_processed['dc_total'] / 1e12).round(2)
    df_processed['used_TB'] = (df_processed['dc_used'] / 1e12).round(2)
    df_processed['avail_TB'] = (df_processed['dc_avail'] / 1e12).round(2)

    # Drop original byte columns
    df_processed = df_processed.drop(columns=['dc_total', 'dc_used', 'dc_avail'])

    # Ensure all required tiers exist
    required_tiers = ["active", "cloud", "total"]

    # Set cloud tier to zeros if not present
    if "cloud" not in df_processed.index:
        df_processed.loc["cloud"] = {
            "percent": 0.0,
            "total_TB": 0.0,
            "used_TB": 0.0,
            "avail_TB": 0.0
        }
        # If cloud is not present, total should be same as active
        df_processed.loc["total"] = df_processed.loc["active"].copy()
    else:
        # If cloud exists, use the original total tier data
        if "total" in df_processed.index:
            # Ensure total tier reflects the original total tier data
            total_data = df_processed.loc["total"]
            df_processed.loc["total"] = total_data

    # Reset index to bring 'tier' back as a column
    df_processed = df_processed.reset_index()

    selected_columns = {
        "tier": "Tier",
        "total_TB": "Total (TB)",
        "used_TB": "Used (TB)",
        "avail_TB": "Available (TB)",
        "percent": "% Used"
    }
    # Rename and select columns, and save to the CSV
    df_processed = df_processed.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)

    # Rename tiers by user friendly names
    new_labels = {
        "active": "Active Tier Used",
        "cloud": "Cloud Tier Used",
        "total": "Combined Used"
    }
    df_processed['Tier'] = df_processed['Tier'].replace(new_labels)

    # Save the modified DataFrame as a CSV file
    dcocfg.save_dataframe_to_csv(df_processed, system, instance, "tiersStatus")

    return df_processed

def process_filesys_status(data, system, instance, dcocfg):
    """
    Processes the file system status, uptime, and last cleaning success,
    then saves it as a CSV file.
    """
    fs_status = data.get('fs_status', "unknown")
    fs_uptime_secs = data.get('fs_uptime_secs', 0)

    # Path to success_epoch: fs_cleaning_info.filesys_clean_info.cleaning_dates.success_epoch
    success_epoch = fn.get_nested(data, ["fs_cleaning_info", "filesys_clean_info", "cleaning_dates", "success_epoch"], 0)

    if fs_status == "sn_enabled":
        status = "OK"
    else:
        status = "ERROR"

    uptime_secs = data.get('fs_uptime_secs', 0)
    current_time = dcocfg.get_param("script_start_time")
    boot_time = current_time - pd.Timedelta(seconds=uptime_secs)
    uptime_str = boot_time.strftime(fn.DCO_DATETIME_FMT)

    if success_epoch > 0:
        last_cleaning = fn.reformat_date('epoch', fn.DCO_DATETIME_FMT, success_epoch)
    else:
        last_cleaning = "N/A"

    df = pd.DataFrame([{
        "Filesystem Status": status,
        "Filesystem Uptime": uptime_str,
        "Last Cleaning Success": last_cleaning
    }])

    # Save the DataFrame as a CSV
    dcocfg.save_dataframe_to_csv(df, system, instance, "filesysStatus")

    return status, uptime_str, last_cleaning


def proccess_info(dcocfg):
    """Main function that coordinates all tasks."""

    logger.info(f'Processing {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'Processing info from: "{instance}"')

        # Process detailed list alert
        fn.process_if_not_empty(process_alerts_detail, system, instance, "activeAlerts", dcocfg)

        # Process Status of Replicas
        fn.process_if_not_empty(process_replicas_status, system, instance, "replicas", dcocfg)

        # Process Status of Tiers
        fn.process_if_not_empty(process_tiers_status, system, instance, "tiers", dcocfg)

        # Process Status of Filesystem
        # process_filesys_status now returns three values
        filesys_status, filesys_uptime, last_cleaning = fn.process_if_not_empty(process_filesys_status, system, instance, "filesys", dcocfg, na_count=3)

        # Generate the instance summary

        # Get System Alerts status based on the most critical active alert
        active_alerts = dcocfg.load_json(system, instance, "activeAlerts")
        df_alerts = pd.DataFrame(active_alerts)
        severity_order = ["EMERGENCY", "ALERT", "CRITICAL", "ERROR", "WARNING", "NOTICE", "INFO", "DEBUG"]
        
        if not df_alerts.empty and 'severity' in df_alerts.columns:
            system_status = fn.get_most_critical(df_alerts, 'severity', severity_order, "OK")
        else:
            system_status = "OK"

        # Load tiers
        df_tiers_status = dcocfg.load_csv_to_dataframe(system, instance, "tiersStatus")

        # Generate the base dataframe
        summary_columns = ['Data Domain', instance]
        instance_summary = pd.DataFrame(columns=summary_columns)

        # Add alerts info
        instance_summary = pd.concat(
            [instance_summary, pd.DataFrame([
                ['System Status', ''],
                ['System Alerts', system_status],
                ['Filesystem Status', filesys_status],
                ['Filesystem Uptime', filesys_uptime],
                ['Last Cleaning Success', last_cleaning]
            ], columns=summary_columns)],
            ignore_index=True)

        # Add tier info
        instance_summary = pd.concat(
            [instance_summary, pd.DataFrame([['Capacity Status', '']],
            columns=summary_columns)],
            ignore_index=True)
        df_tiers_status['Tier'] = df_tiers_status['Tier'] + ' (%)'
        df_tiers_status = df_tiers_status.rename(columns={'Tier': 'Data Domain', '% Used': instance})
        instance_summary = pd.concat(
            [instance_summary, df_tiers_status[summary_columns]],
            ignore_index=True)

        dcocfg.save_dataframe_to_csv(instance_summary, system, instance, "systemSummary")

if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), "DDdebug", level=logging.DEBUG)
    proccess_info(dcocfg)