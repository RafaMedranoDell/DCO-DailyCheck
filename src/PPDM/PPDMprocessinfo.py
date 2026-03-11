import logging
import pandas as pd
import common.functions as fn
import common.DCOreport as DCOreport
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "PPDM"

# Configure module logger
logger = fn.get_module_logger(__name__)

def create_health_by_category(df):
    """
    Create a summary of health metrics by category.

    Args:
        df (DataFrame): Input DataFrame containing health data with columns:
            - healthCategory (str): Category of the health issue
            - scoreDeduction (int): Points deducted for the issue

    Returns:
        DataFrame: A summarized DataFrame with health metrics grouped by category containing:
            - CATEGORY (str): User-friendly category name
            - Issues (int): Total number of issues in the category
            - Score (int): Maximum negative score impact for the category

    Example:
        >>> df_result = create_health_by_category(health_df)
        >>> print(df_result)
           CATEGORY      Issues  Score
        0  Configuration     2    -10
        1  Data Protection   1     -5
        ...
    """

    # Define the health categories to include in the summary
    health_categories = ['CONFIGURATION', 'DATA_PROTECTION', 'PERFORMANCE', 'COMPONENTS', 'CAPACITY']

    # Create a base template DataFrame with predefined health categories
    df_health_template = pd.DataFrame({
        'healthCategory': health_categories,
        'Score': 0,  # Default score is 0
        'Issues': 0  # Default issue count is 0
    })

    # Group data by healthCategory and calculate the maximum score deduction and issue count
    df_grouped_health_metrics = df.groupby('healthCategory').agg({
        'scoreDeduction': 'max',  # Maximum score deduction per category
        'healthCategory': 'count'  # Count of issues per category
    }).rename(columns={'scoreDeduction': 'Score', 'healthCategory': 'Issues'})
    # Negate the score deduction values to reflect negative impact
    df_grouped_health_metrics['Score'] = -df_grouped_health_metrics['Score']

    # Merge the base template with the grouped health metrics
    df_health_by_category = pd.merge(
        df_health_template,
        df_grouped_health_metrics,
        on='healthCategory',
        how='outer',
        suffixes=('_template', '_grouped')
    )

    # Fill missing values from the template and ensure integer type for numeric columns
    df_health_by_category['Score'] = df_health_by_category['Score_grouped'].fillna(
        df_health_by_category['Score_template']).astype(int)
    df_health_by_category['Issues'] = df_health_by_category['Issues_grouped'].fillna(
        df_health_by_category['Issues_template']).astype(int)

    # Select relevant columns for the final output
    df_health_by_category = df_health_by_category[['healthCategory', 'Issues', 'Score']]

    # Rename 'healthCategory' column to 'CATEGORY'
    df_health_by_category = df_health_by_category.rename(columns={'healthCategory': 'CATEGORY'})

    # Replace internal category names with user-friendly names
    category_mapping = {
        'CONFIGURATION': 'Configuration',
        'DATA_PROTECTION': 'Data Protection',
        'PERFORMANCE': 'Performance',
        'COMPONENTS': 'Components',
        'CAPACITY': 'Capacity'
    }
    df_health_by_category['CATEGORY'] = df_health_by_category['CATEGORY'].replace(category_mapping)

    return df_health_by_category



def create_health_system_status(df_health_by_category):
    """
    Create an overall health status summary for the system.

    Args:
        df_health_by_category (DataFrame): DataFrame containing health metrics by category,
                                         including 'Score' and 'Issues' columns.

    Returns:
        DataFrame: A single-row DataFrame containing:
            - TotalIssuesCount (int): Sum of all issues across categories
            - SystemScore (int): Normalized score (100 + lowest category score)
            - STATUS (str): Overall system status based on SystemScore:
                * "GOOD": SystemScore > 95
                * "FAIR": 71 < SystemScore <= 94
                * "POOR": SystemScore <= 71
    """

    # Calculate the lowest health score from the category scores
    lowest_health_score = df_health_by_category['Score'].min()

    # Normalize the system score to a scale where 100 represents no issues
    normalized_system_score = 100 + lowest_health_score

    # Calculate the total number of issues across all categories
    total_issues_count = df_health_by_category['Issues'].sum()

    # Determine system status based on the normalized score
    if normalized_system_score > 95:
        system_status = "GOOD"
    elif 71 < normalized_system_score <= 94:
        system_status = "FAIR"
    else:
        system_status = "POOR"

    # Create a DataFrame to summarize the system's health status
    df_system_status = pd.DataFrame([{
        'TotalIssuesCount': total_issues_count,
        'SystemScore': normalized_system_score,
        'STATUS': system_status
    }])

    return df_system_status



def create_health_events(df):
    """
    Clean and transform health event records by replacing newline characters.

    Args:
        df (DataFrame): DataFrame containing health event data. All string columns
                       will have their newline characters replaced.

    Returns:
        DataFrame: Transformed DataFrame with newline characters replaced by '|||'
                  delimiter for better CSV compatibility and readability.
    """

    # Replace newline characters in the DataFrame with '|||'
    return df.replace(r'\n', '|||', regex=True)



def process_health(data, system, instance, dcocfg):
    """
    Process health data and save the results as CSV files.

    Args:
        data (str): The data loaded from the file.
        system (str): The system from which the alert data originates.
        instance (str): The instance of the system.
        dcocfg (DCOconfig): Configuration object.

    Returns:
        None
    """
    # Convert JSON data into dataframe
    df = pd.DataFrame(data)

    # Create Dataframes sumarizing health metrics
    df_health_by_category = create_health_by_category(df)
    df_system_status = create_health_system_status(df_health_by_category)
    df_event_logs = create_health_events(df)


    # Save the DataFrames as CSV files
    dcocfg.save_dataframe_to_csv(df_health_by_category, system, instance, "healthByCategory")
    dcocfg.save_dataframe_to_csv(df_event_logs, system, instance, "healthEvents")
    dcocfg.save_dataframe_to_csv(df_system_status, system, instance, "healthSystemStatus")


def summarize_job_group_status(df_filtered):
    """
    Create a summary of activities grouped by result status.

    Args:
        df_filtered (DataFrame): Filtered DataFrame containing job group activities
                               with 'result.status' column.

    Returns:
        DataFrame: A summary DataFrame with:
            - STATUS (str): Activity status mapped from internal to user-friendly names:
                * 'OK' -> 'Successful'
                * 'FAILED' -> 'Failed'
                * 'OK_WITH_ERRORS' -> 'Completed with Exceptions'
                * 'CANCELED' -> 'Canceled'
                * 'SKIPPED' -> 'Skipped'
                * 'UNKNOWN' -> 'Unknown'
            - Count (int): Number of activities in each status
    """

    # Define all possible "status"
    possible_status = ['OK', 'FAILED', 'OK_WITH_ERRORS', 'CANCELED', 'SKIPPED', 'UNKNOWN']
    df_all_statuses = pd.DataFrame({'result_status': possible_status, 'Count': 0})

    # Count occurrences of each result status in the filtered DataFrame
    df_status_counts = df_filtered['result.status'].value_counts().reset_index()
    df_status_counts.columns = ['result_status', 'Count']

    # Merge with all possible "status" to include missing ones
    df_job_group_summary = pd.merge(
        df_all_statuses,
        df_status_counts,
        on='result_status',
        how='outer'
    )
    # Fill missing values with zeros
    df_job_group_summary['Count'] = df_job_group_summary['Count_y'].combine_first(df_job_group_summary['Count_x']).astype(int)
    df_job_group_summary = df_job_group_summary[['result_status', 'Count']]

    # Map result statuses to user-friendly names
    status_mapping = {
        'OK': 'Successful',
        'FAILED': 'Failed',
        'OK_WITH_ERRORS': 'Completed with Exceptions',
        'CANCELED': 'Canceled',
        'SKIPPED': 'Skipped',
        'UNKNOWN': 'Unknown'
    }
    df_job_group_summary['result_status'] = df_job_group_summary['result_status'].replace(status_mapping)

    # Rename columns
    df_job_group_summary = df_job_group_summary.rename(columns={'result_status': 'STATUS'})

    return df_job_group_summary



def calculate_job_group_rate(df_job_group_summary):
    """
    Calculate the total number of job groups and the success rate.

    Args:
        df_job_group_summary (DataFrame): DataFrame summarizing job group statuses and their counts.

    Returns:
        DataFrame: A DataFrame containing the total number of job groups and the success rate.
    """
    # Calculate total number of job groups across all statuses
    total_jobs = df_job_group_summary['Count'].sum()

    # Count only jobs with 'Successful' status for success rate
    successful_jobs = df_job_group_summary.loc[df_job_group_summary['STATUS'] == 'Successful', 'Count'].sum()

    # Calculate success rate as percentage: (successful_jobs / total_jobs) * 100
    # Returns 0 if there are no jobs to avoid division by zero
    success_rate = round((successful_jobs / total_jobs) * 100, 2) if total_jobs > 0 else 0

    # Create a DataFrame with the results
    df_job_group_rate = pd.DataFrame([[total_jobs, success_rate]], columns=['Total Job Groups', 'Rate (%)'])

    return df_job_group_rate



def process_job_group_activities(data, system, instance, dcocfg):
    """
    Process job group activities and save the results to CSV files.

    Args:
        data (str): The data loaded from the file.
        system (str): The system from which the alert data originates.
        instance (str): The instance of the system.
        dcocfg (DCOconfig): Configuration object.

    Returns:
        None
    """
    # Convert JSON data into dataframe
    df = pd.DataFrame(data)

    # Filter the DataFrame for relevant categories
    relevant_categories = ['CLOUD_TIER', 'INDEX', 'PROTECT', 'REPLICATE', 'RESTORE']
    df_filtered_jobs = df[df['category'].isin(relevant_categories)]

    # Create summary and success rate DataFrames
    df_job_group_summary = summarize_job_group_status(df_filtered_jobs)
    df_job_group_rate = calculate_job_group_rate(df_job_group_summary)

    # Save the DataFrames to CSV files
    dcocfg.save_dataframe_to_csv(df_job_group_summary, system, instance, "jobgroupSummary")
    dcocfg.save_dataframe_to_csv(df_job_group_rate, system, instance, "jobgroupRate")


def generate_activities_no_ok_summary(df):
    """
    Generate a summary of activities that are not OK by counting occurrences of specific error combinations.

    Args:
        df (DataFrame): The input DataFrame containing activity data.

    Returns:
        DataFrame: A summary DataFrame of activities with errors, including occurrence counts and relevant details.
    """
    # Fill missing values with "(empty)"
    df = df.fillna("(empty)")

    # Calculate the number of occurrences by key column combinations
    # This step counts how many times each combination of error details occurs
    df_error_occurrences = df.groupby([
        'category',
        'protectionPolicy.name',
        'result.status',
        'result.error.code',
        'host.name',
        'asset.name',
        'result.error.reason'
    ]).size().reset_index(name='occurrences')

    # Select relevant columns for analysis
    # These columns provide the necessary information about the errors and activities
    relevant_columns = [
        'category',
        'protectionPolicy.name',
        'result.status',
        'result.error.code',
        'activityInitiatedType',
        'host.name',
        'asset.name',
        'result.error.reason',
        'result.error.extendedReason',
        'result.error.detailedDescription',
        'result.error.remediation'
    ]
    df_relevant_data = df[relevant_columns]

    # Create a DataFrame with unique errors based on key combinations
    # This removes duplicate rows based on key error details
    df_unique_errors = df_relevant_data.drop_duplicates(subset=[
        'category',
        'protectionPolicy.name',
        'result.status',
        'result.error.code',
        'host.name',
        'asset.name',
        'result.error.reason'
    ])

    # Merge the occurrences with the unique errors DataFrame
    # We merge the error occurrences data with the unique errors to attach occurrence counts to each unique error combination
    df_final_summary = df_unique_errors.merge(
        df_error_occurrences,
        on=[
            'category',
            'protectionPolicy.name',
            'result.status',
            'result.error.code',
            'host.name',
            'asset.name',
            'result.error.reason'
        ]
    )

    # Rearrange and order the columns for the final report
    # This step ensures the final summary has the desired column order for reporting
    final_columns_order = [
        'category',
        'protectionPolicy.name',
        'result.status',
        'result.error.code',
        'activityInitiatedType',
        'occurrences',
        'host.name',
        'asset.name',
        'result.error.reason',
        'result.error.extendedReason',
        'result.error.detailedDescription',
        'result.error.remediation'
    ]

    # Sort the DataFrame to provide a clear and structured report by the specified columns
    return df_final_summary[final_columns_order].sort_values([
        'category',
        'protectionPolicy.name',
        'result.status',
        'result.error.code',
        'host.name',
        'asset.name',
        'result.error.reason'
    ])



def process_activities_no_ok(data, system, instance, dcocfg):
    """
    Process activities that are not OK and save the results in CSV format.

    This function generates a summary of activities with errors, replaces any newline characters
    with a placeholder, and saves the resulting summary in a CSV file.

    Args:
        data (str): The data loaded from the file.
        system (str): The system from which the alert data originates.
        instance (str): The instance of the system.
        dcocfg (DCOconfig): Configuration object.

    Returns:
        None: This function saves the results to a CSV file and does not return any values.
    """
    # Convert JSON data into dataframe
    df = pd.DataFrame(data)

    # Generate a summary table of unique errors
    df_activities_no_ok_summary = generate_activities_no_ok_summary(df)

    # Replace "\n" with "|||" across the entire DataFrame
    df_activities_no_ok_summary = df_activities_no_ok_summary.replace(r'\n', '  ..  ', regex=True)

    # Save the DataFrame to CSV
    dcocfg.save_dataframe_to_csv(df_activities_no_ok_summary, system, instance, "activitiesNoOkSummary")


def process_storage_systems(data, system, instance, dcocfg):
    """
    Process storage systems information from JSON data and save the results in CSV format.

    This function filters the data to include only 'DATA_DOMAIN_SYSTEM' entries, processes relevant
    information for each storage system (such as readiness, capacity details, and usage),
    and saves the resulting data to a CSV file.

    Args:
        data (str): The data loaded from the file.
        system (str): The system from which the alert data originates.
        instance (str): The instance of the system.
        dcocfg (DCOconfig): Configuration object.

    Returns:
        None: This function saves the results to a CSV file and does not return any values.
    """
    # Convert JSON data into dataframe
    df = pd.DataFrame(data)

    # Filter DataFrame to only include DATA_DOMAIN_SYSTEM type entries
    df_storage_systems = df[df['type'] == 'DATA_DOMAIN_SYSTEM']

    # Prepare a list to store processed rows
    processed_rows = []

    # Iterate through storage systems
    for _, row in df_storage_systems.iterrows():
        # Extract base system information
        name = row.get('name', '')
        readiness = row.get('readiness', '').lower()

        # Navigate nested dictionary structure:
        # details -> dataDomain -> capacities
        # capacities is a list of dictionaries containing storage tier information
        capacities = row.get('details', {}).get('dataDomain', {}).get('capacities', [])

        # Process each storage tier's capacity information
        for capacity in capacities:
            processed_rows.append({
                'NAME': name,
                'READINESS': readiness,
                'TIER': capacity.get('type', ''),
                'PERCENT USED': f"{capacity.get('percentUsed', 0):.2f}",  # Format to 2 decimal places
                'STATUS': capacity.get('capacityStatus', '')
            })

    # Create DataFrame from processed rows
    df_storage_systems_output = pd.DataFrame(processed_rows)
    df_storage_systems_output = df_storage_systems_output.sort_values(by=['NAME', 'TIER'])

    # Save to CSV
    dcocfg.save_dataframe_to_csv(df_storage_systems_output, system, instance, "storageSystems")


def unify_csv_files(system, instance, dcocfg):
    """
    Unifies CSV files and creates both CSV and formatted Excel outputs
    """
    final_df = dcocfg.load_csv_to_dataframe(system, instance, "unifiedData")
    if final_df.empty:
        final_df = pd.DataFrame({
            'key': ['SystemScore', 'STATUS', 'Configuration', 'Data Protection',
                   'Performance', 'Components', 'Capacity', 'Total Job Groups',
                   'Rate (%)', 'Successful', 'Failed', 'Completed with Exceptions',
                   'Canceled', 'Skipped', 'Unknown']
        })

    try:
        # Read CSV files for current instance
        df_health_status = dcocfg.load_csv_to_dataframe(system, instance, "healthSystemStatus")
        df_health_category = dcocfg.load_csv_to_dataframe(system, instance, "healthByCategory")
        df_jobgroup_rate = dcocfg.load_csv_to_dataframe(system, instance, "jobgroupRate")
        df_jobgroup_summary = dcocfg.load_csv_to_dataframe(system, instance, "jobgroupSummary")

        # Create column for current instance
        instance_data = []

        # Get health system status data
        instance_data.extend([
            df_health_status['SystemScore'].iloc[0],
            df_health_status['STATUS'].iloc[0]
        ])

        # Get health categories data
        categories = ['Configuration', 'Data Protection', 'Performance', 'Components', 'Capacity']
        for category in categories:
            score = df_health_category[df_health_category['CATEGORY'] == category]['Score'].iloc[0]
            instance_data.append(score)

        # Get job group rates data
        instance_data.extend([
            df_jobgroup_rate['Total Job Groups'].iloc[0],
            df_jobgroup_rate['Rate (%)'].iloc[0]
        ])

        # Get job group summary data
        status_types = ['Successful', 'Failed', 'Completed with Exceptions',
                       'Canceled', 'Skipped', 'Unknown']
        for status in status_types:
            count = df_jobgroup_summary[df_jobgroup_summary['STATUS'] == status]['Count'].iloc[0]
            instance_data.append(count)

        # Add or update column for current instance
        final_df[instance] = instance_data

    except Exception as e:
        logger.error(f"Unable to process CSV files for instance {instance} to unify. Skipping instance.")
        return

    # Save CSV
    dcocfg.save_dataframe_to_csv(final_df, system, instance, "unifiedData")
    logger.debug(f'Updated unified CSV file: {dcocfg.filePath(system, instance, "csv", "unifiedData")}')

    # # Guardar en Excel y aplicar formato
    # writer = pd.ExcelWriter(output_excel, engine='openpyxl')
    # final_df.to_excel(writer, index=True, sheet_name='Report')
    # writer.close()

    # # Cargar el archivo guardado y aplicar formato
    # wb = openpyxl.load_workbook(output_excel)
    # ws = wb.active
    # apply_excel_formatting(ws)
    # wb.save(output_excel)

    # print(f"Updated formatted Excel file: {output_excel}")

    return final_df

def proccess_info(dcocfg):
    """Main function that coordinates all tasks."""


    logger.info(f'Processing {system} systems')
    for instance in dcocfg.instances(system):
        logger.info(f'Processing info from: "{instance}"')

        # Process Health Issues
        fn.process_if_not_empty(process_health, system, instance, "systemHealthIssues", dcocfg)

        # Process Job Group Activities
        fn.process_if_not_empty(process_job_group_activities, system, instance, "jobGroupActivitiesSummary", dcocfg)

        # Process Activities Not OK
        fn.process_if_not_empty(process_activities_no_ok, system, instance, "activitiesNotOK", dcocfg)

        # Process Storage Systems
        fn.process_if_not_empty(process_storage_systems, system, instance, "storageSystems", dcocfg)

        # Create final_csv
        unify_csv_files(system, instance, dcocfg)

if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), "PPDMdebug", level=logging.DEBUG)
    proccess_info(dcocfg)
