import os
import platform


def is_supported_file(file_path):
    supported_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff']
    return any(file_path.lower().endswith(ext) for ext in supported_extensions)


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


def count_files_in_source(directory):
    supported_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff']
    total_files = 0
    unsupported_files_count = 0

    for root, _, files in os.walk(directory):
        for file in files:
            total_files += 1
            print(f"File {total_files}: {file}")
            if not any(file.lower().endswith(ext) for ext in supported_extensions):
                unsupported_files_count += 1
    return total_files, supported_extensions, unsupported_files_count


def create_log_file(dest_dir, num_files_processed, log_entries, total_saved_size):
    # Create log file
    log_file_path = os.path.join(dest_dir, "log.txt")
    with open(log_file_path, "w") as log_file:
        log_file.write(f"Processed {num_files_processed} files:\n")
        log_file.write('\n'.join(log_entries))
        log_file.write('\n')
        log_file.write(f"\nSuccessfully compressed {num_files_processed} images.")
        log_file.write(f"\nIn total, we saved {bytes_to_mb(total_saved_size):.2f} MB")

    return log_file_path
