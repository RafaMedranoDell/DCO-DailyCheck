import logging
import pandas as pd
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "IDRAC"

# Configure module logger
logger = fn.get_module_logger(__name__)

def process_chassis(data, system, instance, dcocfg):
    # Load data into a dataframe
    df = pd.json_normalize(data)

    # Concatenate Health and HealthRollup for locate the most critical status
    overal_health = pd.concat([df["Status.Health"], df["Status.HealthRollup"]]).to_frame(name='Health')

    # Selected columns and their new names and order
    selected_columns = {
        "Model": "Model",
        "Status.Health": "Health",
        "Status.HealthRollup": "Health Rollup",
        "Status.State": "Status"
    }

    # Rename, reorder and filter columns
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(df, system, instance, "chassis")

    return fn.get_most_critical(overal_health, "Health", ["Critical", "Warning", "Unknown", "OK"], "n/a")

def process_system(data, system, instance, dcocfg):
    # Load data into a dataframe
    df = pd.json_normalize(data)

    # Concatenate Health and HealthRollup for locate the most critical status
    overal_health = pd.concat([df["Status.Health"], df["Status.HealthRollup"]]).to_frame(name='Health')

    # Selected columns and their new names and order
    selected_columns = {
        "Model": "Model",
        "PowerState": "Power State",
        "Status.Health": "Health",
        "Status.HealthRollup": "Health Rollup",
        "Status.State": "Status"
    }

    # Rename, reorder and filter columns
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(df, system, instance, "system")

    return fn.get_most_critical(overal_health, "Health", ["Critical", "Warning", "Unknown", "OK"], "n/a")

def process_processors(data, system, instance, dcocfg):
    # Load data into a dataframe
    df = pd.json_normalize(data["Members"])
    df.sort_values(["ProcessorType", "Name"], inplace=True)

    # Selected columns and their new names and order
    selected_columns = {
        "Name": "Name",
        "ProcessorType": "Type",
        "Status.Health": "Health",
        "Status.State": "Status"
    }
    # Rename, reorder and filter columns
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(df, system, instance, "processors")

    return fn.get_most_critical(df, "Health", ["Critical", "Warning", "Unknown", "OK"], "n/a")

def process_logs(data, system, instance, dcocfg):
    common_columns = {
        "Id": "Id",
        "Created": "Created",
        "Description": "Description",
        "Message": "Message",
        "Severity": "Severity"
    }

    logs_status = "OK"

    # Process the log types and identify them
    for log in data["Members"]:
        log_id = log["Id"]
        log_name = log["Name"]
        df = pd.json_normalize(log["Entries"]["Members"])
        if df.empty:
            continue
        df = fn.filter_by_time(df, "Created", "%Y-%m-%dT%H:%M:%S%z", dcocfg.get_param("start_time"))

        if log_id == "Sel":
            df_out = df.reindex(columns=common_columns.keys()).rename(columns=common_columns)
            dcocfg.save_dataframe_to_csv(df_out, system, instance, "log_sel")
        elif log_id == "Lclog":
            selected_columns = dict(common_columns)
            selected_columns.update({"Oem.Dell.Category": "Category"})
            df_out = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
            dcocfg.save_dataframe_to_csv(df_out, system, instance, "log_lc")
        elif log_id == "FaultList":
            df_out = df.reindex(columns=common_columns.keys()).rename(columns=common_columns)
            dcocfg.save_dataframe_to_csv(df_out, system, instance, "log_faults")
        else:
            logger.warning(f'Unknown log type found: {log_id}/{log_name}')
            continue

        # Aggregate log status from Severity column
        if "Severity" in df.columns:
            severities = set(df["Severity"].dropna().unique())
            if "Critical" in severities:
                logs_status = "Critical"
            elif "Warning" in severities and logs_status != "Critical":
                logs_status = "Warning"

    return logs_status


def process_powersupplies(data, system, instance, dcocfg):
    # Load data into a dataframe
    df = pd.json_normalize(data["PowerSupplies"])

    # Selected columns and their new names and order
    selected_columns = {
        "Name": "Name",
        "Status.Health": "Health",
        "Status.State": "Status"
    }

    # Rename, reorder and filter columns
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(df, system, instance, "powersupplies")

    return fn.get_most_critical(df, "Health", ["Critical", "Warning", "Unknown", "OK"], "n/a")

def process_fans(data, system, instance, dcocfg):
    # Load data into a dataframe
    df = pd.json_normalize(data["Fans"])

    # Selected columns and their new names and order
    selected_columns = {
        "Name": "Name",
        "Status.Health": "Health",
        "Status.State": "Status"
    }

    # Rename, reorder and filter columns
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(df, system, instance, "fans")

    return fn.get_most_critical(df, "Health", ["Critical", "Warning", "Unknown", "OK"], "n/a")

def process_storage(data, system, instance, dcocfg):
    # Load data into a dataframe
    df = pd.json_normalize(data["Members"])

    # Filter only controllers with drives
    df = df[df["Drives@odata.count"].astype('int64')>0]


    # Concatenate Health and HealthRollup for locate the most critical status
    overal_health = pd.concat([df["Status.Health"], df["Status.HealthRollup"]]).to_frame(name='Health')

    # Selected columns and their new names and order
    columns = ["Name", "Status.Health", "Status.HealthRollup", "Status.State","Drives@odata.count"]
    selected_columns = {
        "Name": "Name",
        "Status.Health": "Health",
        "Status.HealthRollup": "Health Rollup",
        "Status.State": "Status",
        "Drives@odata.count": "Drive count"
    }

    # Rename, reorder and filter columns
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(df, system, instance, "storage")

    return fn.get_most_critical(overal_health, "Health", ["Critical", "Warning", "Unknown", "OK"], "n/a")

def process_thermal(data, system, instance, dcocfg):
    # Load data into a dataframe
    df = pd.json_normalize(data["Temperatures"])

    # Selected columns and their new names and order
    selected_columns = {
        "Name": "Name",
        "ReadingCelsius": "Temp Cº",
        "Status.Health": "Health",
        "Status.State": "Status"
    }

    # Rename, reorder and filter columns
    df = df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(df, system, instance, "thermal")

    return fn.get_most_critical(df, "Health", ["Critical", "Warning", "Unknown", "OK"], "n/a")

def proccess_info(dcocfg, **kwargs):
    """
    Main function that coordinates all tasks. Generates a 3-row summary:
    - System Health: worst of Chassis, System, Processors, PSU, Fans, Temperatures
    - Storage Health: storage controller health
    - Logs Status: derived from Severity of log entries in the period
    """

    # Process each instance in the system
    logger.info(f'Processing {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'Processing info from: "{instance}"')

        # --- Individual component statuses ---
        chassis_status       = fn.process_if_not_empty(process_chassis,       system, instance, "chassis",    dcocfg)
        system_status        = fn.process_if_not_empty(process_system,         system, instance, "system",     dcocfg)
        processors_status    = fn.process_if_not_empty(process_processors,     system, instance, "processors", dcocfg)
        powersupplies_status = fn.process_if_not_empty(process_powersupplies,  system, instance, "power",      dcocfg)
        fans_status          = fn.process_if_not_empty(process_fans,           system, instance, "thermal",    dcocfg)
        storage_status       = fn.process_if_not_empty(process_storage,        system, instance, "storage",    dcocfg)
        thermal_status       = fn.process_if_not_empty(process_thermal,        system, instance, "thermal",    dcocfg)
        logs_status          = fn.process_if_not_empty(process_logs,           system, instance, "logs",       dcocfg)

        # --- Aggregate: System Health = worst of 6 hardware components (excluding storage) ---
        priority = ["Critical", "Warning", "Unknown", "OK", "n/a"]
        hw_statuses = [chassis_status, system_status, processors_status, 
                       powersupplies_status, fans_status, thermal_status]
        system_health = next((s for s in priority if s in hw_statuses), "n/a")

        # --- Build 3-row summary ---
        instance_summary = [
            ["System Health",  system_health],
            ["Storage Health", storage_status],
            ["Logs Status",    logs_status],
        ]

        dcocfg.save_dataframe_to_csv(
            pd.DataFrame(instance_summary, columns=["System Name", instance]),
            system, instance, "systemSummary")

if __name__ == '__main__':
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    proccess_info(dcocfg)