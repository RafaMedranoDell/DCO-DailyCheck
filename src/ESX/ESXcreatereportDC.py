import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

# Global variable for the system type
system = "ESX"


def color_status(val):
    """Standard coloring for OK/Warning/Critical."""
    color_map = {
        "OK":       DCOreport.PASTEL_GREEN,
        "Warning":  DCOreport.PASTEL_YELLOW,
        "Critical": DCOreport.PASTEL_RED,
    }
    return color_map.get(val, "")


def create_DC(dcocfg, dcorpt):
    """
    Entry point to add the ESX standalone summary table to the Daily Check report.
    """
    for instance in dcocfg.instances(system):
        df = dcocfg.load_csv_to_dataframe(system, instance, "systemSummary")

        if not df.empty:
            # Remove the VMs Powered Off row from the summary view
            df = df[df.iloc[:, 0] != "VMs Powered Off"]

            summary_df = DCOreport.table_base_styler(df)
            summary_df = DCOreport.format_by_rowid(summary_df, [
                ("Host Health",        color_status),
                ("Datastore Capacity", color_status),
                ("Active Alerts",      color_status),
            ])

            display_name = dcocfg.get_instance_display_name(system, instance)
            dcorpt.add_table("Compute", "ESX", display_name, "System Summary", summary_df)


if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport("ESX Standalone Daily Check TEST")
    create_DC(dcocfg, dcorpt)
    dcorpt.save_html("test_esx_report.html")
