#!/bin/bash

set -e  # Exit on error

# Function to check if a package is installed
is_installed() {
    dpkg -l | grep -qw "$1"
}

# Install Wine and Winetricks if not installed
if ! is_installed wine; then
    echo "Installing Wine..."
    sudo apt update && sudo apt install -y wine
else
    echo "Wine is already installed. Skipping..."
fi

if ! is_installed winetricks; then
    echo "Installing Winetricks..."
    sudo apt install -y winetricks
else
    echo "Winetricks is already installed. Skipping..."
fi

# Install pysrim from the specified GitHub repository
if ! python3 -c "import srim" 2>/dev/null; then
    echo "Installing pysrim..."
    pip install git+https://github.com/FilipovicLado/pysrim.git
else
    echo "pysrim is already installed. Skipping..."
fi

# Define SRIM installation variables
SRIM_URL="http://www.srim.org/SRIM/SRIM-2013-Pro.e"
SRIM_EXE="SRIM-2013-Pro.exe"
SRIM_DIR="pysrim/srim"

# Create directory for SRIM inside pysrim if not exists
mkdir -p "$SRIM_DIR"

# Download and install SRIM
if [ ! -f "$SRIM_EXE" ]; then
    echo "Downloading SRIM..."
    wget "$SRIM_URL" -O "$SRIM_EXE"
else
    echo "SRIM installer already downloaded. Skipping..."
fi

# Extract SRIM using 7zip
if [ ! -d "$SRIM_DIR" ]; then
    echo "Extracting SRIM..."
    if ! is_installed p7zip-full; then
        echo "Installing p7zip-full..."
        sudo apt install -y p7zip-full
    fi
    7z x "$SRIM_EXE" -o"$SRIM_DIR"
else
    echo "SRIM directory already exists. Skipping extraction..."
fi

# Install Visual Basic 5 runtime
if ! wine reg query "HKEY_CLASSES_ROOT\\VB5Run" > /dev/null 2>&1; then
    echo "Installing Visual Basic 5 runtime..."
    winetricks vb5run || wine "$SRIM_DIR/SRIM-Setup/MSVBvm50.exe"
else
    echo "Visual Basic 5 runtime already installed. Skipping..."
fi

# Copy .ocx files to main SRIM directory
if [ -d "$SRIM_DIR/SRIM-Setup" ]; then
    echo "Copying .ocx files..."
    cp "$SRIM_DIR/SRIM-Setup"/*.ocx "$SRIM_DIR/"
else
    echo "SRIM-Setup directory not found. Skipping .ocx copy..."
fi

# Installation complete
echo "SRIM and pysrim installation complete!"
echo "You can now run SRIM using:"
echo "cd $SRIM_DIR && wine SRIM.exe"
