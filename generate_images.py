#!/usr/bin/env python3
"""
Generate placeholder images for hotel rooms
"""
import os

def create_placeholder_svg(filename, title, color):
    """Create an SVG placeholder image"""
    svg_content = f'''<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad{filename}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{color};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{color};stop-opacity:0.7" />
    </linearGradient>
  </defs>
  <rect width="800" height="600" fill="url(#grad{filename})"/>
  <text x="50%" y="50%" font-family="Arial, sans-serif" font-size="48" fill="white" 
        text-anchor="middle" dominant-baseline="middle" font-weight="bold">{title}</text>
  <text x="50%" y="60%" font-family="Arial, sans-serif" font-size="24" fill="white" 
        text-anchor="middle" dominant-baseline="middle" opacity="0.8">Hotel Luxe</text>
</svg>'''
    return svg_content

# Create images directory
os.makedirs('static/images', exist_ok=True)

# Generate room images
rooms = [
    ('deluxe-room.jpg', 'Deluxe Room', '#8B7355'),
    ('suite-room.jpg', 'Suite Room', '#C9A962'),
    ('standard-room.jpg', 'Standard Room', '#6B8E9E')
]

for filename, title, color in rooms:
    svg_content = create_placeholder_svg(filename, title, color)
    with open(f'static/images/{filename.replace(".jpg", ".svg")}', 'w') as f:
        f.write(svg_content)
    print(f'Created {filename}')

print('All placeholder images created successfully!')