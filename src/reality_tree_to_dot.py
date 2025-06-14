import re
import subprocess
import os
import sys
from pathlib import Path

def ask_for_filename_with_validation():
    """
    Ask for filename with basic validation (non-empty).
    
    Returns:
        str: Valid filename entered by the user
    """
    while True:
        filename = input("Please enter the filename: ")
        if filename.strip():  # Check if not empty after removing whitespace
            print(f"I got {filename}")
            return filename
        else:
            print("Filename cannot be empty. Please try again.")

def vertical_or_horizontal_output():
    while True:
        orientation = input("Diagram vertical 'V' or horizontal 'H' orientation?: ")
        if orientation.strip():  # Check if not empty after removing whitespace
            print(f"You said {orientation}")
            return orientation.lower()
        else:
            print("Orientation cannot be empty. Please try again.")

def read_entire_txt(file_name):
    """Reads short text file and returns lines as a list."""
    with open(file_name, "r") as file:
        text = file.read()
    return text

def save_gv_source(graphviz_src, out_file):
    """Saves created Graphviz source as a file."""
    with open(out_file, 'w', encoding='utf-8') as outfile:
        outfile.write(graphviz_src)
    print(f'File saved to {out_file}')

def lines_to_string(lines):
    """
    Convert a list of lines to a single string.
    
    Args:
        lines (list): List of strings representing lines
        
    Returns:
        str: Joined string with newlines
    """
    return '\n'.join(lines)

def get_file_name_with_chosen_ext(causal_infile, extension):
    """Take filename, and change its extension as asked."""
    path = Path(causal_infile)
    gv_outfile_name = path.with_suffix(extension)
    gv_outfile_name = str(gv_outfile_name)
    return gv_outfile_name

def convert_causal_to_graphviz(causal_in_data, source_file_attribution, horizontal):
    """
    Takes custom causal script (faster than doing graphviz with HTML tables by hand) and auto-convert it to normal graphviz source.
    Return a list of all the lines in the script

    Args:
        A string of custom causal 'code' that is consistent enough to convert to graphviz source.
    
    Returns:
        list: a list of graphviz lines
    """

    # --- Configuration ---
    TYPE_STYLES = {
        'de':    {'label': 'Desired Effect',     'color': 'lightgreen'},
        'ude':   {'label': 'Undesired Effect',   'color': 'lightcoral'},
        'goal':  {'label': 'Goal',               'color': 'green'},
        'cond':  {'label': 'Precondition',       'color': '#A9CCE3'},
        'act':   {'label': 'Action',             'color': 'orange'},
        'inter': {'label': 'Intermediate Effect','color': 'lightgray'},
        'cause': {'label': 'Cause',              'color': 'red'},
        'and':   {'label': 'AND',                'color': 'white'}
    }

    # --- Parsing ---
    nodes = {}
    edges = []

    for line in causal_in_data.strip().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Match edge
        if '->' in line:
            src, dst = map(str.strip, line.split('->'))
            edges.append((src, dst))
            continue

        # Match node
        match = re.match(r'^(\d+)\s+(\w+)(?:\s+"(.*?)")?$', line)
        if match:
            node_id, node_type, description = match.groups()
            description = description or ""
            nodes[node_id] = {'type': node_type.lower(), 'text': description}
        else:
            raise ValueError(f"Invalid line: {line}")

    # --- Graphviz DOT Output ---
    source_graphviz = []
    source_graphviz.append('digraph causal_graph {')
    if horizontal:
        source_graphviz.append('  rankdir=LR;')
    else:
        source_graphviz.append('  rankdir=BT;')
    source_graphviz.append('  node [shape=plaintext fontname="Helvetica"];')
    gv_entry = f'  # Source causal file: {source_file_attribution}\n'
    source_graphviz.append(gv_entry)
    source_graphviz.append('  # Nodes\n\n')

    # Node generation in graphviz output
    for node_id, node in nodes.items():
        node_type = node['type']
        desc = node['text']
        style = TYPE_STYLES.get(node_type, {'label': node_type.upper(), 'color': 'white'})
        label = style['label']
        color = style['color']

        if node_type == 'and':
            # and both get a cicle shape.
            gv_entry = f'  {node_id} [label={label}, shape=circle, width=0.5, height=0.5, fixedsize=true]; // Sets fixed size'
            source_graphviz.append(gv_entry)
        else:
            # add content to source_graphviz list
            # Should look like this
            #1 [label=<
            #    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
            #    <TR><TD BGCOLOR="lightgreen"><B>Desired Effect</B></TD></TR>
            #    <TR><TD>1. blah blah blah</TD></TR>
            #    </TABLE>
            #>];

            gv_entry1 = f'{node_id} [label=<'
            source_graphviz.append(gv_entry1)
            source_graphviz.append('    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">')
            gv_entry2 = f'      <TR><TD BGCOLOR="{color}"><B>{label}</B></TD></TR>'
            gv_entry3 = f'      <TR><TD>{node_id}. {desc}</TD></TR>'
            source_graphviz.append(gv_entry2)
            source_graphviz.append(gv_entry3)
            source_graphviz.append('    </TABLE>')
            source_graphviz.append('  >];')

    # Edge generation in graphviz output
    source_graphviz.append('  # Edges\n\n')
    for src, dst in edges:
        gv_entry = f'  {src} -> {dst};'
        source_graphviz.append(gv_entry)

    source_graphviz.append('}') # closing paren for dot files

    return source_graphviz

def render_graphviz(input_file, output_file=None, engine='dot', output_format='png'):
    """
    Render a Graphviz file to an image using the specified engine.
    
    Args:
        input_file (str): Path to the .gv or .dot input file
        output_file (str, optional): Output file path. If None, auto-generates based on input filename
        engine (str): Graphviz engine to use ('dot', 'neato', 'circo', 'fdp', 'sfdp', 'twopi')
        output_format (str): Output format ('png', 'svg', 'pdf', 'jpg', etc.)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"Error: Input file '{input_file}' not found.")
            return False
        
        # Generate output filename if not provided
        if output_file is None:
            input_path = Path(input_file)
            output_file = input_path.with_suffix(f'.{output_format}')
        
        # Build the command
        cmd = [engine, f'-T{output_format}', input_file, '-o', str(output_file)]
        
        print(f"Running: {' '.join(cmd)}")
        
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        print(f"Successfully created '{output_file}'")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error running Graphviz: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Command error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Error: '{engine}' command not found. Make sure Graphviz is installed and in your PATH.")
        print("Install Graphviz from: https://graphviz.org/download/")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def convert_gv_to_png(gv_filename):
    """Simple function to convert .gv file to .png with same base name."""
    base_name = Path(gv_filename).stem
    filename_png_extension = f"{base_name}.png"
    return render_graphviz(gv_filename, filename_png_extension)

def convert_gv_to_svg(gv_filename):
    """Simple function to convert .gv file to .svg with same base name."""
    base_name = Path(gv_filename).stem
    filename_svg_extension = f"{base_name}.svg"
    return render_graphviz(gv_filename, filename_svg_extension)

def main():

    causal_in_data = ask_for_filename_with_validation()
    print(f'\nConverting: {causal_in_data}\n')

    graphviz_output_filename = get_file_name_with_chosen_ext(causal_in_data, ".gv")

    user_orientation_preference = vertical_or_horizontal_output()
    if user_orientation_preference == "h":
        horizontal = True
    else:
        horizontal = False

    # Get causal data format
    causal_source = read_entire_txt(causal_in_data)
    
    # Convert causal data format to list of graphviz dot lines
    graphviz_lines_list = convert_causal_to_graphviz(causal_source, causal_in_data, horizontal)
    
    # Change list of lines to a string to save it next
    graphviz_src = lines_to_string(graphviz_lines_list)
    
    # Save dot graphviz version
    save_gv_source(graphviz_src, graphviz_output_filename)

    graphviz_diagram_png_filename = get_file_name_with_chosen_ext(causal_in_data, extension=".png")
    graphviz_diagram_svg_filename = get_file_name_with_chosen_ext(causal_in_data, extension=".svg")
 
    render_graphviz(graphviz_output_filename, graphviz_diagram_svg_filename, output_format='svg')
    render_graphviz(graphviz_output_filename, graphviz_diagram_png_filename, output_format='png')

if __name__ == '__main__':
    main()