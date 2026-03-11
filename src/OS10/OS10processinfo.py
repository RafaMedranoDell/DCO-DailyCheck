import logging
import pandas as pd
import numpy as np
import common.functions as fn
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "OS10"

# Configure module logger
logger = fn.get_module_logger(__name__)

OS10_DATETIME_FMT = "%a %b %d %H:%M:%S %Y"

def process_alarm_summary(data, system, instance, dcocfg):
    # Alert summary
    alert_summary = pd.DataFrame(list(data.items()), columns=["Severity", "Count"])
    alert_summary = alert_summary[alert_summary["Severity"].isin(["critical-count", "major-count", "warning-count"])]
    alert_summary["Severity"] = alert_summary["Severity"].str.replace("-count", "")
    alert_summary["Severity"] = alert_summary["Severity"].str.title()
    alert_summary["Count"] = alert_summary["Count"].astype(int)

    dcocfg.save_dataframe_to_csv(alert_summary, system, instance, "alertSummary")

    alert_summary = alert_summary[alert_summary["Count"] > 0]
    alert_summary_status = fn.get_most_critical(alert_summary, "Severity", ["Critical", "Major", "Warning"], "OK")
    return alert_summary_status

def process_event_history(data, system, instance, dcocfg):
    # Alert detail
    selected_columns = {
        'severity': 'Severity',
        'state': 'Status',
        'timestamp': 'Date',
        'description':'Description'
    }
    alert_list = pd.DataFrame(data)
    alert_list = alert_list[alert_list['state']=='raised']
    alert_list = alert_list[alert_list['severity'].isin(['critical', 'warning'])]
    alert_list = fn.df_reformat_dates(alert_list, ["timestamp"], OS10_DATETIME_FMT)
    alert_list = alert_list.reindex(columns=selected_columns.keys())
    alert_list = alert_list.rename(columns=selected_columns)

    dcocfg.save_dataframe_to_csv(alert_list, system, instance, "alertDetail")
    severity_counts = alert_list['Severity'].value_counts().reset_index()
    active_event_status = fn.get_most_critical(severity_counts, "Severity", ["Critical", "Warning"], "OK")
    return active_event_status

def process_unit_state(data, system, instance, dcocfg):
    unitsdf = pd.DataFrame(data["dell-equipment:system"]["node"]["unit"])
    units_state = (unitsdf["unit-state"]=="up").all()
    return "OK" if units_state else "Critical"

def process_power_supplies(data, system, instance, dcocfg):
    powersupliesdf = pd.DataFrame(data["dell-equipment:system"]["node"]["power-supply"])
    powersuplies_state = (powersupliesdf["status"]=="up").all()
    # Save the DataFrame as a CSV
    dcocfg.save_dataframe_to_csv(powersupliesdf[['psu-id', 'status']], system, instance, "powersuplies")
    return "OK" if powersuplies_state else "Critical"

def process_fans(data, system, instance, dcocfg):
    powersupliesdf = pd.DataFrame(data["dell-equipment:system"]["node"]["power-supply"])
    fansdf = pd.DataFrame(data["dell-equipment:system"]["node"]["fan-tray"])

    ## Power Supplies Fans
    exploded_df = powersupliesdf.explode('fan-info')
    normalized_inner = pd.json_normalize(exploded_df['fan-info'])
    normalized_inner.index = exploded_df.index
    psfan_all = pd.concat([exploded_df[["psu-id"]], normalized_inner[["fan-id", "fan-status"]]], axis=1)

    ## Fan Trays
    exploded_df = fansdf.explode('fan-info')
    normalized_inner = pd.json_normalize(exploded_df['fan-info'])
    normalized_inner.index = exploded_df.index
    trayfan_all = pd.concat([exploded_df[["fan-tray-id"]], normalized_inner[["fan-id", "fan-status"]]], axis=1)

    ## Join together PS fans and tray fans
    psfan_all['container_id'] = 'Power Supply ' + psfan_all['psu-id'].astype(str)
    trayfan_all['container_id'] = 'Fan Tray ' + trayfan_all['fan-tray-id'].astype(str)
    psfan_all = psfan_all[['container_id', 'fan-id', 'fan-status']]
    trayfan_all = trayfan_all[['container_id', 'fan-id', 'fan-status']]
    fan_all = pd.concat([psfan_all, trayfan_all], ignore_index=True)
    fan_state = (fan_all["fan-status"]=="up").all()

    # Save the DataFrame as a CSV
    fan_all.rename(columns={'container_id':'Container', 'fan-id':'Fan ID', 'fan-status':'status'}, inplace=True)
    dcocfg.save_dataframe_to_csv(fan_all, system, instance, "fans")

    return "OK" if fan_state else "Critical"

def process_thermal_sensor(data, system, instance, dcocfg):
    unittempdf = pd.DataFrame(data["dell-equipment:system"]["environment"]["unit"])
    thermaldf = pd.DataFrame(data["dell-equipment:system"]["environment"]["thermal-sensor"])
    selected_columns = {
        "sensor-name": "Sensor",
        "sensor-temp": "Temp Cº",
    }

    unittempdf['sensor-name'] = "Unit_temp"
    unittempdf.rename(columns={'unit-temp':'sensor-temp'}, inplace=True)

    ## Join together unit temp and thermal sensors
    thermal_all = pd.concat([unittempdf[["unit-id", "sensor-name", "sensor-temp"]], thermaldf[["unit-id", "sensor-name", "sensor-temp"]]], ignore_index=True)
    thermal_all["sensor-name"] = thermal_all["sensor-name"].str.replace("_", " ")
    thermal_all.rename(columns={'unit-id':'Unit ID', 'sensor-name':'Sensor', 'sensor-temp':'Temp Cº'}, inplace=True)

    # Save the DataFrame as a CSV
    dcocfg.save_dataframe_to_csv(thermal_all, system, instance, "thermal")
    return DCOreport.rate_num_value(thermal_all["Temp Cº"].max(), [0, 45, 60, 100], ["OK", "Warning", "Critical"])

def process_ports(data, system, instance, dcocfg):
    instance_info = dcocfg.instanceInfo(system, instance)
    expected_up = instance_info.get("ports_up", [])

    if not expected_up:
        return "n/a"

    portsdf = pd.DataFrame(data["dell-port:ports"]["ports-state"]["port"])

    # Create a new column with the first element of the 'channel' array
    portsdf['channel_first'] = portsdf['channel'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)

    # Filter non-None rows and normalize the JSON data
    channel_data = portsdf[portsdf['channel_first'].notna()]['channel_first']
    normalized_channel = pd.json_normalize(channel_data)

    # Reset index to align with the original DataFrame
    normalized_channel.index = portsdf[portsdf['channel_first'].notna()].index

    # Combine the normalized channel data with the original 'name' and 'present' columns
    port_status = pd.concat([portsdf[['name', 'present']], normalized_channel], axis=1)

    # Drop the temporary 'channel_first' column from the original DataFrame
    portsdf = portsdf.drop(columns=['channel_first'])

    # Replace NaN in the normalized columns for rows where 'channel' was NaN
    port_status = port_status.fillna({'sub-port': np.nan, 'state': np.nan, 'rx-power': np.nan})  # Adjust based on your JSON keys

    # Add a column to determine if an interface is "up" based on the conditions
    port_status['is_up'] = (
        (port_status['present'] == True) &
        (port_status['state'] == True) &
        (port_status.get('rx-loss', False) == False) &  # Use .get() to handle missing columns
        (port_status.get('tx-loss', False) == False) &
        (port_status.get('tx-disable', False) == False)
    )

    # Add a column to determine if the interface is expected to be "up"
    port_status['expected_up'] = port_status['name'].isin(expected_up)

    # Add 'Status' and 'Expected Status' columns
    port_status['Status'] = port_status['is_up'].map({True: 'Up', False: 'Down'})
    port_status['Expected Status'] = port_status['expected_up'].map({True: 'Up', False: 'Down'})

    # Rename column "name"
    port_status.rename(columns={'name':'Port name'}, inplace=True)

    # Save the DataFrame as a CSV
    dcocfg.save_dataframe_to_csv(port_status[['Port name', 'Status', 'Expected Status']], system, instance, "port_status")

    # Check unexpected downs (expected up but actually down)
    unexpected_downs = port_status[(~port_status['is_up'] & port_status['expected_up'])][['Port name']]

    # Check unexpected ups (expected down but actually up)
    unexpected_ups = port_status[(port_status['is_up'] & ~port_status['expected_up'])][['Port name']]
    if not unexpected_downs.empty:
        return "Critical"
    elif not unexpected_ups.empty:
        return "Warning"
    else:
        return "OK"

def proccess_info(dcocfg):
    """
    Main function that coordinates all tasks by loading the configuration
    and processing the necessary data for each system and instance.

    This function processes system health, job group activities, activities that
    were not OK, and storage systems based on the configuration file and JSON data.
    """

    # Process each instance in the system
    logger.info(f'Process info from {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'{system}: processing info from "{instance}"')

        # Hardware status
        unit_state = fn.process_if_not_empty(process_unit_state, system, instance, "equipment", dcocfg)
        power_supplies = fn.process_if_not_empty(process_power_supplies, system, instance, "equipment", dcocfg)
        fans = fn.process_if_not_empty(process_fans, system, instance, "equipment", dcocfg)
        thermal_sensor = fn.process_if_not_empty(process_thermal_sensor, system, instance, "equipment", dcocfg)

        # Alerts
        alert_summary_status = fn.process_if_not_empty(process_alarm_summary, system, instance, "alarm-summary", dcocfg)
        active_event_status = fn.process_if_not_empty(process_event_history, system, instance, "event-history", dcocfg)

        # Ports (pending implementation)
        ports_status = fn.process_if_not_empty(process_ports, system, instance, "ports", dcocfg)

        instance_summary = [
            ["Unit State", unit_state],
            ["Power Supplies", power_supplies],
            ["Fans", fans],
            ["Temperature", thermal_sensor],
            ["Ports", ports_status],
            ["Alerts", alert_summary_status],
            ["Events", active_event_status]
        ]

        pd.DataFrame(instance_summary, columns=["TOR", instance])
        dcocfg.save_dataframe_to_csv(
            pd.DataFrame(instance_summary, columns=["TOR", instance]),
            system, instance, "systemSummary")
        #create final_csv
        # unify_csv_files(dcocfg, system, instance, csvPath)

if __name__ == '__main__':
    # Load configuration
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    proccess_info(dcocfg)