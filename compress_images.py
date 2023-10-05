import os
import shutil
import sys
import webbrowser

import wx
import wx.adv
from PIL import Image
from wx.lib.delayedresult import startWorker

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


def compress_image(img_path, compression_option):
    initial_size = os.path.getsize(img_path)
    try:
        with Image.open(img_path) as img:
            width, height = img.size

            # If compression option involves resizing, calculate new dimensions
            if 'Compress Size' in compression_option:
                factor = int(compression_option.split(' ')[-1][1:])
                new_width = int(width / factor)
                aspect_ratio = height / width
                new_height = int(aspect_ratio * new_width)
                # Check the image mode and decide the resampling method
                if img.mode in ["L", "RGB", "RGBA"]:
                    resampling_method = Image.Resampling.LANCZOS
                else:
                    resampling_method = Image.NEAREST

                img = img.resize((new_width, new_height), resampling_method)

            # Apply appropriate compression
            if img_path.lower().endswith('.png'):
                img.save(img_path, optimize=True)
            elif img_path.lower().endswith(('.jpg', '.jpeg')):
                img.save(img_path, quality=95)
            elif img_path.lower().endswith(('.tif', '.tiff')):
                img.save(img_path, compression='tiff_lzw')
            else:
                print("")
                print(f"{img_path} has an unsupported file extension. Skipping...")
                print("")
                return initial_size, initial_size
    except Exception as e:
        print("")
        print(f"Error processing {img_path}: {e}")
        return initial_size, initial_size

    final_size = os.path.getsize(img_path)
    return initial_size, final_size


def get_new_filename(img_path, compression_option):
    base, ext = os.path.splitext(img_path)
    if compression_option == 'Compress with No Data Loss':
        new_name = base + '_compressed' + ext
    elif 'Compress Size' in compression_option:
        factor = compression_option.split(' ')[-1]
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
        print("Destination Directory is empty, that is perfect!")
        print("")
    else:
        print(f"Total Files in Destination Directory: {total_files}")
        print("Warning: It is recommended that the destination directory should be empty.")
        print("Warning: Existing files in the destination will be lost.")
        print("")


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
        open_src_btn = wx.Button(self, label="Open Source Directory")
        open_src_btn.Bind(wx.EVT_BUTTON, self.open_source_directory)

        # Button to open Destination Directory
        open_dest_btn = wx.Button(self, label="Open Destination Directory")
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

    def open_log_file(self, event):
        webbrowser.open(self.log_file_path)

    def open_source_directory(self, event):
        webbrowser.open(self.source_directory)

    def open_destination_directory(self, event):
        webbrowser.open(self.destination_directory)


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
            # If bundled executable, specify correct path to the image
            base_path = sys._MEIPASS
        else:
            # If running as a script, use the default path
            base_path = os.path.abspath(".")

        # Load the image
        self.image_file = os.path.join(base_path, 'background.jpg')
        self.image = wx.Image(self.image_file, wx.BITMAP_TYPE_ANY)

        # Bind the EVT_PAINT event of the panel to the on_paint method
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)

        # Add an explanation label at the top
        explanation = (
            "This tool compresses images from a chosen Source Directory and saves them "
            "in a Destination Directory.\n\n"
            "1. Choose the Source Directory.\n"
            "2. Specify the Destination Directory.\n"
            "3. Pick a Compression Option. (Default: 'Compress with No Data Loss').\n"
            "4. Click 'Start Compression'.\n\n"
            "Compression Options:\n"
            "   - 'Compress with No Data Loss' Compress with top-tier quality retention.\n"
            "   - 'Compress Size x2' Halves the image dimensions, maintaining aspect ratio.\nThe reduction in file size is notable, and the quality remains largely intact.\n\n"
            "   - As you increase the compression size (x4, x8, x16), the image size decreases proportionally.\n\nQuality loss becomes more noticeable, especially with 'Compress Size x16'."
        )
        self.explanation_label = wx.StaticText(self.panel, label=explanation)

        # Add buttons to the panel
        self.btn_source = wx.Button(self.panel, label='Select Source Directory', pos=(50, 150))
        self.btn_dest = wx.Button(self.panel, label='Select Destination Directory', pos=(50, 200))
        self.btn_start = wx.Button(self.panel, label='Start Compression', pos=(500, 360))
        self.stop_button = wx.Button(self.panel, label='Stop Compression', pos=(650, 360))
        self.stop_button.Disable()

        # Add a TextCtrl for console output
        self.console_output = wx.TextCtrl(self.panel, size=(0, 150),
                                          style=wx.TE_MULTILINE | wx.TE_READONLY)

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
        self.compression_choice.SetSelection(0)  # Set default selection to the first option
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
        main_sizer.Add(self.btn_start, 0, wx.CENTER | wx.BOTTOM, 10)
        # Stop button
        main_sizer.Add(self.stop_button, 0, wx.CENTER | wx.BOTTOM, 10)

        # Load standard gif icon and loading animation gif
        self.github_icon_path = os.path.join(base_path, 'github_icon.gif')
        self.github_loading_path = os.path.join(base_path, 'busy_loading.gif')

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

    def copy_tree(self, src, dst):
        if not os.path.exists(dst):
            os.makedirs(dst)

        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                self.copy_tree(s, d)
            else:
                shutil.copy2(s, d)  # copy2 preserves file metadata

    def process_directory(self, src_dir, dest_dir, compression_option, console_output):
        self.copy_tree(src_dir, dest_dir)

        num_files_processed = 0
        num_files_compressed = 0
        total_saved_size = 0
        log_entries = []

        for root, _, files in os.walk(dest_dir):
            for file in files:
                # Check if stop was requested
                if self.stop_requested:
                    return

                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
                    img_path = os.path.join(root, file)
                    initial_size, final_size = compress_image(img_path, compression_option)

                    if initial_size > final_size:
                        num_files_compressed += 1

                    saved_size = initial_size - final_size
                    total_saved_size += saved_size
                    num_files_processed += 1

                    new_name = get_new_filename(img_path, compression_option)
                    os.rename(img_path, new_name)

                    # Logging info for each file
                    log_entry = f"{new_name} with {bytes_to_mb(initial_size):.2f} MB now with {bytes_to_mb(final_size):.2f} MB, saved {bytes_to_mb(saved_size):.2f} MB"
                    log_entries.append(log_entry)
                    wx.CallAfter(console_output.AppendText, log_entry + "\n")
                    # Check for stop again on end.
                    if self.stop_requested:
                        return

        # Create log file
        log_file_path = os.path.join(dest_dir, "log.txt")
        with open(log_file_path, "w") as log_file:
            log_file.write(f"Processed {num_files_processed} files:\n")
            log_file.write('\n'.join(log_entries))
            log_file.write("\n")
            log_file.write(f"\nSuccessfully compressed {num_files_compressed} images.")
            log_file.write(f"\n{num_files_processed - num_files_compressed} images were not compressed.")
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
        if self.source_directory and self.destination_directory:
            if self.source_directory == self.destination_directory:
                wx.MessageBox('Source and Destination directories cannot be the same. Please select a different '
                              'destination directory.', 'Info', wx.OK | wx.ICON_INFORMATION)
            elif os.listdir(self.destination_directory):  # Check if the directory is not empty
                wx.MessageBox('The destination directory is not empty. Please select an empty directory or clear the '
                              'contents of the selected directory before starting the compression.',
                              'Warning', wx.OK | wx.ICON_WARNING)
            else:
                # Disable GitHub icon clickable action
                self.gif_ctrl.Disable()

                # Disable the buttons and the compression option
                self.btn_source.Disable()
                self.btn_dest.Disable()
                self.btn_start.Disable()
                self.compression_choice.Disable()
                self.stop_button.Enable()
                self.stop_requested = False

                # Create a new thread for the compression process
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
        return log_file_path

    def compression_done(self, result):
        """Handle the results of the compression thread."""
        if result.get():
            # If compression was stopped prematurely
            if self.stop_requested:
                self.console_output.AppendText("Compression was stopped by the user. Compressed files might "
                                               "be corrupted due to interruption.\n\n")
            else:
                # Show the custom dialog
                self.show_completion_dialog(result.get())

            # Completed, set the GIF back to standard mode
            self.set_gif_animation('standard')
            # Re-enable the buttons and the compression option
            self.enable_controls()
            # Re-enable the GitHub icon clickable action
            self.gif_ctrl.Enable()


app = wx.App()
CompressorApp(None, title='Meow eat images')
app.MainLoop()

if __name__ == "__main__":
    # The main application logic is already initialized above. Nothing more to do here.
    pass
