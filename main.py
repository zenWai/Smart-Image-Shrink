from multiprocessing import freeze_support

from gui import CompressorApp
import wx.adv
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    app = wx.App()
    CompressorApp(None, title='SmartImageShrink')
    app.MainLoop()


if __name__ == "__main__":
    freeze_support()
    main()
