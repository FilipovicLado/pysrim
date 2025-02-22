# Parallelized SRIM & pysrim Installation Guide

This document provides a streamlined installation guide for SRIM and `pysrim`, now fully integrated into `pip install .` for easier setup.

## Installation Steps

To install SRIM and `pysrim`, simply run:

```bash
git clone https://github.com/FilipovicLado/pysrim
cd pysrim
pip install .
```

The installation process will:
- Check for required dependencies (`wine`, `winetricks`, `p7zip-full`).
- Install missing dependencies if needed.
- Install the parallelized form of `pysrim`.
- Download, extract, and set up SRIM in the `srim_install` subdirectory.

## Step-by-Step Explanation of the Installation Process

1. **Checking and Installing Dependencies**  
   - The script first checks if `wine`, `winetricks`, and `p7zip-full` are installed.  
   - If they are missing, they are installed using:
     ```bash
     sudo apt update && sudo apt install -y wine winetricks p7zip-full
     ```  
     However, if all dependencies are already installed, nothing is required.

2. **Installing pysrim**  
   - `pysrim` is installed automatically in the `build` subfolder when running `pip install .`  

3. **Extracting and Downloading SRIM**  
   - The installer will use the SRIM package from the `assets` subfolder.
   - If `assets` is not available or the package does not exist, it downloads the SRIM package from the official website.  
     ```bash
     wget http://www.srim.org/SRIM/SRIM-2013-Pro.e
     ```  
   - It extracts the files into the `srim_install` subdirectory using `7z`.  
     ```bash
     7z x SRIM-2013-Pro.e -osrim_install
     ```  

4. **Installing Visual Basic 5 Runtime**  
   - SRIM requires the Visual Basic 5 runtime to function.  
   - This is installed automatically using:
     ```bash
     winetricks vb5run
     ```  
   - Alternatively, you can install it manually:
     ```bash
     cd srim_install
     wine ./SRIM-Setup/MSVBvm50.exe
     ```  

5. **Copying Required Files**  
   - `.ocx` files needed for SRIM are copied to the installation directory.  
     ```bash
     cp ./SRIM-Setup/*.ocx ./srim_install
     ```  

6. **Final Instructions**  
   - After installation, you can run SRIM using:
     ```bash
     cd srim_install && wine SRIM.exe
     ```  

This ensures that the entire installation process is automated while minimizing unnecessary privilege escalations.

---

## What's New in This Fork

This fork of `pysrim` includes functionality for parallelizing fragmented TRIM calculations by allowing multiple instances of `TRIM.exe` to run concurrently. This is achieved by:
- Creating unique process-specific directories in `/tmp/` for each TRIM execution using a `unique_id`.
- Copying necessary files to these directories to ensure execution and generated results files are independent.
- Running multiple instances of `TRIM.exe` in parallel without conflicts.
- Automatically managing temporary output directories for parallel execution.

Additionally, an example Jupyter Notebook has been introduced to demonstrate parallelization. The Al doping of SiC simulation is available in two versions:
- **Serial Execution**: `SiC_Al.ipynb`
- **Parallel Execution**: `SiC_Al_parallel.ipynb`

This modification significantly improves efficiency when running large-scale simulations by leveraging parallel processing.

---

## Original README
For the full original documentation for pysrim, refer to [`README_original.md`](README_original.md).
