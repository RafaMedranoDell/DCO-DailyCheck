import functools
import common.functions as fn
from common.DCOconfig import DCOconfig
import common.DCOreport as DCOreport

# Global variable that defines the type of system this file works with
system = "product"

# Configure module logger
logger = fn.get_module_logger(__name__)

# Define formatting functions
def colorAlertsBySeverityRow(row):
    color = [''] # Default color
    if row['Severity'] in ['Critical']:
        color = [DCOreport.GREEN] if row['Count'] == 0 else [DCOreport.PASTEL_RED]
    elif row['Severity'] in ['Warning']:
        color = [DCOreport.GREEN] if row['Count'] == 0 else [DCOreport.YELLOW]
    return color * len(row)

def colorAlertsBySeverityVal(value):
    return DCOreport.key_color_value(
        value,
        key_color={"Critical": DCOreport.PASTEL_RED, "Warning": DCOreport.YELLOW, "OK": DCOreport.GREEN})

def color_jobsByStatus(row):
    return DCOreport.key_color_rows(
        row,
        column="Status",
        key_color={"Critical": DCOreport.PASTEL_RED, "Warning": DCOreport.YELLOW})

def colorByUsage(value):
    return DCOreport.rate_num_value(
        value,
        rate_intervals=[0, 75, 90, 100],
        rating=DCOreport.COLORS_RYG,
        force_conversion=True)

def create_DCI(dcocfg, dcorpt):
    logger.info(f'Generating DCI for {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'Generating DCI for "{instance}"')

        systemSummary = DCOreport.csv_to_styleddf(system, instance,  "systemSummary", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not systemSummary.data.empty:
            systemSummary = DCOreport.apply_styler_map(systemSummary, colorAlertsBySeverityVal, subset=[instance])
            dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "Summary", systemSummary, tableset="ts1")

        alertSummary = DCOreport.csv_to_styleddf(system, instance, "alertSummary", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not alertSummary.data.empty:
            alertSummary = alertSummary.apply(colorAlertsBySeverityRow, axis=1)
            dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "Alerts by severity", alertSummary, tableset="ts1")

        alertDetail = DCOreport.csv_to_styleddf(system, instance, "alertDetail", dcocfg)
        # Confirm styled dataframe has data before formatting it
        if not alertDetail.data.empty:
            alertDetail = DCOreport.column_wordwrap(alertDetail, columns=['Summary', 'Remedy'])
            alertDetail = alertDetail.apply(colorAlertBySeverityRowDeta, axis=1)
            dcorpt.add_table("Protection", "PowerProtect Cyber Recovery", f"Instance {instance}", "Alert detail", alertDetail, tableset="ts2")

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport(f'DCO Daily Check Investigation report for {system}')
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html(f'reports/{system}reportDCI.html')
