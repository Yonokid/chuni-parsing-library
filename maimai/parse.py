import json
import os
import sys

from title import parse_title


def ensure_directory(path: str) -> None:
    """Ensures that the given directory exists."""
    if not os.path.isdir(path):
        os.makedirs(path)

def combine_unique_keys(list1, list2, unique_key):
    combined_dict = {}
    for d in list1 + list2:
        combined_dict[d[unique_key]] = d
    return list(combined_dict.values())

def process_data(directory: str, alt_dir, output_dir: str, data_type: str, parse_func, copy_func, related_dir_name: str) -> None:
    """
    Processes data (music, chara, movie) from the given directory.

    Args:
        directory: The input directory.
        output_dir: The base output directory.
        data_type: The type of data ("music", "chara", "movie").
        parse_func: The function to parse the XML file.
        copy_func: The function to copy related files.
        related_dir_name: The name of the related directory/file.
        id_extraction_func: Function to extract the id used for related files, if needed.
    """
    data_dir = os.path.join(directory, data_type)
    if not os.path.exists(data_dir):
        print(f"Directory {data_type} does not exist, skipping")
        return
    data_output_dir = os.path.join(output_dir, data_type)
    ensure_directory(data_output_dir)

    json_file_path = os.path.join(data_output_dir, f"{data_type}.json")
    existing_data = []

    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading existing {data_type}.json: {e}. Starting with an empty list.")
            existing_data = []

    new_data = []
    for item in os.scandir(data_dir):
        if not item.is_dir():
            continue
        xml_path = os.path.join(data_dir, item.name, f"{data_type.capitalize()}.xml")
        try:
            parsed_data = parse_func(xml_path)
            new_data.append(parsed_data)
            id = parsed_data["id"]

        except (FileNotFoundError, IOError, ValueError) as e:
            print(f"Error processing {data_type} {item.name}: {e}")

    combined_data = combine_unique_keys(existing_data, new_data, "id")

    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=4, ensure_ascii=False)

def parse_AXXX_directory(directory: str, output_dir: str, alt_dir=None) -> None:
    """Parses AXXX directory, processing music, chara, and movie data."""
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return

    process_data(directory, alt_dir, output_dir, "title", parse_title, None, "title")

def process_directory(directory: str, output_dir: str) -> None:
    if directory.split('\\')[-1] == "Option":
        for folder in os.listdir(directory):
            parse_AXXX_directory(os.path.join(directory, folder), output_dir, os.path.join('\\'.join(directory.split('\\')[:-1]), "App", "data", "A000"))
    else:
        parse_AXXX_directory(directory, output_dir)

if __name__ == "__main__":
    directory = sys.argv[1]
    output_directory = sys.argv[2]
    process_directory(directory, output_directory)
