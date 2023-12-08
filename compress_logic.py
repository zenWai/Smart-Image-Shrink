import os
import shutil
import wx.adv
import multiprocessing
from multiprocessing import Manager
from PIL import Image, TiffImagePlugin

from helpers import format_table_row, bytes_to_mb, create_log_file, is_supported_file, is_multi_frame, extract_frames, \
    log_to_console

num_tasks_completed = 0


def run_compression(compression_choice, source_directory, destination_directory, console_output, is_stop_requested):
    compression_option = compression_choice.GetString(compression_choice.GetSelection())
    MSG_START_COMPRESSION = f"[▶] Starting the compression with option: {compression_option}!\n"
    log_to_console(console_output, MSG_START_COMPRESSION, wx.BLUE, True)
    # Processing images
    log_file_path = process_directory(source_directory, destination_directory, compression_option,
                                      console_output, is_stop_requested)
    return log_file_path if log_file_path else "STOPPED"


def process_directory(src_dir, dest_dir, compression_option, console_output, is_stop_requested_gui):
    num_files_processed = 0
    total_saved_size = 0
    # For logging format
    widths = [115, 20, 20, 20]  # Column widths
    header = ["File Name", "Original Size (MB)", "New Size (MB)", "Saved Size (MB)"]
    log_entries = [format_table_row(header, widths)]
    log_entries.append('-' * sum(widths))  # Separator line
    skipped_files = []  # List to keep track of skipped (unsupported) files
    # For multiprocessing
    global num_tasks_completed
    num_tasks_completed = 0
    tasks = []  # List to keep tasks for multiprocessing
    apply_results = []  # List to store ApplyResult objects
    manager = Manager()
    queue = manager.Queue()

    for root, dirs, files in os.walk(src_dir):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            rel_dir = os.path.relpath(dir_path, src_dir)
            dest_dir_path = os.path.join(dest_dir, rel_dir)
            os.makedirs(dest_dir_path, exist_ok=True)

        for file in files:
            # Check if stop was requested
            if is_stop_requested_gui():
                break
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, src_dir)
            dest_path = os.path.join(dest_dir, rel_path)
            if is_supported_file(src_path):
                tasks.append((src_path, dest_path, compression_option, queue, widths))
            else:
                skipped_files.append(file)

    def task_completed(result):
        global num_tasks_completed
        num_tasks_completed += 1
        if num_tasks_completed == len(tasks):
            queue.put("DONE")

    # Process files in parallel using multiprocessing.Pool
    with multiprocessing.Pool(processes=4) as pool:
        for task in tasks:
            if is_stop_requested_gui():
                break
            result = pool.apply_async(process_file, args=task, callback=task_completed)
            apply_results.append(result)
        # Continuously read from the queue and update the UI
        while True:
            message = queue.get()
            if message == "DONE" or is_stop_requested_gui():
                break
            log_to_console(console_output, message, wx.GREEN, True)
    # Stops the compression process
    if is_stop_requested_gui():
        return

    for result_obj in apply_results:
        result = result_obj.get()
        if result:
            saved_size, initial_size, final_size, new_name = result
            total_saved_size += saved_size
            num_files_processed += 1
            log_entry = format_table_row(
                ['[+] ' + new_name, f"{bytes_to_mb(initial_size):.2f}", f"{bytes_to_mb(final_size):.2f}",
                 f"{bytes_to_mb(saved_size):.2f}"], widths)
            log_entries.append(log_entry)

    if skipped_files:
        skipped_msg = f"\n[⚠] {len(skipped_files)} files were not processed (unsupported extensions) - {', '.join(skipped_files)}"
        log_entries.append(skipped_msg)
        log_to_console(console_output, skipped_msg, wx.RED, True)

    MSG_COMPRESSION_ENDED = f'Compression ended\n✅Successfully compressed {num_files_processed} images.\n '
    log_to_console(console_output, MSG_COMPRESSION_ENDED, wx.GREEN, True)
    log_to_console(console_output, "========================================\n", None, False)
    log_file_path = create_log_file(dest_dir, num_files_processed, log_entries, total_saved_size)
    return log_file_path


def process_file(src_path, dest_path, compression_option, queue, widths):
    dest_path_new_name = get_new_file_path_new_name(dest_path, compression_option)
    compress_image(src_path, dest_path_new_name, compression_option)
    initial_size = os.path.getsize(src_path)
    final_size = os.path.getsize(dest_path_new_name)
    new_name = os.path.basename(dest_path_new_name)
    saved_size = initial_size - final_size if initial_size > final_size else 0
    console_entry = format_table_row(
        ['[+] ' + new_name, f"Original Size: {bytes_to_mb(initial_size):.2f}MB",
         f"Final Size: {bytes_to_mb(final_size):.2f}MB",
         f"Saved: {bytes_to_mb(saved_size):.2f}MB"], widths)
    queue.put(console_entry)
    return saved_size, initial_size, final_size, new_name


def get_new_file_path_new_name(img_path, compression_option):
    base, ext = os.path.splitext(img_path)
    if compression_option == 'Compress with No Data Loss':
        new_name = base + '_compressed' + ext
    elif 'Compress Size' in compression_option:
        factor = compression_option.split(' ')[-1]  # Gets factor from COMPRESSION_OPTIONS text
        new_name = base + '_compressed_' + factor + ext
    # In case any problems with compression_option
    else:
        new_name = base + '_compressed' + ext
    return new_name


def compress_image(src_path, dest_path_new_name, compression_option):
    # copy2 for metadata and never open source
    shutil.copy2(src_path, dest_path_new_name)
    try:
        with Image.open(dest_path_new_name) as img:
            if 'Compress Size' in compression_option:
                if is_multi_frame(img):
                    resized_frames = resize_multi_frame_image(img, compression_option)
                    save_image_and_compress(resized_frames, dest_path_new_name)
                else:
                    img = resize_image(img, compression_option)
                    save_image_and_compress(img, dest_path_new_name)
            else:
                if is_multi_frame(img):
                    save_image_and_compress(extract_frames(img), dest_path_new_name)
                else:
                    save_image_and_compress(img, dest_path_new_name)
            del img
    except Exception as e:
        print(f"Error processing {src_path}: {e}")


def resize_image(img, compression_option):
    factor = int(compression_option.split(' ')[-1][1:])
    new_width = int(img.width / factor)
    aspect_ratio = img.height / img.width
    new_height = int(aspect_ratio * new_width)
    resampling_method = Image.Resampling.LANCZOS if img.mode in ["L", "RGB", "RGBA"] else Image.Resampling.NEAREST
    return img.resize((new_width, new_height), resampling_method)


def resize_multi_frame_image(img, compression_option):
    resized_frames = []
    while True:
        try:
            resized_frames.append(resize_image(img.copy(), compression_option))
            img.seek(img.tell() + 1)
        except EOFError:
            break  # End of frames
    return resized_frames


def save_image_and_compress(img, img_path):
    if img_path.lower().endswith('.png'):
        img.save(img_path, optimize=True, compress_level=9)
    elif img_path.lower().endswith('.jpg'):
        img.save(img_path, quality=100, progressive=True)
    elif img_path.lower().endswith('.jpeg'):
        img.save(img_path, optimize=True, quality='keep', progressive=True)
    elif img_path.lower().endswith('.webp'):
        img.save(img_path, quality=100, lossless=True, method=6)
    elif img_path.lower().endswith('.bmp', '.dib'):
        img.save(img_path, compression=1)
    elif img_path.lower().endswith(('.tif', '.tiff')):
        metadata = TiffImagePlugin.ImageFileDirectory_v2()
        if hasattr(img, "tag_v2"):
            metadata = img.tag_v2
        # multi-frame
        if isinstance(img, list):
            img[0].save(img_path, save_all=True, append_images=img[1:], compression='tiff_lzw', tiffinfo=metadata)
        # single frame
        else:
            img.save(img_path, compression='tiff_lzw', tiffinfo=metadata)


def request_stop(stop_flag_callback, console_output):
    MSG_STOPPING = "[⚠] Stopping... Please wait. The stop process has finished when the UI buttons are active"
    log_to_console(console_output, "\n========================================", wx.RED, False)
    log_to_console(console_output, MSG_STOPPING, wx.RED, True)
    stop_flag_callback(True)
