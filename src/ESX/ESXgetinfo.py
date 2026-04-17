import ssl
import urllib3
import logging
import common.functions as fn
from common.DCOconfig import DCOconfig

# Conditional import of pyVmomi (required for ESXi SOAP API)
try:
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim
    SOAP_AVAILABLE = True
except ImportError:
    SOAP_AVAILABLE = False
    logging.warning("pyVmomi not installed. ESX module will not work without it.")

# Reuse the alarm-fetching logic from the VC module
try:
    from VC.VCgetinfo import fetch_soap_alarms
except ImportError:
    fetch_soap_alarms = None
    logging.warning("Could not import fetch_soap_alarms from VCgetinfo. Alarm collection will be skipped.")

# Disable insecure request warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global variable for the system type
system = "ESX"

# Configure module logger
logger = fn.get_module_logger(__name__)


def fetch_host_health(si):
    """
    Fetches overall health and basic system info from a standalone ESXi host.
    Returns a dictionary with health status and host summary details.
    """
    content = si.RetrieveContent()
    host_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.HostSystem], True
    )

    result = {}
    if host_view.view:
        host = host_view.view[0]
        summary = host.summary
        hardware = summary.hardware
        runtime = summary.runtime

        result = {
            "overall_status": str(host.overallStatus),       # green, yellow, red, gray
            "connection_state": str(runtime.connectionState), # connected, disconnected, notResponding
            "power_state": str(runtime.powerState),           # poweredOn, poweredOff, standBy
            "cpu_mhz": getattr(hardware, "cpuMhz", None),
            "num_cpu_cores": getattr(hardware, "numCpuCores", None),
            "memory_size": getattr(hardware, "memorySize", None),  # bytes
            "model": getattr(hardware, "model", None),
            "vendor": getattr(hardware, "vendor", None),
            "product_name": getattr(summary.config, "product", {}).name if hasattr(summary, "config") and summary.config.product else None,
        }

    host_view.Destroy()
    return result


def fetch_datastores(si):
    """
    Fetches all datastores accessible from the ESXi host via SOAP API.
    Returns a list of datastore dictionaries with capacity and free space.
    """
    content = si.RetrieveContent()
    ds_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.Datastore], True
    )

    ds_list = []
    for ds in ds_view.view:
        try:
            summary = ds.summary
            ds_dict = {
                "name": summary.name,
                "type": summary.type,
                "capacity": summary.capacity,    # bytes
                "free_space": summary.freeSpace,  # bytes
                "accessible": summary.accessible,
            }
            ds_list.append(ds_dict)
        except Exception as e:
            logger.warning(f"{system}: Error processing datastore: {e}")
            continue

    ds_view.Destroy()
    return ds_list


def fetch_vms(si):
    """
    Fetches all virtual machines from the ESXi host via SOAP API.
    Returns a list of VM dictionaries with name and power state.
    """
    content = si.RetrieveContent()
    vm_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )

    vm_list = []
    for vm in vm_view.view:
        try:
            summary = vm.summary
            config = summary.config
            runtime = summary.runtime

            vm_dict = {
                "name": getattr(config, "name", None),
                "power_state": str(runtime.powerState),   # poweredOn, poweredOff, suspended
                "num_cpu": getattr(config, "numCpu", None),
                "memory_mb": getattr(config, "memorySizeMB", None),
            }
            vm_list.append(vm_dict)
        except Exception as e:
            logger.warning(f"{system}: Error processing VM: {e}")
            continue

    vm_view.Destroy()
    return vm_list


def getinfo(dcocfg, **kwargs):
    """
    Main entry point for the ESX getinfo phase.
    Collects host health, datastores, VMs, and alarms from standalone ESXi hosts via SOAP.
    """
    if not SOAP_AVAILABLE:
        logger.error(f"{system}: pyVmomi is required but not installed. Cannot collect ESX data.")
        return

    logger.info(f"Starting {system} getinfo phase")

    for instance in dcocfg.instances(system):
        logger.info(f"{system}/{instance}: Getting info...")

        try:
            api_port, username, password, cert_hash = dcocfg.loginInfo(system, instance)
        except Exception as e:
            logger.error(f"{system}/{instance}: Could not read credentials: {e}")
            continue

        si = None
        try:
            ssl_ctx = ssl._create_unverified_context()
            si = SmartConnect(host=instance, user=username, pwd=password,
                              port=int(api_port), sslContext=ssl_ctx)
            logger.info(f"{system}/{instance}: SOAP connection established.")

            # 1. Host health
            logger.info(f"{system}/{instance}: Fetching host health...")
            host_health = fetch_host_health(si)
            dcocfg.save_json(host_health, system, instance, "host_health")

            # 2. Datastores
            logger.info(f"{system}/{instance}: Fetching datastores...")
            datastores = fetch_datastores(si)
            dcocfg.save_json(datastores, system, instance, "datastores")

            # 3. VMs
            logger.info(f"{system}/{instance}: Fetching VMs...")
            vms = fetch_vms(si)
            dcocfg.save_json(vms, system, instance, "vms")

            # 4. Triggered alarms (reusing VC module logic)
            if fetch_soap_alarms:
                logger.info(f"{system}/{instance}: Fetching triggered alarms...")
                alarms = fetch_soap_alarms(instance, username, password)
                dcocfg.save_json(alarms, system, instance, "alarms")
            else:
                logger.warning(f"{system}/{instance}: Alarm collection skipped (import failed).")

            logger.info(f"{system}/{instance}: Data collection complete.")

        except Exception as e:
            logger.error(f"{system}/{instance}: Error during data collection: {e}")
        finally:
            if si:
                try:
                    Disconnect(si)
                    logger.debug(f"{system}/{instance}: SOAP connection closed.")
                except Exception:
                    pass


if __name__ == "__main__":
    dcocfg = DCOconfig("config_encrypted.json")
    fn.setup_logging(dcocfg.fileTypePath("log"), f"{system}debug", level=logging.DEBUG)
    getinfo(dcocfg)
