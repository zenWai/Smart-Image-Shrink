import os
import shutil
from PIL import Image
import wx
import sys
import subprocess

Image.MAX_IMAGE_PIXELS = None

COMPRESSION_OPTIONS = [
    'Compress with No Data Loss',
    'Compress Size x2',
    'Compress Size x4',
    'Compress Size x8',
    'Compress Size x16',
]


def bytes_to_mb(size_in_bytes):
    return size_in_bytes / (1024 * 1024)


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


def process_directory(src_dir, dest_dir, compression_option):
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.copytree(src_dir, dest_dir)

    num_files_processed = 0
    num_files_compressed = 0
    total_saved_size = 0
    log_entries = []

    for root, _, files in os.walk(dest_dir):
        for file in files:
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
                print(log_entry)
                wx.Yield()  # Process any pending events, allowing the GUI to update

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
        if sys.platform == 'win32':
            os.startfile(self.log_file_path)
        elif sys.platform == 'darwin':
            subprocess.call(['open', self.log_file_path])
        else:
            subprocess.call(['xdg-open', self.log_file_path])

    def open_source_directory(self, event):
        self.open_directory(self.source_directory)

    def open_destination_directory(self, event):
        self.open_directory(self.destination_directory)

    def open_directory(self, directory_path):
        if sys.platform == 'win32':
            os.startfile(directory_path)
        elif sys.platform == 'darwin':
            subprocess.call(['open', directory_path])
        else:
            subprocess.call(['xdg-open', directory_path])


class CompressorApp(wx.Frame):
    def __init__(self, parent, title):
        super(CompressorApp, self).__init__(parent, title=title, size=(1300, 800))

        self.source_directory = None
        self.destination_directory = None
        self.panel = wx.Panel(self)

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
            "This script compresses all images in the selected source directory and saves them "
            "in the selected destination directory. To use:\n"
            "1. Select the source directory.\n"
            "2. Select the destination directory.\n"
            "3. Select a compression option. (Default is 'Compress with No Data Loss').\n"
            "4. Click 'Start Compression'.\n\n"
            "Note on compression options:\n"
            "- 'Compress with No Data Loss' retains the original image size but tries to reduce the file size without quality loss.\n"
            "- 'Compress Size x2' resizes the image to half its original dimensions while maintaining the aspect ratio. This usually results in a significant file size reduction with little to no perceptible quality loss.\n"
            "- As you increase the compression size (x4, x8, x16), the image size decreases proportionally. Quality loss becomes more noticeable, especially with 'Compress Size x16'."
        )
        self.explanation_label = wx.StaticText(self.panel, label=explanation)

        # Add buttons to the panel
        self.btn_source = wx.Button(self.panel, label='Select Source Directory', pos=(50, 150))
        self.btn_dest = wx.Button(self.panel, label='Select Destination Directory', pos=(50, 200))
        self.btn_start = wx.Button(self.panel, label='Start Compression', pos=(500, 360))

        # Add a TextCtrl for console output
        self.console_output = wx.TextCtrl(self.panel, pos=(500, 100), size=(200, 150),
                                          style=wx.TE_MULTILINE | wx.TE_READONLY)

        # Redirect stdout and stderr to the TextCtrl widget
        sys.stdout = self.TextRedirector(self.console_output)
        sys.stderr = self.TextRedirector(self.console_output)

        # Bind the buttons to their respective event handlers
        self.Bind(wx.EVT_BUTTON, self.on_select_source, self.btn_source)
        self.Bind(wx.EVT_BUTTON, self.on_select_destination, self.btn_dest)
        self.Bind(wx.EVT_BUTTON, self.on_start_compression, self.btn_start)

        # Bind the resize event to the update background function
        self.Bind(wx.EVT_SIZE, self.update_background)

        # Create a BoxSizer for vertical layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Explanation label
        main_sizer.Add(self.explanation_label, 0, wx.ALL, 10)

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.btn_source, 0, wx.ALL, 10)
        button_sizer.Add(self.btn_dest, 0, wx.ALL, 10)

        main_sizer.Add(button_sizer, 0, wx.CENTER)

        # Console output with a maximum height of what is set console_output
        console_sizer = wx.BoxSizer(wx.VERTICAL)
        console_sizer.Add(self.console_output, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(console_sizer, 0, wx.EXPAND, 10)

        # Start button
        main_sizer.Add(self.btn_start, 0, wx.CENTER | wx.BOTTOM, 10)

        # Add a Choice widget for compression options
        self.compression_choice = wx.Choice(self.panel, choices=COMPRESSION_OPTIONS, pos=(500, 50))
        self.compression_choice.SetSelection(0)  # Set default selection to the first option

        # Set the main sizer for the panel
        self.panel.SetSizer(main_sizer)
        self.Centre()
        self.Show(True)

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

        # Resize the image
        image = wx.Image(self.image_file, wx.BITMAP_TYPE_ANY)
        image = image.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH)
        self.bmp = wx.Bitmap(image)

        event.Skip()  # Ensure other event handlers get the resize event as well

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
            # starting compression
            else:
                # Get selected compression option
                compression_option = self.compression_choice.GetString(self.compression_choice.GetSelection())
                print(f"Starting the compression with option: {compression_option}!")
                wx.Yield()
                log_file_path = process_directory(self.source_directory, self.destination_directory, compression_option)

                # Custom Message Box on completion
                dlg = CustomDialog(self, title="Compression Completed", log_file_path=log_file_path,
                                   source_directory=self.source_directory,
                                   destination_directory=self.destination_directory)
                dlg.ShowModal()
                dlg.Destroy()
        else:
            wx.MessageBox('Please select both source and destination directories first.', 'Info',
                          wx.OK | wx.ICON_INFORMATION)


app = wx.App()
CompressorApp(None, title='Meow eat images')
app.MainLoop()

if __name__ == "__main__":
    # The main application logic is already initialized above. Nothing more to do here.
    pass
