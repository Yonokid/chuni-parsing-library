import xml.etree.ElementTree as ET


def safe_find(path: ET.Element, element: str, message: str="Element not found") -> ET.Element:
    found_element = path.find(element)
    if found_element is None:
        raise ValueError(message)
    return found_element

def line_break(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace(r"\n", "\n")

def get_text_element(element: ET.Element, tag: str):
    text_element = safe_find(element, tag).text
    return line_break(text_element)
