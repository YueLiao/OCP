from typing import Any, Dict, Iterable, List, Optional


def trail_artifact_links(trails: Optional[Iterable[Any]]) -> List[Dict[str, str]]:
    """Return standard artifact links for generated cryptanalysis trails."""
    links: List[Dict[str, str]] = []
    if not trails:
        return links

    for index, trail in enumerate(trails, start=1):
        json_path = getattr(trail, "json_filename", None)
        if json_path:
            links.append({"label": f"trail_json_{index}", "path": str(json_path)})

        text_path = getattr(trail, "txt_filename", None)
        if text_path:
            links.append({"label": f"trail_text_{index}", "path": str(text_path)})

    return links
