import functools
import logging
from datetime import datetime
import common.functions as fn
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

sectionStyle = functools.partial(
    DCOreport.key_color_rows,
    column="Data Domain",
    key_color={
        'System Status': 'font-weight: bold; background-color: #e0e0e0;',
        'Capacity Status': 'font-weight: bold; background-color: #e0e0e0;'}
)

colorByStatus = functools.partial(
    DCOreport.key_color_value,
    key_color={"OK": DCOreport.PASTEL_GREEN},
    def_color=DCOreport.PASTEL_RED
)

colorByPercent = functools.partial(
    DCOreport.rate_num_value,
    rate_intervals=[0, 70, 85, 100],
    rating=DCOreport.COLORS_GYR,
    force_conversion=True
)

def colorByUptime(val):
    try:
        boot_date = datetime.strptime(val, fn.DCO_DATETIME_FMT)
        if (datetime.now() - boot_date).days < 1:
            return DCOreport.PASTEL_RED
        return DCOreport.PASTEL_GREEN
    except Exception:
        return DCOreport.PASTEL_RED


def create_DC(dcocfg, dcorpt):
    system = "DD"

    # Get summarized dataframe for all the instances of this system type
    summaryDf = fn.systemSummary(system, "Data Domain", "systemSummary", dcocfg)
    
    if not summaryDf.empty:
        # Check if "Cloud Tier Used (%)" should be hidden (hide only if all instances are 0)
        cloud_row_label = "Cloud Tier Used (%)"
        combined_row_label = "Combined Used (%)"
        
        cloud_tier_row = summaryDf[summaryDf['Data Domain'] == cloud_row_label]
        if not cloud_tier_row.empty:
            instance_cols = [c for c in summaryDf.columns if c != 'Data Domain']
            all_zero = True
            for col in instance_cols:
                val = cloud_tier_row[col].values[0]
                try:
                    if float(val) != 0:
                        all_zero = False
                        break
                except (ValueError, TypeError):
                    # If it's "N/A" or non-numeric, we show the rows (Case 2)
                    all_zero = False
                    break
            
            if all_zero:
                # Remove both Cloud Tier Used (%) and Combined Used (%)
                summaryDf = summaryDf[~summaryDf['Data Domain'].isin([cloud_row_label, combined_row_label])]

    if not summaryDf.empty:
        # Filter out rows we don't want to show in the DC report
        summaryDf = summaryDf[summaryDf['Data Domain'] != 'Last Cleaning Success']

        # Apply base style with equal width columns (fixed) to the sumarized dataframe
        summaryDfsty = DCOreport.table_base_styler(summaryDf, fixed=True)

        # Bold text and background for titles
        summaryDfsty = summaryDfsty.apply(sectionStyle, axis=1)

        # Apply 2 decimal format to specific rows
        summaryDfsty = DCOreport.format_nums_by_rowid(summaryDfsty, "Active Tier Used (%)", "{:.2f}")
        summaryDfsty = DCOreport.format_nums_by_rowid(summaryDfsty, "Cloud Tier Used (%)", "{:.2f}")
        summaryDfsty = DCOreport.format_nums_by_rowid(summaryDfsty, "Combined Used (%)", "{:.2f}")

        # Apply format based on row names
        summaryDfsty = DCOreport.format_by_rowid(
            summaryDfsty,
            [
                ("System Alerts", colorByStatus),
                ("Filesystem Status", colorByStatus),
                ("Filesystem Uptime", colorByUptime),
                ("Active Tier Used (%)", colorByPercent),
                ("Cloud Tier Used (%)", colorByPercent),
                ("Combined Used (%)", colorByPercent)
            ]
            )

        # Add table to the report
        dcorpt.add_table("Protection", "Data Domain", "", "", summaryDfsty)

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), "DDdebug", level=logging.DEBUG)
    dcorpt = DCOreport.DCOreport("DCO Daily Check report")
    create_DC(dcocfg, dcorpt)
    dcorpt.save_html("reports/DDreportDC.html")
