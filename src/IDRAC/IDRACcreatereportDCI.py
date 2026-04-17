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

# Row-level color coding for logs
colorBySeverityRow = functools.partial(
    DCOreport.key_color_rows,
    column="Severity",
    key_color={
        "Critical": DCOreport.PASTEL_RED,
        "Warning": DCOreport.PASTEL_YELLOW}
)

def create_DCI(dcocfg, dcorpt):
    logger.info(f'Generating DCI for {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'Generating DCI for "{instance}"')

        # --- 1. Chassis ---
        df_chassis = dcocfg.load_csv_to_dataframe(system, instance, "chassis")
        if not df_chassis.empty:
            # Filter: Show only if Health or Health Rollup is not OK, or Status is not Enabled
            problems = df_chassis[
                (df_chassis["Health"] != "OK") | 
                (df_chassis["Health Rollup"] != "OK") | 
                (df_chassis["Status"] != "Enabled")
            ]
            if not problems.empty:
                chassis = DCOreport.table_base_styler(problems)
                chassis = DCOreport.apply_styler_map(chassis, colorByHealth, subset=["Health"])
                chassis = DCOreport.apply_styler_map(chassis, colorByHealth, subset=["Health Rollup"])
                chassis = DCOreport.apply_styler_map(chassis, colorByStatus, subset=["Status"])
                dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Chassis (Problems)", chassis, tableset="hardware1/col1")

        # --- 2. System ---
        df_sys = dcocfg.load_csv_to_dataframe(system, instance, "system")
        if not df_sys.empty:
            problems = df_sys[
                (df_sys["Health"] != "OK") | 
                (df_sys["Health Rollup"] != "OK") | 
                (df_sys["Status"] != "Enabled")
            ]
            if not problems.empty:
                system_hw = DCOreport.table_base_styler(problems)
                system_hw = DCOreport.apply_styler_map(system_hw, colorByPowerStatus, subset=["Power State"])
                system_hw = DCOreport.apply_styler_map(system_hw, colorByHealth, subset=["Health"])
                system_hw = DCOreport.apply_styler_map(system_hw, colorByHealth, subset=["Health Rollup"])
                system_hw = DCOreport.apply_styler_map(system_hw, colorByStatus, subset=["Status"])
                dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "System (Problems)", system_hw, tableset="hardware1/col1")

        # --- 3. Processors ---
        df_proc = dcocfg.load_csv_to_dataframe(system, instance, "processors")
        if not df_proc.empty:
            problems = df_proc[(df_proc["Health"] != "OK") | (df_proc["Status"] != "Enabled")]
            if not problems.empty:
                processors = DCOreport.table_base_styler(problems)
                processors = DCOreport.apply_styler_map(processors, colorByHealth, subset=["Health"])
                processors = DCOreport.apply_styler_map(processors, colorByStatus, subset=["Status"])
                dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Processors (Problems)", processors, tableset="hardware1/col1")

        # --- 4. Power Supplies ---
        df_psu = dcocfg.load_csv_to_dataframe(system, instance, "powersupplies")
        if not df_psu.empty:
            problems = df_psu[(df_psu["Health"] != "OK") | (df_psu["Status"] != "Enabled")]
            if not problems.empty:
                powersupplies = DCOreport.table_base_styler(problems)
                powersupplies = DCOreport.apply_styler_map(powersupplies, colorByHealth, subset=["Health"])
                powersupplies = DCOreport.apply_styler_map(powersupplies, colorByStatus, subset=["Status"])
                dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Power Supplies (Problems)", powersupplies, tableset="hardware1/col1")

        # --- 5. Fans ---
        df_fans = dcocfg.load_csv_to_dataframe(system, instance, "fans")
        if not df_fans.empty:
            problems = df_fans[(df_fans["Health"] != "OK") | (df_fans["Status"] != "Enabled")]
            if not problems.empty:
                fans = DCOreport.table_base_styler(problems)
                fans = DCOreport.apply_styler_map(fans, colorByHealth, subset=["Health"])
                fans = DCOreport.apply_styler_map(fans, colorByStatus, subset=["Status"])
                dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Fans (Problems)", fans, tableset="hardware1")

        # --- 6. Storage ---
        df_storage = dcocfg.load_csv_to_dataframe(system, instance, "storage")
        if not df_storage.empty:
            problems = df_storage[
                (df_storage["Health"] != "OK") | 
                (df_storage["Health Rollup"] != "OK") | 
                (df_storage["Status"] != "Enabled")
            ]
            if not problems.empty:
                storage = DCOreport.table_base_styler(problems)
                storage = DCOreport.apply_styler_map(storage, colorByHealth, subset=["Health"])
                storage = DCOreport.apply_styler_map(storage, colorByHealth, subset=["Health Rollup"])
                storage = DCOreport.apply_styler_map(storage, colorByStatus, subset=["Status"])
                dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Storage (Problems)", storage, tableset="hardware1/col1")

        # --- 7. Temperatures ---
        df_thermal = dcocfg.load_csv_to_dataframe(system, instance, "thermal")
        if not df_thermal.empty:
            problems = df_thermal[(df_thermal["Health"] != "OK") | (df_thermal["Status"] != "Enabled")]
            if not problems.empty:
                thermal = DCOreport.table_base_styler(problems)
                thermal = DCOreport.apply_styler_map(thermal, colorByHealth, subset=["Health"])
                thermal = DCOreport.apply_styler_map(thermal, colorByStatus, subset=["Status"])
                thermal = DCOreport.apply_styler_map(thermal, colorTempRows, subset=["Temp Cº"])
                dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "Temperatures (Problems)", thermal, tableset="hardware1")

        # --- 8. Event Logs ---
        log_sel_styled = DCOreport.csv_to_styleddf(system, instance, "log_sel", dcocfg)
        if not log_sel_styled.data.empty:
            log_sel_styled = log_sel_styled.apply(colorBySeverityRow, axis=1)
            log_sel_styled = DCOreport.column_wordwrap(log_sel_styled, "Message")
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "System Event Log", log_sel_styled, tableset="log_sel")

        log_lc_df = dcocfg.load_csv_to_dataframe(system, instance, "log_lc")
        if not log_lc_df.empty:
            problems_lc = log_lc_df[log_lc_df["Severity"] != "OK"]
            if not problems_lc.empty:
                log_lc = DCOreport.table_base_styler(problems_lc)
                log_lc = log_lc.apply(colorBySeverityRow, axis=1) 
                log_lc = DCOreport.column_wordwrap(log_lc, "Message")
                dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "LifeCycle Controller Log (Problems)", log_lc, tableset="log_lc")

        log_faults_styled = DCOreport.csv_to_styleddf(system, instance, "log_faults", dcocfg)
        if not log_faults_styled.data.empty:
            log_faults_styled = log_faults_styled.apply(colorBySeverityRow, axis=1)
            log_faults_styled = DCOreport.column_wordwrap(log_faults_styled, "Message")
            dcorpt.add_table("Compute", "Server / iDRAC", f"Instance {instance}", "FaultList Entries", log_faults_styled, tableset="log_faults")

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport(f'DCO Daily Check Investigation report for {system}')
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html(f'reports/{system}reportDCI.html')
