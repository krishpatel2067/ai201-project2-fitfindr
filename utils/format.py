def format_listing_item(new_item: dict) -> str:
    return "\n".join(
        [
            f"Item: {new_item.get('title') or "UNKNOWN"}",
            f"Description: {new_item.get('description') or "NONE"}",
            f"Category: {new_item.get('category') or "UNKNOWN"}",
            f"Style tags: {', '.join(new_item.get('style_tags') or []) or "NONE"}",
            f"Size: {new_item.get('size') or "UNKNOWN"}",
            f"Condition: {new_item.get('condition') or "UNKNOWN"}",
            f"Price: {f"${new_item.get('price'):.2f}" if new_item.get('price') is not None else 'UNKNOWN'}",
            f"Colors: {', '.join(new_item.get('colors') or []) or "UNKNOWN"}",
            f"Brand: {new_item.get('brand') or "UNKNOWN"}",
            f"Platform: {new_item.get('platform') or "UNKNOWN"}",
        ]
    )
