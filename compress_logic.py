import os
import shutil
import wx
import wx.adv
from PIL import Image

from helpers import format_table_row, bytes_to_mb, create_log_file, is_supported_file


def run_compression(compression_choice, source_directory, destination_directory, console_output, is_stop_requested):
    compression_option = compression_choice.GetString(compression_choice.GetSelection())
    wx.CallAfter(console_output.AppendText, f"Starting the compression with option: {compression_option}!\n")
    # Processing images
    log_file_path = process_directory(source_directory, destination_directory, compression_option,
                                      console_output, is_stop_requested)
    return log_file_path if log_file_path else "STOPPED"


def process_directory(src_dir, dest_dir, compression_option, console_output, is_stop_requested):
    num_files_processed = 0
    total_saved_size = 0
    widths = [65, 20, 20, 20]  # Column widths
    header = ["File Name", "Original Size (MB)", "New Size (MB)", "Saved Size (MB)"]
    log_entries = [format_table_row(header, widths)]
    log_entries.append('-' * sum(widths))  # Separator line
    skipped_files = []  # List to keep track of skipped (unsupported) files

    for root, dirs, files in os.walk(src_dir):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            rel_dir = os.path.relpath(dir_path, src_dir)
            dest_dir_path = os.path.join(dest_dir, rel_dir)
            os.makedirs(dest_dir_path, exist_ok=True)

        for file in files:
            # Check if stop was requested
            if is_stop_requested():
                return
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, src_dir)
            dest_path = os.path.join(dest_dir, rel_path)
            if is_supported_file(src_path):
                result = process_file(src_path, dest_path, compression_option)
                if result:
                    initial_size, final_size, new_name = result
                    saved_size = initial_size - final_size if initial_size > final_size else 0
                    total_saved_size += saved_size
                    num_files_processed += 1
                    log_entry = format_table_row(
                        [new_name, f"{bytes_to_mb(initial_size):.2f}", f"{bytes_to_mb(final_size):.2f}",
                         f"{bytes_to_mb(saved_size):.2f}"], widths)
                    log_entries.append(log_entry)
                    console_entry = format_table_row(
                        [new_name, f"Original Size: {bytes_to_mb(initial_size):.2f}MB",
                         f"Final Size: {bytes_to_mb(final_size):.2f}MB",
                         f"Saved: {bytes_to_mb(saved_size):.2f}MB"], widths)
                    wx.CallAfter(console_output.AppendText, console_entry + "\n")
            else:
                skipped_files.append(file)

            # Check for stop again on end.
            if is_stop_requested():
                return

    if skipped_files:
        skipped_msg = f"\n{len(skipped_files)} files were not processed (unsupported extensions):\n{', '.join(skipped_files)}"
        log_entries.append(skipped_msg)
        wx.CallAfter(console_output.AppendText, skipped_msg)
        wx.CallAfter(console_output.AppendText, '\n')

    wx.CallAfter(console_output.AppendText, '\nCompression ended\n')
    wx.CallAfter(console_output.AppendText, f"\n✅Successfully compressed {num_files_processed} images.\n")
    log_file_path = create_log_file(dest_dir, num_files_processed, log_entries, total_saved_size)
    return log_file_path


def process_file(src_path, dest_path, compression_option):
    dest_path_new_name = get_new_file_path_new_name(dest_path, compression_option)
    compress_image(src_path, dest_path_new_name, compression_option)
    initial_size = os.path.getsize(src_path)
    final_size = os.path.getsize(dest_path_new_name)
    new_name = os.path.basename(dest_path_new_name)
    return initial_size, final_size, new_name


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
                img = resize_image(img, compression_option)
            save_image_and_compress(img, dest_path_new_name)
            del img
    except Exception as e:
        print(f"Error processing {src_path}: {e}")


def resize_image(img, compression_option):
    factor = int(compression_option.split(' ')[-1][1:])
    new_width = int(img.width / factor)
    aspect_ratio = img.height / img.width
    new_height = int(aspect_ratio * new_width)
    resampling_method = Image.Resampling.LANCZOS if img.mode in ["L", "RGB", "RGBA"] else Image.NEAREST
    return img.resize((new_width, new_height), resampling_method)


def save_image_and_compress(img, img_path):
    if img_path.lower().endswith('.png'):
        img.save(img_path, optimize=True)
    elif img_path.lower().endswith(('.jpg', '.jpeg')):
        img.save(img_path, quality=95)
    elif img_path.lower().endswith(('.tif', '.tiff')):
        img.save(img_path, compression='tiff_lzw')


def request_stop(stop_flag_callback, console_output):
    wx.CallAfter(console_output.AppendText,
                 "\nStopping... Please wait. When buttons are enabled the stop process is finished.\n")
    stop_flag_callback(True)
