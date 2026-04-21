import functools
import logging
import common.functions as fn
from common.DCOconfig import DCOconfig
import common.DCOreport as DCOreport

color_severity = functools.partial(
    DCOreport.key_color_rows,
    column="severity",
    key_color={"LOW": DCOreport.PASTEL_YELLOW, "MEDIUM": DCOreport.PASTEL_ORANGE, "HIGH": DCOreport.PASTEL_RED}
)

def create_DCI(dcocfg, dcorpt):
    system = "PPDM"
    for instance in dcocfg.instances(system):
        full_name = dcocfg.get_instance_full_name(system, instance)
        healthSystemStatus = DCOreport.csv_to_styleddf(system, instance,  "healthSystemStatus", dcocfg)
        if not healthSystemStatus.data.empty:
            #healthSystemStatus = healthSystemStatus.apply(color_severity, axis=1)
            #healthSystemStatus = DCOreport.column_wordwrap(healthSystemStatus, ["detailedDescription", "responseAction"])
            dcorpt.add_table("Protection", "PowerProtect DataManager", full_name, "Health Status", healthSystemStatus, tableset="ts1")

        # Add all the tables without formating
        healthByCategory = DCOreport.csv_to_styleddf(system, instance,  "healthByCategory", dcocfg)
        if not healthByCategory.data.empty:
            dcorpt.add_table("Protection", "PowerProtect DataManager", full_name, "Health By Category", healthByCategory, tableset="ts1")

        jobgroupSummary = DCOreport.csv_to_styleddf(system, instance,  "jobgroupSummary", dcocfg)
        if not jobgroupSummary.data.empty:
            dcorpt.add_table("Protection", "PowerProtect DataManager", full_name, "Job Group Summary", jobgroupSummary, tableset="ts2")

        jobgroupRate = DCOreport.csv_to_styleddf(system, instance,  "jobgroupRate", dcocfg)
        if not jobgroupRate.data.empty:
            dcorpt.add_table("Protection", "PowerProtect DataManager", full_name, "Job Group Rate", jobgroupRate, tableset="ts2")

        healthEvents = DCOreport.csv_to_styleddf(system, instance,  "healthEvents", dcocfg)
        if not healthEvents.data.empty:
            dcorpt.add_table("Protection", "PowerProtect DataManager", full_name, "Health Events", healthEvents, tableset="ts3")

        storageSystems = DCOreport.csv_to_styleddf(system, instance,  "storageSystems", dcocfg)
        if not storageSystems.data.empty:
            dcorpt.add_table("Protection", "PowerProtect DataManager", full_name, "Storage Systems", storageSystems, tableset="ts5")

if __name__ == "__main__":
    # Load configuration and create a report
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), "PPDMdebug", level=logging.DEBUG)
    dcorpt = DCOreport.DCOreport("PowerProtect DataManager")
    create_DCI(dcocfg, dcorpt)
    dcorpt.save_html("reports/PPDMreportDCI.html")
