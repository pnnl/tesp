# Copyright (C) 2018-2020 Battelle Memorial Institute
# file: read_dot.py
""" This script parses a .dot file containing the coordinates of each object in 
the corresponding .glm and creates a .json file with just the object name and 
coordinates, as follows: 

    "R1_12_47_1_cap_1": [
        3534.0,
        4669.2
    ]

The resulting .json file is to be read by gld_feeder_generator.py to aid in 
plotting the populated feeder. For taxonomy feeders, the "gis_file" does not 
need to be specified in feeder_config.json5, as it is read automatically. For
any non-taxonomy, user-defined feeder, "gis_file" should point to the pos.json 
file, if available.

Credit: .dot files were obtained from 
https://emac.berkeley.edu/gridlabd/taxonomy_graphs/ courtesy of Michael A. Cohen,
last updated 2013-10-03.
    
"""


dot_file_path = "R5-12.47-3.dot"

prefix = dot_file_path.replace('.dot', '').replace('-', '_').replace('.', '_')


import re
import json

def extract_node_positions(dot_file_path):
    # Dictionary to store the node names and positions
    node_positions = {}

    # Open and read the .dot file
    with open(dot_file_path, 'r') as file:
        content = file.read()

        edge_pos_pattern = re.compile(r'(\w+)\s*--\s*(\w+)\s*\[.*?pos\s*=\s*"([^"]+)"', re.DOTALL)
        content = re.sub(edge_pos_pattern, "", content)

        # Regular expression to match nodes and their positions
        node_pos_pattern = re.compile(r'([a-zA-Z]+)(\d+)\s*\[\s*.*?pos\s*=\s*"([-\d.]+),([-\d.]+)"', re.DOTALL)

        # Find all matches for node names and positions
        matches = node_pos_pattern.findall(content)
        # Populate the dictionary with the node name and position
        for match in matches:
            node_letters = match[0]  # The letters part of the node name
            node_numbers = match[1]  # The number part of the node name
            x = float(match[2])  # First number (x-coordinate)
            y = float(match[3])  # Second number (y-coordinate)
            node_positions[f'{prefix}_{node_letters}_{node_numbers}'] = [x, y]

    return node_positions

# Example usage:
node_positions = extract_node_positions(dot_file_path)

with open(f'{prefix}_pos.json', 'w') as json_file:
    json.dump(node_positions, json_file, indent=4)
