import pandas as pd
import common.functions as fn
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

# Global variable for the system type
system = "ESX"

# Configure module logger
logger = fn.get_module_logger(__name__)


def process_esx_instance(dcocfg, instance):
    """
    Processes the collected JSON data for a single standalone ESXi instance.
    Generates summary and detailed CSV files.
    """
    logger.info(f"{system}/{instance}: Loading collected data...")
    host_health = dcocfg.load_json(system, instance, "host_health")
    datastores   = dcocfg.load_json(system, instance, "datastores")
    vms          = dcocfg.load_json(system, instance, "vms")
    alarms       = dcocfg.load_json(system, instance, "alarms")

    # --- A. Host Health Status ---
    # Map overallStatus (green/yellow/red/gray) to OK/Warning/Critical/Unknown
    health_map = {
        "green": "OK",
        "yellow": "Warning",
        "orange": "Warning",
        "red": "Critical",
        "gray": "Unknown",
    }
    raw_health = str(host_health.get("overall_status", "gray")).lower()
    host_status = health_map.get(raw_health, "Unknown")

    # --- B. Datastores Status & Detail ---
    ds_df = pd.DataFrame(datastores)
    ds_status = "OK"
    if not ds_df.empty:
        # Ensure required columns
        for col in ["capacity", "free_space"]:
            if col not in ds_df.columns:
                ds_df[col] = 0

        ds_df["% Used"] = ((ds_df["capacity"] - ds_df["free_space"]) / ds_df["capacity"]) * 100
        max_used = ds_df["% Used"].max()

        ds_status = DCOreport.rate_num_value(
            max_used,
            rate_intervals=[0, 85, 95, 101],
            rating=["OK", "Warning", "Critical"]
        )

        ds_df["Total (TB)"] = ds_df["capacity"] / (1024 ** 4)
        ds_df["Free (TB)"]  = ds_df["free_space"] / (1024 ** 4)
        ds_detail = ds_df[["name", "type", "Total (TB)", "Free (TB)", "% Used"]].copy()
        dcocfg.save_dataframe_to_csv(ds_detail, system, instance, "datastoreStatus")
    else:
        ds_status = "Critical"

    # --- C. VMs Status & Detail ---
    vms_df = pd.DataFrame(vms)
    off_vms_count = 0
    if not vms_df.empty:
        for col in ["name", "power_state"]:
            if col not in vms_df.columns:
                vms_df[col] = "UNKNOWN"
        off_vms_count = len(vms_df[vms_df["power_state"] != "poweredOn"])
        vm_detail = vms_df[["name", "power_state"]].copy()
        dcocfg.save_dataframe_to_csv(vm_detail, system, instance, "vmStatus")

    # --- D. Alerts Status & Detail ---
    alarms_df = pd.DataFrame(alarms)
    alerts_status = "OK"
    if not alarms_df.empty:
        # Only unacknowledged alarms affect status
        unacked = alarms_df[alarms_df["acknowledged"] == False]
        if not unacked.empty:
            if "red" in unacked["overall_status"].values:
                alerts_status = "Critical"
            elif "yellow" in unacked["overall_status"].values:
                alerts_status = "Warning"

        # Build detail CSV — same columns as VC module
        detail_cols = [
            "triggered_time", "overall_status", "acknowledged", "alarm_enabled",
            "acknowledged_time", "acknowledged_by", "entity_type", "entity_name",
            "alarm_name", "alarm_description"
        ]
        for col in detail_cols:
            if col not in alarms_df.columns:
                alarms_df[col] = None

        alerts_detail = alarms_df[detail_cols].copy()
        dcocfg.save_dataframe_to_csv(alerts_detail, system, instance, "alertsDetail")
    else:
        empty_df = pd.DataFrame(columns=[
            "triggered_time", "overall_status", "acknowledged", "alarm_enabled",
            "acknowledged_time", "acknowledged_by", "entity_type", "entity_name",
            "alarm_name", "alarm_description"
        ])
        dcocfg.save_dataframe_to_csv(empty_df, system, instance, "alertsDetail")

    # --- E. Final Summary CSV ---
    summary_data = [
        ["Host Health",        host_status],
        ["Datastore Capacity", ds_status],
        ["Active Alerts",      alerts_status],
        ["VMs Powered Off",    off_vms_count],
    ]
    summary_df = pd.DataFrame(summary_data, columns=["ESX Host", instance])
    dcocfg.save_dataframe_to_csv(summary_df, system, instance, "systemSummary")


def proccess_info(dcocfg, **kwargs):
    """
    Main entry point for processing ESX standalone data.
    Called by the DCO orchestrator.
    """
    logger.info(f"Starting {system} process phase")
    for instance in dcocfg.instances(system):
        try:
            process_esx_instance(dcocfg, instance)
            logger.info(f"Successfully processed {system}/{instance}")
        except Exception as e:
            logger.error(f"Error processing {system}/{instance}: {e}")


if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    proccess_info(dcocfg)
