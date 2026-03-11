# functions module
## GetInfo helpers
## ProccessInfo helpers

### process_if_not_empty(process_function, system, instance, data_type, dcocfg)
For a system type, instance and data type (usually JSON), load the file asociated and process it calling the proccess_function.

The data is loaded as it is for flexibility (originally the function loaded the data ina Pandas DataFrame).

### get_most_critical(df, column, status_order, default)

### df_timestamps_to_dates(df: pd.DataFrame, columns: list)
Convert to standar datetime the columns in a dataframe storing dates as timestaps.
### reformat_date(fmt_in: str, fmt_out: str, date: str)
Reformat a single data from one imput format (fmt_in) ot an output format (fmt_out).

### df_reformat_dates(df: pd.DataFrame, columns: list, current_fmt: str)
Reformad columns storing dates in a dataframe from the imput format (current_fmt) to the format used in the DOC reports (DCO_DATEIMA_FMT constant).

## CreatereportDC/DCI helpers
### systemSummary(system, index_key, data_type, dcocfg)
Load all the system summaries for a given systemt type into a single dataframe.

For systems generating unified.csv files (DD, ECS, PPDM), load that file.

