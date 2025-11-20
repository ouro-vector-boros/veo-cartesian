# Veo 3.1 Expressive JSON Prompt Generator (Cartesian Product Edition)

This is the revised version of the `VeoJsonGenerator` class, updated to support the generation of **multiple JSON prompts** based on the **Cartesian product** of all set/list inputs. This allows for rapid A/B testing and exploration of the prompt space by combining every possible variant of your expressive inputs.

## Features

*   **Cartesian Product Generation:** If any input field (e.g., `style`, `description`, `character.pose`) is provided as a `set` or `list`, the generator will create a unique JSON for every combination of those variants.
*   **Structured Output:** Generates a list of multi-scene JSON strings, each one a complete, valid Veo 3.1 prompt.
*   **Input Flexibility:** Supports single strings, content from `.txt` files, and collections (`set`/`list`) for expansion.

## `veo_json_generator.py` - Key Changes

The `generate_json()` method now returns a `List[str]`, where each string is a complete JSON prompt.

## Example Invocation (User-Specified Sets)

This example demonstrates how a small number of variants can lead to a large number of generated JSONs.

**Input Variants:**
*   **Style:** 2 variants
*   **Description:** 2 variants
*   **Scene.environment:** 2 variants
*   **Character.pose:** 2 variants

**Total JSONs Generated:** 2 (Style) * 2 (Desc) * 2 (Env) * 2 (Pose) = **16 JSONs**

```python
from veo_json_generator import VeoJsonGenerator

# User-specified sets
genre_set = {'hauntingly beautiful, fantastic grotesque, eerie', 'kawaii horror, playful and whimsically dark'}
    
# Character set
character_set = {
    "pose": {'floating', 'cross-legged'},
    "expression": "serene",
    "action": "whispering a lullaby"
}
    
# Scene set
scene_set = {
    "environment": {'abandoned amusement park', 'under a blood moon'},
    "props": "a single, glowing carousel horse"
}

generator_user = VeoJsonGenerator(
    title="The Grotesque Lullaby",
    style=genre_set
)
    
description_set = {'a child-like figure', 'surrounded by overgrown vines'}
camera_dict = {
    "movement": "slow 360 degree orbit",
    "angle": "high angle"
}

generator_user.add_single_scene(
    description=description_set,
    camera=camera_dict,
    scene=scene_set,
    character=character_set,
    timestamp="00:00-00:07",
    shot_type="wide shot",
    sound="eerie music box melody"
)

generated_jsons = generator_user.generate_json()
# generated_jsons will contain 16 unique JSON strings
```

## Sample Output (JSON 1 of 16)

```json
{
    "title": "The Grotesque Lullaby",
    "style": "kawaii horror, playful and whimsically dark",
    "cuts": [
        {
            "timestamp": "00:00-00:07",
            "shot_type": "wide shot",
            "description": "a child-like figure",
            "sound": "eerie music box melody",
            "camera": {
                "movement": "slow 360 degree orbit",
                "angle": "high angle"
            },
            "scene": {
                "environment": "abandoned amusement park",
                "props": "a single, glowing carousel horse"
            },
            "character": {
                "pose": "floating",
                "expression": "serene",
                "action": "whispering a lullaby"
            }
        }
    ]
}
```

## Sample Output (JSON 16 of 16)

```json
{
    "title": "The Grotesque Lullaby",
    "style": "hauntingly beautiful, fantastic grotesque, eerie",
    "cuts": [
        {
            "timestamp": "00:00-00:07",
            "shot_type": "wide shot",
            "description": "surrounded by overgrown vines",
            "sound": "eerie music box melody",
            "camera": {
                "movement": "slow 360 degree orbit",
                "angle": "high angle"
            },
            "scene": {
                "environment": "abandoned amusement park",
                "props": "a single, glowing carousel horse"
            },
            "character": {
                "pose": "cross-legged",
                "expression": "serene",
                "action": "whispering a lullaby"
            }
        }
    ]
}
```
