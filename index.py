import os
import shutil
import random

# Paths
base_dir = "data"
image_dir = os.path.join(base_dir, "images")
label_dir = os.path.join(base_dir, "labels")
output_base = base_dir  # will create train/val under data/

# Create train/val folders
for split in ["train", "val"]:
    os.makedirs(os.path.join(output_base, "images", split), exist_ok=True)
    os.makedirs(os.path.join(output_base, "labels", split), exist_ok=True)

# All image files
images = [f for f in os.listdir(image_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
random.shuffle(images)

val_split = 0.2
val_count = int(len(images) * val_split)
val_images = set(images[:val_count])

for img_name in images:
    split = "val" if img_name in val_images else "train"

    # File paths
    img_path = os.path.join(image_dir, img_name)
    label_name = os.path.splitext(img_name)[0] + ".txt"
    label_path = os.path.join(label_dir, label_name)

    # Copy image
    dest_img = os.path.join(output_base, "images", split, img_name)
    shutil.copy(img_path, dest_img)

    # Copy label
    if os.path.exists(label_path):
        dest_lbl = os.path.join(output_base, "labels", split, label_name)
        shutil.copy(label_path, dest_lbl)
    else:
        print(f"⚠️ Warning: Label not found for {img_name}")

print("✅ Dataset split complete! YOLO-ready train/val folders created.")
