import os
import zipfile
import shutil
import subprocess
from tkinter import Tk, Frame, Button, Label, filedialog, Toplevel, messagebox, LEFT, TOP, BOTTOM, RIGHT
from PIL import Image
import setuptools

# 设置输出目录
output_dir = "/Users/howl/Downloads/IMAGE/FFOutput"  # 修改为适合macOS的路径

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
        epub_file = file_path
        status_label.config(text=f"已导入文件: {os.path.basename(epub_file)}")

def process_epub():
    global epub_file
    if not epub_file:
        messagebox.showerror("错误", "没有导入文件")
        return

    # 将.epub文件后缀改为.zip
    zip_file = epub_file.replace('.epub', '.zip')

    # 复制文件并改名为.zip
    shutil.copy(epub_file, zip_file)

    # 打开zip文件
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        # 获取文件列表
        file_list = zip_ref.namelist()
        
        # 处理cover.jpg文件
        if 'cover.jpg' in file_list:
            with zip_ref.open('cover.jpg') as source:
                cover_path = os.path.join(output_dir, 'cover.jpg')
                with open(cover_path, 'wb') as target:
                    shutil.copyfileobj(source, target)

        # 找到images文件夹
        images_folder = 'images/'
        if images_folder not in file_list:
            messagebox.showerror("错误", "未找到images文件夹")
            return
        
        # 处理images文件夹中的所有文件
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
                
                # 提取文件到临时目录
                with zip_ref.open(file_info) as source:
                    with open(new_filepath, 'wb') as target:
                        shutil.copyfileobj(source, target)
                
                # 处理图片
                if file_info.filename.endswith('.png'):
                    with Image.open(new_filepath) as img:
                        rgb_img = img.convert('RGB')
                        rgb_img.save(new_filepath, 'JPEG', quality=95)
                elif file_info.filename.endswith('.jpeg'):
                    os.rename(new_filepath, new_filepath.replace('.jpeg', '.jpg'))

    # 删除.zip文件
    os.remove(zip_file)

    show_completion_dialog()

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
        subprocess.Popen(['open', output_dir])
        dialog.destroy()

    button_frame = Frame(dialog)
    button_frame.pack(pady=10)

    open_button = Button(button_frame, text="打开FFOutput", command=open_output_dir)
    open_button.pack(side=LEFT, padx=5)

    ok_button = Button(button_frame, text="确定", command=dialog.destroy)
    ok_button.pack(side=RIGHT, padx=5)

# 创建主窗口
root = Tk()
root.title("EPUB 图片提取工具")
root.geometry("800x450")  # 16:9 比例

# 左半边框架
left_frame = Frame(root, width=400, height=450, bg="lightgrey")
left_frame.pack_propagate(False)
left_frame.pack(side=LEFT, fill="y")

# 提示标签
drop_label = Label(left_frame, text="拖入EPUB文件到这里（Mac暂不支持）", bg="lightgrey")
drop_label.pack(expand=True)

# 右半边框架
right_frame = Frame(root, width=400, height=450)
right_frame.pack_propagate(False)
right_frame.pack(side=RIGHT, fill="y")

# 状态标签
status_label = Label(right_frame, text="没有导入文件")
status_label.pack(side=TOP, pady=10)

# 打开文件按钮
open_button = Button(right_frame, text="选择EPUB文件", command=select_epub)
open_button.pack(side=TOP, pady=10)

# 处理文件按钮
process_button = Button(right_frame, text="处理导入的EPUB", command=process_epub)
process_button.pack(side=BOTTOM, pady=10)

# 运行主循环
root.mainloop()