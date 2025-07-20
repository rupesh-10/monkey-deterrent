import os

# Base directories
base_image_dir = "data/images"
base_label_dir = "data/labels"

# Subfolders to handle
splits = ['train', 'val']

for split in splits:
    image_dir = os.path.join(base_image_dir, split)
    label_dir = os.path.join(base_label_dir, split)

    image_files = sorted([f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

    for i, filename in enumerate(image_files, start=1):
        ext = os.path.splitext(filename)[1]
        new_name = f"monkey_{split}_{i:03d}{ext}"
        old_image_path = os.path.join(image_dir, filename)
        new_image_path = os.path.join(image_dir, new_name)

        # Rename image
        os.rename(old_image_path, new_image_path)

        # Rename label
        old_label = os.path.splitext(filename)[0] + ".txt"
        new_label = f"monkey_{split}_{i:03d}.txt"
        old_label_path = os.path.join(label_dir, old_label)
        new_label_path = os.path.join(label_dir, new_label)

        if os.path.exists(old_label_path):
            os.rename(old_label_path, new_label_path)
        else:
            print(f"⚠️ Label missing for: {filename} in {split}")

print("✅ Done renaming all images and labels inside train and val folders.")
