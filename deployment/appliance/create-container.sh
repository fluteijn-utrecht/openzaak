#!/bin/bash
VM_NAME=openzaak
BRIDGE_ADAPTER="Realtek PCIe GBE Family Controller"

# Check script arguments.
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <ISO-file>"
    exit 2
fi

# Check if VBoxManage is available.
command -v vboxmanage >/dev/null 2>&1 || { echo >&2 "Error: The executable \"vboxmanage\" could not be found."; exit 1; }

OS_ISO_PATH=$1

# Check if ISO-file exists.
if [ ! -f $1 ]; then
    echo -n >&2 "Error: ISO-file \"$1\" not found."
    exit 1
fi

# If a VirtualBox container already exists, ask if we need to make a new one.
if [ -f ${VM_NAME}/${VM_NAME}.vdi ]; then
    echo -n "Delete existing and create new container? [y/n] "
    read -n 1 NEW_CONTAINER
    echo ""
else
    NEW_CONTAINER="y"
fi

# Create a new VirtualBox container from scratch.
if [ "$NEW_CONTAINER" == "y" ]; then

    echo "Cleaning up previous VirtualBox container..."

    vboxmanage unregistervm ${VM_NAME} --delete
    rm -rf ${VM_NAME}

    echo "Creating new VirtualBox container..."

    mkdir ${VM_NAME}
    cd ${VM_NAME}

    # Create basic container
    vboxmanage createhd --filename ${VM_NAME}.vdi --size 30720
    vboxmanage createvm --name ${VM_NAME} --ostype Debian_64 --register
    # A minimum of vram=10 is required to show the console.
    vboxmanage modifyvm ${VM_NAME} --memory 4096 --vram=12 --acpi on --nic1 bridged --bridgeadapter1 ${BRIDGE_ADAPTER}
    vboxmanage modifyvm ${VM_NAME} --nictype1 virtio 
    # Audio doesn't work with the OVF-tool and we don't need it.
    # Error: No support for the virtual hardware device type [...]
    vboxmanage modifyvm ${VM_NAME} --audio none
    vboxmanage modifyvm ${VM_NAME} --boot1 dvd --boot2 disk --boot3 none --boot4 none
    # SATA doesn't work with the OVF-tool, so we use SCSI
    # Error: Unsupported virtual hardware device 'AHCI'.
    # Error: No space left for device [...] on parent controller [...].
    # See: https://communities.vmware.com/thread/299949
    vboxmanage storagectl ${VM_NAME} --name "SCSI Controller" --add scsi
    vboxmanage storageattach ${VM_NAME} --storagectl "SCSI Controller" --port 0 --device 0 --type hdd --medium `pwd`/${VM_NAME}.vdi

    vboxmanage storagectl ${VM_NAME} --name "IDE Controller" --add ide --controller PIIX4
    vboxmanage storageattach ${VM_NAME} --storagectl "IDE Controller" --port 1 --device 0 --type dvddrive --medium `pwd`/../debian-10.2.0-amd64-netinst.iso

    echo "Start OS installation in VirtualBox container..."
    echo "(continue with the OS installation procedure in container)"

    virtualbox --startvm ${VM_NAME}
    echo "VirtualBox container was closed. Press any key to continue..."
    read -n 1

    # Remove DVD and poweroff (this fails if container already shutdown but doesn't matter).
    vboxmanage modifyvm ${VM_NAME} --dvd none
    # After the initial installation, the container should shut down automatically.
    # vboxmanage controlvm ${VM_NAME} poweroff
    # Remove dvd from boot order.
    vboxmanage modifyvm ${VM_NAME} --boot1 disk --boot2 none --boot3 none --boot4 none

    echo "Creating snapshot..."
    vboxmanage snapshot ${VM_NAME} take "initial-install"
    
# Use existing VirtualBox container and reset an initial-install image.
else
    cd ${VM_NAME}

    echo "Restoring snapshot..."
    vboxmanage snapshot ${VM_NAME} restore "initial-install"
fi

echo "Launching VirtualBox container..."
echo "(continue with the Open Zaak installation procedure in container and shut down when done)"

virtualbox --startvm ${VM_NAME}

echo "Creating snapshot..."
vboxmanage snapshot ${VM_NAME} take "openzaak-install"

echo "VirtualBox container was closed, assuming all done."
