from setuptools import setup, find_packages
from setuptools.command.install import install
from codecs import open
import subprocess
from os import path
import sys
import shutil

class CustomInstallCommand(install):
    """Custom install command to set up SRIM and dependencies."""

    def is_installed(self, package):
        """Check if a package is installed."""
        try:
            subprocess.run(["dpkg", "-l", package], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def run(self):
        # Run standard installation
        install.run(self)

        # Check if Wine and Winetricks are installed before requesting sudo
        need_sudo = False
        missing_packages = []

        if not self.is_installed("wine"):
            missing_packages.append("wine")
            need_sudo = True
        if not self.is_installed("winetricks"):
            missing_packages.append("winetricks")
            need_sudo = True
        if not self.is_installed("p7zip-full"):
            missing_packages.append("p7zip-full")
            need_sudo = True

        if need_sudo:
            print(f"Installing missing packages: {', '.join(missing_packages)}")
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y"] + missing_packages, check=True)
        else:
            print("Wine, Winetricks, and p7zip-full are already installed. Skipping package installation.")

        # Define SRIM installation
        srim_url = "http://www.srim.org/SRIM/SRIM-2013-Pro.e"
        srim_exe = "SRIM-2013-Pro.exe"
        srim_dir = os.path.join(os.getcwd(), "srim_install")

        os.makedirs(srim_dir, exist_ok=True)

        # Download SRIM
        if not os.path.exists(srim_exe):
            print("Downloading SRIM...")
            subprocess.run(["wget", srim_url, "-O", srim_exe], check=True)
        else:
            print("SRIM installer already downloaded. Skipping download.")

        # Extract SRIM
        print("Extracting SRIM...")
        subprocess.run(["7z", "x", srim_exe, f"-o{srim_dir}"], check=True)

        # Install Visual Basic runtime for Wine
        print("Installing VB5 runtime for SRIM...")
        subprocess.run(["winetricks", "vb5run"], check=True)

        # Copy .ocx files
        srim_setup_dir = os.path.join(srim_dir, "SRIM-Setup")
        if os.path.exists(srim_setup_dir):
            print("Copying .ocx files...")
            for file in os.listdir(srim_setup_dir):
                if file.endswith(".ocx"):
                    shutil.copy(os.path.join(srim_setup_dir, file), srim_dir)
        else:
            print("No .ocx files found. Skipping copy.")

        print("SRIM installation complete!")
        print(f"Run SRIM using:\ncd {srim_dir} && wine SRIM.exe")

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pysrim',
    version='0.5.10',
    description='Srim Automation of Tasks via Python',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://gitlab.com/costrouc/pysrim',
    author='Christopher Ostrouchov',
    author_email='chris.ostrouchov+pysrim@gmail.com',
    license="MIT",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='material srim automation plotting',
    download_url='https://gitlab.com/costrouc/pysrim/repository/master/archive.zip',
    packages=find_packages(exclude=['examples', 'tests', 'test_files', 'docs']),
    package_data={
        'srim': ['data/*.yaml'],
    },
    setup_requires=['pytest-runner', 'setuptools>=38.6.0'],  # >38.6.0 needed for markdown README.md
    install_requires=['pyyaml', 'numpy>=1.10.0'],
    tests_require=['pytest', 'pytest-mock', 'pytest-cov'],
    cmdclass={"install": CustomInstallCommand},  # Hook the custom install command
)
