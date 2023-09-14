# Image Compressor
This script provides a GUI for compressing images in a selected source directory and saving them in a specified destination directory. The image resizing threshold is set at a width of 1080 pixels with max quality and will mantain the aspect ratio. The script supports .png, .jpg, .jpeg, .tif, and .tiff file formats.

| ![logTXT of compressed images](https://github.com/zenWai/CompressImages-python/assets/124523559/f0f99b5a-1831-4155-b5a4-4477075bf4d4) | ![Compress images preview image](https://github.com/zenWai/CompressImages-python/assets/124523559/d49f36f4-82dc-4c5e-9232-a2553fe97ca7) |
|:---:|:---:|

# Using the Application
This script has been bundled into standalone executables for both macOS(arm64 only) and Windows. This means you can run the application on these platforms without needing to have Python or the required packages installed.

### Running on macOS:
1. [Download the macOS executable from the releases section.](https://github.com/zenWai/CompressImages-python/releases/download/v0.1-alpha/compress_images_macOS_arm64)
2. Right-click(options macOS) on the downloaded file and click open.
3. Open again on prompt.

### Running on Windows:
1. [Download the Windows executable from the releases section.](https://github.com/zenWai/CompressImages-python/releases/download/v0.1-alpha/compress_images_windows.exe)
2. Double-click on the downloaded file to run the application.

### Open the application.
1. Click on 'Select Source Directory' to choose the directory containing the images you want to compress.
2. Click on 'Select Destination Directory' to choose where the compressed images will be saved.
3. Click 'Start Compression'. The script will process the images and provide feedback in the console window.

# Run Locally
Setup Python 3.x

### Clone the repository:
```
git clone https://github.com/zenWai/CompressImages-python
```

### Install the required packages:
```
pip install -r requirements.txt
```
### Run the script using:
```
python3 compress_images.py
```
