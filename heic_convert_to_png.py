import os
import webbrowser

from PIL import Image
import pillow_heif

# path='''C:/Users/kanishkmalik/Downloads/Shubham Marriage''
path = '''C:/Users/kanishkmalik/Downloads/Friends'''

print ("Program Started")

# webbrowser.open(path)   

folderContent = os.listdir(path)
print (folderContent)
for file in folderContent:
    if file.upper().endswith(".HEIC"):
        fullPath = f"{path}/{file}"
        # print (fullPath)
        fileNameSplit = file.split(".")
        # print (fileNameSplit[0])
        fileNamePrefix = fileNameSplit[0]
        heif_file = pillow_heif.read_heif(fullPath)
        # print (heif_file.mode)
        # print (heif_file.size)
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
        )

        print (image.format)
        # img=image.resize((160,300), quality=95)
        # img.save(f"{path}/{fileNamePrefix}.png", format("png"))

        width, height = image.size
        # print (width, height)
        TARGET_WIDTH = 2000
        coefficient = width / TARGET_WIDTH
        new_height = height / coefficient
        # print (TARGET_WIDTH, new_height)
        # TARGET_WIDTH = 1020
        # new_height = 720
        optimalSizeImage = image.resize((int(TARGET_WIDTH),int(new_height)),Image.LANCZOS)
        optimalSizeImage.save(f"{path}/{fileNamePrefix}.jpeg", format("jpeg"),quality=50)
        # os.remove(fullPath)
        print (f"{fullPath} is converted to png")
        # break

print ("Program Ended")