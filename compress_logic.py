import os
import shutil
import wx.adv
import multiprocessing
from multiprocessing import Manager
from PIL import Image, TiffImagePlugin

from helpers import format_table_row, bytes_to_mb, create_log_file, is_supported_file, is_multi_frame, \
    log_to_console, collect_multi_frame_tiff_groups, merge_tiffs, get_channel_range, extract_frames_with_metadata, \
    resize_image

num_tasks_completed = 0


def run_compression(compression_choice, source_directory, destination_directory, console_output, is_stop_requested,
                    should_merge):
    apply_results_merge = []
    widths = [115, 20, 20, 20]  # Column widths
    header = ["File Name", "Original Size (MB)", "New Size (MB)", "Saved Size (MB)"]
    log_entries = [format_table_row(header, widths)]
    log_entries.append('-' * sum(widths))  # Separator line
    compression_option = compression_choice.GetString(compression_choice.GetSelection())

    MSG_START_COMPRESSION = f"[▶] Compression with: {compression_option}!\n"
    log_to_console(console_output, MSG_START_COMPRESSION, None, True)
    copy_source_directory_tree(source_directory, destination_directory)
    # Processing images
    if should_merge:
        log_to_console(console_output, '[*] Creating and compressing multi-frame images from your channels', None, True)
        apply_results_merge = compress_and_merge_tiff(console_output, source_directory, destination_directory,
                                                      is_stop_requested, compression_option, widths)
        if is_stop_requested():
            return "STOPPED"

        log_to_console(console_output, '[*] Multi-frame images from your channels created', None, True)
    log_to_console(console_output, '[*] Compressing images at directory', None, True)
    apply_results, skipped_files = process_directory(source_directory, destination_directory, compression_option,
                                                     console_output, is_stop_requested, widths)
    if is_stop_requested():
        return "STOPPED"
    merged_results = apply_results_merge + apply_results
    log_entries, num_files_processed, total_saved_size = process_results_create_log_entries(merged_results, skipped_files, widths)

    if skipped_files:
        skipped_msg = f"[⚠] {len(skipped_files)} files were not processed (unsupported extensions) - {', '.join(skipped_files)}"
        log_to_console(console_output, skipped_msg, wx.RED, True)

    MSG_COMPRESSION_ENDED = f'Compression ended\n✅Successfully compressed {num_files_processed} images.\n '
    log_to_console(console_output, MSG_COMPRESSION_ENDED, wx.GREEN, True)
    log_to_console(console_output, "========================================\n", None, False)
    log_file_path = create_log_file(destination_directory, num_files_processed, log_entries, total_saved_size)
    return log_file_path if log_file_path else "STOPPED"


def copy_source_directory_tree(src_dir, dest_dir):
    for root, dirs, files in os.walk(src_dir):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            rel_dir = os.path.relpath(dir_path, src_dir)
            dest_dir_path = os.path.join(dest_dir, rel_dir)
            os.makedirs(dest_dir_path, exist_ok=True)


def process_results_create_log_entries(apply_results, skipped_files, widths):
    num_files_processed = 0
    total_saved_size = 0
    log_entries = []
    for result_obj in apply_results:
        result = result_obj.get()
        if result:
            saved_size, initial_size, final_size, new_name = result
            total_saved_size += saved_size
            num_files_processed += 1
            is_merged = "_ch" in new_name and "to" in new_name
            merge_indicator = "[Merged]" if is_merged else ""
            log_entry = format_table_row(
                ['[+] ' + merge_indicator + new_name, f"{bytes_to_mb(initial_size):.2f}",
                 f"{bytes_to_mb(final_size):.2f}",
                 f"{bytes_to_mb(saved_size):.2f}"], widths)
            log_entries.append(log_entry)

    if skipped_files:
        log_entries.append("========================================\n")
        skipped_msg = f"[⚠] {len(skipped_files)} files were not processed - {', '.join(skipped_files)}"
        log_entries.append(skipped_msg)

    return log_entries, num_files_processed, total_saved_size


def compress_and_merge_tiff(console_output, source_directory, destination_directory, is_stop_requested_gui,
                            compression_option, widths):
    # For multiprocessing
    global num_tasks_completed
    num_tasks_completed = 0

    # Processing images
    grouped_files = collect_multi_frame_tiff_groups(source_directory)

    manager = Manager()
    queue = manager.Queue()
    tasks = create_compression_tasks(grouped_files.values(), source_directory, destination_directory, compression_option, queue, widths, merge=True)

    if tasks:
        apply_results_merge = parallel_processing(console_output, tasks, queue, is_stop_requested_gui, merge_tiffs)

    return apply_results_merge


def process_directory(src_dir, dest_dir, compression_option, console_output, is_stop_requested_gui,
                      widths):
    skipped_files = []
    supported_files = []
    # For multiprocessing
    global num_tasks_completed
    num_tasks_completed = 0

    supported_files = [os.path.join(root, file) for root, _, files in os.walk(src_dir) for file in files if is_supported_file(file)]
    skipped_files = [file for root, _, files in os.walk(src_dir) for file in files if not is_supported_file(os.path.join(root, file))]

    manager = Manager()
    queue = manager.Queue()
    tasks = create_compression_tasks(supported_files, src_dir, dest_dir, compression_option, queue, widths, merge=False)
    apply_results = parallel_processing(console_output, tasks, queue, is_stop_requested_gui, process_file)

    return apply_results, skipped_files


def parallel_processing(console_output, tasks, queue, is_stop_requested_gui, function_exec):
    # For multiprocessing
    global num_tasks_completed
    num_tasks_completed = 0
    apply_results = []  # List to store ApplyResult objects

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
            result = pool.apply_async(function_exec, args=task, callback=task_completed)
            apply_results.append(result)
        # Continuously read from the queue and update the UI
        while True:
            message = queue.get()
            if message == "DONE" or is_stop_requested_gui():
                break
            log_to_console(console_output, message, wx.GREEN, True)
    return apply_results


def create_compression_tasks(files, source_directory, destination_directory, compression_option, queue, widths, merge=False):
    tasks = []
    for file_or_group in files:
        if merge:
            first_file_rel_path = os.path.relpath(file_or_group[0], source_directory)
            rel_dir_path = os.path.dirname(first_file_rel_path)
            output_dir = os.path.join(destination_directory, rel_dir_path)
            channel_range = get_channel_range(file_or_group)
            if channel_range:
                min_channel, max_channel = channel_range
                output_filename = f"{os.path.basename(file_or_group[0]).split('_ch')[0]}_ch{min_channel:02d}to{max_channel:02d}_compressed.tif"
            else:
                output_filename = f"{os.path.basename(file_or_group[0]).split('_ch')[0]}_compressed.tif"
            output_path = os.path.join(output_dir, output_filename)
            tasks.append((file_or_group, output_path, widths, queue, compression_option))
        else:
            # For individual file processing, 'file_or_group' is a single file path
            src_path = os.path.join(source_directory, file_or_group)
            rel_path = os.path.relpath(src_path, source_directory)
            dest_path = os.path.join(destination_directory, rel_path)
            tasks.append((src_path, dest_path, compression_option, queue, widths))

    return tasks


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
                    save_image_and_compress(extract_frames_with_metadata(img), dest_path_new_name)
                else:
                    save_image_and_compress(img, dest_path_new_name)
            del img
    except Exception as e:
        print(f"Error processing {src_path}: {e}")


def resize_multi_frame_image(img, compression_option):
    resized_frames = []
    while True:
        try:
            frame = img.copy()
            if hasattr(img, "tag_v2"):
                frame.tag_v2 = img.tag_v2
            frame_resized = resize_image(frame, compression_option)
            resized_frames.append(frame_resized)
            img.seek(img.tell() + 1)
        except EOFError:
            break  # End of frames
    return resized_frames


def save_image_and_compress(img, img_path):
    try:
        if img_path.lower().endswith('.png'):
            img.save(img_path, optimize=True, compress_level=9)
        elif img_path.lower().endswith(('.jpg', '.jpeg')):
            img.save(img_path, optimize=True, quality=95, progressive=True)
        elif img_path.lower().endswith('.webp'):
            img.save(img_path, quality=95, lossless=True, method=6)
        elif img_path.lower().endswith(('.bmp', '.dib')):
            img.save(img_path)
        elif img_path.lower().endswith(('.tif', '.tiff')):
            # Handle multi-frame TIFF
            if isinstance(img, list):
                metadata = img[0].info.get("tag_v2", TiffImagePlugin.ImageFileDirectory_v2())
                img[0].save(img_path, save_all=True, append_images=img[1:], compression='tiff_lzw', tiffinfo=metadata)
            else:
                metadata = img.info.get("tag_v2", TiffImagePlugin.ImageFileDirectory_v2())
                img.save(img_path, compression='tiff_lzw', tiffinfo=metadata)
        else:
            print(f"Unsupported file format for {img_path}")
    except Exception as e:
        print(f"Error saving {img_path}: {e}")


def request_stop(stop_flag_callback, console_output):
    MSG_STOPPING = "[⚠] Stopping... Please wait. The stop process has finished when the UI buttons are active"
    log_to_console(console_output, "\n========================================", wx.RED, False)
    log_to_console(console_output, MSG_STOPPING, wx.RED, True)
    stop_flag_callback(True)
