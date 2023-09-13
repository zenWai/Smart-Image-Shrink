import os
import shutil
from PIL import Image
import wx
import sys

Image.MAX_IMAGE_PIXELS = None


def bytes_to_mb(size_in_bytes):
    return size_in_bytes / (1024 * 1024)


def compress_image(img_path):
    initial_size = os.path.getsize(img_path)
    with Image.open(img_path) as img:
        width, height = img.size

        # Resize only if width exceeds 1080
        if width > 1080:
            aspect_ratio = height / width
            new_width = 1080
            new_height = int(aspect_ratio * new_width)

            # If the image is a .tif file, handle it differently
            if img_path.lower().endswith('.tif'):
                try:
                    img = img.resize((new_width, new_height))
                    img.save(img_path)
                except Exception as e:
                    print(f"Error processing {img_path}: {e}")
                    return initial_size, initial_size
            else:
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img.save(img_path, quality=100)

    final_size = os.path.getsize(img_path)
    return initial_size, final_size


def process_directory(src_dir, dest_dir):
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
                initial_size, final_size = compress_image(img_path)

                if initial_size > final_size:
                    num_files_compressed += 1

                saved_size = initial_size - final_size
                total_saved_size += saved_size
                num_files_processed += 1

                base, ext = os.path.splitext(img_path)
                new_name = base + '_compressed' + ext
                os.rename(img_path, new_name)

                # Logging info for each file
                log_entry = f"{new_name} with {bytes_to_mb(initial_size):.2f} MB now with {bytes_to_mb(final_size):.2f} MB, saved {bytes_to_mb(saved_size):.2f} MB"
                log_entries.append(log_entry)
                print(log_entry)
                wx.Yield()  # Process any pending events, allowing the GUI to update

    with open("log.txt", "w") as log_file:
        log_file.write(f"Processed {num_files_processed} files:\n")
        log_file.write('\n'.join(log_entries))
        log_file.write(f"\nSuccessfully compressed {num_files_compressed} images.")
        log_file.write(f"\n{num_files_processed - num_files_compressed} images were not compressed.")
        log_file.write(f"\nIn total, we saved {bytes_to_mb(total_saved_size):.2f} MB")


class CompressorApp(wx.Frame):
    def __init__(self, parent, title):
        super(CompressorApp, self).__init__(parent, title=title, size=(1000, 500))

        self.source_directory = None
        self.destination_directory = None

        # Create a panel in the frame
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
        explanation = ("This script compresses all images in the selected source directory and saves them \n"
                       "in the selected destination directory. To use:\n"
                       "1. Select the source directory.\n"
                       "2. Select the destination directory.\n"
                       "3. Click 'Start Compression'.")
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
        dlg.Destroy()

    def on_select_destination(self, event):
        dlg = wx.DirDialog(self, "Choose a destination directory", "", wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.destination_directory = dlg.GetPath()
            print(f"Selected Destination Directory: {self.destination_directory}")
        dlg.Destroy()

    def on_start_compression(self, event):
        if self.source_directory and self.destination_directory:
            print("Starting the compression!")
            wx.Yield()
            process_directory(self.source_directory, self.destination_directory)
        else:
            wx.MessageBox('Please select both source and destination directories first.', 'Info',
                          wx.OK | wx.ICON_INFORMATION)


app = wx.App()
CompressorApp(None, title='Meow eat images')
app.MainLoop()

if __name__ == "__main__":
    # The main application logic is already initialized above. Nothing more to do here.
    pass
