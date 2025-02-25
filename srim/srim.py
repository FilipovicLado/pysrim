""" Module for automating srim calculations

"""
import os
import random
import subprocess
import shutil
import distutils.spawn
import re
import multiprocessing
import numpy as np

from filelock import FileLock
from srim.core.ion import Ion
from itertools import count

from .core.utils import (
    check_input,
    is_zero, is_zero_or_one, is_zero_to_two, is_zero_to_five,
    is_one_to_seven, is_one_to_eight,
    is_srim_degrees,
    is_positive,
    is_quoteless
)

from .output import Results, SRResults
from .input import AutoTRIM, TRIMInput, SRInput
from .config import DEFAULT_SRIM_DIRECTORY

class TRIMSettings(object):
    def __init__(self, **kwargs):
        """Initialize settings for a TRIM running"""
        self._settings = {
            'description': check_input(str, is_quoteless, kwargs.get('description', 'pysrim run')),
            'reminders': check_input(int, is_zero_or_one, kwargs.get('reminders', 0)),
            'autosave': check_input(int, is_zero_or_one, kwargs.get('autosave', 0)),
            'plot_mode': check_input(int, is_zero_to_five, kwargs.get('plot_mode', 5)),
            'plot_xmin': check_input(float, is_positive, kwargs.get('plot_xmin', 0.0)),
            'plot_xmax': check_input(float, is_positive, kwargs.get('plot_xmax', 0.0)),
            'ranges': check_input(int, is_zero_or_one, kwargs.get('ranges', 0)),
            'backscattered': check_input(int, is_zero_or_one, kwargs.get('backscattered', 0)),
            'transmit': check_input(int, is_zero_or_one, kwargs.get('transmit', 0)),
            'sputtered': check_input(int, is_zero_or_one, kwargs.get('ranges', 0)),
            'collisions': check_input(int, is_zero_to_two, kwargs.get('collisions', 0)),
            'exyz': check_input(int, is_positive, kwargs.get('exyz', 0)),
            'angle_ions': check_input(float, is_srim_degrees, kwargs.get('angle_ions', 0.0)),
            'bragg_correction': float(kwargs.get('bragg_correction', 1.0)), # TODO: Not sure what correct values are
            'random_seed': check_input(int, is_positive, kwargs.get('random_seed', random.randint(0, 100000))),
            'version': check_input(int, is_zero_or_one, kwargs.get('version', 0)),
        }

        if self.plot_xmin > self.plot_xmax:
            raise ValueError('xmin must be <= xmax')

    def __getattr__(self, attr):
        return self._settings[attr]

    def __getstate__(self):
        return self._settings
    
    def __setstate__(self, state):
        self._settings = state

class RunTRIM(object):
    """ Automate TRIM Calculations

    Parameters
    ----------
    target : :class:`srim.core.target.Target`
        constructed target for TRIM calculation
    ion : :class:`srim.core.ion.Ion`
        constructed ion for TRIM calculation
    calculation : :obj:`int`, optional
        Default 1 quick KP calculation
        (1) Ion Distribution and Quick Calculation of Damage (quick KP)
        (2) Detailed Calculation with full Damage Cascades (full cascades)
        (3) Monolayer Collision Steps / Surface Sputtering
        (4) Ions with specific energy/angle/depth (quick KP damage) using TRIM.DAT
        (5) Ions with specific energy/angle/depth (full cascades) using TRIM.DAT
        (6) Recoil cascades from neutrons, etc. (full cascades) using TRIM.DAT
        (7) Recoil cascades and monolayer steps (full cascades) using TRIM.DAT
        (8) Recoil cascades from neutrons, etc. (quick KP damage) using TRIM.DAT
    number_ions : :obj:`int`, optional
        number of ions that you want to simulate. Default 1000. A lot
        better than the 99999 default in TRIM...
    kwargs :
        See :class:`srim.srim.TRIMSettings` for available TRIM
        options. There are many and none are required defaults are
        appropriate for most cases.

    Notes
    -----
        If you are doing a simulation with over 1,000 ions it is
        recomended to split the calculaion into several smaller
        calculations. TRIM has been known to unexpectedly crash mainly
        due to memory usage.
    """
    def __init__(self, target, ion, calculation=1, number_ions=1000, **kwargs):
        """ Initialize TRIM calcualtion"""
        self.settings = TRIMSettings(**kwargs)
        self.calculation = check_input(int, is_one_to_seven, calculation)
        self.number_ions = check_input(int, is_positive, number_ions)
        self.target = target
        self.ion = ion

    def _write_input_files(self):
        """ Write necissary TRIM input files for calculation """
        AutoTRIM().write()
        TRIMInput(self).write()

    @staticmethod
    def copy_output_files(src_directory, dest_directory, check_srim_output=True):
        """Copies known TRIM files in directory to destination directory

        Parameters
        ----------
        src_directory : :obj:`str`
            source directory to look for TRIM output files
        dest_directory : :obj:`str`
            destination directory to copy TRIM output files to
        check_srim_output : :obj:`bool`, optional
            ensure that all files exist
        """
        known_files = {
            'TRIM.IN', 'PHONON.txt', 'E2RECOIL.txt', 'IONIZ.txt',
            'LATERAL.txt', 'NOVAC.txt', 'RANGE.txt', 'VACANCY.txt',
            'COLLISON.txt', 'BACKSCAT.txt', 'SPUTTER.txt',
            'RANGE_3D.txt', 'TRANSMIT.txt', 'TRIMOUT.txt',
            'TDATA.txt'
        }

        if not os.path.isdir(src_directory):
            raise ValueError('src_directory must be directory')

        if not os.path.isdir(dest_directory):
            raise ValueError('dest_directory must be directory')

        for known_file in known_files:
            if os.path.isfile(os.path.join(
                    src_directory, known_file)):
                shutil.copy(os.path.join(
                    src_directory, known_file), dest_directory)
            elif os.path.isfile(os.path.join(src_directory, 'SRIM Outputs', known_file)) and check_srim_output:
                shutil.move(os.path.join(
                    src_directory, 'SRIM Outputs', known_file), dest_directory)
        try:
            # Ensure we only delete directories inside /tmp/
            if src_directory.startswith("/tmp/"):
                shutil.rmtree(src_directory)  # Delete the entire source directory
                # print(f"Deleted source directory: {src_directory}")
        except Exception as e:
            print(f"Warning: Could not delete {src_directory} - {e}")

    def run(self, srim_directory=DEFAULT_SRIM_DIRECTORY, unique_id = -1):
        if unique_id < 2:
            process_directory = srim_directory
        else:
            process_directory = os.path.join("/tmp/", f"trim_{unique_id}")

            # Copy necessary SRIM/TRIM files into the temp directory
            # Create a process-specific working directory
            os.makedirs(process_directory, exist_ok=True)
            # Find all .exe, .dat, and .ocx files in the SRIM directory
            for file_name in os.listdir(srim_directory):
                if file_name.lower().endswith((".exe", ".dat", ".ocx")):
                    src_path = os.path.join(srim_directory, file_name)
                    dst_path = os.path.join(process_directory, file_name)
                    shutil.copy(src_path, dst_path)

            folders_to_copy=["SRIM Outputs", "SRIM Restore", "Data"]
            for folder in folders_to_copy:
                src_folder = os.path.join(srim_directory, folder)
                dst_folder = os.path.join(process_directory, folder)
                if os.path.exists(src_folder) and os.path.isdir(src_folder):
                    shutil.copytree(src_folder, dst_folder, dirs_exist_ok=True)

        current_directory = os.getcwd()
        try:
            # Change working directory to the process-specific folder
            os.chdir(process_directory)
            self._write_input_files()  # Ensure input files are written in this directory

       
            # Execute TRIM.exe in this directory
            if distutils.spawn.find_executable("wine"):  # Use Wine for Linux/macOS
                # Set a process-specific Wine environment
                env = os.environ.copy()
                env["WINEPREFIX"] = os.path.expanduser("~/.wine")
                env["WINEDEBUG"] = "-all"  # Suppress Wine debug messages
                env["TMP"] = process_directory
                env["TEMP"] = process_directory
                env["TMPDIR"] = process_directory

                # **Optimize Wine Initialization**
                wine_initialized_flag = os.path.join(env["WINEPREFIX"], ".wine_initialized")
                
                if not os.path.exists(wine_initialized_flag):
                    print("Initializing Wine")
                    subprocess.run(["wine", "wineboot", "-u"], env=env, stderr=subprocess.DEVNULL)
                    open(wine_initialized_flag, 'w').close()  # Create a flag file so Wine is not reset again

                process = subprocess.Popen(
                    ['wine', str(os.path.join('.', 'TRIM.exe'))],
                    cwd=process_directory,
                    # env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()
                # print("STDERR:", stderr.decode("utf-8", errors="ignore"))  # Debugging only

                # subprocess.check_call(['wine', str(os.path.join('.', 'TRIM.exe'))])
            else:
                subprocess.check_call([str(os.path.join('.', 'TRIM.exe'))])

            os.chdir(current_directory)
            return process_directory # Return the unique results directory
        finally:
            os.chdir(current_directory)  # Ensure we always return to the original directory

class TRIM(object):
    def __init__(self, ions, target, srim_dir, output_dir, number_ions=1000, step_size=100, **trim_settings):
        """ Initialize TRIM calcualtion"""
        self.ions = ions
        self.target = target
        self.srim_dir = srim_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.number_ions = check_input(int, is_positive, number_ions)
        self.step_size = check_input(int, is_positive, step_size)
        self.settings = trim_settings

    @staticmethod
    def find_folder(directory):
        """Finds a unique folder path safely using a file lock, without using pathlib."""
        os.makedirs(directory, exist_ok=True)  # Ensure base directory exists
        lock_path = os.path.join(directory, ".folder_lock")

        with FileLock(lock_path):  # Locking to prevent race conditions
            for i in count():
                folder_path = os.path.join(directory, str(i))
                if not os.path.exists(folder_path):  # Ensure uniqueness
                    os.makedirs(folder_path, exist_ok=True)  # Create folder safely
                    return os.path.abspath(folder_path)  # Return absolute folder path

    def fragment(self, step, total):
        """Generator to yield ion fragments for processing."""
        remaining = total
        while remaining > 0:
            if step > remaining:
                yield remaining
                break
            else:
                remaining -= step
                yield step

    @staticmethod
    def run_fragment(i, num_ions, ion, target, srim_dir, path, trim_settings):
        """Runs TRIM for a single ion fragment in a separate process, passing a unique process ID."""
        process_id = os.getpid()  # Generate unique ID based on process ID
        # print(f"Process {process_id} running fragment {i}: {num_ions} ions for {ion.symbol}")

        trim_settings = trim_settings or {'calculation': 2}

        # Run TRIM, passing the SRIM executable directory and unique process ID
        trim = RunTRIM(target, ion, number_ions=num_ions, **trim_settings)
        results = trim.run(srim_dir, process_id)  # Pass both
        # print(f"Process {process_id} finished fragment {i}")

        # Find a unique save directory and copy results
        save_directory = TRIM.find_folder(path)
        os.makedirs(save_directory, exist_ok=True)
        RunTRIM.copy_output_files(results, save_directory)
        print(f"Fragment {i} saved to: {save_directory}")
    
    def run_process(self, num_ions, ion, target, srim_dir, path, trim_settings):
        trim_settings = trim_settings or {'calculation': 2}

        # Run TRIM, passing the SRIM executable directory and unique process ID
        trim = RunTRIM(target, ion, number_ions=num_ions, **trim_settings)
        results = trim.run(srim_dir)  # Pass both

        # Find a unique save directory and copy results
        save_directory = TRIM.find_folder(path)
        os.makedirs(save_directory, exist_ok=True)
        RunTRIM.copy_output_files(results, save_directory)
        print(f"Process saved to: {save_directory}")

    def apply(self, threads = None):
        """Runs TRIM calculations in parallel for each ion, ensuring unique execution paths.

        Parameters
        ----------
        number_of_threads : int
            Number of parallel threads/processes to use.
        """
        if threads is None:
            threads = os.cpu_count()

        for ion in self.ions:  # Loop over each ion separately
            symbol_path = os.path.join(self.output_dir, ion['identifier'])  # Define unique output path
            # print("symbol_path = ", symbol_path)

            if threads < 2:  # Run in serial if only one thread
                # trim_settings = self.settings or {'calculation': 2}
                self.run_process(self.number_ions, Ion(**ion), self.target, self.srim_dir, symbol_path, self.settings)
            else:
                # Generate fragment arguments
                pool_args = [(i, self.step_size, Ion(**ion), self.target, self.srim_dir, symbol_path, self.settings) 
                            for i, num_ions in enumerate(self.fragment(self.step_size, self.number_ions))]

                num_workers = max(min(min(len(pool_args), threads), os.cpu_count()), 2)  # Limit to requested threads

                # Run parallel TRIM calculations for this ion
                with multiprocessing.Pool(processes=num_workers) as pool:
                    pool.starmap(TRIM.run_fragment, pool_args)  # Run fragments in parallel

            print(f"Completed TRIM simulation for ion: {ion['identifier']}")

class SRSettings(object):
    def __init__(self, **args):
        self._settings = {
            'energy_min': check_input(float, is_positive, args.get('energy_min', 1.0E3)),
            'output_type': check_input(int, is_one_to_eight, args.get('output_type', 1)),
            'output_filename': args.get('output_filename', 'SR_OUTPUT.txt'),
            'correction': check_input(float, is_positive, args.get('correction', 1.0))
        }

    def __getattr__(self, attr):
        return self._settings[attr]


class SR(object):
    def __init__(self, layer, ion, **kwargs):
        self.settings = SRSettings(**kwargs)
        self.layer = layer
        self.ion = ion

    def _write_input_file(self):
        """ Write necissary SR input file for calculation """
        SRInput(self).write()

    def run(self, srim_directory=DEFAULT_SRIM_DIRECTORY):
        current_directory = os.getcwd()
        try:
            os.chdir(os.path.join(srim_directory, 'SR Module'))
            self._write_input_file()
            # Make sure compatible with Windows, OSX, and Linux
            # If 'wine' command exists use it to launch TRIM
            if distutils.spawn.find_executable("wine"):
                subprocess.check_call(['wine', str(os.path.join('.', 'SRModule.exe'))])
            else:
                subprocess.check_call([str(os.path.join('.', 'SRModule.exe'))])

            return SRResults(os.path.join(srim_directory, 'SR Module'))
        finally:
            os.chdir(current_directory)
