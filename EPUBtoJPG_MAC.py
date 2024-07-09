import os
import zipfile
import shutil
import subprocess
from tkinter import Tk, Frame, Button, Label, filedialog, LEFT, RIGHT, TOP, messagebox, Toplevel
from PIL import Image
from tkinterdnd2 import TkinterDnD, DND_FILES  # Corrected import
import cv2
import numpy as np

# Set output directory
OUTPUT_DIR = r"D:\FFOutput"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global variable to store the imported epub file path
epub_file = None

def clear_epub():
    global epub_file
    epub_file = None
    status_label.config(text="No file imported")

def select_epub():
    global epub_file
    file_path = filedialog.askopenfilename(title="Select an EPUB file", filetypes=[("EPUB files", "*.epub")])
    if file_path:
        clear_epub()
        epub_file = os.path.normpath(file_path)
        status_label.config(text=f"Imported file: {os.path.basename(epub_file)}")

def process_epub():
    global epub_file
    if not epub_file:
        messagebox.showerror("Error", "No file imported")
        return

    try:
        # Change .epub file extension to .zip
        zip_file = os.path.splitext(epub_file)[0] + '.zip'

        # Copy file and rename to .zip
        shutil.copy(epub_file, zip_file)

        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()

            # Define list of image folders to process
            images_folders = ['images/'] + [f'{name}images/' for name in file_list if name.endswith('_files/')]

            for images_folder in images_folders:
                for file_info in zip_ref.infolist():
                    if file_info.filename.startswith(images_folder) and file_info.filename.lower().endswith(('.jpeg', '.jpg', '.png')):
                        process_image(zip_ref, file_info, images_folder)

        # Delete .zip file
        os.remove(zip_file)

        show_completion_dialog()

    except Exception as e:
        messagebox.showerror("Error", f"Error processing EPUB file: {e}")

def process_image(zip_ref, file_info, images_folder):
    # Get filename and remove leading zeros
    original_filename = file_info.filename.replace(images_folder, '')
    new_filename = original_filename.lstrip('0') or '0'
    new_filename = os.path.splitext(new_filename)[0] + '.jpg'
    
    # Construct new file path
    new_filepath = os.path.join(OUTPUT_DIR, new_filename)
    
    # Ensure target directory exists
    os.makedirs(os.path.dirname(new_filepath), exist_ok=True)
    
    # Extract file to target directory
    with zip_ref.open(file_info) as source, open(new_filepath, 'wb') as target:
        shutil.copyfileobj(source, target)
    
    # Handle image format conversion
    if file_info.filename.lower().endswith('.png'):
        with Image.open(new_filepath) as img:
            rgb_img = img.convert('RGB')
            rgb_img.save(new_filepath, 'JPEG', quality=95)
    elif file_info.filename.lower().endswith('.jpeg'):
        os.rename(new_filepath, new_filepath.replace('.jpeg', '.jpg'))

def show_completion_dialog():
    dialog = Toplevel(root)
    dialog.title("Completed")
    dialog.geometry("300x100")
    dialog.resizable(False, False)

    # Center the window
    window_width, window_height = 300, 100
    screen_width, screen_height = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
    position_top = int(screen_height / 2 - window_height / 2)
    position_right = int(screen_width / 2 - window_width / 2)
    dialog.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

    Label(dialog, text=f"Images extracted to {OUTPUT_DIR} and converted to .jpg format").pack(pady=10)

    def open_output_dir():
        subprocess.Popen(f'explorer "{OUTPUT_DIR}"')
        dialog.destroy()

    button_frame = Frame(dialog)
    button_frame.pack(pady=10)

    Button(button_frame, text="Open FFOutput", command=open_output_dir).pack(side=LEFT, padx=5)
    Button(button_frame, text="OK", command=dialog.destroy).pack(side=RIGHT, padx=5)

def pack_folder():
    target_dir = os.path.join(OUTPUT_DIR, "digital")
    os.makedirs(target_dir, exist_ok=True)

    # Move all items except the target directory itself
    for item in os.listdir(OUTPUT_DIR):
        source_item = os.path.join(OUTPUT_DIR, item)
        if source_item != target_dir:
            shutil.move(source_item, os.path.join(target_dir, item))
    
    messagebox.showinfo("Completed", f"All files have been moved to {target_dir}")

def drop(event):
    global epub_file
    clear_epub()
    epub_file = os.path.normpath(event.data.strip("{}"))
    status_label.config(text=f"Imported file: {os.path.basename(epub_file)}")

def get_image_resolution(directory):
    for file in os.listdir(directory):
        if file.lower().endswith(('.jpg', '.png')):
            img = cv2.imread(os.path.join(directory, file))
            if img is not None:
                print(f"First image resolution: {img.shape}")
                return img.shape
    return None

def are_images_edge_similar(img1, img2, column1, column2, threshold):
    edge1 = img1[:, column1, :]  # Specified column of img1
    edge2 = img2[:, column2, :]  # Specified column of img2
    
    matches = np.all(edge1 == edge2, axis=1)
    matching_ratio = np.sum(matches) / len(matches)
    print(f"Matching ratio: {matching_ratio:.2f} (column {column1} vs column {column2})")
    
    return matching_ratio >= threshold

def check_images_in_directory(directory):
    resolution = get_image_resolution(directory)
    if resolution is None:
        print("No valid images found in the directory.")
        return
    
    height, width, channels = resolution
    double_width = width * 2

    stitched_dir = os.path.join(directory, "Stitched")
    os.makedirs(stitched_dir, exist_ok=True)
    
    files = sorted(
        [f for f in os.listdir(directory) if f.lower().endswith(('.jpg', '.png')) and not f.startswith('stitched_')],
        key=lambda x: int(os.path.splitext(x)[0])
    )
    
    processed_files = set()
    
    for i in range(0, len(files) - 1, 2):
        if i+1 >= len(files):
            break
        
        file_even, file_odd = files[i], files[i + 1]
        
        if int(os.path.splitext(file_even)[0]) % 2 != 0 or int(os.path.splitext(file_odd)[0]) % 2 != 1:
            continue
        
        if file_even in processed_files or file_odd in processed_files:
            continue
        
        img1 = cv2.imread(os.path.join(directory, file_even))
        img2 = cv2.imread(os.path.join(directory, file_odd))
        
        if img1.shape == resolution and img2.shape == resolution:
            left_right_match = are_images_edge_similar(img1, img2, -1, 0, 0.15)
            right_left_match = are_images_edge_similar(img1, img2, 0, -1, 0.15)
            
            if left_right_match or right_left_match:
                print(f"{file_even} and {file_odd} were likely split from the same original image.")
                stitched_image = np.zeros((height, double_width, 3), dtype=np.uint8)
                stitched_image[:, :width] = img2 if right_left_match else img1
                stitched_image[:, width:] = img1 if right_left_match else img2
                output_filename = os.path.join(directory, f"{file_even.split('.')[0]}-{file_odd.split('.')[0]}.jpg")
                cv2.imwrite(output_filename, stitched_image)
                print(f"Saved stitched image as {output_filename}")
                
                for file in (file_even, file_odd):
                    shutil.move(os.path.join(directory, file), os.path.join(stitched_dir, file))
                    processed_files.add(file)
            else:
                print(f"{file_even} and {file_odd} do not appear to be from the same original image.")

def auto_img_stitch():
    check_images_in_directory(OUTPUT_DIR)

# Create main window
root = TkinterDnD.Tk()  # Use TkinterDnD instead of TkinterDnd
root.title("EPUB Image Extractor Tool")
root.geometry("800x450")  # 16:9 aspect ratio

# Left frame
left_frame = Frame(root, width=400, height=450, bg="lightgrey")
left_frame.pack_propagate(False)
left_frame.pack(side=LEFT, fill="y")

# Drop hint label
drop_label = Label(left_frame, text="Drop EPUB file here", bg="lightgrey")
drop_label.pack(expand=True)

# Right frame
right_frame = Frame(root, width=400, height=450)
right_frame.pack_propagate(False)
right_frame.pack(side=RIGHT, fill="y")

# Status label
status_label = Label(right_frame, text="No file imported")
status_label.pack(side=TOP, pady=10)

# Button frame
button_frame = Frame(right_frame)
button_frame.pack(expand=True)

# Open file button
open_button = Button(button_frame, text="Select EPUB File", command=select_epub)
open_button.pack(pady=10)

# Process file button
process_button = Button(button_frame, text="Process Imported EPUB", command=process_epub)
process_button.pack(pady=10)

# AutoImgStitch button
auto_img_stitch_button = Button(button_frame, text="Auto Stitch (Simple)", command=auto_img_stitch)
auto_img_stitch_button.pack(pady=10)

# PackFolder button
pack_folder_button = Button(button_frame, text="Pack to digital", command=pack_folder)
pack_folder_button.pack(pady=10)

# Enable drag and drop
root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', drop)

# Run main loop
root.mainloop()
