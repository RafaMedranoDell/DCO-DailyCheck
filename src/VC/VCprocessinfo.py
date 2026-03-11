import pandas as pd
import common.functions as fn
import logging

# Global variable for the system type
system = "VC"

# Configure module logger
logger = fn.get_module_logger(__name__)

def process_vc_instance(dcocfg, instance):
    """
    Processes the collected JSON data for a single vCenter instance.
    Generates summary and detailed CSV files.
    """
    # 1. Load JSON data
    logger.info(f"{system}/{instance}: Loading collected data...")
    appliance_health = dcocfg.load_json(system, instance, "appliance_health")
    hosts = dcocfg.load_json(system, instance, "hosts")
    datastores = dcocfg.load_json(system, instance, "datastores")
    vms = dcocfg.load_json(system, instance, "vms")

    # --- A. Appliance Health Status ---
    # Map green/yellow/red to OK/Warning/Critical
    raw_health = appliance_health.get("overall_health", "UNKNOWN").lower()
    health_map = {
        "green": "OK", 
        "yellow": "Warning", 
        "orange": "Warning", 
        "red": "Critical", 
        "gray": "Unknown"
    }
    vc_status = health_map.get(raw_health, "Unknown")

    # --- B. Hosts Status ---
    hosts_df = pd.DataFrame(hosts)
    if not hosts_df.empty:
        # 1. Critical: Any host NOT connected
        if (hosts_df["connection_state"] != "CONNECTED").any():
            hosts_status = "Critical"
        # 2. Warning: All connected, but some NOT powered on (e.g. Standby)
        elif (hosts_df["power_state"] != "POWERED_ON").any():
            hosts_status = "Warning"
        # 3. OK: All connected and powered on
        else:
            hosts_status = "OK"
    else:
        hosts_status = "Critical"

    # --- C. Datastores Status & Detail ---
    ds_df = pd.DataFrame(datastores)
    ds_status = "OK"
    if not ds_df.empty:
        # 1. Calculate % Used before unit conversion for precision
        ds_df["% Used"] = ((ds_df["capacity"] - ds_df["free_space"]) / ds_df["capacity"]) * 100
        
        # 2. Determine aggregate Status
        max_used = ds_df["% Used"].max()
        if max_used > 90:
            ds_status = "Critical"
        elif max_used > 80:
            ds_status = "Warning"
            
        # 3. Create detail for DCI report (Convert to TB)
        if "hosts" not in ds_df.columns:
            ds_df["hosts"] = "N/A"
            
        ds_detail = ds_df[["name", "type", "capacity", "free_space", "% Used", "hosts"]].copy()
        
        # Sort by hosts (replacing default sort)
        ds_detail = ds_detail.sort_values(by="hosts", ascending=True)
        
        ds_detail["Total (TB)"] = ds_detail["capacity"] / (1024**4)
        ds_detail["Free (TB)"] = ds_detail["free_space"] / (1024**4)
        
        # Reorder final columns (Hosts first)
        ds_detail = ds_detail[["hosts", "name", "type", "Total (TB)", "Free (TB)", "% Used"]]
        dcocfg.save_dataframe_to_csv(ds_detail, system, instance, "datastoreStatus")
    else:
        ds_status = "Critical"

    # --- D. VMs Status & Detail ---
    vms_df = pd.DataFrame(vms)
    off_vms_count = 0
    if not vms_df.empty:
        # Count only non-running VMs
        off_vms_count = len(vms_df[vms_df["power_state"] != "POWERED_ON"])
        
        # Create detail for DCI report
        # We use 'host_name' which was added during getinfo phase
        if "host_name" not in vms_df.columns:
            vms_df["host_name"] = "N/A"
            
        vm_detail = vms_df[["host_name", "name", "power_state"]].copy()
        
        # Sort by host for better readability
        vm_detail = vm_detail.sort_values(by="host_name", ascending=True)
        
        dcocfg.save_dataframe_to_csv(vm_detail, system, instance, "vmStatus")

    # --- E. Alerts Status & Detail ---
    alarms = dcocfg.load_json(system, instance, "alarms")
    alarms_df = pd.DataFrame(alarms)
    alerts_status = "OK"

    if not alarms_df.empty:
        # 1. Determine aggregate Status (Only unacknowledged alarms affect status)
        unacked_alarms = alarms_df[alarms_df["acknowledged"] == False]
        
        if not unacked_alarms.empty:
            # Check for critical/red alarms first
            if "red" in unacked_alarms["overall_status"].values:
                alerts_status = "Critical"
            elif "yellow" in unacked_alarms["overall_status"].values:
                alerts_status = "Warning"
        
        # 2. Create detail for DCI report (All alarms)
        # Select and reorder columns as requested
        detail_cols = [
            "triggered_time", "overall_status", "acknowledged", "alarm_enabled",
            "entity_type", "entity_name", "alarm_key", "alarm_name", "alarm_description"
        ]
        # Ensure all columns exist (fill with None if missing)
        for col in detail_cols:
            if col not in alarms_df.columns:
                alarms_df[col] = None
                
        alerts_detail = alarms_df[detail_cols].copy()
        dcocfg.save_dataframe_to_csv(alerts_detail, system, instance, "alertsDetail")
    else:
        # If no alarms at all, create empty detail file with headers
        empty_df = pd.DataFrame(columns=[
            "triggered_time", "overall_status", "acknowledged", "alarm_enabled",
            "entity_type", "entity_name", "alarm_key", "alarm_name", "alarm_description"
        ])
        dcocfg.save_dataframe_to_csv(empty_df, system, instance, "alertsDetail")

    # --- F. Final Summary CSV for Daily Check ---
    summary_data = [
        ["Appliance Health", vc_status],
        ["Hosts Connectivity", hosts_status],
        ["Datastore Capacity", ds_status],
        ["Active Alerts", alerts_status],
        ["VMs Powered Off", off_vms_count]
    ]
    # Header 1 is 'vSphere' as requested for the report
    summary_df = pd.DataFrame(summary_data, columns=["vSphere", instance])
    dcocfg.save_dataframe_to_csv(summary_df, system, instance, "systemSummary")

def proccess_info(dcocfg, **kwargs):
    """
    Main entry point for processing vCenter data.
    Called by the DCO orquestrator.
    """
    logger.info(f"Starting {system} process phase")
    for instance in dcocfg.instances(system):
        try:
            process_vc_instance(dcocfg, instance)
            logger.info(f"Successfully processed {system}/{instance}")
        except Exception as e:
            logger.error(f"Error processing {system}/{instance}: {e}")

if __name__ == "__main__":
    from common.DCOconfig import DCOconfig
    cfg = DCOconfig("config_encrypted.json")
    proccess_info(cfg)
