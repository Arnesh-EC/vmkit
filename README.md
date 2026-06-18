# vmkit

ESXi/vCenter VM automation library — the reusable core behind the VM-Setup-Scripts CLIs and
(future) REST API.

Modules:
- `connect`, datacenter/datastore/VM lookups, register, power on/off, task waiting (`esxi`)
- server-side datastore file/disk copy, HTTPS upload/download, size queries (`datastore`)
- VMX template rendering, guest-OS detection, random VMware MAC (`vmx`)
- input validators for argparse `type=` (`validate`)
- progress bars + logging helpers (`progress`)

Consumed as a git submodule by the `VM-Setup-Scripts` superproject. Install editable for local
dev: `uv pip install -e .`

> Library code takes parameters (including credentials) and raises exceptions; it does not
> prompt, print, or call `sys.exit` — those are the caller's concern.
