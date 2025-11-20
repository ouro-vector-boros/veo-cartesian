import json
from typing import List, Dict, Any, Union, Set, Tuple
from itertools import product

class VeoJsonGenerator:
    """
    A class to generate structured JSON prompts for Veo 3.1, supporting
    expressive templates from various input types, and generating multiple
    prompts based on the Cartesian product of all set/list/file inputs.
    """

    def __init__(self, title: str, style: Union[str, Set, List]):
        """
        Initializes the generator with mandatory fields.
        """
        self.title = title
        # Style is the first input to be expanded into a list of possibilities
        self.style_variants = self._expand_input(style)
        self.cuts_variants = []

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
                file_content_list = self._load_text_file(input_data)
                # If the result is an error message, treat the original string as a literal
                if file_content_list and file_content_list[0].startswith("ERROR:"):
                    return [input_data]
                return file_content_list
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
                         sound: Union[str, Set, List] = ""):
        """
        Adds a single scene (cut) to the video. This cut will be expanded
        into multiple variants based on the Cartesian product of its inputs.
        """
        
        # 1. Expand all inputs into lists of variants
        desc_variants = self._expand_input(description)
        sound_variants = self._expand_input(sound)
        
        camera_expanded = self._expand_dict_inputs(camera)
        scene_expanded = self._expand_dict_inputs(scene)
        character_expanded = self._expand_dict_inputs(character)

        # 2. Get the keys and lists of variants for the Cartesian product
        all_keys = ['description', 'sound']
        all_variants = [desc_variants, sound_variants]
        
        # Add nested dictionary keys and variants
        for key, variants in camera_expanded.items():
            all_keys.append(f"camera.{key}")
            all_variants.append(variants)
        
        for key, variants in scene_expanded.items():
            all_keys.append(f"scene.{key}")
            all_variants.append(variants)

        for key, variants in character_expanded.items():
            all_keys.append(f"character.{key}")
            all_variants.append(variants)

        # 3. Calculate the Cartesian product of all variants
        cut_variants = []
        for variant_tuple in product(*all_variants):
            cut = {
                "timestamp": timestamp,
                "shot_type": shot_type,
            }
            
            # 4. Reconstruct the cut dictionary for each variant
            variant_map = dict(zip(all_keys, variant_tuple))
            
            cut["description"] = variant_map.pop('description')
            cut["sound"] = variant_map.pop('sound')
            
            cut["camera"] = {}
            cut["scene"] = {}
            cut["character"] = {}
            
            for key, value in variant_map.items():
                if key.startswith('camera.'):
                    cut["camera"][key.split('.')[1]] = value
                elif key.startswith('scene.'):
                    cut["scene"][key.split('.')[1]] = value
                elif key.startswith('character.'):
                    cut["character"][key.split('.')[1]] = value
            
            # Remove sound if it's an empty string (from default value)
            if "sound" in cut and not cut["sound"]:
                del cut["sound"]

            cut_variants.append(cut)
            
        self.cuts_variants.append(cut_variants)

    def generate_json(self) -> List[str]:
        """
        Generates the final list of Veo 3.1 compatible JSON strings,
        based on the Cartesian product of all scene cuts and the style variants.
        """
        
        # 1. Combine all cut variants into a list of full video cut sequences
        # This is the Cartesian product of all cut_variants lists
        all_cut_sequences = list(product(*self.cuts_variants))
        
        final_json_list = []
        
        # 2. Cartesian product of style variants and cut sequences
        for style_variant, cut_sequence in product(self.style_variants, all_cut_sequences):
            final_json = {
                "title": self.title,
                "style": style_variant,
                "cuts": cut_sequence
            }
            final_json_list.append(json.dumps(final_json, indent=4))
            
        return final_json_list

# --- Example Usage (Commented out to be replaced by user's final request) ---
# def create_example_files():
#     pass
# def run_examples():
#     pass
# def run_user_example():
#     pass

# if __name__ == "__main__":
#     pass
