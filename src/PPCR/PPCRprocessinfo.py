import logging
from datetime import datetime
import pandas as pd
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "PPCR"

# Configure module logger
logger = fn.get_module_logger(__name__)

def process_alerts(data, system, instance, dcocfg):
    alerts = pd.DataFrame(data)

    # Filter not acknowledged and count them by severity
    active_alerts = alerts[alerts["acknowledged"]==False]
    severity_counts = active_alerts["severity"].value_counts()

    # Load the result in a dataframe with relevant severities
    relevant_severities = ['Critical', 'Warning']
    severity_counts = severity_counts.reindex(relevant_severities, fill_value=0).reset_index()

    # Rename the columns for the CSV
    severity_counts = severity_counts.rename(columns={"severity": "Severity", "count": "Count"})

    # Save the alert summary as a CSV
    dcocfg.save_dataframe_to_csv(severity_counts, system, instance, "alertSummary")

    selected_columns = {
        'type': 'Type',
        'category': 'Category',
        'severity': 'Severity',
        'creationDate': 'Creation Date',
        'modifiedDate': 'Modified Date',
        'acknowledged': 'Acknowledged',
        'summary': 'Summary',
        'remedy': 'Remedy'
    }
    system_status = fn.get_most_critical(active_alerts[active_alerts["category"] == "system"], "severity", ["Critical", "Warning"], "OK")
    security_status = fn.get_most_critical(active_alerts[active_alerts["category"] == "security"], "severity", ["Critical", "Warning"], "OK")

    active_alerts = fn.df_timestamps_to_dates(active_alerts, ["creationDate", "modifiedDate"])
    active_alerts = active_alerts.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)

    # Rename and select columns, and save to the CSV
    dcocfg.save_dataframe_to_csv(active_alerts, system, instance, "alertDetail")

    return system_status, security_status

def process_policies(data, system, instance, dcocfg):
    policies = pd.DataFrame(data)

    current_time = dcocfg.get_param("script_start_time")

    # Load the protectionJobs not finished and the their policies
    unfinishedJobs = dcocfg.load_csv_to_dataframe(system, instance, "protectionJobs")
    policiesWithUnfinishedJobs = set(unfinishedJobs["Policy name"].unique())

    # Compute the elapsed time since the last update in each policy
    policies['elapsed_seconds'] = (int(current_time.timestamp()) - pd.to_numeric(policies['modifiedDate']))

    # Format the elapsed time
    policies['Time since last update'] = policies['elapsed_seconds'].apply(fn.format_duration)

    # Mark policies with not unfinished jobs as "bad" seting their duration to 25 hours (workaround)
    policies.loc[policies["policyName"].isin(policiesWithUnfinishedJobs), "elapsed_seconds"] = 3600*25

    # Get the total number of policies and the number of policies not updated in the last 24 hours
    policies_count = len(policies)
    policies_ok = len(policies[policies['elapsed_seconds']<3600*24])

    # Reformat the last update timestamp
    policies = fn.df_timestamps_to_dates(policies, ["modifiedDate"])
    # Convert to string to allow setting "-" without FutureWarning
    policies["modifiedDate"] = policies["modifiedDate"].astype(str)

    # Overwrite info for policies with not unfinished jobs
    policies.loc[policies["policyName"].isin(policiesWithUnfinishedJobs), "Time since last update"] = "Check jobs"
    policies.loc[policies["policyName"].isin(policiesWithUnfinishedJobs), "modifiedDate"] = "-"

    selected_columns = {
        "policyName": "Policy Name",
        "numCopies": "# Copies",
        "modifiedDate": "Update date",
        "Time since last update": "Time since last update",
        "elapsed_seconds": "elapsed_seconds"
    }
    # Rename and select columns, and save to the CSV
    policies = policies.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)
    dcocfg.save_dataframe_to_csv(policies, system, instance, "policiesDetail")

    return f'{policies_ok} / {policies_count}'

def process_jobs_by_type(df, jobType, dcocfg):
    # Filter by time including empty dates (running/unfinished jobs)
    df = fn.filter_by_time(df, "endTime", "epoch", dcocfg.get_param("start_time"), include_nat=True)

    jobs = df[df["jobType"]==jobType]

    # Filter no "success" jobs and set the index to the job_id (needed for the join)
    jobs_nosucccessfull = jobs[jobs["status"] != "Success"].set_index("id")

    # Get the tasks in the non succesfull jobs and set index to the job_id (needed for the join)
    tasks_nosucccessfull = jobs_nosucccessfull.explode('tasks').reset_index(drop=True)
    tasks_nosucccessfull = pd.json_normalize(tasks_nosucccessfull["tasks"])
    # Add columns if not present
    tasks_nosucccessfull = tasks_nosucccessfull.reindex(columns=["taskAction", "taskStatus", "jobID"])
    tasks_nosucccessfull = tasks_nosucccessfull[tasks_nosucccessfull["taskStatus"] != "Success"].set_index("jobID")

    # Join both non succesfull jobs and tasks in one dataframe using index "id" and "jobID"
    jobs_tasks_nosucccessfull = jobs_nosucccessfull.join(tasks_nosucccessfull, lsuffix="_job", rsuffix="_task")

    # Translate timestamps to human readable dates/times
    jobs_tasks_nosucccessfull = fn.df_reformat_dates(jobs_tasks_nosucccessfull, ["startTime", "endTime"], 'epoch')

    # Return only the relevant columns
    selected_columns = {
        "policyName": "Policy name",
        "status": "Status",
        "startTime": "Start time",
        "endTime": "End time",
        "elapsedTime": "Elapsed seconds",
        "taskAction": "Last task",
        "taskStatus": "Last task status",
        "statusDetail": "Detailed description"
    }

    # Add/filter columns columns if not present
    #jobs_tasks_nosucccessfull = jobs_tasks_nosucccessfull.reindex(columns=selected_columns)
    return jobs_tasks_nosucccessfull.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)

def process_system_jobs(data, system, instance, dcocfg):
    # 1. Proccess system jobs for the detailed CSV (includes all failures/running)
    df = pd.DataFrame(data)
    system_jobs_fail_df = process_jobs_by_type(df, "System", dcocfg)
    dcocfg.save_dataframe_to_csv(system_jobs_fail_df, system, instance, "systemJobs")

    # 2. Calculate summary status for the DC report (New logic: only finished jobs)
    start_time = dcocfg.get_param("start_time")
    df_system = df[df["jobType"] == "System"]

    # filter_by_time with include_nat=False drops rows with null endTime
    df_finished = fn.filter_by_time(df_system, "endTime", "epoch", start_time, include_nat=False)

    if df_finished.empty:
        return "OK"

    # Identify failures among finished jobs
    failures = df_finished[df_finished["status"] != "Success"]
    if failures.empty:
        return "OK"

    # Return the most critical status (Critical/Warning) based on the severity field
    return fn.get_most_critical(failures, "status", ["Critical", "Warning"], "Critical")

def process_protection_jobs(data, system, instance, dcocfg):
    # 1. Proccess Protections jobs for the detailed CSV (includes all failures/running)
    df = pd.DataFrame(data)
    protection_jobs_fail_df = process_jobs_by_type(df, "Protection", dcocfg)
    dcocfg.save_dataframe_to_csv(protection_jobs_fail_df, system, instance, "protectionJobs")

    # 2. Calculate summary status for the DC report (New logic: only finished jobs)
    start_time = dcocfg.get_param("start_time")
    df_protection = df[df["jobType"] == "Protection"]

    # filter_by_time with include_nat=False (default) drops rows with null endTime
    df_finished = fn.filter_by_time(df_protection, "endTime", "epoch", start_time, include_nat=False)

    if df_finished.empty:
        return "OK"

    # Identify failures among finished jobs
    failures = df_finished[df_finished["status"] != "Success"]
    if failures.empty:
        return "OK"

    # Return the most critical status (Critical/Warning) based on the severity field
    return fn.get_most_critical(failures, "status", ["Critical", "Warning"], "Critical")

def process_recovery_jobs(data, system, instance, dcocfg):
    # 1. Proccess recovery jobs for the detailed CSV (includes all failures/running)
    df = pd.DataFrame(data)
    recovery_jobs_fail_df = process_jobs_by_type(df, "Recovery", dcocfg)
    dcocfg.save_dataframe_to_csv(recovery_jobs_fail_df, system, instance, "recoveryJobs")

    # 2. Calculate summary status for the DC report (New logic: only finished jobs)
    start_time = dcocfg.get_param("start_time")
    df_recovery = df[df["jobType"] == "Recovery"]

    # filter_by_time with include_nat=False drops rows with null endTime
    df_finished = fn.filter_by_time(df_recovery, "endTime", "epoch", start_time, include_nat=False)

    if df_finished.empty:
        return "OK"

    # Identify failures among finished jobs
    failures = df_finished[df_finished["status"] != "Success"]
    if failures.empty:
        return "OK"

    # Return the most critical status (Critical/Warning) based on the severity field
    return fn.get_most_critical(failures, "status", ["Critical", "Warning"], "Critical")

def process_protection_long_running(data, system, instance, dcocfg):
    df = pd.DataFrame(data)
    current_time = dcocfg.get_param("script_start_time")
    # Marginal time: 24 hours ago
    threshold_time = int((current_time - pd.Timedelta(hours=24)).timestamp())

    # Filter: jobType Protection, Running (no endTime), and started before threshold
    long_running = df[
        (df["jobType"] == "Protection") & 
        (df["endTime"].isna() | (df["endTime"] == 0)) & 
        (pd.to_numeric(df["startTime"], errors='coerce') < threshold_time)
    ]

    if not long_running.empty:
        return "Warning"
    
    return "OK"

def process_tasks_status(data, system, instance, dcocfg):
    df = pd.DataFrame(data)
    protection_jobs = process_jobs_by_type(df, "Protection", dcocfg)
    analyze_tasks = protection_jobs[protection_jobs["Last task"]=="analyze"]
    analyze_tasks_status = fn.get_most_critical(analyze_tasks, "Last task status", ["Critical", "Warning", "Running"], "OK")
    return analyze_tasks_status

def process_cs_info(data, system, instance, dcocfg):
    licenseInfo = fn.get_nested(data, ['summary', 'licenseUsageSummary', 0])

    # Process capacity info
    # Ensure precision by calculating from raw bytes first
    raw_total = licenseInfo["totalCapacity"]
    raw_used = licenseInfo["usedCapacity"]
    used_pct = (raw_used / raw_total) * 100 if raw_total > 0 else 0
    
    total_space_tb = raw_total / (1024**4)
    used_space_tb = raw_used / (1024**4)

    capacityData = [['Used capacity (TB)', used_space_tb], ['Total capacity (TB)', total_space_tb], ['Used percent (%)', used_pct]]
    df_cap = pd.DataFrame(capacityData, columns=[licenseInfo["nickName"], licenseInfo["server"]])
    dcocfg.save_dataframe_to_csv(df_cap, system, instance, "cs_capacity")

    # Process expiration time info with error handling and Remaining Days
    try:
        expirationTS = int(licenseInfo.get("expirationDate", 0))
        if expirationTS > 0:
            exp_dt = datetime.fromtimestamp(expirationTS)
            exp_date = exp_dt.strftime("%Y-%m-%d")
            days_left = (exp_dt - datetime.now()).days
        else:
            exp_date, days_left = "N/A", "N/A"
    except (ValueError, TypeError, OSError):
        exp_date, days_left = "Error", "N/A"

    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expirationData = [['Report date', report_date], ['Expiration date', exp_date], ['Remaining days', days_left]]
    df_exp = pd.DataFrame(expirationData, columns=[licenseInfo["nickName"], licenseInfo["server"]])
    dcocfg.save_dataframe_to_csv(df_exp, system, instance, "cs_expiration")

    return total_space_tb, used_pct, exp_date

def proccess_info(dcocfg):
    """
    Main function that coordinates all tasks by loading the configuration
    and processing the necessary data for each system and instance.

    This function processes system health, job group activities, activities that
    were not OK, and storage systems based on the configuration file and JSON data.
    """

    # Process each instance in the system
    logger.info(f'Processing {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'Processing info from: "{instance}"')

        # Alerts
        system_alerts_status, security_alerts_status = fn.process_if_not_empty(process_alerts, system, instance, "alerts", dcocfg, na_count=2)

        system_jobs_status = fn.process_if_not_empty(process_system_jobs, system, instance, "policies_jobs", dcocfg)
        protection_jobs_status = fn.process_if_not_empty(process_protection_jobs, system, instance, "policies_jobs", dcocfg)
        recovery_jobs_status = fn.process_if_not_empty(process_recovery_jobs, system, instance, "policies_jobs", dcocfg)
        long_running_status = fn.process_if_not_empty(process_protection_long_running, system, instance, "policies_jobs", dcocfg)
        analyze_tasks_status = fn.process_if_not_empty(process_tasks_status, system, instance, "policies_jobs", dcocfg)
        policies_status = fn.process_if_not_empty(process_policies, system, instance, "policies", dcocfg)
        if not policies_status:
            policies_status = '0 / 0'

        cs_capacity, cs_usage_pct, cs_expiration_date = fn.process_if_not_empty(process_cs_info, system, instance, "cs_report", dcocfg, na_count=3)

        # Generate a CSV with the instance summary
        instance_summary =[
            ["System Status", ""],
            ["System Alerts", system_alerts_status],
            ["Security Alerts", security_alerts_status],
            ["Jobs Status", ""],
            ["System Jobs", system_jobs_status],
            ["Protection Jobs", protection_jobs_status],
            ["Recovery Jobs", recovery_jobs_status],
            ["Protection Jobs running for more than 24hrs", long_running_status],
            ["License Status", ""],
            ["Total License Capacity (TB)", cs_capacity],
            ["CyberSense license / usage (%)", cs_usage_pct],
            ["License Expiration Date", cs_expiration_date]
            ]

        pd.DataFrame(instance_summary, columns=["CyberRecovery", instance])
        dcocfg.save_dataframe_to_csv(
            pd.DataFrame(instance_summary, columns=["CyberRecovery", instance]),
            system, instance, "systemSummary")


if __name__ == '__main__':
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    proccess_info(dcocfg)