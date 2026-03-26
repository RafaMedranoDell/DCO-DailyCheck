import requests
import urllib3
import logging
import ssl
from datetime import datetime
import common.functions as fn

# Conditional import of pyVmomi for SOAP API (alarms)
try:
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim
    SOAP_AVAILABLE = True
except ImportError:
    SOAP_AVAILABLE = False
    logging.warning("pyVmomi not installed. SOAP alarm extraction will be skipped.")

# Disable insecure request warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global variable for the system type
system = "VC"

# Configure module logger
logger = fn.get_module_logger(__name__)

class VCClient:
    """
    Elegant Context Manager for vCenter REST API sessions.
    Ensures safe login and automatic logout.
    """
    def __init__(self, host, user, password, port=443):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.session_id = None
        self.base_url = f"https://{self.host}:{self.port}/api"

    def __enter__(self):
        login_url = f"{self.base_url}/session"
        try:
            logger.info(f"{system}/{self.host}: Authenticating...")
            response = requests.post(
                login_url, 
                auth=(self.user, self.password), 
                verify=False, 
                timeout=15
            )
            response.raise_for_status()
            self.session_id = response.json()
            return self
        except Exception as e:
            logger.error(f"{system}/{self.host}: Authentication failed: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session_id:
            logout_url = f"{self.base_url}/session"
            headers = {"vmware-api-session-id": self.session_id}
            try:
                requests.delete(logout_url, headers=headers, verify=False, timeout=5)
                logger.debug(f"{system}/{self.host}: Session closed")
            except Exception as e:
                logger.warning(f"{system}/{self.host}: Error closing session: {e}")

    def _get(self, endpoint):
        """Helper to perform GET requests with the session token."""
        headers = {"vmware-api-session-id": self.session_id}
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        return response.json()

def fetch_soap_alarms(host, username, password):
    """
    Fetches triggered alarms from all entities in vCenter using SOAP API.
    Returns a list of alarm dictionaries with complete information.
    """
    if not SOAP_AVAILABLE:
        logger.warning(f"{system}/{host}: pyVmomi not available, skipping SOAP alarms")
        return []
    
    alarms_list = []
    
    try:
        # Connect via SOAP
        ssl_ctx = ssl._create_unverified_context()
        si = SmartConnect(host=host, user=username, pwd=password, sslContext=ssl_ctx)
        content = si.RetrieveContent()
        
        # Create a container view for specific managed entities
        # We filter by specific types to avoid duplicate alarms propagated to parent containers
        # (e.g. a Host alarm appearing on the parent Folder or Datacenter).
        # We are only interested in the actual source of the alarm.
        container = content.viewManager.CreateContainerView(
            content.rootFolder, 
            [vim.ManagedEntity], 
            True  # Recursive
        )
        
        # Iterate through all entities plus the root folder itself
        # (the root folder might not be in the view if it's the container)
        entities_to_check = list(container.view)
        if content.rootFolder not in entities_to_check:
            entities_to_check.append(content.rootFolder)
            
        for entity in entities_to_check:
            try:
                triggered_alarms = entity.triggeredAlarmState
                
                for alarm_state in triggered_alarms:
                    try:
                        # Skip propagated alarms to avoid duplicates.
                        # We only capture the alarm on the object where it was actually triggered.
                        if alarm_state.entity != entity:
                            continue
                            
                        # Extract entity information
                        entity_type = type(entity).__name__
                        entity_name = getattr(entity, 'name', None)
                        entity_id = str(entity._moId) if hasattr(entity, '_moId') else None
                        
                        # Extract parent information (with null handling)
                        entity_parent_name = None
                        entity_parent_type = None
                        try:
                            if hasattr(entity, 'parent') and entity.parent:
                                entity_parent_name = getattr(entity.parent, 'name', None)
                                entity_parent_type = type(entity.parent).__name__
                        except:
                            pass
                        
                        # Extract alarm information
                        alarm_info = alarm_state.alarm.info
                        alarm_name = getattr(alarm_info, 'name', None)
                        alarm_description = getattr(alarm_info, 'description', None)
                        alarm_enabled = getattr(alarm_info, 'enabled', None)
                        alarm_key = str(alarm_state.alarm._moId) if hasattr(alarm_state.alarm, '_moId') else None
                        
                        # Extract alarm state
                        overall_status = getattr(alarm_state, 'overallStatus', None)
                        acknowledged = getattr(alarm_state, 'acknowledged', False)
                        
                        # Extract timestamps
                        triggered_time = None
                        if hasattr(alarm_state, 'time') and alarm_state.time:
                            triggered_time = alarm_state.time.isoformat()
                        
                        acknowledged_time = None
                        acknowledged_by = None
                        if acknowledged:
                            if hasattr(alarm_state, 'acknowledgedTime') and alarm_state.acknowledgedTime:
                                acknowledged_time = alarm_state.acknowledgedTime.isoformat()
                            acknowledged_by = getattr(alarm_state, 'acknowledgedByUser', None)
                        
                        # Build alarm dictionary
                        alarm_dict = {
                            "entity_type": entity_type,
                            "entity_name": entity_name,
                            "entity_id": entity_id,
                            "entity_parent_name": entity_parent_name,
                            "entity_parent_type": entity_parent_type,
                            "alarm_name": alarm_name,
                            "alarm_description": alarm_description,
                            "alarm_enabled": alarm_enabled,
                            "alarm_key": alarm_key,
                            "overall_status": overall_status,
                            "acknowledged": acknowledged,
                            "triggered_time": triggered_time,
                            "acknowledged_time": acknowledged_time,
                            "acknowledged_by": acknowledged_by
                        }
                        
                        alarms_list.append(alarm_dict)
                        
                    except Exception as e:
                        logger.warning(f"{system}/{host}: Error processing alarm for entity {entity_name}: {e}")
                        continue
                        
            except:
                # Entity doesn't have triggeredAlarmState or we don't have permission
                continue
        
        # Cleanup
        container.Destroy()
        Disconnect(si)
        
        logger.info(f"{system}/{host}: Collected {len(alarms_list)} triggered alarms via SOAP")
        
    except Exception as e:
        logger.error(f"{system}/{host}: SOAP alarm extraction failed: {e}")
        return []
    
    return alarms_list

def fetch_soap_datastores(host, username, password):
    """
    Fetches datastores and their associated hosts using SOAP API.
    Returns a list of datastore dictionaries including capacity, free space, and host list.
    """
    if not SOAP_AVAILABLE:
        logger.warning(f"{system}/{host}: pyVmomi not available, skipping SOAP datastores")
        return []
    
    ds_list = []
    
    try:
        # Connect via SOAP
        ssl_ctx = ssl._create_unverified_context()
        si = SmartConnect(host=host, user=username, pwd=password, sslContext=ssl_ctx)
        content = si.RetrieveContent()
        
        # Create a container view for Datastores
        container = content.viewManager.CreateContainerView(
            content.rootFolder, 
            [vim.Datastore], 
            True  # Recursive
        )
        
        for ds in container.view:
            try:
                summary = ds.summary
                
                # Basic info
                name = summary.name
                ds_type = summary.type
                capacity = summary.capacity
                free_space = summary.freeSpace
                
                # Get connected hosts
                connected_hosts = []
                if hasattr(ds, 'host'):
                    for host_mount in ds.host:
                        try:
                            # host_mount.key is the HostSystem object
                            h_name = host_mount.key.name
                            connected_hosts.append(h_name)
                        except:
                            continue
                
                # Format hosts string
                # Strategy: If <= 3 hosts, list them. If > 3, show count and list in parens.
                connected_hosts.sort()
                num_hosts = len(connected_hosts)
                
                if num_hosts == 0:
                    hosts_str = "None"
                elif num_hosts <= 3:
                    hosts_str = ", ".join(connected_hosts)
                else:
                    # Example: "5 hosts (ESXi01, ESXi02...)"
                    preview = ", ".join(connected_hosts[:2])
                    hosts_str = f"{num_hosts} hosts ({preview}...)"
                
                ds_dict = {
                    "datastore": str(ds._moId),  # Internal ID
                    "name": name,
                    "type": ds_type,
                    "capacity": capacity,
                    "free_space": free_space,
                    "hosts": hosts_str
                }
                
                ds_list.append(ds_dict)
                
            except Exception as e:
                logger.warning(f"{system}/{host}: Error processing datastore: {e}")
                continue
        
        # Cleanup
        container.Destroy()
        Disconnect(si)
        
        logger.info(f"{system}/{host}: Collected {len(ds_list)} datastores via SOAP")
        
    except Exception as e:
        logger.error(f"{system}/{host}: SOAP datastore extraction failed: {e}")
        return []
    
    return ds_list
def getinfo(dcocfg, **kwargs):
    """
    Main entry point for the getinfo phase for vCenter.
    """
    logger.info(f"Starting {system} getinfo phase")
    
    for instance in dcocfg.instances(system):
        # Handle authentication (with fallback for plain text during testing)
        try:
            api_port, username, password, cert_hash = dcocfg.loginInfo(system, instance)
            host = instance
        except Exception as e:
            logger.warning(f"{system}/{instance}: Falling back to raw password: {e}")
            instance_data = dcocfg._getInstanceData(system, instance)
            host = instance_data.get("hostname", instance)
            username = instance_data.get("username")
            password = instance_data.get("encrypted_password")
            api_port = dcocfg.config["systems"][system]["cfg"].get("api_port", 443)

        try:
            with VCClient(host, username, password, api_port) as client:
                # 1. Fetch Appliance Health (vCenter Status)
                try:
                    health = client._get("/appliance/health/system")
                    dcocfg.save_json({"overall_health": health}, system, instance, "appliance_health")
                except Exception as e:
                    logger.warning(f"{system}/{instance}: Could not get appliance health: {e}")
                    # Save a placeholder so process phase doesn't fail
                    dcocfg.save_json({"overall_health": "gray", "error": str(e)}, system, instance, "appliance_health")

                # 2. Fetch Hosts with potentially extra fields
                # We fetch the basic list first
                basic_hosts = client._get("/vcenter/host")
                
                # For each host, try to get a more detailed view using the filter
                # In some versions, filtering by host-id returns more fields
                detailed_hosts = []
                for h in basic_hosts:
                    hid = h.get('host')
                    try:
                        # Attempt to get extra fields if available
                        h_detail = client._get(f"/vcenter/host?hosts={hid}")
                        if h_detail and isinstance(h_detail, list):
                            detailed_hosts.append(h_detail[0])
                        else:
                            detailed_hosts.append(h)
                    except:
                        detailed_hosts.append(h)
                
                dcocfg.save_json(detailed_hosts, system, instance, "hosts")

                # 3. Fetch Datastores
                # 3. Fetch Datastores (SOAP preferred for host info)
                ds_list = []
                if SOAP_AVAILABLE:
                    try:
                        ds_list = fetch_soap_datastores(host, username, password)
                        dcocfg.save_json(ds_list, system, instance, "datastores")
                    except Exception as e:
                        logger.warning(f"{system}/{instance}: SOAP datastore extraction failed: {e}")
                
                if not ds_list:
                    # Fallback to REST
                    try:
                        logger.info(f"{system}/{instance}: Falling back to REST for datastores")
                        datastores = client._get("/vcenter/datastore")
                        dcocfg.save_json(datastores, system, instance, "datastores")
                    except Exception as e:
                        logger.error(f"{system}/{instance}: REST datastore extraction failed: {e}")

                # 4. Fetch VMs (Enriched with Host info)
                # To include the host name as requested, we query VMs for each host
                all_vms = []
                for host_obj in detailed_hosts:
                    hid = host_obj['host']
                    hname = host_obj['name']
                    try:
                        vms_on_host = client._get(f"/vcenter/vm?hosts={hid}")
                        for vm in vms_on_host:
                            vm['host_id'] = hid
                            vm['host_name'] = hname
                            all_vms.append(vm)
                    except Exception as e:
                        logger.warning(f"{system}/{instance}: Error fetching VMs for host {hname}: {e}")
                
                # If host-based fetch failed or returned nothing, try global fetch as fallback
                if not all_vms:
                    all_vms = client._get("/vcenter/vm")
                
                dcocfg.save_json(all_vms, system, instance, "vms")
                
                # 5. Fetch Triggered Alarms via SOAP API (all entities)
                # This runs after REST extraction to reuse credentials
                if SOAP_AVAILABLE:
                    try:
                        soap_alarms = fetch_soap_alarms(host, username, password)
                        dcocfg.save_json(soap_alarms, system, instance, "alarms")
                    except Exception as e:
                        logger.warning(f"{system}/{instance}: SOAP alarm extraction failed: {e}")
                else:
                    logger.info(f"{system}/{instance}: Skipping SOAP alarms (pyVmomi not installed)")
                
                logger.info(f"Successfully collected data for {system}/{instance}")

        except Exception as e:
            logger.error(f"Error collecting data for {system}/{instance}: {e}")

if __name__ == "__main__":
    from common.DCOconfig import DCOconfig
    cfg = DCOconfig("config_encrypted.json")
    getinfo(cfg)
