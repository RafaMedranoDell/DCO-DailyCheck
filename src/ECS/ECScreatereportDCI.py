import functools
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

def colorRedNonZero(val):
    return DCOreport.PASTEL_RED if val else ''

def colorYellowNonZero(val):
    return DCOreport.PASTEL_YELLOW if val else ''

def colorBlueNonZero(val):
    return DCOreport.PASTEL_BLUE if val else ''

colorByPercent = functools.partial(
    DCOreport.rate_num_value,
    rate_intervals=[0, 80, 90, 100],
    rating=DCOreport.COLORS_GYR,
    force_conversion=True
)

def colorAlertBySeverity(row):
    return DCOreport.key_color_rows(
        row,
        column="Severity",
        key_color={
            "CRITICAL": DCOreport.PASTEL_RED, 
            "ERROR": DCOreport.PASTEL_RED, 
            "WARNING": DCOreport.PASTEL_YELLOW,
            "INFO": DCOreport.PASTEL_BLUE
        })

def create_DCI(dcocfg, dcorpt):
    system = "ECS"
    for instance in dcocfg.instances(system):
        full_name = dcocfg.get_instance_full_name(system, instance)

        # --- 1. Nodes Table (Exception-based) ---
        nodes_sdf = DCOreport.csv_to_styleddf(system, instance, 'nodes', dcocfg)
        if not nodes_sdf.data.empty:
            df = nodes_sdf.data
            key_col, val_col = df.columns[0], df.columns[1]
            try:
                # Detect issues
                bad = int(df.loc[df[key_col] == 'Bad Nodes', val_col].iloc[0])
                maint = int(df.loc[df[key_col] == 'Maintenance Nodes', val_col].iloc[0])
                
                if bad > 0 or maint > 0:
                    # Filter rows: Keep Total, and any other where value > 0, excluding Good Nodes
                    mask = (df[key_col] == 'Total Nodes') | ((df[val_col].astype(int) > 0) & (df[key_col] != 'Good Nodes'))
                    filtered_df = df[mask]
                    
                    # Create new styler for the filtered data
                    nodes_sdf = DCOreport.table_base_styler(filtered_df, fixed=True)
                    nodes_sdf = DCOreport.format_by_rowid(
                        nodes_sdf,
                        [("Bad Nodes", colorRedNonZero),
                        ("Maintenance Nodes", colorYellowNonZero)])
                    dcorpt.add_table("Storage", "ECS", full_name, 'Nodes', nodes_sdf, "ts1")
            except Exception as e:
                logger.error(f"Error processing Nodes exceptions for {instance}: {e}")

        # --- 2. Disks Table (Exception-based) ---
        disks_sdf = DCOreport.csv_to_styleddf(system, instance, 'disks', dcocfg)
        if not disks_sdf.data.empty:
            df = disks_sdf.data
            key_col, val_col = df.columns[0], df.columns[1]
            try:
                # Detect issues
                bad = int(df.loc[df[key_col] == 'Bad Disks', val_col].iloc[0])
                maint = int(df.loc[df[key_col] == 'Maintenance Disks', val_col].iloc[0])
                
                if bad > 0 or maint > 0:
                    # Filter rows: Keep Total, and any other where value > 0, excluding Good Disks
                    mask = (df[key_col] == 'Total Disks') | ((df[val_col].astype(int) > 0) & (df[key_col] != 'Good Disks'))
                    filtered_df = df[mask]
                    
                    # Create new styler for the filtered data
                    disks_sdf = DCOreport.table_base_styler(filtered_df, fixed=True)
                    disks_sdf = DCOreport.format_by_rowid(
                        disks_sdf,
                        [("Bad Disks", colorRedNonZero),
                        ("Maintenance Disks", colorYellowNonZero)])
                    dcorpt.add_table("Storage", "ECS", full_name, 'Disks', disks_sdf, "ts1")
            except Exception as e:
                logger.error(f"Error processing Disks exceptions for {instance}: {e}")

        # --- 3. Space Table (Always visible) ---

        space_sdf = DCOreport.csv_to_styleddf(system, instance,  'space', dcocfg)
        if not space_sdf.data.empty:
            space_sdf = DCOreport.format_by_rowid(space_sdf, [("Space Allocated (%)", colorByPercent)] )
            space_sdf = DCOreport.format_nums_by_rowid(space_sdf, "Space Total (TB)", "{:,.2f}")
            space_sdf = DCOreport.format_nums_by_rowid(space_sdf, "Space Allocated (TB)", "{:,.2f}")
            space_sdf = DCOreport.format_nums_by_rowid(space_sdf, "Space Free (TB)", "{:,.2f}")
            space_sdf = DCOreport.format_nums_by_rowid(space_sdf, "Space Allocated (%)", "{:.2f}")
            dcorpt.add_table("Storage", "ECS", full_name, 'Space', space_sdf, "ts1")

        alertDetail = DCOreport.csv_to_styleddf(system, instance,  "alertsDetail", dcocfg)
        if not alertDetail.data.empty:
            alertDetail = DCOreport.column_wordwrap(alertDetail, columns=['Description'])
            alertDetail = alertDetail.apply(colorAlertBySeverity, axis=1)
            dcorpt.add_table("Storage", "ECS", full_name, "Alert Detail", alertDetail, "ts2")

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    dcorpt = DCOreport.DCOreport("ECS")
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html("reports/ECSreportDCI.html")
