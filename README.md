# SmartImageProcessor
SmartImageProcessor Application offers an efficient solution for compressing images while meticulously preserving their quality, metadata and data integrity.

It's designed to be both user-friendly and powerful, employing state-of-the-art technologies to ensure optimal results of compression user have options that range from quality retention to agressive reducing size.

Supports .tif .tiff .jpg .jpeg .png and high quality bit-depth 32-16.

# 

![Gif use-case of SmartImageProcessor](https://github.com/zenWai/CompressImages-python/assets/124523559/1b25040a-1420-4295-b2c1-63bbe07b1bd4)


### Running on macOS:
1. [Download the macOS Zip from the releases section.](https://github.com/zenWai/CompressImages-python/releases/download/v0.3-alpha/Compress_Images_v0.3_MacOS.zip)
2. Run the Application

### Running on Windows:
1. [Download the Windows Zip from the releases section.](https://github.com/zenWai/CompressImages-python/releases/download/v0.3-alpha/Compress_Images_v0.3_Windows.zip)
2. Run the Application

### Open the application.
1. Select the directory containing the images you want to compress.
2. Select where the compressed images will be saved.
3. Choose a Compression Method
4. 'Start Compression'. The App will process the images and provide feedback in the console window.

# Test Case Original vs Compressed

#### Size of 1,56 GB vs 899MB
![SmartImageProcessor Test Case of Sagittal cut and image with Size 1,56 GB vs 899MB](https://github.com/zenWai/CompressImages-python/assets/124523559/0e720eb4-6dd1-41b4-aaac-3d40227d4ff6)
![SmartImageProcessor Test Case of Sagittal cut zoomed in and image with Size 1,56 GB vs 899MB](https://github.com/zenWai/CompressImages-python/assets/124523559/59560038-5217-46c4-984e-982a441ee47d)

#### Size of 1,56GB vs 3,6MB
![SmartImageProcessor Test Case of Sagittal cut and image with Size 1,56 GB vs 3,6MB](https://github.com/zenWai/CompressImages-python/assets/124523559/9ac4af1e-f8ec-4b79-b171-dfa1a9df7854)


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
