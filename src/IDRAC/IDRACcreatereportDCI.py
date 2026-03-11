import functools
import common.functions as fn
from common.DCOconfig import DCOconfig
import common.DCOreport as DCOreport

# Global variable that defines the type of system this file works with
system = "IDRAC"

# Configure module logger
logger = fn.get_module_logger(__name__)

# Define formatting functions
def colorRowByStatus(row):
    if row["Health"] == "OK" and row["Status"] == "Enabled":
        return [DCOreport.PASTEL_GREEN] * len(row)
    else:
        return [DCOreport.PASTEL_RED] * len(row)

def colorTempRows(val):
    return DCOreport.rate_num_value(
        val,
        rate_intervals=[0, 45, 60, 100],
        rating=DCOreport.COLORS_GYR,
        force_conversion=True)

def colorByHealth(val):
    return DCOreport.key_color_value(val,
        key_color={
            "Critical": DCOreport.PASTEL_RED,
            "Warning": DCOreport.PASTEL_YELLOW,
            "Unknown": '',
            "OK": DCOreport.PASTEL_GREEN},
        def_color=DCOreport.PASTEL_ORANGE)

def colorByStatus(val):
    return DCOreport.PASTEL_GREEN if val == 'Enabled' else DCOreport.PASTEL_RED

def colorByPowerStatus(val):
    return DCOreport.PASTEL_GREEN if val == 'On' else DCOreport.PASTEL_RED

def create_DCI(dcocfg, dcorpt):
    logger.info(f'Generating DCI for {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'Generating DCI for "{instance}"')
        chassis = DCOreport.csv_to_styleddf(system, instance,  "chassis", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not chassis.data.empty:
            chassis = DCOreport.apply_styler_map(chassis, colorByHealth, subset=["Health"])
            chassis = DCOreport.apply_styler_map(chassis, colorByHealth, subset=["Health Rollup"])
            chassis = DCOreport.apply_styler_map(chassis, colorByStatus, subset=["Status"])
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Chassis", chassis, tableset="hardware1/col1")

        system_hw = DCOreport.csv_to_styleddf(system, instance,  "system", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not system_hw.data.empty:
            system_hw = DCOreport.apply_styler_map(system_hw, colorByPowerStatus, subset=["Power State"])
            system_hw = DCOreport.apply_styler_map(system_hw, colorByHealth, subset=["Health"])
            system_hw = DCOreport.apply_styler_map(system_hw, colorByHealth, subset=["Health Rollup"])
            system_hw = DCOreport.apply_styler_map(system_hw, colorByStatus, subset=["Status"])
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "System", system_hw, tableset="hardware1/col1")

        processors = DCOreport.csv_to_styleddf(system, instance,  "processors", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not processors.data.empty:
            processors = DCOreport.apply_styler_map(processors, colorByHealth, subset=["Health"])
            processors = DCOreport.apply_styler_map(processors, colorByStatus, subset=["Status"])
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Processors", processors, tableset="hardware1/col1")

        powersupplies = DCOreport.csv_to_styleddf(system, instance, "powersupplies", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not powersupplies.data.empty:
            powersupplies = DCOreport.apply_styler_map(powersupplies, colorByHealth, subset=["Health"])
            powersupplies = DCOreport.apply_styler_map(powersupplies, colorByStatus, subset=["Status"])
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Power Supplies", powersupplies, tableset="hardware1/col1")

        fans = DCOreport.csv_to_styleddf(system, instance, "fans", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not fans.data.empty:
            fans = DCOreport.apply_styler_map(fans, colorByHealth, subset=["Health"])
            fans = DCOreport.apply_styler_map(fans, colorByStatus, subset=["Status"])
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Fans", fans, tableset="hardware1")

        storage = DCOreport.csv_to_styleddf(system, instance, "storage", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not storage.data.empty:
            storage = DCOreport.apply_styler_map(storage, colorByHealth, subset=["Health"])
            storage = DCOreport.apply_styler_map(storage, colorByHealth, subset=["Health Rollup"])
            storage = DCOreport.apply_styler_map(storage, colorByStatus, subset=["Status"])
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Storage", storage, tableset="hardware1/col1")

        thermal = DCOreport.csv_to_styleddf(system, instance, "thermal", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not thermal.data.empty:
            thermal = DCOreport.apply_styler_map(thermal, colorByHealth, subset=["Health"])
            thermal = DCOreport.apply_styler_map(thermal, colorByStatus, subset=["Status"])
            thermal = DCOreport.apply_styler_map(thermal, colorTempRows, subset=["Temp Cº"])
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Temperatures", thermal, tableset="hardware1")

        log_sel = DCOreport.csv_to_styleddf(system, instance,  "log_sel", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not log_sel.data.empty:
            log_sel = DCOreport.column_wordwrap(log_sel, "Message")
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "System Event Log", log_sel, tableset="log_sel")

        log_lc = DCOreport.csv_to_styleddf(system, instance,  "log_lc", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not log_lc.data.empty:
            log_lc = DCOreport.column_wordwrap(log_lc, "Message")
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "LifeCycle Controller Log", log_lc, tableset="log_lc")

        log_faults = DCOreport.csv_to_styleddf(system, instance,  "log_faults", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not log_faults.data.empty:
            log_faults = DCOreport.column_wordwrap(log_faults, "Message")
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "FaultList log", log_faults, tableset="log_faults")

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport(f'DCO Daily Check Investigation report for {system}')
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html(f'reports/{system}reportDCI.html')
