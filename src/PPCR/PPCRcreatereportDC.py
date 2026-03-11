import common.functions as fn
import functools
from datetime import datetime
from common.DCOconfig import DCOconfig
import common.DCOreport as DCOreport

sectionStyle = functools.partial(
    DCOreport.key_color_rows,
    column="CyberRecovery",
    key_color={
        'System Status': 'font-weight: bold; background-color: #e0e0e0;',
        'Jobs Status': 'font-weight: bold; background-color: #e0e0e0;',
        'License Status': 'font-weight: bold; background-color: #e0e0e0;'}
)                                
                             
def colorAlertsBySeverityVal(val):
    color_rules = {
        "Critical": DCOreport.PASTEL_RED,
        "Warning": DCOreport.YELLOW,
        "Running": DCOreport.PASTEL_ORANGE,
        "OK": DCOreport.GREEN}
    return DCOreport.key_color_value(val, key_color=color_rules)

def colorByPoliciesRatioOk(val):
    try:
        policies_ok, policies_total = map(int, val.split('/'))
    except ValueError:
        return
    if policies_ok == policies_total:
        return DCOreport.GREEN
    elif policies_ok == 0:
        return DCOreport.PASTEL_RED
    else:
        return DCOreport.YELLOW

def colorByCScapacity(val):
    return DCOreport.rate_num_value(val, [0, 80, 90, 100], DCOreport.COLORS_GYR, force_conversion=True)

def colorByCSdays(val):
    return DCOreport.rate_num_value(val, [0, 30, 90, 10000], DCOreport.COLORS_RYG, force_conversion=True)
def colorByExpirationDate(val):
    try:
        exp_date = datetime.strptime(val, "%Y-%m-%d")
        days_left = (exp_date - datetime.now()).days
        if days_left < 90:
            return DCOreport.PASTEL_RED
        elif days_left < 180:
            return DCOreport.YELLOW
        else:
            return DCOreport.GREEN
    except Exception:
        return ""

def create_DC(dcocfg, dcorpt):
    system = "PPCR"

    # Get summarized dataframe for all the instances of this system type
    summaryDf = fn.systemSummary(system, 'CyberRecovery', "systemSummary", dcocfg)
    if not summaryDf.empty:
        # Apply base style with equal width columns (fixed) to the sumarized dataframe
        summaryDfsty = DCOreport.table_base_styler(summaryDf, fixed=True)

        # Bold text and background for titles
        summaryDfsty = summaryDfsty.apply(sectionStyle, axis=1)
        # Colorize the data columns
        summaryDfsty = DCOreport.format_by_rowid(
            summaryDfsty,
            [
                ("System Alerts", colorAlertsBySeverityVal),
                ("Security Alerts", colorAlertsBySeverityVal),
                ("System Jobs", colorAlertsBySeverityVal),
                ("Protection Jobs", colorAlertsBySeverityVal),
                ("Recovery Jobs", colorAlertsBySeverityVal),
                ("Protection Jobs running for more than 24hrs", colorAlertsBySeverityVal),
                ("CyberSense license / usage (%)", colorByCScapacity),
                ("License Expiration Date", colorByExpirationDate)
            ]
        )
        summaryDfsty = DCOreport.format_nums_by_rowid(summaryDfsty, "Total License Capacity (TB)", "{:.2f}")
        summaryDfsty = DCOreport.format_nums_by_rowid(summaryDfsty, "CyberSense license / usage (%)", "{:.2f}")
        # Add table to the report
        dcorpt.add_table("Protection", "Power Protect", "", "CyberRecovery", summaryDfsty)

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport("DCO Daily Check report")
    create_DC(dcocfg, dcorpt)
    dcorpt.save_html("reports/PPCRreportDC.html")
