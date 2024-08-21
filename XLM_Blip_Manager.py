import xml.etree.ElementTree as ET
import math
import os
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import checkboxlist_dialog, radiolist_dialog
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.key_binding import KeyBindings

# Validator for coordinate input
class CoordinateValidator(Validator):
    def validate(self, document):
        try:
            parts = document.text.split(',')
            if len(parts) != 3:
                raise ValidationError(message="Please enter exactly three values separated by commas.")
            tuple(map(float, parts))
        except ValueError:
            raise ValidationError(message="All values must be valid numbers.")

# Validator for offset input
class OffsetValidator(Validator):
    def validate(self, document):
        try:
            parts = document.text.split()
            if len(parts) != 3:
                raise ValidationError(message="Please enter exactly three values separated by spaces.")
            tuple(map(float, parts))
        except ValueError:
            raise ValidationError(message="All values must be valid numbers.")

# Function to find all XML files in the directory
def list_xml_files(directory):
    return [f for f in os.listdir(directory) if f.endswith('.xml')]

# Function to find all blips in the XML
def find_blips(tree, file_name):
    root = tree.getroot()
    blips = []

    excluded_tags = {'CameraPosition', 'CameraDirection', 'VehiclePreviewCameraPosition', 'VehiclePreviewCameraDirection', 'EntrancePosition', 'Position', 'SpawnPlace', 'Vector1', 'Vector2', 'RoadToggler'}

    for element in root.iter():
        x = element.find('.//X')
        y = element.find('.//Y')
        z = element.find('.//Z')

        if x is not None and y is not None and z is not None:
            name = element.find('.//Name')
            blip_name = name.text if name is not None else element.tag

            if blip_name in excluded_tags:
                continue

            blips.append({
                'name': blip_name,
                'X': float(x.text),
                'Y': float(y.text),
                'Z': float(z.text),
                'element': element,
                'file': file_name  # Set file name for each blip
            })

    return blips

# Function to calculate offset
def calculate_offset(blip, ref_vector):
    ref_x, ref_y, ref_z = ref_vector

    offset_x = ref_x - blip['X']
    offset_y = ref_y - blip['Y']
    offset_z = ref_z - blip['Z']

    distance = math.sqrt(offset_x**2 + offset_y**2 + offset_z**2)

    return offset_x, offset_y, offset_z, distance

# Function to apply offset to a blip
def apply_offset(blip, offset_x, offset_y, offset_z):
    blip['X'] += offset_x
    blip['Y'] += offset_y
    blip['Z'] += offset_z

    blip['element'].find('.//X').text = str(blip['X'])
    blip['element'].find('.//Y').text = str(blip['Y'])
    blip['element'].find('.//Z').text = str(blip['Z'])

# Function to display the main menu
def display_menu():
    return radiolist_dialog(
        title="Main Menu",
        text="Choose an option:",
        values=[
            ("1", "Calculate Offset"),
            ("2", "Apply Offset to Blips"),
            ("3", "Replace Original XML Files with Fixed Versions"),
            ("4", "Combine Blips into a New File"),
            ("5", "Reset All Values"),
            ("6", "Exit")
        ],
    ).run()

def replace_original_files(directory):
    for file_name in list_xml_files(directory):
        fixed_file = file_name.replace('.xml', '_fixed.xml')
        if os.path.exists(fixed_file):
            os.replace(fixed_file, file_name)
            print(f"Replaced {file_name} with {fixed_file}.")
        else:
            print(f"Fixed version for {file_name} not found.")

# Function to combine blips into a new file while preserving the structure without the XML declaration
def combine_blips(blips, output_file_name, trees):
    if not blips:
        print("No blips to combine.")
        return
    
    # Ensure the output file name ends with .xml
    if not output_file_name.endswith('.xml'):
        output_file_name += '.xml'
    
    # Create the root element for the new XML
    root = ET.Element("PossibleLocations")
    
    # Copy relevant tags from each original XML file's tree
    for tree in trees.values():
        original_root = tree.getroot()
        
        # Iterate over all child elements of the original root (e.g., DeadDrops, ScrapYards)
        for child in original_root:
            root.append(child)
    
    # Write the combined content into the output file without the XML declaration
    tree = ET.ElementTree(root)
    with open(output_file_name, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=False)
    print(f"Combined XML saved to {output_file_name}.")

def reset_values():
    global offset_x, offset_y, offset_z
    offset_x = offset_y = offset_z = None
    print("All values have been reset.")

# Function to select XML files from a list
def select_xml_files(directory):
    files = list_xml_files(directory)
    if not files:
        print("No XML files found in the directory.")
        return []

    return checkboxlist_dialog(
        title="Select XML Files",
        text="Select XML files:",
        values=[(f, f) for f in files],
    ).run()

def group_blips_by_file(blips):
    grouped_blips = {}
    for blip in blips:
        file_name = blip['file']
        if file_name not in grouped_blips:
            grouped_blips[file_name] = []
        grouped_blips[file_name].append(blip)
    return grouped_blips

def select_blip_for_calculation(blips):
    grouped_blips = group_blips_by_file(blips)
    
    choices = []
    choice_map = {}
    
    index = 0
    for file_name, file_blips in grouped_blips.items():
        choices.append((None, f"--- {file_name} ---", 'header'))
        for blip in file_blips:
            blip_name = blip.get("name", "Unknown Blip")
            blip_coords = f"({blip['X']:.6f}, {blip['Y']:.6f}, {blip['Z']:.6f})"
            display_text = f"{blip_name} - {blip_coords}"
            choices.append((index, display_text, 'blip'))
            choice_map[display_text] = index
            index += 1
    
    selected_text = radiolist_dialog(
        title="Select a Blip",
        text="Select a blip to calculate offset:",
        values=[(text, text) for _, text, _ in choices],
    ).run()
    
    if selected_text is None:
        return None
    
    selected_index = choice_map.get(selected_text)
    if selected_index is not None:
        print(f"Selected blip index: {selected_index}")  # Debugging line
        return blips[selected_index]
    
    return None

def select_blips_for_offset(blips, all_blips_option=True):
    grouped_blips = group_blips_by_file(blips)
    
    file_names = list(set(blip['file'] for blip in blips))

    if all_blips_option:
        file_names.insert(0, "All Files")

    selected_files = checkboxlist_dialog(
        title="Select Files",
        text="Select files to apply offset:",
        values=[(file_name, file_name) for file_name in file_names],
    ).run()

    if "All Files" in selected_files:
        return [blip for blip in blips]

    return [blip for blip in blips if blip['file'] in selected_files]

def save_modified_tree(original_file_path, tree, offset_suffix="_fixed"):
    base, ext = os.path.splitext(original_file_path)
    new_file_path = f"{base}{offset_suffix}{ext}"
    tree.write(new_file_path)
    print(f"Modified file saved as {new_file_path}")

# Key bindings setup
bindings = KeyBindings()

@bindings.add('c-c')
def _(event):
    event.app.exit()

@bindings.add('c-s')
def _(event):
    event.app.set_return_value(None)

# Main function
def main():
    directory = '.'  # Set the directory where your XML files are located

    global offset_x, offset_y, offset_z
    offset_x = offset_y = offset_z = None  # Initialize offset variables

    while True:
        choice = display_menu()

        if choice == '1':
            selected_files = select_xml_files(directory)
            if not selected_files:
                print("No XML files selected. Returning to menu.")
                continue

            all_blips = []
            trees = {}
            for xml_file in selected_files:
                tree = ET.parse(xml_file)
                trees[xml_file] = tree
                blips = find_blips(tree, xml_file)  # Pass file name to find_blips
                all_blips.extend(blips)

            blip = select_blip_for_calculation(all_blips)
            if not blip:
                print("No blip selected for calculation.")
                continue

            ref_vector_input = prompt("Enter the reference vector (in the format: 7554.967, -285.6804, 6.080537): ",
                                      validator=CoordinateValidator(), key_bindings=bindings)

            if not ref_vector_input:
                print("No reference vector entered. Returning to menu.")
                continue

            try:
                ref_vector = tuple(map(float, ref_vector_input.split(',')))
            except ValueError:
                print("Invalid reference vector format. Returning to menu.")
                continue

            offset_x, offset_y, offset_z, distance = calculate_offset(blip, ref_vector)
            print(f"\nBlip {blip['name']} - Offset: X={offset_x}, Y={offset_y}, Z={offset_z}, Distance={distance}")

            prompt("\nPress Enter to return to the menu...", key_bindings=bindings)

        elif choice == '2':
            selected_files = select_xml_files(directory)
            if not selected_files:
                print("No XML files selected. Returning to menu.")
                continue

            all_blips = []
            trees = {}
            for xml_file in selected_files:
                tree = ET.parse(xml_file)
                trees[xml_file] = tree
                blips = find_blips(tree, xml_file)  # Pass file name to find_blips
                all_blips.extend(blips)

            blips_to_apply_offset = select_blips_for_offset(all_blips, all_blips_option=True)
            if not blips_to_apply_offset:
                print("No blips selected for offsetting.")
                continue

            offset_input = prompt("Enter the offset values (X Y Z) or press Enter to use the previously calculated offset: ",
                                default=f"{offset_x:.6f} {offset_y:.6f} {offset_z:.6f}" if offset_x is not None else "", 
                                validator=OffsetValidator(), key_bindings=bindings)

            if not offset_input:
                print("No offset values entered. Returning to menu.")
                continue

            try:
                offset_x, offset_y, offset_z = map(float, offset_input.split())
            except ValueError:
                print("Invalid offset values format. Returning to menu.")
                continue

            for blip in blips_to_apply_offset:
                apply_offset(blip, offset_x, offset_y, offset_z)
                print(f"\nOffset applied to {blip['name']}: New X={blip['X']}, Y={blip['Y']}, Z={blip['Z']}")

            for xml_file, tree in trees.items():
                save_modified_tree(xml_file, tree)

            prompt("\nPress Enter to return to the menu...", key_bindings=bindings)

        elif choice == '3':
            replace_original_files(directory)
            prompt("\nPress Enter to return to the menu...", key_bindings=bindings)

        elif choice == '4':
            selected_files = select_xml_files(directory)
            if not selected_files:
                print("No XML files selected. Returning to menu.")
                continue

            combined_blips = []
            for file_name in selected_files:
                tree = ET.parse(file_name)
                blips = find_blips(tree, file_name)
                combined_blips.extend(blips)

            output_file_base_name = prompt("Enter the base name for the combined XML file (e.g., combined_blips): ")
            if output_file_base_name:
                combine_blips(combined_blips, output_file_base_name, {file_name: ET.parse(file_name) for file_name in selected_files})
            else:
                print("No output file name provided. Returning to menu.")

            prompt("\nPress Enter to return to the menu...", key_bindings=bindings)

        elif choice == '5':
            reset_values()
            prompt("\nPress Enter to return to the menu...", key_bindings=bindings)

        elif choice == '6':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Exiting...")
            break

if __name__ == "__main__":
    main()
