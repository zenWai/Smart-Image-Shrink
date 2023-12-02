import os
import shutil
import sys
import webbrowser
import subprocess
import platform

import wx
import wx.adv
from PIL import Image
from wx.lib.delayedresult import startWorker
import wx.lib.buttons as buttons

Image.MAX_IMAGE_PIXELS = None

COMPRESSION_OPTIONS = [
    'Compress with No Data Loss',
    'Compress Size x2',
    'Compress Size x4',
    'Compress Size x8',
    'Compress Size x16',
]


# using base of 1000 instead of Mebibytes 1024 (MiB)
def bytes_to_mb(size_in_bytes):
    return size_in_bytes / (1000 * 1000)


def resize_image(img, compression_option):
    factor = int(compression_option.split(' ')[-1][1:])
    new_width = int(img.width / factor)
    aspect_ratio = img.height / img.width
    new_height = int(aspect_ratio * new_width)
    resampling_method = Image.Resampling.LANCZOS if img.mode in ["L", "RGB", "RGBA"] else Image.NEAREST
    return img.resize((new_width, new_height), resampling_method)


def save_image(img, img_path):
    if img_path.lower().endswith('.png'):
        img.save(img_path, optimize=True)
    elif img_path.lower().endswith(('.jpg', '.jpeg')):
        img.save(img_path, quality=95)
    elif img_path.lower().endswith(('.tif', '.tiff')):
        img.save(img_path, compression='tiff_lzw')


def compress_image(img_path, compression_option):
    initial_size = os.path.getsize(img_path)
    try:
        with Image.open(img_path) as img:
            if 'Compress Size' in compression_option:
                img = resize_image(img, compression_option)
            save_image(img, img_path)
    except Exception as e:
        print(f"Error processing {img_path}: {e}")
        return initial_size, initial_size
    final_size = os.path.getsize(img_path)
    return initial_size, final_size


def get_new_filename(img_path, compression_option):
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


def count_files_in_destination(directory):
    total_files = 0

    for root, _, files in os.walk(directory):
        for file in files:
            total_files += 1

    if total_files == 0:
        print("👌Destination Directory is empty, that is perfect!")
        print("")
    else:
        print(f"Total Files in Destination Directory: {total_files}")
        print("⚠️Warning: It is recommended that the destination directory should be empty.")
        print("⚠️Warning: Existing files in the destination will be lost.")
        print("")


def format_table_row(items, widths):
    return ' | '.join(item.ljust(width) for item, width in zip(items, widths))


def count_files_in_source(directory):
    total_files = 0
    unsupported_files_count = 0
    supported_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff']

    for root, _, files in os.walk(directory):
        for file in files:
            total_files += 1
            print(f"File {total_files}: {file}")
            if not any(file.lower().endswith(ext) for ext in supported_extensions):
                unsupported_files_count += 1

    print(f"Total Files in Source Directory: {total_files}")
    print("")
    if unsupported_files_count > 0:
        print(f"Unsupported Files in Source Directory: {unsupported_files_count}")
        print(f"Note: Only files with the following extensions will be compressed: {', '.join(supported_extensions)}")
        print("")


# Dialog with option to open log.txt
class CustomDialog(wx.Dialog):
    def __init__(self, *args, log_file_path, source_directory, destination_directory, **kwargs):
        super(CustomDialog, self).__init__(*args, **kwargs)
        self.log_file_path = log_file_path
        self.source_directory = source_directory
        self.destination_directory = destination_directory

        sizer = wx.BoxSizer(wx.VERTICAL)
        message = wx.StaticText(self, label="Compression of images has completed!")
        sizer.Add(message, wx.SizerFlags().Border(wx.TOP | wx.LEFT, 10))

        # Button to open the log file
        open_log_btn = wx.Button(self, label="Open Log File")
        open_log_btn.Bind(wx.EVT_BUTTON, self.open_log_file)
        sizer.Add(open_log_btn, wx.SizerFlags().Border(wx.ALL, 10))

        # Button to open Source Directory
        open_src_btn = wx.Button(self, label="Source Directory")
        open_src_btn.Bind(wx.EVT_BUTTON, self.open_source_directory)

        # Button to open Destination Directory
        open_dest_btn = wx.Button(self, label="Destination Directory")
        open_dest_btn.Bind(wx.EVT_BUTTON, self.open_destination_directory)

        # Buttons Source and Destination together
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(open_src_btn, 0, wx.RIGHT, 10)
        button_sizer.Add(open_dest_btn, 0, wx.LEFT, 10)
        sizer.Add(button_sizer, 0, wx.CENTER | wx.ALL, 10)

        ok_button = wx.Button(self, wx.ID_OK, "OK")
        sizer.Add(ok_button, wx.SizerFlags().Border(wx.ALL, 10).Center())

        self.SetSizer(sizer)
        self.Fit()

    def open_path(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path], check=True)
            else:  # Assuming Linux or other Unix-like OS
                subprocess.run(["xdg-open", path], check=True)
        except Exception as e:
            wx.MessageBox(f"Failed to open the path: {e}", "Error", wx.OK | wx.ICON_ERROR)

    def open_log_file(self, event):
        self.open_path(self.log_file_path)

    def open_source_directory(self, event):
        self.open_path(self.source_directory)

    def open_destination_directory(self, event):
        self.open_path(self.destination_directory)


class CompressorApp(wx.Frame):
    def __init__(self, parent, title):
        super(CompressorApp, self).__init__(parent, title=title, size=(1300, 800))
        # Initialize the attributes
        self.last_frame_size = (0, 0)  # Initialize with a dummy value
        self.bmp = None
        self.last_size = (0, 0)  # Initialize with a dummy value
        self.source_directory = None
        self.destination_directory = None
        self.panel = wx.Panel(self)
        self.last_github_click_time = 0
        self.stop_requested = False

        # Determine if we're running as a bundled executable
        if getattr(sys, 'frozen', False):
            # If running as bundled executable, use the current directory
            base_path = os.path.dirname(sys.executable)
        else:
            # If running as a script, use the directory of the script
            base_path = os.path.dirname(os.path.abspath(__file__))

        # Load the icon
        self.icon = wx.Icon()
        if platform.system() == "Windows":
            icon_path = "img/icon.ico"
        else:  # macOS and potentially other platforms
            icon_path = "img/icon.icns"

        self.icon.CopyFromBitmap(wx.Bitmap(icon_path, wx.BITMAP_TYPE_ANY))
        self.SetIcon(self.icon)

        # Load the image
        self.image_file = os.path.join(base_path, 'img', 'background2.png')
        self.image = wx.Image(self.image_file, wx.BITMAP_TYPE_ANY)

        # Bind the EVT_PAINT event of the panel to the on_paint method
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)

        # Add an explanation label at the top
        explanation = (
            "This Software Compress images from a chosen Source Directory and saves them "
            "in a Destination Directory.\n\n"
            "✳️ Select the Source Directory.\n"
            "✳️ Select the Destination Directory.\n"
            "✳️ Pick a Compression Option. (Default: 'Compress with No Data Loss').\n"
            "✳️ Click 'Start Compression'.\n\n"
            "⭐Compression Options:\n"
            "   - To Compress with Top-Tier Quality retention use ➡️'Compress with No Data Loss'\n"
            "   - To Compress and Greatly Decrease the Image Size use ➡️ 'Compress Size x2'\nHalves the image dimensions, maintaining aspect ratio.\nThe reduction in file size is notable, and the quality remains largely intact.\n\n"
            "   - As you increase the compression size (x4, x8, x16), the image size decreases proportionally.\n\nQuality loss becomes more noticeable, especially with 'Compress Size x16'."
        )
        self.explanation_label = wx.StaticText(self.panel, label=explanation)
        font_explanation_label = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.explanation_label.SetFont(font_explanation_label)
        # Add buttons to the panel
        # Select Source Directory button
        self.btn_source = buttons.GenButton(self.panel, label='📁 Source Directory   ', pos=(50, 150))
        self.btn_source.SetBackgroundColour('navy')
        self.btn_source.SetForegroundColour('white')
        self.btn_source.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        # Select Destination Directory Button
        self.btn_dest = buttons.GenButton(self.panel, label='📁 Destination Directory   ', pos=(50, 200))
        self.btn_dest.SetBackgroundColour('navy')
        self.btn_dest.SetForegroundColour('white')
        self.btn_dest.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        self.btn_start = buttons.GenButton(self.panel, label='▶️ Start Compression', pos=(500, 360))
        self.btn_start.SetBackgroundColour('navy')
        self.btn_start.SetForegroundColour('white')
        self.btn_start.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        self.stop_button = buttons.GenButton(self.panel, label='⏹️ Stop Compression', pos=(650, 360))
        self.stop_button.SetBackgroundColour('navy')
        self.stop_button.SetForegroundColour('white')
        self.stop_button.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stop_button.Disable()

        # Add a TextCtrl for console output
        self.console_output = wx.TextCtrl(self.panel, size=(0, 150),
                                          style=wx.TE_MULTILINE | wx.TE_READONLY)
        monospaced_font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.console_output.SetFont(monospaced_font)

        # Redirect stdout and stderr to the TextCtrl widget
        sys.stdout = self.TextRedirector(self.console_output)
        sys.stderr = self.TextRedirector(self.console_output)

        # Bind the buttons to their respective event handlers
        self.Bind(wx.EVT_BUTTON, self.on_select_source, self.btn_source)
        self.Bind(wx.EVT_BUTTON, self.on_select_destination, self.btn_dest)
        self.Bind(wx.EVT_BUTTON, self.on_start_compression, self.btn_start)
        self.Bind(wx.EVT_BUTTON, self.request_stop, self.stop_button)

        # Bind the resize event to the update background function
        self.Bind(wx.EVT_SIZE, self.on_resize)

        # Create a BoxSizer for vertical layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Explanation label
        main_sizer.Add(self.explanation_label, 0, wx.ALL, 10)

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.btn_source, 0, wx.ALL, 10)
        button_sizer.Add(self.btn_dest, 0, wx.ALL, 10)
        # Add a Choice widget for compression options
        self.compression_choice = wx.Choice(self.panel, choices=COMPRESSION_OPTIONS)
        self.compression_choice.SetBackgroundColour(wx.Colour('navy'))
        self.compression_choice.SetForegroundColour(wx.Colour('white'))
        self.compression_choice.SetSelection(0)  # Set default selection to the first option
        font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.compression_choice.SetFont(font)

        # Sizer for the compression choice widget
        choice_sizer = wx.BoxSizer(wx.HORIZONTAL)
        choice_label = wx.StaticText(self.panel)
        choice_sizer.Add(choice_label, 0, wx.CENTER | wx.ALL, 5)
        choice_sizer.Add(self.compression_choice, 1, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(button_sizer, 0, wx.CENTER)
        main_sizer.Add(choice_sizer, 0, wx.CENTER)

        # Console output
        console_sizer = wx.BoxSizer(wx.VERTICAL)
        console_sizer.Add(self.console_output, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(console_sizer, 0, wx.EXPAND, 10)

        # Start button
        button_sizer_start_stop = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer_start_stop.Add(self.btn_start, 0, wx.ALL, 10)
        button_sizer_start_stop.Add(self.stop_button, 0, wx.ALL, 10)
        main_sizer.Add(button_sizer_start_stop, 0, wx.CENTER)

        # Load standard gif icon and loading animation gif
        self.github_icon_path = os.path.join(base_path, 'img', 'github_icon.gif')
        self.github_loading_path = os.path.join(base_path, 'img', 'busy_loading.gif')

        self.standard_animation = wx.adv.Animation(self.github_icon_path)
        self.loading_animation = wx.adv.Animation(self.github_loading_path)

        self.gif_ctrl = wx.adv.AnimationCtrl(self.panel, -1, self.standard_animation)
        self.gif_ctrl.Play()

        # Initially position the GIF control; will be updated in the on_resize method
        self.on_resize(None)  # Call once to set the initial position

        # Bind the gif control to the GitHub link click event
        self.gif_ctrl.Bind(wx.EVT_LEFT_DOWN, self.on_github_icon_click)

        # Set the main sizer for the panel
        self.panel.SetSizer(main_sizer)
        self.Centre()
        self.Show(True)

    def process_file(self, file_path, dest_dir, compression_option):
        if not self.is_supported_file(file_path):
            return
        dest_path = self.prepare_destination_path(file_path, dest_dir)
        initial_size, final_size = compress_image(dest_path, compression_option)
        new_name = get_new_filename(dest_path, compression_option)
        os.rename(dest_path, new_name)
        return initial_size, final_size, new_name

    def is_supported_file(self, file_path):
        supported_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff']
        return any(file_path.lower().endswith(ext) for ext in supported_extensions)

    def prepare_destination_path(self, src_path, dest_dir):
        rel_path = os.path.relpath(src_path, self.source_directory)
        dest_path = os.path.join(dest_dir, rel_path)
        self.create_destination_subdirectory(dest_path)
        shutil.copy2(src_path, dest_path)
        return dest_path

    def create_destination_subdirectory(self, dest_path):
        dest_subdir = os.path.dirname(dest_path)
        os.makedirs(dest_subdir, exist_ok=True)

    def process_directory(self, src_dir, dest_dir, compression_option, console_output):
        num_files_processed = 0
        total_saved_size = 0
        widths = [65, 20, 20, 20]  # Column widths
        header = ["File Name", "Original Size (MB)", "New Size (MB)", "Saved Size (MB)"]
        log_entries = [format_table_row(header, widths)]
        log_entries.append('-' * sum(widths))  # Separator line
        skipped_files = []  # List to keep track of skipped (unsupported) files

        for root, _, files in os.walk(src_dir):
            for file in files:
                # Check if stop was requested
                if self.stop_requested:
                    return
                src_path = os.path.join(root, file)
                result = self.process_file(src_path, dest_dir, compression_option)
                if result:
                    initial_size, final_size, new_name = result
                    saved_size = initial_size - final_size
                    total_saved_size += saved_size
                    num_files_processed += 1
                    # Parsing only the file name from new_name
                    file_name = os.path.basename(new_name)
                    log_entry = format_table_row(
                        [file_name, f"{bytes_to_mb(initial_size):.2f}", f"{bytes_to_mb(final_size):.2f}",
                         f"{bytes_to_mb(saved_size):.2f}"], widths)
                    log_entries.append(log_entry)
                    console_entry = format_table_row(
                        [file_name, f"Original Size: {bytes_to_mb(initial_size):.2f}MB",
                         f"Final Size: {bytes_to_mb(final_size):.2f}MB",
                         f"Saved: {bytes_to_mb(saved_size):.2f}MB"], widths)
                    wx.CallAfter(console_output.AppendText, console_entry + "\n")
                else:
                    skipped_files.append(file)
                # Check for stop again on end.
                if self.stop_requested:
                    return

        if skipped_files:
            skipped_msg = f"\n{len(skipped_files)} files were not processed (unsupported extensions):\n{', '.join(skipped_files)}"
            log_entries.append(skipped_msg)
            wx.CallAfter(console_output.AppendText, skipped_msg)
            wx.CallAfter(console_output.AppendText, '\n')

        wx.CallAfter(console_output.AppendText, '\nCompression ended\n')
        wx.CallAfter(console_output.AppendText, f"\n✅Successfully compressed {num_files_processed} images.\n")
        # Create log file
        log_file_path = os.path.join(dest_dir, "log.txt")
        with open(log_file_path, "w") as log_file:
            log_file.write(f"Processed {num_files_processed} files:\n")
            log_file.write('\n'.join(log_entries))
            log_file.write('\n')
            log_file.write(f"\nSuccessfully compressed {num_files_processed} images.")
            log_file.write(f"\nIn total, we saved {bytes_to_mb(total_saved_size):.2f} MB")

        return log_file_path

    def on_resize(self, event):
        """Reposition the GitHub GIF when the window size changes."""
        frame_width, frame_height = self.GetSize()
        if not hasattr(self, "last_frame_size") or abs(self.last_frame_size[0] - frame_width) > 10 or abs(
                self.last_frame_size[1] - frame_height) > 10:
            gif_width, gif_height = self.gif_ctrl.GetSize()
            margin = 55  # Margin from the bottom and right edges
            gif_position = (frame_width - gif_width - margin, frame_height - gif_height - margin)
            self.gif_ctrl.SetPosition(gif_position)
            self.last_frame_size = (frame_width, frame_height)

        if event:  # Check if the event exists to avoid errors on initial call
            self.update_background(event)  # Update the background image as well

    def set_gif_animation(self, mode):
        """Swap the animation based on the mode."""
        if mode == 'standard':
            self.gif_ctrl.SetAnimation(self.standard_animation)
        elif mode == 'loading':
            self.gif_ctrl.SetAnimation(self.loading_animation)
        self.gif_ctrl.Play()

    def on_paint(self, event):
        """Paint the background image."""
        # Create a device context (DC) used for drawing onto the widget
        dc = wx.PaintDC(self.panel)
        width, height = self.panel.GetSize()

        # Scale the image to cover the entire panel
        scaled_image = self.image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
        bmp = wx.Bitmap(scaled_image)

        # Draw the bitmap onto the panel
        dc.DrawBitmap(bmp, 0, 0, True)

    def on_github_icon_click(self, event):
        # Disable the GitHub icon temporarily
        self.gif_ctrl.Disable()

        github_url = "https://github.com/zenWai/CompressImages-python"
        webbrowser.open(github_url)

        # Clickable once every 5 seconds
        wx.CallLater(5000, self.gif_ctrl.Enable)

    class TextRedirector:
        """A helper class to redirect the stdout/stderr to the TextCtrl widget."""

        def __init__(self, widget):
            self.widget = widget

        def write(self, text):
            # Append text to the TextCtrl widget
            self.widget.AppendText(text)

        def flush(self):
            # Needed for file-like interface
            pass

    def update_background(self, event):
        size = self.GetSize()
        if not hasattr(self, "last_size") or self.last_size != size:
            # Resize the image
            image = wx.Image(self.image_file, wx.BITMAP_TYPE_ANY)
            image = image.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH)
            self.bmp = wx.Bitmap(image)
            self.last_size = size

        event.Skip()  # Ensure other event handlers get the resize event as well
        self.panel.Refresh()

    def on_select_source(self, event):
        dlg = wx.DirDialog(self, "Choose a source directory", "", wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.source_directory = dlg.GetPath()
            print(f"Selected Source Directory: {self.source_directory}")
            count_files_in_source(self.source_directory)
        dlg.Destroy()

    def on_select_destination(self, event):
        dlg = wx.DirDialog(self, "Choose a destination directory", "", wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.destination_directory = dlg.GetPath()
            print(f"Selected Destination Directory: {self.destination_directory}")
            count_files_in_destination(self.destination_directory)
        dlg.Destroy()

    def on_start_compression(self, event):
        # Check if source directory is not selected
        if not self.source_directory:
            wx.MessageBox('Missing source directory. Please select a source directory.',
                          'Warning', wx.OK | wx.ICON_WARNING)
            return

        # Check if destination directory is not selected
        if not self.destination_directory:
            wx.MessageBox('Missing destination directory. Please select a destination directory.',
                          'Warning', wx.OK | wx.ICON_WARNING)
            return

        # Check if source and destination directories are the same
        if self.source_directory == self.destination_directory:
            wx.MessageBox(
                'Source and Destination directories cannot be the same. Please select a different destination directory.',
                'Warning', wx.OK | wx.ICON_WARNING)
            return

        # Check for different disks (or partitions)
        if os.name == 'nt':  # For Windows
            if os.path.splitdrive(self.source_directory)[0] != os.path.splitdrive(self.destination_directory)[0]:
                wx.MessageBox(
                    'DETECTED: Source and Destination directories are on different Partition/Disk. App needs Source and Destination on same Partition/Disk',
                    'Warning', wx.OK | wx.ICON_WARNING)
                return
        else:  # For Unix-like systems (macOS, Linux)
            if os.path.ismount(self.source_directory) != os.path.ismount(self.destination_directory):
                wx.MessageBox(
                    'DETECTED: Source and Destination directories are on different Partition/Disk. App needs Source and Destination on same Partition/Disk',
                    'Warning', wx.OK | wx.ICON_WARNING)
                return

        # Check if the destination directory is a subdirectory of the source directory
        if os.path.commonpath([self.source_directory, self.destination_directory]) == os.path.normpath(
                self.source_directory):
            wx.MessageBox(
                'The destination directory cannot be a subdirectory of the source directory.\n -Try creating a new Empty Folder outside of the Source Directory.\n -Select that new Folder as your Destination Directory',
                'Warning', wx.OK | wx.ICON_WARNING)
            return

        # Check if the destination directory is not empty
        if os.listdir(self.destination_directory):
            wx.MessageBox(
                'The destination directory is not empty. Please select an empty directory or clear the contents of the selected directory before starting the compression.',
                'Warning', wx.OK | wx.ICON_WARNING)
            return

        # Proceed with disabling UI elements and starting the compression
        self.gif_ctrl.Disable()
        self.btn_source.Disable()
        self.btn_dest.Disable()
        self.btn_start.Disable()
        self.compression_choice.Disable()
        self.stop_button.Enable()
        self.stop_requested = False
        startWorker(self.compression_done, self.run_compression)

    # User request Stop Button
    def request_stop(self, event):
        print("\nStopping... Please wait. When buttons are enabled the stop process is finished.\n")
        self.stop_button.Disable()
        self.stop_requested = True

    def enable_controls(self):
        self.btn_source.Enable()
        self.btn_dest.Enable()
        self.btn_start.Enable()
        self.compression_choice.Enable()
        self.stop_button.Disable()  # Disable the stop button since processing is done

    def show_completion_dialog(self, log_file_path):
        dlg = CustomDialog(self, title="Compression Completed", log_file_path=log_file_path,
                           source_directory=self.source_directory,
                           destination_directory=self.destination_directory)
        dlg.ShowModal()
        dlg.Destroy()

    def run_compression(self):
        compression_option = self.compression_choice.GetString(self.compression_choice.GetSelection())
        wx.CallAfter(self.console_output.AppendText, f"Starting the compression with option: {compression_option}!\n")
        # Set the GIF to loading mode
        wx.CallAfter(self.set_gif_animation, 'loading')
        # Processing images
        log_file_path = self.process_directory(self.source_directory, self.destination_directory, compression_option,
                                               self.console_output)
        return log_file_path if log_file_path else "STOPPED"

    def compression_done(self, result):
        """Handle the results of the compression thread."""
        result_value = result.get()
        if result_value:
            # If compression was stopped prematurely
            if result_value == "STOPPED":
                print("Compression was stopped by the user. Compressed files might "
                      "be corrupted due to interruption.\n\n")
            else:
                # Show the custom dialog
                self.set_gif_animation('standard')
                self.show_completion_dialog(result_value)

            # Completed, set the GIF back to standard mode
            self.set_gif_animation('standard')
            # Re-enable the buttons and the compression option
            self.enable_controls()
            # Re-enable the GitHub icon clickable action
            self.gif_ctrl.Enable()


app = wx.App()
CompressorApp(None, title='SmartImageShrink')
app.MainLoop()

if __name__ == "__main__":
    # The main application logic is already initialized above. Nothing more to do here.
    pass
