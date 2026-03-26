import argparse
from datetime import datetime, timedelta
import importlib
import logging
import os
import sys
from common.DCOconfig import DCOconfig
import common.DCOreport as DCOreport
from getpass import getpass
import common.functions as fn

# Script version and changelog
__version__ = "1.11.0"

CHANGELOG = [
    ("1.0",  "SCRIPT",  "Initial baseline version"),
    ("1.01", "PPCR",    "Improved job duration display to human-readable format (e.g. 1d 02h 30m)"),
    ("",     "PPCR",    "Fixed a report generation error in the Protection Jobs table"),
    ("1.02", "PPCR",    "Updated Policies table color coding based on last backup date"),
    ("1.03", "GETINFO", "Improved compatibility when passing parameters to collection modules"),
    ("1.04", "REPORTS", "Fixed display order of systems (Protection -> Storage -> Compute -> Network)"),
    ("1.05", "VC",      "Updated datastore capacity thresholds (Green<85%, Yellow 85-95%, Red>=95%)"),
    ("1.06", "SCRIPT",  "Added --version and --changelog arguments"),
    ("",     "DOCS", "Renamed and reorganized historical artifacts to match version numbers"),
    ("1.07", "VC",      "Fixed datastore status aggregation (define max_used before rating)"),
    ("1.08", "DOCS",    "Document WinPython dependencies and add requirements-verified list"),
    ("1.09", "DOCS",    "Clarify WinPython portable installation workflow"),
    ("1.10.0", "PPCR",  "Improved compatibility with PPCR 19.22 (v9 auth) and error reporting"),
    ("",       "PPCR",  "Implemented automatic username normalization (lowercase) for IAM"),
    ("",       "DOCS",  "Updated README.md with troubleshooting for upgrades and certs"),
    ("1.11.0", "VC",    "Expanded triggered alarms collection to include Folder-based objects (e.g. license alarms)"),
    ("",       "VC",    "Added acknowledged details (time and user) to DCI report alarms table"),
]

# Get the logger for this module
logger = logging.getLogger(__name__)

def last_hours(arg):
    # Function to validate and convert --last parameter
    try:
        if arg.endswith('d'):
            hours = int(arg[:-1])*24
        elif arg.endswith('h'):
            hours = int(arg[:-1])
        else:
            hours = int(arg)
    except:
        raise argparse.ArgumentTypeError(f'{arg}')
    return hours

def create_parser():
    parser = argparse.ArgumentParser(description='DCO daily report script')
    parser.add_argument('-c', '--cfg', type=str, default='config_encrypted.json',
        help='Use an alternate configuration file (default=config_encrypted.json).')
    parser.add_argument('-l', '--list', action='store_true',
        help='List the system/instances in the configuration file.')
    parser.add_argument('-s', '--scope', type=str, default='',
        help='Run the script only for system or system/instance.')
    parser.add_argument('-p', '--phase',
        choices=['getinfo', 'process', 'reportDC', 'reportDCI'],
        nargs='+',
        default=['getinfo', 'process', 'reportDC', 'reportDCI'],
        help='Run only one phase of the script.')
    parser.add_argument('--last', type=last_hours, default=None,
        help="Number of hours (or days if followed by 'd') to look back")
    parser.add_argument('--email', action="store_true",
        help='Send the report by email.')
    parser.add_argument('-f', '--fmt',
       choices=['html', 'xls', 'all'],
       default='html',
       help='Save the report in one of the formats (default: html).')
    parser.add_argument('--split', action='store_true',
        help='Split DCI report in subreports by system type.')
    parser.add_argument('--numbers', action='store_true',
        help='Adds hierarchical numbering to the report.')
    parser.add_argument('--loglevel',
       choices=['error', 'warn', 'info', 'debug'],
       default='INFO',
       help='Set the logging level.')
    parser.add_argument('--version', action='store_true',
        help='Show the current script version and exit.')
    parser.add_argument('--changelog', action='store_true',
        help='Show a table of all changes per version and exit.')
    return parser

def process_phase(dcocfg, phase, **kwargs):
    """
        For a provided phase, load the modules for the systems present in the config file and execute the default function
        Provide the kargs arguments to the default function
    """

    """
    For each phase:
    - subfix: suffix needed to generate the module name (appended to the system name)
    - function: function name to call inside the module
    """
    phase_info = {
        "getinfo": {"subfix": "getinfo", "function": "getinfo" },
        "process": {"subfix": "processinfo", "function": "proccess_info" },
        "reportDC": {"subfix": "createreportDC", "function": "create_DC" },
        "reportDCI": {"subfix": "createreportDCI", "function": "create_DCI" }
    }
    if phase not in phase_info.keys():
        raise KeyError(f'Module type {phase} not found')

    for system in dcocfg.systems():
        logger.info(f'Running {phase} phase for {system} systems')
        try:
            # Dynamically import the module
            module_name = f'{system}.{system}{phase_info[phase]["subfix"]}'
            module = importlib.import_module(module_name)

            # Get the function for this phase type
            process_func = getattr(module, phase_info[phase]["function"])

            # Call the function with the with the configuration and the provided arguments
            process_func(dcocfg, **kwargs)
        except ImportError as e:
            logger.critical(f'Error importing module {module_name}: {e}')
        except Exception as e:
            # Catch any unhandled exception and log it
            logger.critical(e, exc_info=True)

def gen_report(dcocfg, dcorpt, fmt, rpt_name, gen_index):
    try:
        if fmt in ['all', 'html']:
            report_path = dcocfg.fileTypePath("html")
            dcorpt.save_html(os.path.join(report_path, f"{rpt_name}.html"), gen_index=gen_index)
        if fmt in ['all', 'xls']:
            report_path = dcocfg.fileTypePath("xlsx")
            dcorpt.save_xls(os.path.join(report_path, f"{rpt_name}.xlsx"), gen_index=gen_index)
    except Exception as e:
        # Catch any unhandled exception and log it
        logger.critical(e, exc_info=True)

def send_report(dcocfg, dcorpt, current_time, rpt_name):
    # Load info to send the email and generate the date/time subject
    customer = dcocfg.customerInfo()
    timestr_email = current_time.strftime("%Y-%m-%d %H:%M")

    logger.info(f'Sending {rpt_name}')
    dcorpt.send_email(
        f'{customer["name"]} {rpt_name} ({timestr_email})',
        customer["senderEmail"],
        customer["receiverEmail"],
        customer["smtpServer"],
        customer["smtpPort"])

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()

    if args.version:
        print(f"DCO-DailyCheck v{__version__}")
        sys.exit()
    if args.changelog:
        print(f"{'Version':<10} {'Module':<10} {'Change'}")
        print("-" * 90)
        for version, module, change in CHANGELOG:
            print(f"{version:<10} {module:<10} {change}")
        sys.exit()

    current_time = datetime.now()
    # Generate date/time format to be used in file names
    timestr_fname = current_time.strftime("%Y%m%d_%H%M")

    # Load the configuration
    dcocfg = DCOconfig(args.cfg)

    # Setup logging
    fn.setup_logging(
        log_path=dcocfg.fileTypePath("log"),
        file_prefix=timestr_fname,
        level = getattr(logging, args.loglevel.upper()))

    # Remove old logs and reports
    fn.remove_logs(dcocfg, keep_days=14, keep_months=True)
    fn.remove_reports(dcocfg, keep_days=14, keep_months=True)

    # Filter system or instance if provided
    dcocfg.limit_to(args.scope)

    # Sanitize the scope to be used in report file names
    rpt_scope = args.scope.replace("/", "_").replace(".", "_") if args.scope else 'ALL'

    # Calculate the start time for filtering
    if args.last == None:
        # Include the weekend logs on Mondays, 24 the Tuesday to Sunday
        args.last = 72 if datetime.today().weekday() == 0 else 24
    dcocfg.set_param("script_start_time", current_time)
    dcocfg.set_param("start_time", current_time - timedelta(hours=args.last))

    # Option --list: list the systems/instances and exit
    if args.list:
        for system in dcocfg.systems():
            for instance in dcocfg.instances(system):
                print(f'{system}/{instance}')
        sys.exit()

    # Create the DC and DCI report objects
    dcorpt_dc = DCOreport.DCOreport("DCO Daily Check report")
    dcorpt_dci = DCOreport.DCOreport("DCO Daily Check Investigation report")

    # Add top level items in the desired order
    for header2 in ["Protection", "Storage", "Compute", "Network"]:
        dcorpt_dc.add_header2(header2)
        dcorpt_dci.add_header2(header2)

    # Process the phases with the present systems in the configuration
    if 'getinfo' in args.phase:
        dcocfg.delete_type("json")
        process_phase(dcocfg, "getinfo", hours_ago=args.last)
        dcocfg.archive_type("json", current_time)
        dcocfg.archive_cleanup("json")
    if 'process' in args.phase:
        dcocfg.delete_type("csv")
        process_phase(dcocfg, "process")
        dcocfg.archive_type("csv", current_time)
        dcocfg.archive_cleanup("csv")
    if 'reportDC' in args.phase:
        process_phase(dcocfg, "reportDC", dcorpt=dcorpt_dc)
        gen_report(dcocfg, dcorpt_dc, args.fmt, f'DCO_DCreport_{timestr_fname}_{rpt_scope}', args.numbers)
        if args.email:
            send_report(dcocfg, dcorpt_dc, current_time, 'DCO_Daily_Check_Automated')
    if 'reportDCI' in args.phase:
        process_phase(dcocfg, "reportDCI", dcorpt=dcorpt_dci)
        gen_report(dcocfg, dcorpt_dci, args.fmt, f'DCO_DCIreport_{timestr_fname}_{rpt_scope}', args.numbers)
        if not args.scope and args.split:
            for system in dcocfg.systems():
                system_rpt_dci = DCOreport.DCOreport(f"DCO Daily Check Investigation report for {system}")
                dcocfg.limit_to(system)
                process_phase(dcocfg, "reportDCI", dcorpt=system_rpt_dci)
                gen_report(dcocfg, system_rpt_dci, args.fmt, f'DCO_DCIreport_{timestr_fname}_{system}', args.numbers)
                dcocfg.remove_limit()
        if args.email:
            send_report(dcocfg, dcorpt_dci, current_time, 'DCO_Daily_Check_Investigation_Automated')
