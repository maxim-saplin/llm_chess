import os
import re

# Define the top-level directory
TOP_LEVEL_DIR = "_logs/reflection"

# Regular expression to match the date format in the directory name
date_pattern = re.compile(r"_(\d{2})\.(\d{2})\.(\d{4})_")


def rename_directories(top_level_dir):
    # Iterate through all items in the top-level directory
    for item in os.listdir(top_level_dir):
        item_path = os.path.join(top_level_dir, item)

        # Check if the item is a directory
        if os.path.isdir(item_path):
            # Search for the date pattern in the directory name
            match = date_pattern.search(item)
            if match:
                # Extract day, month, and year from the match
                day, month, year = match.groups()
                # Create the new directory name with the date in 'YYYY-DD-MM' format
                new_name = item.replace(match.group(0), f"{year}-{day}-{month}_")
                new_path = os.path.join(top_level_dir, new_name)

                # Rename the directory
                os.rename(item_path, new_path)
                print(f"Renamed: {item} -> {new_name}")


# Run the function
rename_directories(TOP_LEVEL_DIR)
