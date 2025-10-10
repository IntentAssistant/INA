from PIL import Image, ImageDraw, ImageFont
import os

# Create build_assets directory if it doesn't exist
os.makedirs("build_assets", exist_ok=True)

# Create a background image for the DMG
width, height = 640, 280
background_color = (32, 32, 32)  # Dark gray background

# Create the image
img = Image.new("RGBA", (width, height), background_color)
draw = ImageDraw.Draw(img)

# Add text
try:
    # Try to load a font
    font = ImageFont.truetype("Arial.ttf", 20)
except IOError:
    # If the font is not available, use the default font
    font = ImageFont.load_default()

# Draw text
text = "Drag INA to Applications folder"
text_width = draw.textlength(text, font=font)
text_position = ((width - text_width) // 2, 30)
draw.text(text_position, text, fill=(255, 255, 255), font=font)

# Add arrows
arrow_color = (0, 122, 255)  # Blue color
arrow_width = 4
arrow_start = (180, 120)
arrow_end = (460, 120)

# Draw arrow line
draw.line([arrow_start, arrow_end], fill=arrow_color, width=arrow_width)

# Draw arrow head
arrow_head_length = 15
arrow_head_width = 10
draw.polygon(
    [
        (arrow_end[0], arrow_end[1]),
        (arrow_end[0] - arrow_head_length, arrow_end[1] - arrow_head_width // 2),
        (arrow_end[0] - arrow_head_length, arrow_end[1] + arrow_head_width // 2),
    ],
    fill=arrow_color,
)

# Save the image
img.save("build_assets/dmg_background.png")
print("DMG background image created at build_assets/dmg_background.png")
