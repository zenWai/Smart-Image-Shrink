import os
import platform
import re
from collections import defaultdict
from datetime import datetime
import wx
from PIL import Image, TiffImagePlugin


def is_supported_file(file_path):
    supported_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp', '.bmp', '.dib']
    return any(file_path.lower().endswith(ext) for ext in supported_extensions)


def extract_frames_with_metadata(img):
    frames = []
    while True:
        try:
            frame = img.copy()
            if hasattr(img, "tag_v2"):
                frame.tag_v2 = img.tag_v2
            frames.append(frame)
            img.seek(img.tell() + 1)
        except EOFError:
            break  # End of frames
    return frames


def is_multi_frame(img):
    try:
        return img.n_frames > 1
    except Exception as e:
        print(f"Error: {e}")
        return False


def bytes_to_mb(size_in_bytes):
    if platform.system() == "Windows":
        # Windows Use binary system but labels it as MB (1 MB = 1024 * 1024 bytes)
        return size_in_bytes / (1024 * 1024)
    else:
        # macOS Use decimal system (1 MB = 1000 * 1000 bytes)
        return size_in_bytes / (1000 * 1000)


def format_table_row(items, widths):
    return ' | '.join(item.ljust(width) for item, width in zip(items, widths))


def count_files_in_destination(directory):
    total_files = 0
    for root, _, files in os.walk(directory):
        for file in files:
            total_files += 1
    return total_files


def count_files_in_source(directory, console_output):
    supported_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp', '.bmp', '.dib']
    total_files = 0
    unsupported_files_count = 0
    unsupported_files = []
    log_to_console(console_output, "========================================", None, False)
    for root, _, files in os.walk(directory):
        for file in files:
            total_files += 1
            MSG_SUPPORTED_FILES = f'[*] File {total_files}: {file}'
            MSG_UNSUPPORTED_FILES = f'[!] Unsupported File {total_files}: {file}'
            if any(file.lower().endswith(ext) for ext in supported_extensions):
                log_to_console(console_output, MSG_SUPPORTED_FILES, wx.GREEN, False)
            else:
                log_to_console(console_output, MSG_UNSUPPORTED_FILES, wx.RED, False)
                unsupported_files_count += 1
                unsupported_files.append(file)

    return total_files, supported_extensions, unsupported_files_count, unsupported_files


def collect_multi_frame_tiff_groups(directory):
    def extract_channel_number(filename):
        match = re.search(r'_ch(\d+)', filename)
        return int(match.group(1)) if match else -1

    def sort_files_by_channel(files):
        return sorted(files, key=extract_channel_number)
    # Regex to match files ending with _chXX.tif
    pattern = re.compile(r'(.+)_ch\d\d\.tif$')
    groups = defaultdict(list)

    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith('.tif'):
                match = pattern.match(filename)
                if match:
                    full_path = os.path.join(root, filename)
                    base_name = match.group(1)
                    groups[base_name].append(full_path)

    # Filter out groups with only one file and sort the files in each group
    grouped_files = {base: sort_files_by_channel(files) for base, files in groups.items() if len(files) > 1}

    return grouped_files


def resize_image(img, compression_option):
    factor = int(compression_option.split(' ')[-1][1:])
    new_width = int(img.width / factor)
    aspect_ratio = img.height / img.width
    new_height = int(aspect_ratio * new_width)
    resampling_method = Image.Resampling.LANCZOS if img.mode in ["L", "RGB", "RGBA"] else Image.NEAREST
    return img.resize((new_width, new_height), resampling_method)


def merge_tiffs(file_paths, output_path, widths, queue, compression_option):
    initial_size = sum(os.path.getsize(file_path) for file_path in file_paths)
    frames = []
    for file_path in file_paths:
        with Image.open(file_path) as img:
            frame = img.copy()
            if 'Compress Size' in compression_option:
                frame = resize_image(frame, compression_option)
            frames.append(frame)

    # Extract metadata from the first frame
    if hasattr(frames[0], "tag_v2"):
        metadata = frames[0].tag_v2
    else:
        metadata = TiffImagePlugin.ImageFileDirectory_v2()

    # Save as a multi-frame TIFF
    frames[0].save(output_path, save_all=True, append_images=frames[1:], compression='tiff_lzw', tiffinfo=metadata)

    final_size = os.path.getsize(output_path)
    saved_size = initial_size - final_size
    new_name = os.path.basename(output_path)
    console_entry = format_table_row(
        ['[+] [Merged]' + new_name, f"Original Size: {bytes_to_mb(initial_size):.2f}MB",
         f"Final Size: {bytes_to_mb(final_size):.2f}MB",
         f"Saved: {bytes_to_mb(saved_size):.2f}MB"], widths)
    queue.put(console_entry)

    return saved_size, initial_size, final_size, new_name


def get_channel_range(files):
    channel_numbers = []
    for file in files:
        match = re.search(r'_ch(\d\d)\.tif$', file)
        if match:
            channel_numbers.append(int(match.group(1)))

    if channel_numbers:
        min_channel = min(channel_numbers)
        max_channel = max(channel_numbers)
        return min_channel, max_channel
    else:
        return None


def log_to_console(console_output, text, color=None, include_timestamp=True):
    # Function to update the console_output in a thread-safe manner
    def update_console():
        if color is not None:
            console_output.SetDefaultStyle(wx.TextAttr(color))
        console_output.AppendText(formatted_text + "\n")
        if color is not None:
            console_output.SetDefaultStyle(wx.TextAttr(wx.WHITE))  # Reset color

    if include_timestamp:
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_text = f"{timestamp} - {text}"
    else:
        formatted_text = text

    wx.CallAfter(update_console)


def create_log_file(dest_dir, num_files_processed, log_entries, total_saved_size):
    # Create log file
    log_file_path = os.path.join(dest_dir, "log.txt")
    with open(log_file_path, "w") as log_file:
        log_file.write(f"[*] Processed {num_files_processed} files:\n")
        log_file.write('========================================\n')
        log_file.write('\n'.join(log_entries))
        log_file.write('\n========================================')
        log_file.write(f"\n[*] Successfully compressed {num_files_processed} images.")
        log_file.write(f"\n[*] In total, we saved {bytes_to_mb(total_saved_size):.2f} MB")

    return log_file_path
