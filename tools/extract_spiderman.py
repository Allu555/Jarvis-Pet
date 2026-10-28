import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path
import scipy.ndimage as ndi

SRC_IMG = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\spiderman_sources\spiderman_raw.jpg")
DEST_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\spiderman_sources")
OUT_FILE = DEST_DIR / "spiderman_cutout.png"

def extract_spiderman():
    img = Image.open(SRC_IMG).convert("RGB")
    w, h = img.size
    print(f"Original image size: {w}x{h}")
    
    arr = np.array(img, dtype=np.float32)
    print("Corners:")
    print("Top-left (0,0):", arr[0, 0])
    print("Top-right (0,-1):", arr[0, -1])
    print("Bottom-left (-1,0):", arr[-1, 0])
    print("Bottom-right (-1,-1):", arr[-1, -1])
    
    # Check background pixels
    # In JPEG images, white background might have subtle compression artifacts (e.g. 245-255 or slightly off-white)
    # The character itself is red, blue, black outlines, and white eyes.
    # Background is anywhere outside the outer black boundary of Spider-Man and the web.
    
    # Flood fill background starting from edges
    # Any pixel with brightness > 220 and saturation < 30 is likely background
    max_c = np.maximum.reduce([arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]])
    min_c = np.minimum.reduce([arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]])
    diff = max_c - min_c
    brightness = (arr[:, :, 0] + arr[:, :, 1] + arr[:, :, 2]) / 3.0
    
    is_white_ish = (brightness > 230) & (diff < 30)
    print(f"White-ish pixels count: {np.sum(is_white_ish)} / {w * h} ({np.sum(is_white_ish)/(w*h)*100:.1f}%)")
    
    # Label white-ish regions
    labeled, num_features = ndi.label(is_white_ish)
    print(f"Num white-ish features: {num_features}")
    
    # Check which features touch borders
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
    
    border_labels = np.unique(labeled[border_mask])
    border_labels = border_labels[border_labels > 0]
    print(f"Border touching labels: {border_labels}")
    
    bg_mask = np.isin(labeled, border_labels)
    
    # Also check if there are enclosed cavities in the web or between arm and head or legs
    # For instance, under the right arm hanging web
    # Let's check other components and their centers
    for lbl in range(1, num_features + 1):
        if lbl not in border_labels:
            m = labeled == lbl
            cnt = np.sum(m)
            cy, cx = ndi.center_of_mass(m)
            # Eyes are around y in [0.25*h, 0.55*h], x in [0.25*w, 0.65*w]
            print(f"Internal white region {lbl}: count={cnt}, center=({cx:.1f}, {cy:.1f})")
            # If region is outside the character body (e.g. between web strings on right side), we can include it in bg_mask
            if cx > 0.65 * w or cy > 0.85 * h or cy < 0.15 * h or cx < 0.15 * w:
                print(f" -> Treating component {lbl} as background cavity")
                bg_mask |= m

    # Smooth the background mask
    # Clean isolated noise
    bg_mask = ndi.binary_closing(bg_mask, structure=np.ones((3, 3)))
    
    # Foreground is ~bg_mask
    fg_mask = ~bg_mask
    
    # Distance transform for anti-aliasing
    dist_in = ndi.distance_transform_edt(fg_mask)
    dist_out = ndi.distance_transform_edt(bg_mask)
    
    alpha = np.zeros((h, w), dtype=np.float32)
    alpha[fg_mask] = 255.0
    
    # Soft edge transition 1.5 pixels
    edge_blur = (dist_out < 1.5) & bg_mask
    alpha[edge_blur] = 255.0 * (1.0 - dist_out[edge_blur] / 1.5)
    
    # Also slightly feather inside border to remove white halo
    halo_edge = (dist_in < 1.2) & fg_mask
    alpha[halo_edge] = np.minimum(alpha[halo_edge], 255.0 * (dist_in[halo_edge] / 1.2))
    
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    
    rgba = Image.fromarray(np.dstack([arr.astype(np.uint8), alpha]), mode="RGBA")
    
    # Auto crop to bounding box
    bbox = rgba.getbbox()
    print("Bbox:", bbox)
    if bbox:
        cropped = rgba.crop(bbox)
    else:
        cropped = rgba
        
    cropped.save(OUT_FILE, "PNG")
    print(f"Saved Spider-Man cutout to {OUT_FILE} (size: {cropped.size})")

if __name__ == "__main__":
    extract_spiderman()
