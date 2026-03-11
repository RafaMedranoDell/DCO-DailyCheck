import logging
import pandas as pd
import common.functions as fn
from common.DCOconfig import DCOconfig

# Global variable that defines the type of system this file works with
system = "product"

# Configure module logger
logger = fn.get_module_logger(__name__)

def process_data1(data, system, instance, dcocfg):
    # Load data into a dataframe
    df = pd.DataFrame(data)

    # Make the transformations needed for this data type
    # Use fn functions to help with the processing
    # ...

    if problems:
        logger.warn(f'Problem while processing data1 for {system}/{instance}: problem description')

    # Selected columns and their new names and order
    selected_columns = {
        "column3": "Column data 3"
        "column1": "Column data 1",
        "column2": "Column data 2",
    }
    # Rename, reorder and filter columns
    return df.reindex(columns=selected_columns.keys()).rename(columns=selected_columns)


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

        # Process data1
        data1_result = fn.process_if_not_empty(process_data1, system, instance, "data1", dcocfg)
        dcocfg.save_dataframe_to_csv(data1_result, system, instance, "data1_result")

        # Generate a CSV with the instance summary
        instance_summary =[
            ["row1", info1],
            ["row2", info1],
            ["row3", info1],
            ["row4", info1]]

        dcocfg.save_dataframe_to_csv(
            pd.DataFrame(instance_summary, columns=["System Name", instance]),
            system, instance, "systemSummary")

if __name__ == '__main__':
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    proccess_info(dcocfg)