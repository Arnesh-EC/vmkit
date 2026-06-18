import atexit
import logging
import ssl
import sys
import time

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

from vmkit.progress import make_progress_bar

log = logging.getLogger("deploy-vm")


def connect(host: str, user: str, password: str, port: int) -> vim.ServiceInstance:
    """Connect to ESXi/vCenter, return the ServiceInstance."""
    log.info("Connecting to %s as %s ...", host, user)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        si = SmartConnect(host=host, user=user, pwd=password, port=port, sslContext=ctx)
    except vim.fault.InvalidLogin:
        log.error("Login failed: invalid username or password.")
        sys.exit(2)
    except Exception as exc:
        log.error("Could not connect to %s: %s", host, exc)
        sys.exit(2)
    atexit.register(Disconnect, si)
    log.info("Connected. API version: %s", si.content.about.fullName)
    return si


def get_datacenter(content: vim.ServiceInstanceContent) -> vim.Datacenter:
    """Return the first (only, on standalone ESXi) datacenter."""
    for child in content.rootFolder.childEntity:
        if isinstance(child, vim.Datacenter):
            return child
    raise RuntimeError("No datacenter found on host.")


def list_vm_names(content: vim.ServiceInstanceContent) -> set[str]:
    """Return a set of all VM names currently in inventory."""
    view_mgr = content.viewManager
    assert view_mgr is not None
    view = view_mgr.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    try:
        return {vm.name for vm in view.view}
    finally:
        view.Destroy()


def get_datastore(content: vim.ServiceInstanceContent, name: str) -> vim.Datastore:
    """Return the datastore object matching ``name``."""
    view_mgr = content.viewManager
    assert view_mgr is not None
    view = view_mgr.CreateContainerView(content.rootFolder, [vim.Datastore], True)
    try:
        for ds in view.view:
            if ds.name == name:
                return ds
    finally:
        view.Destroy()
    raise RuntimeError(f"Datastore '{name}' not found on host.")


def register_vm(
    content: vim.ServiceInstanceContent,
    dc: vim.Datacenter,
    datastore: str,
    name: str,
) -> None:
    """Register the VM from its .vmx file."""
    vmx_ds_path = f"[{datastore}] {name}/{name}.vmx"
    log.info("Registering VM from: %s", vmx_ds_path)

    view_mgr = content.viewManager
    assert view_mgr is not None
    host_view = view_mgr.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
    try:
        esxi_host = host_view.view[0]
    finally:
        host_view.Destroy()
    resource_pool = esxi_host.parent.resourcePool

    task = dc.vmFolder.RegisterVM_Task(
        path=vmx_ds_path,
        name=name,
        asTemplate=False,
        pool=resource_pool,
        host=esxi_host,
    )
    wait_for_task(task, "Register VM")


def get_vm_by_name(
    content: vim.ServiceInstanceContent, name: str
) -> vim.VirtualMachine | None:
    """Return the VM object matching ``name``, or None if not found."""
    view_mgr = content.viewManager
    assert view_mgr is not None
    view = view_mgr.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    try:
        return next((vm for vm in view.view if vm.name == name), None)
    finally:
        view.Destroy()


def power_on_vm(content: vim.ServiceInstanceContent, name: str) -> None:
    """Power on the named VM."""
    target = get_vm_by_name(content, name)
    if not target:
        log.warning("Could not find VM '%s' to power on.", name)
        return
    log.info("Powering on VM: %s", name)
    task = target.PowerOnVM_Task()
    wait_for_task(task, "Power on")


def power_off_vm(content: vim.ServiceInstanceContent, name: str) -> None:
    """Power off the named VM."""
    target = get_vm_by_name(content, name)
    if not target:
        log.warning("Could not find VM '%s' to power off.", name)
        return
    log.info("Powering off VM: %s", name)
    task = target.PowerOffVM_Task()
    wait_for_task(task, "Power off")


def wait_for_task(task: vim.Task, label: str) -> object:
    """Block until a vSphere task completes, showing a progress bar."""
    bar = make_progress_bar(total=100, desc=label, unit="%")
    last_pct = 0
    while task.info.state in (vim.TaskInfo.State.running, vim.TaskInfo.State.queued):
        pct = task.info.progress or 0
        if pct > last_pct:
            bar.update(pct - last_pct)
            last_pct = pct
        time.sleep(1)

    if task.info.state == vim.TaskInfo.State.success:
        bar.update(100 - last_pct)
        bar.close()
        log.info("  %s: done", label)
        return task.info.result
    else:
        bar.close()
        err = task.info.error
        msg = err.msg if err else "unknown error"
        log.error("  %s FAILED: %s", label, msg)
        raise RuntimeError(f"{label} failed: {msg}")
