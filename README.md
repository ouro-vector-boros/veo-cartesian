# Veo 3.1 Expressive JSON Prompt Generator (Cartesian Product Edition)

This Python script provides a class, `VeoJsonGenerator`, designed to create structured JSON prompts compatible with Google Veo 3.1. It is specifically engineered to generate **multiple JSON prompts** based on the **Cartesian product** of all input variants, allowing for efficient A/B testing of expressive templates.

## Features

*   **Cartesian Product Generation:** If any input field is provided as a collection (set/list) or a `.txt` file, the generator creates a unique JSON for every combination of those variants.
*   **Flexible Input Handling:**
    *   **Single Strings:** Used directly as the prompt value.
    *   **Sets/Lists of Strings:** Each element is treated as a variant.
    *   **`.txt` Filenames:** The file content is read, split by newlines, and each non-empty line is treated as a variant for the Cartesian product.

## `veo_json_generator.py`

The core logic is contained within the `VeoJsonGenerator` class. The `generate_json()` method returns a `List[str]`, where each string is a complete, unique JSON prompt.

## Final Example: The Cryptid Dancer

This example demonstrates the power of the Cartesian product using the provided `.txt` files.

### Input Files

| File | Content (Variants) | Used For |
| :--- | :--- | :--- |
| `characters.txt` | 2 variants (oni nephilim, ethereal cryptid) | `description` |
| `actions.txt` | 2 variants (breakdancing, capoeira) | `character.action` |
| `scenes.txt` | 2 variants (mossy clearing, quartz temple) | `scene.environment` |

**Total JSONs Generated:** $2 \times 2 \times 2 = 8$

### Invocation

The following code was used to generate the 8 unique JSON prompts:

```python
from veo_json_generator import VeoJsonGenerator

# Inputs are specified as filenames, which the generator automatically expands
character_file = "characters.txt"
action_file = "actions.txt"
scene_file = "scenes.txt"

generator_final = VeoJsonGenerator(
    title="The Cryptid Dancer",
    style="Cinematic, High-Detail, 8K" # Single string style
)

# The description, character.action, and scene.environment fields will be expanded
generator_final.add_single_scene(
    description=character_file, # Expanded from characters.txt
    camera={
        "movement": "dynamic orbit",
        "angle": "low angle"
    },
    scene={
        "environment": scene_file, # Expanded from scenes.txt
        "props": "a single spotlight, ancient runes"
    },
    character={
        "pose": "mid-action",
        "expression": "intense focus",
        "action": action_file # Expanded from actions.txt
    },
    timestamp="00:00-00:05",
    shot_type="full body shot",
    sound="upbeat electronic music"
)

generated_jsons = generator_final.generate_json()
# generated_jsons will contain 8 unique JSON strings
```

### Sample Output (JSON 1 of 8)

This is the first JSON from the generated `outputs.txt` file:

```json
{
    "title": "The Cryptid Dancer",
    "style": "Cinematic, High-Detail, 8K",
    "cuts": [
        {
            "timestamp": "00:00-00:05",
            "shot_type": "full body shot",
            "description": "Fantastic grotesque oni nephilim in sunglasses and trenchcoat",
            "sound": "upbeat electronic music",
            "camera": {
                "movement": "dynamic orbit",
                "angle": "low angle"
            },
            "scene": {
                "environment": "moonlit mossy clearing",
                "props": "a single spotlight, ancient runes"
            },
            "character": {
                "pose": "mid-action",
                "expression": "intense focus",
                "action": "breakdancing"
            }
        }
    ]
}
```
