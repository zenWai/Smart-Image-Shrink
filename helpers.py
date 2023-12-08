import os
import platform
from datetime import datetime
import wx


def is_supported_file(file_path):
    supported_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp', '.bmp', '.dib']
    return any(file_path.lower().endswith(ext) for ext in supported_extensions)


def extract_frames(img):
    frames = []
    while True:
        try:
            frames.append(img.copy())
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
            if any(file.lower().endswith(ext) for ext in supported_extensions):
                message = f'[*] File {total_files}: {file}'
                log_to_console(console_output, message, wx.GREEN, False)
            else:
                unsupported_files_count += 1
                unsupported_files.append(file)
                message = f'[!] Unsupported File {total_files}: {file}'
                log_to_console(console_output, message, wx.RED, False)
    return total_files, supported_extensions, unsupported_files_count, unsupported_files


def log_to_console(console_output, text, color=None, include_timestamp=True):
    if include_timestamp:
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_text = f"{timestamp} - {text}"
    else:
        formatted_text = text

    # Function to update the console_output in a thread-safe manner
    def update_console():
        if color is not None:
            console_output.SetDefaultStyle(wx.TextAttr(color))
        console_output.AppendText(formatted_text + "\n")
        if color is not None:
            console_output.SetDefaultStyle(wx.TextAttr(wx.WHITE))  # Reset to white color

    # Ensure the update is done in the main GUI thread
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
