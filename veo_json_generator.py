import json
import argparse
import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import List, Dict, Any, Union, Set, Tuple
from itertools import product
import re

# --- Core Logic (VeoJsonGenerator Class) ---

class VeoJsonGenerator:
    """
    A class to generate structured JSON prompts for Veo 3.1, supporting
    expressive templates from various input types, and generating multiple
    prompts based on the Cartesian product of all set/list/file inputs.
    """

    def __init__(self, title: str, style: Union[str, Set, List]):
        self.title = title
        self.style_variants = self._expand_input(style)
        self.cuts_variants = []
        self.input_map = {'s': self.style_variants} # Map to store expanded variants with short names

    def _load_text_file(self, file_path: str) -> List[str]:
        """
        Helper to read content from a .txt file, splitting by newline
        to create a list of variants.
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                # Split by newline, strip whitespace, and filter out empty lines
                variants = [line.strip() for line in content.splitlines() if line.strip()]
                if not variants:
                    return [f"ERROR: File at {file_path} is empty or contains only whitespace."]
                return variants
        except FileNotFoundError:
            return [f"ERROR: File not found at {file_path}"]
        except Exception as e:
            return [f"ERROR: Could not read file: {e}"]

    def _expand_input(self, input_data: Union[str, Set, List]) -> List[str]:
        """
        Expands a single input into a list of string variants.
        - String: checks for .txt file path, otherwise returns [string].
        - Set/List: returns a list of strings, where each element is a variant.
        - .txt file: returns a list of strings from the file content (newline-separated).
        """
        if isinstance(input_data, str):
            # Check if it's a file path and attempt to load its content
            if input_data.endswith('.txt'):
                if os.path.exists(input_data):
                    file_content_list = self._load_text_file(input_data)
                    # If the file is found and has content, return the content
                    if file_content_list and not file_content_list[0].startswith("ERROR:"):
                        return file_content_list
                    # If the file is empty or has a read error, treat the original string as a literal
                    return [input_data]
                else:
                    # If file not found, treat the original string as a literal
                    return [input_data]
            return [input_data]
        elif isinstance(input_data, (set, list)):
            # Convert each element in the set/list to a string variant
            return [str(item) for item in input_data]
        return [str(input_data)]

    def _expand_dict_inputs(self, input_dict: Dict[str, Union[str, Set, List]]) -> Dict[str, List[str]]:
        """
        Expands all values in a dictionary that are sets/lists/files into a list of string variants.
        Returns a dictionary where values are lists of strings.
        """
        expanded_dict = {}
        for key, value in input_dict.items():
            expanded_dict[key] = self._expand_input(value)
        return expanded_dict

    def add_single_scene(self,
                         description: Union[str, Set, List],
                         camera: Dict[str, Union[str, Set, List]],
                         scene: Dict[str, Union[str, Set, List]],
                         character: Dict[str, Union[str, Set, List]],
                         timestamp: str = "00:00-00:05",
                         shot_type: str = "medium shot",
                         sound: Union[str, Set, List] = "",
                         # Short names for advanced pattern matching
                         desc_var_name: str = 'd',
                         sound_var_name: str = 'o', # o for other sound
                         cam_mov_var_name: str = 'm',
                         cam_ang_var_name: str = 'g', # g for angle
                         scene_env_var_name: str = 'e',
                         scene_prop_var_name: str = 'p',
                         char_pose_var_name: str = 'z', # z for pose
                         char_expr_var_name: str = 'x', # x for expression
                         char_act_var_name: str = 'a'): # a for action
        """
        Adds a single scene (cut) to the video. This cut will be expanded
        into multiple variants based on the Cartesian product of its inputs.
        """
        
        # 1. Expand all inputs into lists of variants and store in input_map
        desc_variants = self._expand_input(description) or [""]
        self.input_map[desc_var_name] = desc_variants
        
        sound_variants = self._expand_input(sound) or [""]
        self.input_map[sound_var_name] = sound_variants
        
        camera_expanded = self._expand_dict_inputs(camera)
        scene_expanded = self._expand_dict_inputs(scene)
        character_expanded = self._expand_dict_inputs(character)

        # Map expanded variants to their full and short names
        variant_definitions = [
            ('description', desc_var_name, desc_variants),
            ('sound', sound_var_name, sound_variants),
            (f"camera.movement", cam_mov_var_name, camera_expanded.get('movement', ['dynamic orbit']) or [""]),
            (f"camera.angle", cam_ang_var_name, camera_expanded.get('angle', ['low angle']) or [""]),
            (f"scene.environment", scene_env_var_name, scene_expanded.get('environment', ['a forest']) or [""]),
            (f"scene.props", scene_prop_var_name, scene_expanded.get('props', ['a single spotlight, ancient runes']) or [""]),
            (f"character.pose", char_pose_var_name, character_expanded.get('pose', ['mid-action']) or [""]),
            (f"character.expression", char_expr_var_name, character_expanded.get('expression', ['intense focus']) or [""]),
            (f"character.action", char_act_var_name, character_expanded.get('action', ['running']) or [""]),
        ]
        
        # Store all variants in the input_map for later use in pattern parsing
        for _, short_name, variants in variant_definitions:
            self.input_map[short_name] = variants
            
        # 2. Get the keys and lists of variants for the Cartesian product
        # Filter out single-variant inputs for the initial product calculation
        product_variants = [(full_name, short_name, variants) for full_name, short_name, variants in variant_definitions if len(variants) > 1]
        
        all_keys = [full_name for full_name, _, _ in product_variants]
        all_variants = [variants for _, _, variants in product_variants]
        
        # Also include the single-variant inputs to be added back later
        single_variants = {full_name: variants[0] for full_name, _, variants in variant_definitions if len(variants) == 1}

        # 3. Calculate the Cartesian product of all variants
        cut_variants = []
        
        # If there are no multi-variants, we still need one cut
        if not all_variants:
            # If there are no multi-variants, we still need one cut
            # The product should run once with an empty tuple
            all_variants = [[]]
            
        for variant_tuple in product(*all_variants):
            cut = {
                "timestamp": timestamp,
                "shot_type": shot_type,
            }
            
            # 4. Reconstruct the cut dictionary for each variant
            variant_map = dict(zip(all_keys, variant_tuple))
            
            # Start with single variants
            cut_data = {
                "description": single_variants.get('description', desc_variants[0] if desc_variants else ''),
                "sound": single_variants.get('sound', sound_variants[0] if sound_variants else ''),
                "camera": {
                    "movement": single_variants.get('camera.movement', camera_expanded.get('movement', [''])[0]),
                    "angle": single_variants.get('camera.angle', camera_expanded.get('angle', [''])[0])
                },
                "scene": {
                    "environment": single_variants.get('scene.environment', scene_expanded.get('environment', [''])[0]),
                    "props": single_variants.get('scene.props', scene_expanded.get('props', [''])[0])
                },
                "character": {
                    "pose": single_variants.get('character.pose', character_expanded.get('pose', [''])[0]),
                    "expression": single_variants.get('character.expression', character_expanded.get('expression', [''])[0]),
                    "action": single_variants.get('character.action', character_expanded.get('action', [''])[0])
                }
            }
            
            # Overwrite with multi-variants
            for full_key, value in variant_map.items():
                if full_key == 'description':
                    cut_data['description'] = value
                elif full_key == 'sound':
                    cut_data['sound'] = value
                elif full_key.startswith('camera.'):
                    cut_data['camera'][full_key.split('.')[1]] = value
                elif full_key.startswith('scene.'):
                    cut_data['scene'][full_key.split('.')[1]] = value
                elif full_key.startswith('character.'):
                    cut_data['character'][full_key.split('.')[1]] = value
            
            cut = {
                "timestamp": timestamp,
                "shot_type": shot_type,
                "description": cut_data['description'],
                "sound": cut_data['sound'],
                "camera": cut_data['camera'],
                "scene": cut_data['scene'],
                "character": cut_data['character']
            }
            
            # Clean up empty sound
            if not cut["sound"]:
                del cut["sound"]

            cut_variants.append(cut)
            
        self.cuts_variants.append(cut_variants)

    def _generate_json_advanced(self, pattern: str) -> List[str]:
        """
        Generates JSONs based on the advanced pattern language.
        The pattern defines the Cartesian product of a subset of variables.
        """
        
        # 1. Parse the pattern to get the list of variables and their index patterns
        # Example: "s[0,2] x d * a[2n]"
        
        # The pattern is a sequence of variable definitions separated by 'x' or '*'
        # We will use a simple regex to split the pattern into variable definitions
        # and then parse the index pattern within the brackets.
        
        # Split by 'x' or '*'
        # We need to handle nested expressions like (...)[2n+1]
        
        # First, check for a final subsetting pattern on the whole expression
        final_subset_pattern = None
        match_final_subset = re.match(r'^(.*?)\[(.*?)\]$', pattern.strip())
        if match_final_subset:
            pattern = match_final_subset.group(1).strip()
            final_subset_pattern = match_final_subset.group(2).strip()
            
        # Split by 'x' or '*'
        variable_definitions = re.split(r'\s*[x*]\s*', pattern.strip())
        
        # Map of short name to (list of variants, list of indices)
        product_components = {}
        
        # List of full keys in the order they appear in the pattern
        product_full_keys = []
        
        # The full Cartesian product of the selected variants
        product_variants_list = []
        
        # Map short names to full keys for reconstruction
        short_to_full_map = {
            's': 'style', 'd': 'description', 'o': 'sound', 'm': 'camera.movement',
            'g': 'camera.angle', 'e': 'scene.environment', 'p': 'scene.props',
            'z': 'character.pose', 'x': 'character.expression', 'a': 'character.action'
        }
        
        # 2. Process each variable definition
        for var_def in variable_definitions:
            match = re.match(r'([a-z])(?:\[(.*?)\])?', var_def.lower())
            if not match:
                raise ValueError(f"Invalid variable definition in pattern: {var_def}")
            
            short_name = match.group(1)
            index_pattern = match.group(2)
            
            if short_name not in self.input_map:
                raise ValueError(f"Unknown variable short name in pattern: {short_name}")
            
            variants = self.input_map[short_name]
            
            if index_pattern:
                # Parse the index pattern to get the 0-based indices
                indices = parse_index_pattern(index_pattern, len(variants))
                
                # Get the subset of variants
                selected_variants = [variants[i] for i in indices]
            else:
                # If no index pattern, use all variants
                selected_variants = variants
            
            if not selected_variants:
                raise ValueError(f"Variable '{short_name}' resulted in an empty set of variants.")
            
            product_components[short_name] = selected_variants
            product_full_keys.append(short_to_full_map[short_name])
            product_variants_list.append(selected_variants)

        # 3. Calculate the product based on the operators
        
        # Split the pattern by spaces to get the operators
        operators = [op.strip() for op in re.findall(r'\s*([x*])\s*', pattern.strip())]
        
        # If no operators, assume a single variable or a single cross product
        if not operators and len(product_variants_list) > 1:
            # Default to cross product if multiple variables are present without explicit operators
            operators = ['x'] * (len(product_variants_list) - 1)
        elif not operators and len(product_variants_list) == 1:
            # Single variable, no product needed
            operators = []
        
        # The number of components must be one more than the number of operators
        if len(product_variants_list) != len(operators) + 1 and len(product_variants_list) > 1:
            raise ValueError("Invalid pattern structure. Number of variables must be one more than the number of operators.")
        
        final_json_list = []
        
        # --- Dot Product Logic ---
        
        # Find the length of the longest component for dot product expansion
        max_len = 1
        if '*' in operators:
            max_len = max(len(variants) for variants in product_variants_list)
        
        # The final product will be a list of tuples, where each tuple is a set of values
        # for the variables in the pattern.
        
        # If the pattern is a simple cross product (or single variable), use itertools.product
        if all(op == 'x' for op in operators) or not operators:
            product_iterator = product(*product_variants_list)
        else:
            # Complex product with '*' (dot product)
            
            # The number of iterations is determined by the max_len
            product_iterator = []
            for i in range(max_len):
                current_tuple = []
                for variants in product_variants_list:
                    # Efficient repetition: use modulo to cycle through the variants
                    current_tuple.append(variants[i % len(variants)])
                product_iterator.append(tuple(current_tuple))
        
        # --- JSON Generation ---
        
        # Calculate the product
        for product_tuple in product_iterator:
            
            # Find the first cut variant (which contains all single-variant fields)
            # Assuming only one cut is added for now (self.cuts_variants[0])
            # Check if cuts_variants is empty, which should not happen if inputs are correctly handled
            if not self.cuts_variants or not self.cuts_variants[0]:
                # This should be caught earlier, but as a safeguard, return an empty list
                return []
            base_cut = self.cuts_variants[0][0]
            
            # Create a new cut based on the base cut
            new_cut = json.loads(json.dumps(base_cut)) # Deep copy
            
            # The style variant is the first element of the product if 's' is in the pattern
            style_variant = self.style_variants[0] # Default to first style
            
            # Map the product tuple values to the cut fields
            for i, value in enumerate(product_tuple):
                full_key = product_full_keys[i]
                
                if full_key == 'style':
                    style_variant = value
                    # The style variant is only used in the final JSON, not the cut
                    continue
                elif full_key == 'description':
                    new_cut['description'] = value
                elif full_key == 'sound':
                    new_cut['sound'] = value
                elif full_key.startswith('camera.'):
                    new_cut['camera'][full_key.split('.')[1]] = value
                elif full_key.startswith('scene.'):
                    new_cut['scene'][full_key.split('.')[1]] = value
                elif full_key.startswith('character.'):
                    new_cut['character'][full_key.split('.')[1]] = value
            
            # Reconstruct the final JSON
            final_json = {
                "title": self.title,
                "style": style_variant,
                "cuts": [new_cut]
            }
            
            final_json_list.append(json.dumps(final_json, indent=4))
            
        # 4. Apply final subsetting if a pattern was provided
        if final_subset_pattern:
            indices = parse_index_pattern(final_subset_pattern, len(final_json_list))
            final_json_list = [final_json_list[i] for i in indices]
            
        return final_json_list

    def generate_json(self, pattern: str = None) -> List[str]:
        """
        Generates the final list of Veo 3.1 compatible JSON strings,
        based on the Cartesian product of all scene cuts and the style variants.
        
        If a pattern is provided, it is used to define the product and sequence.
        """
        
        # If a pattern is provided, we use the advanced logic
        if pattern and pattern.lower() not in ['all', 'default']:
            return self._generate_json_advanced(pattern)
        
        # --- Default 'all' or 'default' logic ---
        
        # 1. Combine all cut variants into a list of full video cut sequences
        all_cut_sequences = list(product(*self.cuts_variants))
        
        final_json_list = []
        
        # 2. Cartesian product of style variants and cut sequences
        for style_variant, cut_sequence in product(self.style_variants, all_cut_sequences):
            final_json = {
                "title": self.title,
                "style": style_variant,
                "cuts": list(cut_sequence)
            }
            final_json_list.append(json.dumps(final_json, indent=4))
            
        return final_json_list

# --- Utility Functions for CLI/GUI ---

def parse_index_pattern(pattern: str, max_index: int) -> List[int]:
    """
    Parses a pattern string to return a list of 0-based indices.
    Supports:
    - Comma-separated list of 0-based indices (e.g., '0,2,4')
    - Range of 0-based indices (e.g., '0-4')
    - Simple formula using 'n' (e.g., '2*n+1')
    
    max_index is the total number of variants (e.g., len(variants)).
    """
    pattern = pattern.strip().lower()
    indices = set()
    
    # Check for formula pattern (e.g., '2*n+1')
    if 'n' in pattern:
        try:
            # Use a safe evaluation environment
            code = compile(pattern, '<string>', 'eval')
            
            # Restrict globals to prevent arbitrary code execution
            safe_globals = {}
            
            # Iterate through 'n' starting from 0
            n = 0
            while True:
                safe_locals = {'n': n}
                
                # Evaluate the formula
                index = eval(code, safe_globals, safe_locals)
                
                # Convert to integer
                index = int(index)
                
                if index >= max_index:
                    break
                
                if index >= 0:
                    indices.add(index)
                
                n += 1
                # Safety break to prevent infinite loops
                if n > max_index * 2:
                    break
        except Exception:
            # Fall through to comma-separated list if formula fails
            pass
    
    # Check for comma-separated list of 0-based indices (e.g., '0,2,4' or '0-4')
    if not indices:
        try:
            parts = [p.strip() for p in pattern.split(',')]
            for part in parts:
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    # Range is inclusive
                    for i in range(start, end + 1):
                        if 0 <= i < max_index:
                            indices.add(i)
                else:
                    index = int(part)
                    if 0 <= index < max_index:
                        indices.add(index)
        except Exception:
            # If all parsing fails, return empty list
            return []
            
    return sorted(list(indices))

def save_outputs(jsons: List[str], output_path: str) -> str:
    """Saves a list of JSON strings to a file or multiple files."""
    if '%d' in output_path:
        # Save numerically
        directory = os.path.dirname(output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        for i, json_str in enumerate(jsons):
            file_path = output_path.replace('%d', str(i + 1))
            with open(file_path, 'w') as f:
                f.write(json_str)
        return f"Successfully saved {len(jsons)} JSONs numerically to {os.path.dirname(output_path)}."
    else:
        # Save all to a single file
        directory = os.path.dirname(output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(output_path, 'w') as f:
            for i, json_str in enumerate(jsons):
                f.write(f"--- JSON {i+1} ---\n")
                f.write(json_str)
                f.write("\n\n")
        return f"Successfully saved {len(jsons)} JSONs to {output_path}."

# --- GUI Implementation ---

class VeoJsonGeneratorGUI:
    
    def __init__(self, master, initial_args: argparse.Namespace):
        self.master = master
        master.title("Veo 3.1 JSON Prompt Generator")
        
        self.inputs = {
            "title": "", "style": [], "description": [], "timestamp": "00:00-00:05",
            "shot_type": "medium shot", "sound": [], "camera_movement": [],
            "camera_angle": [], "scene_environment": [], "scene_props": [],
            "char_pose": [], "char_expression": [], "char_action": []
        }
        self.generated_jsons = []
        self.input_widgets = {}
        
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Tab 1: Inputs
        self.input_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.input_frame, text="Inputs")
        self.create_input_tab()
        
        # Tab 2: Outputs
        self.output_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.output_frame, text="Outputs")
        self.create_output_tab()
        
        # Load initial arguments
        self.load_initial_args(initial_args)

    def load_initial_args(self, args: argparse.Namespace):
        """Load arguments passed via CLI into the GUI."""
        if args.title:
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, args.title)
            self.inputs["title"] = args.title
            
        if args.style:
            self.add_input("style", args.style)
            
        if args.description:
            self.add_input("description", args.description)
            
        if args.timestamp:
            self.timestamp_entry.delete(0, tk.END)
            self.timestamp_entry.insert(0, args.timestamp)
            self.inputs["timestamp"] = args.timestamp
            
        if args.shot_type:
            self.shot_type_entry.delete(0, tk.END)
            self.shot_type_entry.insert(0, args.shot_type)
            self.inputs["shot_type"] = args.shot_type
            
        if args.sound:
            self.add_input("sound", args.sound)
            
        if args.camera_movement:
            self.add_input("camera_movement", args.camera_movement)
            
        if args.camera_angle:
            self.add_input("camera_angle", args.camera_angle)
            
        if args.scene_environment:
            self.add_input("scene_environment", args.scene_environment)
            
        if args.scene_props:
            self.add_input("scene_props", args.scene_props)
            
        if args.char_pose:
            self.add_input("char_pose", args.char_pose)
            
        if args.char_expression:
            self.add_input("char_expression", args.char_expression)
            
        if args.char_action:
            self.add_input("char_action", args.char_action)
            
        if args.pattern and args.pattern != "all":
            self.pattern_entry.delete(0, tk.END)
            self.pattern_entry.insert(0, args.pattern)

    def create_input_tab(self):
        """Create the input tab layout."""
        
        # Scrollable frame for inputs
        canvas = tk.Canvas(self.input_frame)
        scrollbar = ttk.Scrollbar(self.input_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        row = 0
        
        # --- Core Inputs ---
        ttk.Label(self.scrollable_frame, text="--- Core Inputs ---").grid(row=row, column=0, columnspan=2, pady=5, sticky="w")
        row += 1
        
        ttk.Label(self.scrollable_frame, text="Title:").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.title_entry = ttk.Entry(self.scrollable_frame, width=50)
        self.title_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        self.title_entry.bind("<KeyRelease>", lambda e: self.update_single_input("title", self.title_entry.get()))
        row += 1
        
        self.create_multi_input_field("Style (s):", "style", row)
        row += 2
        
        # --- Scene Inputs ---
        ttk.Label(self.scrollable_frame, text="--- Scene Inputs ---").grid(row=row, column=0, columnspan=2, pady=5, sticky="w")
        row += 1
        
        self.create_multi_input_field("Description (d):", "description", row)
        row += 2
        
        ttk.Label(self.scrollable_frame, text="Timestamp:").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.timestamp_entry = ttk.Entry(self.scrollable_frame, width=50)
        self.timestamp_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        self.timestamp_entry.insert(0, "00:00-00:05")
        self.timestamp_entry.bind("<KeyRelease>", lambda e: self.update_single_input("timestamp", self.timestamp_entry.get()))
        self.inputs["timestamp"] = "00:00-00:05"
        row += 1
        
        ttk.Label(self.scrollable_frame, text="Shot Type:").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.shot_type_entry = ttk.Entry(self.scrollable_frame, width=50)
        self.shot_type_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        self.shot_type_entry.insert(0, "medium shot")
        self.shot_type_entry.bind("<KeyRelease>", lambda e: self.update_single_input("shot_type", self.shot_type_entry.get()))
        self.inputs["shot_type"] = "medium shot"
        row += 1
        
        self.create_multi_input_field("Sound (o):", "sound", row)
        row += 2
        
        # --- Camera Inputs ---
        ttk.Label(self.scrollable_frame, text="--- Camera Inputs ---").grid(row=row, column=0, columnspan=2, pady=5, sticky="w")
        row += 1
        
        self.create_multi_input_field("Movement (m):", "camera_movement", row)
        row += 2
        
        self.create_multi_input_field("Angle (g):", "camera_angle", row)
        row += 2
        
        # --- Environment Inputs ---
        ttk.Label(self.scrollable_frame, text="--- Environment Inputs ---").grid(row=row, column=0, columnspan=2, pady=5, sticky="w")
        row += 1
        
        self.create_multi_input_field("Environment (e):", "scene_environment", row)
        row += 2
        
        self.create_multi_input_field("Props (p):", "scene_props", row)
        row += 2
        
        # --- Character Inputs ---
        ttk.Label(self.scrollable_frame, text="--- Character Inputs ---").grid(row=row, column=0, columnspan=2, pady=5, sticky="w")
        row += 1
        
        self.create_multi_input_field("Pose (z):", "char_pose", row)
        row += 2
        
        self.create_multi_input_field("Expression (x):", "char_expression", row)
        row += 2
        
        self.create_multi_input_field("Action (a):", "char_action", row)
        row += 2
        
        # --- Pattern and Output Controls ---
        control_frame = ttk.Frame(self.scrollable_frame)
        control_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        
        ttk.Label(control_frame, text="Pattern (e.g., 'all', '2*n', 'd x a x e'):").pack(side=tk.LEFT, padx=5)
        self.pattern_entry = ttk.Entry(control_frame, width=20)
        self.pattern_entry.insert(0, "all")
        self.pattern_entry.pack(side=tk.LEFT, padx=5)
        
        row += 1
        
        # --- Buttons ---
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.grid(row=row, column=0, columnspan=2, padx=5, pady=10)
        
        ttk.Button(button_frame, text="Generate", command=self.generate_outputs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Import", command=self.import_inputs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export", command=self.export_inputs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save All", command=self.save_all_outputs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Numerically", command=self.save_numerically).pack(side=tk.LEFT, padx=5)

    def create_output_tab(self):
        """Create the output tab."""
        # Top frame for controls
        control_frame = ttk.Frame(self.output_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Show All Generated", command=self.show_all_outputs).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Show Filtered (using pattern from Input tab)", command=self.show_filtered_outputs).pack(side=tk.LEFT, padx=5)
        
        # Output display
        self.output_text = scrolledtext.ScrolledText(self.output_frame, wrap=tk.WORD, height=30, width=100)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_multi_input_field(self, label_text, field_name, row):
        """Helper to create a multi-variant input field (text entry, add button, display)."""
        
        parent = self.scrollable_frame
        
        ttk.Label(parent, text=label_text).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        
        field_frame = ttk.Frame(parent)
        field_frame.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        
        text_entry = ttk.Entry(field_frame, width=40)
        text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def add_input():
            text = text_entry.get().strip()
            if text:
                self.add_input(field_name, text)
                text_entry.delete(0, tk.END)
        
        def load_file():
            file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
            if file_path:
                self.add_input(field_name, file_path)
        
        ttk.Button(field_frame, text="Add", command=add_input).pack(side=tk.LEFT, padx=2)
        ttk.Button(field_frame, text="Load File", command=load_file).pack(side=tk.LEFT, padx=2)
        
        # Display area for added inputs
        display_frame = ttk.Frame(parent)
        display_frame.grid(row=row + 1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        self.input_widgets[field_name] = {
            "text_entry": text_entry,
            "display_frame": display_frame,
            "items": []
        }
        
        # Ensure the display frame expands to fill the column
        parent.grid_columnconfigure(1, weight=1)
        display_frame.grid_columnconfigure(0, weight=1)

    def update_single_input(self, field_name, value):
        """Update a single-value input field."""
        self.inputs[field_name] = value

    def add_input(self, field_name, item):
        """Add an input item."""
        if item not in self.inputs[field_name]:
            self.inputs[field_name].append(item)
            self.update_input_display(field_name)

    def remove_input(self, field_name, item):
        """Remove an input item."""
        if item in self.inputs[field_name]:
            self.inputs[field_name].remove(item)
            self.update_input_display(field_name) # Re-draw the list to fix gaps

    def update_input_display(self, field_name):
        """Update the display of added inputs."""
        # Clear the display frame
        for widget in self.input_widgets[field_name]["display_frame"].winfo_children():
            widget.destroy()
        
        # Add items
        for item in self.inputs[field_name]:
            item_frame = ttk.Frame(self.input_widgets[field_name]["display_frame"])
            item_frame.pack(fill=tk.X, padx=2, pady=2)
            
            # Use a Label to display the item text, allowing wrapping
            label = ttk.Label(item_frame, text=item, relief=tk.SUNKEN, wraplength=400) # Added wraplength
            label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Use a lambda function with a default argument to capture the current item value
            ttk.Button(item_frame, text="Remove", command=lambda i=item: self.remove_input(field_name, i)).pack(side=tk.LEFT, padx=2)

    def clear_all(self):
        """Clear all inputs."""
        self.title_entry.delete(0, tk.END)
        self.timestamp_entry.delete(0, tk.END)
        self.shot_type_entry.delete(0, tk.END)
        self.pattern_entry.delete(0, tk.END)
        self.pattern_entry.insert(0, "all")
        
        self.inputs = {
            "title": "", "style": [], "description": [], "timestamp": "00:00-00:05",
            "shot_type": "medium shot", "sound": [], "camera_movement": [],
            "camera_angle": [], "scene_environment": [], "scene_props": [],
            "char_pose": [], "char_expression": [], "char_action": []
        }
        
        for field_name in self.input_widgets.keys():
            self.update_input_display(field_name)
            
        self.generated_jsons = []
        self.output_text.delete(1.0, tk.END)

    def generate_outputs(self):
        """Generate the JSON outputs."""
        try:
            # Validate inputs
            # Only Title and Style are strictly required for the generator to initialize
            required_fields = ["title", "style"]
            for field in required_fields:
                if not self.inputs[field] or (isinstance(self.inputs[field], str) and not self.inputs[field].strip()):
                    messagebox.showerror("Error", f"Field '{field.replace('_', ' ').title()}' is required.")
                    return
            
            # All other fields are optional and will default to a single variant if empty
            # to ensure the Cartesian product can be calculated.
            
            # Create generator
            generator = VeoJsonGenerator(
                title=self.inputs["title"],
                style=self.inputs["style"]
            )
            
            # Prepare nested dictionaries
            camera_dict = {
                "movement": self.inputs["camera_movement"] or ["dynamic orbit"],
                "angle": self.inputs["camera_angle"] or ["low angle"]
            }
            scene_dict = {
                "environment": self.inputs["scene_environment"] or ["a forest"],
                "props": self.inputs["scene_props"] or ["a single spotlight, ancient runes"]
            }
            character_dict = {
                "pose": self.inputs["char_pose"] or ["mid-action"],
                "expression": self.inputs["char_expression"] or ["intense focus"],
                "action": self.inputs["char_action"] or ["running"]
            }
            
            # Add scene
            generator.add_single_scene(
                description=self.inputs["description"] or ["a scene"],
                camera=camera_dict,
                scene=scene_dict,
                character=character_dict,
                timestamp=self.inputs["timestamp"],
                shot_type=self.inputs["shot_type"],
                sound=self.inputs["sound"] or ["upbeat electronic music"]
            )
            
            # Generate
            # Always generate the full Cartesian product first (default behavior)
            self.generated_jsons = generator.generate_json()
            
            messagebox.showinfo("Success", f"Generated {len(self.generated_jsons)} JSON prompts (Full Cartesian Product).")
            self.notebook.select(self.output_frame)
            self.show_filtered_outputs() # Show the filtered output based on the pattern on the input tab
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate outputs: {e}")

    def regenerate_with_pattern(self, pattern: str) -> List[str]:
        """Helper to regenerate JSONs using the current inputs and a specific pattern."""
        # Create generator
        generator = VeoJsonGenerator(
            title=self.inputs["title"],
            style=self.inputs["style"]
        )
        
        # Prepare nested dictionaries
        camera_dict = {
            "movement": self.inputs["camera_movement"] or ["dynamic orbit"],
            "angle": self.inputs["camera_angle"] or ["low angle"]
        }
        scene_dict = {
            "environment": self.inputs["scene_environment"] or ["a forest"],
            "props": self.inputs["scene_props"] or ["a single spotlight, ancient runes"]
        }
        character_dict = {
            "pose": self.inputs["char_pose"] or ["mid-action"],
            "expression": self.inputs["char_expression"] or ["intense focus"],
            "action": self.inputs["char_action"] or ["running"]
        }
        
        # Add scene
        generator.add_single_scene(
            description=self.inputs["description"] or ["a scene"],
            camera=camera_dict,
            scene=scene_dict,
            character=character_dict,
            timestamp=self.inputs["timestamp"],
            shot_type=self.inputs["shot_type"],
            sound=self.inputs["sound"] or ["upbeat electronic music"]
        )
        
        # Generate with pattern
        return generator.generate_json(pattern=pattern)

    def show_all_outputs(self):
        """Show all generated outputs."""
        if not self.generated_jsons:
            messagebox.showerror("Error", "No JSONs generated yet. Click 'Generate' first.")
            return
            
        self.output_text.delete(1.0, tk.END)
        for i, json_str in enumerate(self.generated_jsons):
            self.output_text.insert(tk.END, f"--- JSON {i+1} ---\n")
            self.output_text.insert(tk.END, json_str)
            self.output_text.insert(tk.END, "\n\n")

    def show_filtered_outputs(self):
        """Show filtered outputs based on the pattern."""
        if not self.generated_jsons:
            messagebox.showerror("Error", "No JSONs generated yet. Click 'Generate' first.")
            return
            
        pattern = self.pattern_entry.get()
        
        # Check if it's an advanced pattern
        if 'x' in pattern.lower() or '*' in pattern.lower() or any(c in pattern.lower() for c in 'sdeap'):
            # Regenerate with the advanced pattern
            try:
                # The advanced pattern should be used to *generate* the output, not filter the existing one.
                # We need to re-run the generation logic with the pattern.
                filtered_jsons = self.regenerate_with_pattern(pattern)
                
                self.output_text.delete(1.0, tk.END)
                for i, json_str in enumerate(filtered_jsons):
                    self.output_text.insert(tk.END, f"--- JSON {i+1} ---\n")
                    self.output_text.insert(tk.END, json_str)
                    self.output_text.insert(tk.END, "\n\n")
                
                messagebox.showinfo("Success", f"Generated {len(filtered_jsons)} JSONs using Advanced Pattern '{pattern}'.")
                return
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate with advanced pattern: {e}")
                return
        
        # Standard numerical filtering
        indices = parse_index_pattern(pattern, len(self.generated_jsons))
        
        self.output_text.delete(1.0, tk.END)
        for idx in indices:
            self.output_text.insert(tk.END, f"--- JSON {idx+1} ---\n")
            self.output_text.insert(tk.END, self.generated_jsons[idx])
            self.output_text.insert(tk.END, "\n\n")

    def save_all_outputs(self):
        """Save all outputs to a single file."""
        if not self.generated_jsons:
            messagebox.showerror("Error", "No JSONs generated yet. Click 'Generate' first.")
            return
            
        # Use the currently filtered/generated set of JSONs
        pattern = self.pattern_entry.get()
        if 'x' in pattern.lower() or '*' in pattern.lower() or any(c in pattern.lower() for c in 'sdeap'):
            # Regenerate with the advanced pattern to get the correct set
            jsons_to_save = self.regenerate_with_pattern(pattern)
        else:
            # Filter the full set
            indices = parse_index_pattern(pattern, len(self.generated_jsons))
            jsons_to_save = [self.generated_jsons[i] for i in indices]
            
        if not jsons_to_save:
            messagebox.showerror("Error", "No JSONs to save. Check your pattern.")
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            message = save_outputs(jsons_to_save, file_path)
            messagebox.showinfo("Success", message)

    def save_numerically(self):
        """Save outputs to separate files with numerical naming."""
        if not self.generated_jsons:
            messagebox.showerror("Error", "No JSONs generated yet. Click 'Generate' first.")
            return
            
        # Use the currently filtered/generated set of JSONs
        pattern = self.pattern_entry.get()
        if 'x' in pattern.lower() or '*' in pattern.lower() or any(c in pattern.lower() for c in 'sdeap'):
            # Regenerate with the advanced pattern to get the correct set
            jsons_to_save = self.regenerate_with_pattern(pattern)
        else:
            # Filter the full set
            indices = parse_index_pattern(pattern, len(self.generated_jsons))
            jsons_to_save = [self.generated_jsons[i] for i in indices]
            
        if not jsons_to_save:
            messagebox.showerror("Error", "No JSONs to save. Check your pattern.")
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            # Replace the filename with a pattern
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            # Remove extension and add %d pattern
            filename_without_ext = os.path.splitext(filename)[0]
            pattern_path = os.path.join(directory, f"{filename_without_ext}_%d.json")
            
            message = save_outputs(jsons_to_save, pattern_path)
            messagebox.showinfo("Success", message)

    def export_inputs(self):
        """Export all current inputs to a JSON file."""
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            try:
                # Include pattern in the export
                export_data = self.inputs.copy()
                export_data['pattern'] = self.pattern_entry.get()
                
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=4)
                messagebox.showinfo("Success", f"Inputs successfully exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export inputs: {e}")

    def import_inputs(self):
        """Import inputs from a JSON file."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    import_data = json.load(f)
                
                self.clear_all()
                
                # Load single-value inputs
                self.title_entry.insert(0, import_data.get("title", ""))
                self.inputs["title"] = import_data.get("title", "")
                self.timestamp_entry.delete(0, tk.END)
                self.timestamp_entry.insert(0, import_data.get("timestamp", "00:00-00:05"))
                self.inputs["timestamp"] = import_data.get("timestamp", "00:00-00:05")
                self.shot_type_entry.delete(0, tk.END)
                self.shot_type_entry.insert(0, import_data.get("shot_type", "medium shot"))
                self.inputs["shot_type"] = import_data.get("shot_type", "medium shot")
                
                # Load multi-value inputs
                for field in ["style", "description", "sound", "camera_movement", "camera_angle", 
                             "scene_environment", "scene_props", "char_pose", "char_expression", "char_action"]:
                    for item in import_data.get(field, []):
                        self.add_input(field, item)
                        
                # Load pattern
                self.pattern_entry.delete(0, tk.END)
                self.pattern_entry.insert(0, import_data.get("pattern", "all"))
                
                messagebox.showinfo("Success", f"Inputs successfully imported from {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import inputs: {e}")

# --- CLI Entry Point ---

def parse_args():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="Veo 3.1 Expressive JSON Prompt Generator.")
    
    # Core arguments
    parser.add_argument('--title', type=str, help="The title of the video.")
    parser.add_argument('--style', type=str, help="The style/genre of the video.")
    
    # Scene arguments (can be single string or file path)
    parser.add_argument('--description', type=str, help="The main scene description.")
    parser.add_argument('--timestamp', type=str, default="00:00-00:05", help="The timestamp for the cut.")
    parser.add_argument('--shot-type', type=str, default="medium shot", help="The shot type for the cut.")
    parser.add_argument('--sound', type=str, help="The sound/music for the cut.")
    
    # Nested arguments (can be single string or file path)
    parser.add_argument('--camera-movement', type=str, help="Camera movement (e.g., 'dynamic orbit').")
    parser.add_argument('--camera-angle', type=str, help="Camera angle (e.g., 'low angle').")
    parser.add_argument('--scene-environment', type=str, help="Scene environment (e.g., 'a forest').")
    parser.add_argument('--scene-props', type=str, help="Scene props (e.g., 'a single spotlight, ancient runes').")
    parser.add_argument('--char-pose', type=str, help="Character pose (e.g., 'mid-action').")
    parser.add_argument('--char-expression', type=str, help="Character expression (e.g., 'intense focus').")
    parser.add_argument('--char-action', type=str, help="Character action (e.g., 'running').")
    
    # Output options
    parser.add_argument('--pattern', type=str, default="all", help="Filter pattern (e.g., '2*n', '0,2,4', 'all') or Advanced Pattern (e.g., 'd x a x e').")
    parser.add_argument('--output', type=str, help="Output file path. Use '%%d' for numerical saving (e.g., 'output_%%d.json').")
    
    # GUI option
    parser.add_argument('--gui', action='store_true', help="Launch the graphical user interface.")
    
    args = parser.parse_args()
    
    # Check if any arguments were provided (excluding --gui)
    if not any(getattr(args, arg) for arg in vars(args) if arg not in ['gui', 'output', 'pattern', 'timestamp', 'shot_type']) and not args.gui:
        # If no core arguments, launch GUI
        args.gui = True
        
    return args

def cli_main(args: argparse.Namespace):
    """Main function for CLI mode."""
    
    if not args.title or not args.style:
        print("Error: --title and --style are required in CLI mode.", file=sys.stderr)
        sys.exit(1)
        
    try:
        # Create generator
        generator = VeoJsonGenerator(
            title=args.title,
            style=args.style
        )
        
        # Prepare nested dictionaries
        camera_dict = {
            "movement": args.camera_movement,
            "angle": args.camera_angle
        }
        scene_dict = {
            "environment": args.scene_environment,
            "props": args.scene_props
        }
        character_dict = {
            "pose": args.char_pose,
            "expression": args.char_expression,
            "action": args.char_action
        }
        
        # Add scene
        generator.add_single_scene(
            description=args.description,
            camera=camera_dict,
            scene=scene_dict,
            character=character_dict,
            timestamp=args.timestamp,
            shot_type=args.shot_type,
            sound=args.sound
        )
        
        # Generate all JSONs
        all_jsons = generator.generate_json(pattern=args.pattern)
        total_count = len(all_jsons)
        
        # If the pattern is an advanced pattern, all_jsons is already the filtered set
        if 'x' in args.pattern.lower() or '*' in args.pattern.lower() or any(c in args.pattern.lower() for c in 'sdeap'):
            filtered_jsons = all_jsons
            print(f"Generated {total_count} JSONs using Advanced Pattern '{args.pattern}'.")
        else:
            # Filter JSONs based on numerical pattern
            indices_to_keep = parse_index_pattern(args.pattern, total_count)
            filtered_jsons = [all_jsons[i] for i in indices_to_keep]
            
            print(f"Generated {total_count} total JSONs. Filtered to {len(filtered_jsons)} using pattern '{args.pattern}'.")

        if not filtered_jsons:
            print("No JSONs generated or filtered. Check your inputs and pattern.", file=sys.stderr)
            sys.exit(1)
            
        if args.output:
            save_outputs(filtered_jsons, args.output)
        else:
            # Output to stdout
            for i, json_str in enumerate(filtered_jsons):
                print(f"--- JSON {i+1} ---\n{json_str}\n")
                
    except Exception as e:
        print(f"An error occurred in CLI mode: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    args = parse_args()
    
    if args.gui:
        root = tk.Tk()
        app = VeoJsonGeneratorGUI(root, args)
        root.mainloop()
    else:
        cli_main(args)

if __name__ == "__main__":
    main()
