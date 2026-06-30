import atexit
import logging
import ssl
import time

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

from vmkit.errors import AuthenticationError, ConnectionFailedError
from vmkit.progress import ProgressCallback, Reporter

log = logging.getLogger("deploy-vm")


def connect(host: str, user: str, password: str, port: int) -> vim.ServiceInstance:
    """Connect to ESXi/vCenter, return the ServiceInstance.

    Raises AuthenticationError on bad credentials, ConnectionFailedError otherwise.
    """
    log.info("Connecting to %s as %s ...", host, user)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        si = SmartConnect(host=host, user=user, pwd=password, port=port, sslContext=ctx)
    except vim.fault.InvalidLogin:
        raise AuthenticationError(
            f"Login failed: invalid username or password for {user}@{host}."
        )
    except Exception as exc:
        raise ConnectionFailedError(f"Could not connect to {host}: {exc}")
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
    progress: ProgressCallback | None = None,
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
    wait_for_task(task, "Register VM", progress)


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


def power_on_vm(
    content: vim.ServiceInstanceContent,
    name: str,
    progress: ProgressCallback | None = None,
) -> None:
    """Power on the named VM."""
    target = get_vm_by_name(content, name)
    if not target:
        log.warning("Could not find VM '%s' to power on.", name)
        return
    log.info("Powering on VM: %s", name)
    task = target.PowerOnVM_Task()
    wait_for_task(task, "Power on", progress)


def power_off_vm(
    content: vim.ServiceInstanceContent,
    name: str,
    progress: ProgressCallback | None = None,
) -> None:
    """Power off the named VM."""
    target = get_vm_by_name(content, name)
    if not target:
        log.warning("Could not find VM '%s' to power off.", name)
        return
    log.info("Powering off VM: %s", name)
    task = target.PowerOffVM_Task()
    wait_for_task(task, "Power off", progress)


def _task_key(label: str) -> str:
    """Stable per-operation key for progress consumers (one bar/channel each)."""
    return "task:" + label.lower().replace(" ", "-")


def wait_for_task(
    task: vim.Task, label: str, progress: ProgressCallback | None = None
) -> object:
    """Block until a vSphere task completes, emitting 0-100% progress events."""
    rep = Reporter(progress, key=_task_key(label), label=label, total=100, unit="%")
    rep.start()
    while task.info.state in (vim.TaskInfo.State.running, vim.TaskInfo.State.queued):
        rep.to(task.info.progress or 0)
        time.sleep(1)

    if task.info.state == vim.TaskInfo.State.success:
        rep.finish()
        log.info("  %s: done", label)
        return task.info.result
    else:
        err = task.info.error
        msg = err.msg if err else "unknown error"
        rep.fail(msg)
        log.error("  %s FAILED: %s", label, msg)
        raise RuntimeError(f"{label} failed: {msg}")
