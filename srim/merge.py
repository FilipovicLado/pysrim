import os
import numpy as np
import re
import shutil

from srim.core.ion import Element


class CASCADES:
    def __init__(self, data_directory):
        """
        Initialize CASCADES with the root directory containing ion calculations.
        It will scan for COLLISON.txt files and prepare data storage.
        """
        print("Initializing CASCADES from", data_directory)
        self.data_directory = data_directory
        self.collision_files = {}  # Stores files per ion symbol
        self.total_ions = {}  # Stores total ion count per ion type
        self.data = {}  # Stores NumPy arrays of positions

        # Scan and store file locations
        self._scan_directory()

    def _scan_directory(self):
        """ Scan the directory structure to find COLLISON.txt files. """
        for ion_symbol in os.listdir(self.data_directory):
            ion_dir = os.path.join(self.data_directory, ion_symbol)
            if not os.path.isdir(ion_dir):
                continue  # Skip non-directory files

            # Store collision files per ion type
            self.collision_files[ion_symbol] = []
            self.total_ions[ion_symbol] = 0

            for sub_dir in os.listdir(ion_dir):
                sub_path = os.path.join(ion_dir, sub_dir)
                if os.path.isdir(sub_path) and sub_dir.isdigit():  # Ensure directory is numeric
                    collision_file = os.path.join(sub_path, "COLLISON.txt")
                    trim_file = os.path.join(sub_path, "TRIM.IN")
                    if os.path.exists(collision_file):
                        self.collision_files[ion_symbol].append(collision_file)
                        # self._parse_directory(sub_path)  # Parse and store positions
                    
                    if os.path.exists(trim_file):
                        with open(trim_file, "r") as f:
                            try:
                                num_ions = int(f.read().split('\n')[2].split()[-3])
                                self.total_ions[ion_symbol] += num_ions
                            except (IndexError, ValueError):
                                print(f"Error reading TRIM.IN for {ion_symbol} in {sub_path}")

    def merge_collisions(self):
        """ Merge COLLISON.txt files for each ion type into a single file. """
        for ion_symbol, files in self.collision_files.items():
            if not files:
                continue  # Skip if no files found for this ion type

            output_file = os.path.join(self.data_directory, ion_symbol, "COLLISON.txt")
            # print(f"Merging {len(files)} files for {ion_symbol} into {output_file}")

            self._merge_collision_files(output_file, *files)

    def _get_total_ions(self, base_file):
        """ Extract the total number of simulated ions from TRIM.IN. """
        trim_file = os.path.join(os.path.dirname(base_file), "TRIM.IN")
        try:
            with open(trim_file, "r") as f:
                return int(f.read().split('\n')[2].split()[-3])  # Extract total ion count
        except (IndexError, ValueError, FileNotFoundError):
            print(f"Warning: Could not read total ions from {trim_file}")
            return 0  # Default to 0 if there's an issue

    def _merge_collision_files(self, output_file, *files):
        """ Merges multiple COLLISON.txt files while keeping correct ion numbering. """
        if len(files) < 1:
            print("Error: No files provided.")
            return
        
        if len(files) == 1:
            # Only one file: just copy it to the output location
            shutil.copy(files[0], output_file)
            # print(f"Only one file provided. Copied {files[0]} to {output_file}.")
            return

        history_marker = b"==========================  COLLISION HISTORY"
        ion_number_pattern = re.compile(br"For Ion\s+(\d+)")
        
        base_file = files[0]
        additional_files = files[1:]

        # Simply copy the first file to the output
        shutil.copy(base_file, output_file)

        # # Copy the first file completely to the output
        # with open(base_file, "rb") as f1, open(output_file, "wb") as out_f:
        #     copying = True
        #     for line in f1:
        #         out_f.write(line)
        #         if history_marker in line:
        #             copying = False  # Stop copying headers

        # Get the last ion number from the first file
        current_ion_number = self._get_total_ions(base_file)
        # print(f"Last ion number in {base_file}: {current_ion_number}")

        # Process and append the rest of the files
        for file_path in additional_files:
            # print(f"Processing {file_path}...")

            with open(file_path, "rb") as f, open(output_file, "ab") as out_f:
                skipping = True  # Start skipping header
                header_lines_to_skip = 10  # Skip "COLLISION HISTORY" + 9 lines

                for line in f:
                    if skipping:
                        if history_marker in line:
                            skipping = False
                            header_lines_to_skip = 9
                        continue

                    if header_lines_to_skip > 0:
                        header_lines_to_skip -= 1
                        continue  # Skip header lines

                    # Update ion numbering
                    match = ion_number_pattern.search(line)
                    if match:
                        current_ion_number += 1
                        line = ion_number_pattern.sub(f"For Ion {current_ion_number:07d}".encode(), line)

                    out_f.write(line)  # Append processed line

        print(f"Merged file created at: {output_file}")

    def generate_numpy_arrays(self):
        """
        Extract <x, y, z> positions from the merged COLLISION.txt files.
        Each ion type will have its final NumPy array saved as collision.dat.npy.
        """
        data = {}
        print("keys = ", self.collision_files.keys())
        for ion_symbol in self.collision_files.keys():
            # print(f"Processing {ion_symbol}...")

            element_obj = Element(ion_symbol)

            merged_file = os.path.join(self.data_directory, ion_symbol, "COLLISON.txt")
            npy_path = os.path.join(self.data_directory, ion_symbol, "collision.dat.npy")

            if not os.path.exists(merged_file):
                print(f"Warning: Merged file {merged_file} not found for {ion_symbol}. Skipping...")
                continue

            positions = []

            with open(merged_file, "rb") as f:
                for line in f.readlines():
                    line = line.decode('latin-1')
                    if line.endswith('Start of New Cascade  ³\r\n'):
                        tokens = line.split(chr(179))[1:-1]
                        positions.append([float(tokens[2]), float(tokens[3]), float(tokens[4])])
                    elif line.startswith('Û 0'):
                        tokens = line.split()[1:-1]
                        positions.append([float(tokens[3]), float(tokens[4]), float(tokens[5])])
            np_positions = np.array(positions)
            np.save(npy_path, np_positions)
            # print(f"Extracted {len(positions)} positions and saved to {npy_path}")

            self.data[ion_symbol] = {
                "total_ions": self.total_ions[ion_symbol],
                "collisions": np_positions / 10
            }

        return self.data
    def print_summary(self):
        sort_by_mass = lambda e1: Element(e1).mass
        # print summary information
        for ion in sorted(self.data, key=sort_by_mass):
            data_str = (
                "Symbol: {:2}\tNum Ions: {:7d}\tCollisions: {:7d}\n"
                "|\tMedian (x, y, z) [nm]: [{:.3f}\t{:.3f}\t{:.3f}]\n"
                "|\tMean   (x, y, z) [nm]: [{:.3f}\t{:.3f}\t{:.3f}]\n"
            )
            print(data_str.format(ion, self.data[ion]['total_ions'], len(self.data[ion]['collisions']), 
                                *np.median(self.data[ion]['collisions'], axis=0),
                                *np.mean(self.data[ion]['collisions'], axis=0)))

# Example usage:
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Merge SRIM collision files and extract data.")
    parser.add_argument("data_directory", help="Root directory containing SRIM outputs")
    args = parser.parse_args()
    
    cascades = CASCADES(args.data_directory)
    cascades.merge_collisions()  # Step 1: Merge COLLISION.txt files
    cascades._parse_merged_collisions()  # Step 2: Extract positions from merged file