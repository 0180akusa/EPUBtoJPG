import os
import zipfile
import shutil
import subprocess
from tkinter import Tk, Frame, Button, Label, filedialog, LEFT, RIGHT, TOP, messagebox, Toplevel
from PIL import Image
from tkinterdnd2 import TkinterDnD, DND_FILES
import cv2
import numpy as np

# 设置输出目录
output_dir = r"D:\FFOutput"

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 全局变量保存导入的epub文件路径
epub_file = None

def clear_epub():
    global epub_file
    epub_file = None
    status_label.config(text="没有导入文件")

def select_epub():
    global epub_file
    file_path = filedialog.askopenfilename(title="选择一个EPUB文件", filetypes=[("EPUB files", "*.epub")])
    if file_path:
        clear_epub()
        epub_file = os.path.normpath(file_path)
        status_label.config(text=f"已导入文件: {os.path.basename(epub_file)}")

def process_epub():
    global epub_file
    if not epub_file:
        messagebox.showerror("错误", "没有导入文件")
        return

    try:
        # 将.epub文件后缀改为.zip
        zip_file = os.path.splitext(epub_file)[0] + '.zip'

        # 复制文件并改名为.zip
        shutil.copy(epub_file, zip_file)

        # 打开zip文件
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            # 获取文件列表
            file_list = zip_ref.namelist()

            # 定义要处理的images文件夹列表
            images_folders = ['images/']
            for name in file_list:
                if name.endswith('_files/'):
                    images_folders.append(f'{name}images/')

            # 处理所有找到的images文件夹
            for images_folder in images_folders:
                for file_info in zip_ref.infolist():
                    if file_info.filename.startswith(images_folder) and (
                        file_info.filename.endswith('.jpeg') or
                        file_info.filename.endswith('.jpg') or
                        file_info.filename.endswith('.png')):
                        
                        # 获取文件名并删除前导零
                        original_filename = file_info.filename.replace(images_folder, '')
                        new_filename = original_filename.lstrip('0')
                        if new_filename == '':
                            new_filename = '0'
                        new_filename = os.path.splitext(new_filename)[0] + '.jpg'
                        
                        # 构造新的文件路径
                        new_filepath = os.path.join(output_dir, new_filename)
                        
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(new_filepath), exist_ok=True)
                        
                        # 提取文件到目标目录
                        with zip_ref.open(file_info) as source:
                            with open(new_filepath, 'wb') as target:
                                shutil.copyfileobj(source, target)
                        
                        # 处理图片格式转换
                        if file_info.filename.endswith('.png'):
                            with Image.open(new_filepath) as img:
                                rgb_img = img.convert('RGB')
                                rgb_img.save(new_filepath, 'JPEG', quality=95)
                        elif file_info.filename.endswith('.jpeg'):
                            os.rename(new_filepath, new_filepath.replace('.jpeg', '.jpg'))
        
        # 删除.zip文件
        os.remove(zip_file)

        show_completion_dialog()

    except Exception as e:
        messagebox.showerror("错误", f"处理EPUB文件时出错: {e}")

def show_completion_dialog():
    dialog = Toplevel(root)
    dialog.title("完成")
    dialog.geometry("300x100")
    dialog.resizable(False, False)

    # 设置窗口居中
    window_width = 300
    window_height = 100
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    position_top = int(screen_height / 2 - window_height / 2)
    position_right = int(screen_width / 2 - window_width / 2)
    dialog.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

    Label(dialog, text=f"图片已提取到 {output_dir}，并且已转换为.jpg格式").pack(pady=10)

    def open_output_dir():
        subprocess.Popen(f'explorer "{output_dir}"')
        dialog.destroy()

    button_frame = Frame(dialog)
    button_frame.pack(pady=10)

    open_button = Button(button_frame, text="打开FFOutput", command=open_output_dir)
    open_button.pack(side=LEFT, padx=5)

    ok_button = Button(button_frame, text="确定", command=dialog.destroy)
    ok_button.pack(side=RIGHT, padx=5)

def pack_folder():
    source_dir = output_dir
    target_dir = os.path.join(source_dir, "digital")

    # 如果目标目录不存在，则创建它
    os.makedirs(target_dir, exist_ok=True)

    # 获取源目录中的所有文件和文件夹
    items = os.listdir(source_dir)

    # 将所有项目移动到目标目录
    for item in items:
        source_item = os.path.join(source_dir, item)
        target_item = os.path.join(target_dir, item)
        
        # 跳过目标目录自身
        if source_item == target_dir:
            continue
        
        # 移动项目
        shutil.move(source_item, target_item)
    
    messagebox.showinfo("完成", f"所有文件已移动到 {target_dir}")

def drop(event):
    global epub_file
    clear_epub()
    epub_file = os.path.normpath(event.data.strip("{}"))
    status_label.config(text=f"已导入文件: {os.path.basename(epub_file)}")

def get_image_resolution(directory):
    for file in os.listdir(directory):
        if file.endswith('.jpg') or file.endswith('.png'):
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
    if not os.path.exists(stitched_dir):
        os.makedirs(stitched_dir)
    
    files = sorted(
        [f for f in os.listdir(directory) if (f.endswith('.jpg') or f.endswith('.png')) and not f.startswith('stitched_')],
        key=lambda x: int(os.path.splitext(x)[0])
    )
    
    processed_files = set()
    
    for i in range(0, len(files) - 1, 2):
        if i+1 >= len(files):
            break
        
        file_even = files[i]
        file_odd = files[i + 1]
        
        if int(os.path.splitext(file_even)[0]) % 2 != 0 or int(os.path.splitext(file_odd)[0]) % 2 != 1:
            continue
        
        if file_even in processed_files or file_odd in processed_files:
            continue
        
        img1 = cv2.imread(os.path.join(directory, file_even))
        img2 = cv2.imread(os.path.join(directory, file_odd))
        
        if img1.shape == resolution and img2.shape == resolution:
            left_right_match = are_images_edge_similar(img1, img2, -1, 0, 0.15)
            right_left_match = are_images_edge_similar(img1, img2, 0, -1, 0.15)
            
            if left_right_match:
                print(f"{file_even} and {file_odd} were likely split from the same original image (left-right).")
                stitched_image = np.zeros((height, double_width, 3), dtype=np.uint8)
                stitched_image[:, :width] = img1
                stitched_image[:, width:] = img2
                output_filename = os.path.join(directory, f"{file_even.split('.')[0]}-{file_odd.split('.')[0]}.jpg")
                cv2.imwrite(output_filename, stitched_image)
                print(f"Saved stitched image as {output_filename}")
            elif right_left_match:
                print(f"{file_even} and {file_odd} were likely split from the same original image (right-left).")
                stitched_image = np.zeros((height, double_width, 3), dtype=np.uint8)
                stitched_image[:, :width] = img2
                stitched_image[:, width:] = img1
                output_filename = os.path.join(directory, f"{file_even.split('.')[0]}-{file_odd.split('.')[0]}.jpg")
                cv2.imwrite(output_filename, stitched_image)
                print(f"Saved stitched image as {output_filename}")
            else:
                print(f"{file_even} and {file_odd} do not appear to be from the same original image.")
                continue
            
            shutil.move(os.path.join(directory, file_even), os.path.join(stitched_dir, file_even))
            shutil.move(os.path.join(directory, file_odd), os.path.join(stitched_dir, file_odd))
            processed_files.add(file_even)
            processed_files.add(file_odd)

def auto_img_stitch():
    directory = output_dir
    check_images_in_directory(directory)

# 创建主窗口
root = TkinterDnD.Tk()
root.title("EPUB 图片提取工具")
root.geometry("800x450")  # 16:9 比例

# 左半边框架
left_frame = Frame(root, width=400, height=450, bg="lightgrey")
left_frame.pack_propagate(False)
left_frame.pack(side=LEFT, fill="y")

# 提示标签
drop_label = Label(left_frame, text="拖入EPUB文件到这里", bg="lightgrey")
drop_label.pack(expand=True)

# 右半边框架
right_frame = Frame(root, width=400, height=450)
right_frame.pack_propagate(False)
right_frame.pack(side=RIGHT, fill="y")

# 状态标签
status_label = Label(right_frame, text="没有导入文件")
status_label.pack(side=TOP, pady=10)

# 按钮框架
button_frame = Frame(right_frame)
button_frame.pack(expand=True)

# 打开文件按钮
open_button = Button(button_frame, text="选择EPUB文件", command=select_epub)
open_button.pack(pady=10)

# 处理文件按钮
process_button = Button(button_frame, text="处理导入的EPUB", command=process_epub)
process_button.pack(pady=10)

# AutoImgStitch按钮
auto_img_stitch_button = Button(button_frame, text="自动拼接（简易）", command=auto_img_stitch)
auto_img_stitch_button.pack(pady=10)

# PackFolder按钮
pack_folder_button = Button(button_frame, text="打包到digital", command=pack_folder)
pack_folder_button.pack(pady=10)

# 支持拖放
root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', drop)

# 运行主循环
root.mainloop()
