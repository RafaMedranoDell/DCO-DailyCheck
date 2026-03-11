import logging
import pandas as pd
import common.functions as fn
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "ECS"

# Configure module logger
logger = fn.get_module_logger(__name__)

def process_alerts(data, system, instance, dcocfg):
    pass
    df = pd.DataFrame(data)

    df = df[df["acknowledged"]==False]
    df = fn.df_reformat_dates(df, ["timestamp"], "%Y-%m-%dT%H:%M:%S")

    active_alerts_status = fn.get_most_critical(df, "severity", ["CRITICAL", "ERROR", "WARNING", "INFO"], "OK")

    # Filter, rename and sort the selected columns
    selected_columns = {
        'type': 'Type',
        'severity': 'Severity',
        'timestamp': 'Time',
        'description': 'Description'
    }
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(df, system, instance, "alertsDetail")
    return active_alerts_status

def process_localzoneInfo(data, system, instance, dcocfg):
    """
    Processes the local zone information DataFrame, performing calculations, filtering, renaming columns,
    and saving the results to a CSV file.

    Parameters:
    data (str): The data loaded from the file.
    system (str): The system from which the alert data originates.
    instance (str): The instance of the system.
    dcocfg (DCOconfig): Configuration object.

    Returns:
        None
    """

    # Convert JSON data into dataframe
    df = pd.DataFrame(data)

    # Convert relevant columns to numeric types to enable calculations
    cols_to_numeric = ['diskSpaceTotalCurrent.Space', 'diskSpaceAllocatedCurrent.Space', 'diskSpaceFreeCurrent.Space']
    df[cols_to_numeric] = df[cols_to_numeric].apply(pd.to_numeric, errors='coerce')

    # Calculate the percentage of disk space used
    df['diskSpacePercentUsed'] = ((df['diskSpaceAllocatedCurrent.Space'] / df['diskSpaceTotalCurrent.Space']) * 100).round(2)

    # Convert byte values to terabytes (TB) for readability
    bytes_columns = ['diskSpaceTotalCurrent.Space', 'diskSpaceAllocatedCurrent.Space', 'diskSpaceFreeCurrent.Space']
    df[bytes_columns] = (df[bytes_columns] / (1024 ** 4)).round(2)

    # Filter, rename and sort the selected columns
    selected_columns = {
        'id': "ID",
        'name': 'Name',
        'numNodes': 'Total Nodes',
        'numGoodNodes': 'Good Nodes',
        'numMaintenanceNodes': 'Maintenance Nodes',
        'numBadNodes': 'Bad Nodes',
        'numDisks': 'Total Disks',
        'numGoodDisks': 'Good Disks',
        'numMaintenanceDisks': 'Maintenance Disks',
        'numBadDisks': 'Bad Disks',
        'alertsNumUnackInfo.Count': 'Alerts Info',
        'alertsNumUnackWarning.Count': 'Alerts Warning',
        'alertsNumUnackError.Count': 'Alerts Error',
        'alertsNumUnackCritical.Count': 'Alerts Critical',
        'diskSpaceTotalCurrent.Space': 'Space Total (TB)',
        'diskSpaceAllocatedCurrent.Space': 'Space Allocated (TB)',
        'diskSpaceFreeCurrent.Space': 'Space Free (TB)',
        'diskSpacePercentUsed': 'Space Allocated (%)'
    }
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)

    # Add the index as a column and reset the index to its default
    df_transposed = df.transpose().reset_index()
    df_transposed.columns=["ECS", instance]
    dcocfg.save_dataframe_to_csv(df_transposed, system, instance, "localzoneInfo")

    nodes_df = df_transposed[df_transposed['ECS'].isin(['Total Nodes', 'Good Nodes', 'Maintenance Nodes', 'Bad Nodes'])]
    nodes_df.columns=["Nodes", instance]
    dcocfg.save_dataframe_to_csv(nodes_df, system, instance, "nodes")

    disks_df = df_transposed[df_transposed['ECS'].isin(['Total Disks', 'Good Disks', 'Maintenance Disks', 'Bad Disks'])]
    disks_df.columns=["Disks", instance]
    dcocfg.save_dataframe_to_csv(disks_df, system, instance, "disks")

    alerts_df = df_transposed[df_transposed['ECS'].isin(['Alerts Info', 'Alerts Warning', 'Alerts Error', 'Alerts Critical'])]
    alerts_df.columns=["Alerts", instance]
    dcocfg.save_dataframe_to_csv(alerts_df, system, instance, "alerts")

    space_df = df_transposed[df_transposed['ECS'].isin(['Space Total (TB)', 'Space Allocated (TB)', 'Space Free (TB)', 'Space Allocated (%)'])]
    space_df.columns=["Space", instance]
    dcocfg.save_dataframe_to_csv(space_df, system, instance, "space")

    # Return the metrics as a dictionary for the main summary calculation
    return df.iloc[0].to_dict()

def proccess_info(dcocfg):
    """Main function that coordinates all tasks."""

    logger.info(f'Processing {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'Processing info from: "{instance}"')

        # Process Alerts (get most critical status)
        alert_status_raw = fn.process_if_not_empty(process_alerts, system, instance, "alerts", dcocfg)
        if alert_status_raw is None:
            alert_status_raw = "OK"

        # Process LocalzoneInfo (get metrics dict)
        metrics = fn.process_if_not_empty(process_localzoneInfo, system, instance, "localzoneInfo", dcocfg)
        
        if metrics:
            # 1. Nodes Status Logic (using renamed keys from process_localzoneInfo)
            bad_nodes = int(metrics.get('Bad Nodes', 0))
            maint_nodes = int(metrics.get('Maintenance Nodes', 0))
            if bad_nodes > 0:
                nodes_txt = f"Error ({bad_nodes} Bad)"
            elif maint_nodes > 0:
                nodes_txt = f"Warning ({maint_nodes} Maint)"
            else:
                nodes_txt = "OK"

            # 2. Disks Status Logic (using renamed keys from process_localzoneInfo)
            bad_disks = int(metrics.get('Bad Disks', 0))
            maint_disks = int(metrics.get('Maintenance Disks', 0))
            if bad_disks > 0:
                disks_txt = f"Error ({bad_disks} Bad)"
            elif maint_disks > 0:
                disks_txt = f"Warning ({maint_disks} Maint)"
            else:
                disks_txt = "OK"

            # 3. Alerts Status (Mappping)
            alert_map = {
                "CRITICAL": "Critical",
                "ERROR": "Error",
                "WARNING": "Warning",
                "INFO": "Info",
                "OK": "OK"
            }
            alerts_txt = alert_map.get(alert_status_raw, "OK")

            # 4. Storage Utilization (%)
            utilization = metrics.get('Space Allocated (%)', 0)

            # Build the simplified summary dataframe
            summary_data = [
                ["Nodes Status", nodes_txt],
                ["Disks Status", disks_txt],
                ["Alerts Status", alerts_txt],
                ["Storage Utilization (%)", utilization]
            ]
            summary_df = pd.DataFrame(summary_data, columns=["ECS", instance])
            
            # Save final system summary CSV
            dcocfg.save_dataframe_to_csv(summary_df, system, instance, "systemSummary")

if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), "ECSdebug", level=logging.DEBUG)
    proccess_info(dcocfg)