import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import scipy.ndimage as ndi
import math

FRAME_SIZE = 192

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC
except AttributeError:
    RESAMPLE_LANCZOS = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", Image.BICUBIC))
    RESAMPLE_BICUBIC = Image.BICUBIC

def get_clean_cutout(img_path, target_h=150):
    img = Image.open(img_path).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    w, h = img.size
    scale = target_h / h
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return img.resize((nw, nh), RESAMPLE_LANCZOS)

def create_articulated_walk_cycle(base_img, is_venom=False):
    """
    Creates a 6-phase walk cycle matching the reference walk cycle:
    1. Contact 1: Lead leg forward heel-strike, trail leg back push-off, opposite arm swings.
    2. Down 1: Lead leg absorbs weight (knee bent, foot flat), torso dips (dy=+6), trail leg flexing.
    3. Pass 1: Stance leg straight, torso at apex (dy=-6), swing leg high knee lift passing through.
    4. Contact 2: Opposite contact pose.
    5. Down 2: Opposite down/recoil pose.
    6. Pass 2: Opposite pass/high pose.
    """
    w, h = base_img.size
    arr = np.array(base_img, dtype=np.float32)
    
    # 6 Phase parameter definitions:
    # (torso_dy, torso_pitch_deg, near_hip_angle, near_knee_bend, near_foot_angle, 
    #  far_hip_angle, far_knee_bend, far_foot_angle, near_arm_rot, far_arm_rot, bounce_scale_y)
    if is_venom:
        # Venom has a predatory, powerful stride with longer reach and flexed claws
        phases = [
            # Phase 1: Contact 1
            (0, 3.5,   22, 10,  12,   -24, 15, -15,  -26,  28, 1.00),
            # Phase 2: Down 1 (recoil squash)
            (5, 5.0,   12, -22,  0,   -10, 38, -10,  -12,  14, 0.96),
            # Phase 3: Pass 1 (apex stretch)
            (-6, -1.0,  0,   2,  0,    18, -48,  20,    6,  -8, 1.04),
            # Phase 4: Contact 2
            (0, 3.5,  -24, 15, -15,    22, 10,  12,   28, -26, 1.00),
            # Phase 5: Down 2 (recoil squash)
            (5, 5.0,  -10, 38, -10,    12, -22,  0,   14, -12, 0.96),
            # Phase 6: Pass 2 (apex stretch)
            (-6, -1.0, 18, -48,  20,    0,   2,  0,   -8,   6, 1.04),
        ]
    else:
        # Goku has an energetic, buoyant anime hero stride
        phases = [
            # Phase 1: Contact 1
            (0, 2.0,   20,  8,  14,   -20, 12, -12,  -24,  24, 1.00),
            # Phase 2: Down 1 (recoil squash)
            (6, 4.0,   10, -18,  0,    -8, 32,  -8,  -10,  10, 0.96),
            # Phase 3: Pass 1 (apex stretch)
            (-6, -1.5,  0,   0,  0,    16, -42,  18,    5,  -6, 1.04),
            # Phase 4: Contact 2
            (0, 2.0,  -20, 12, -12,    20,  8,  14,   24, -24, 1.00),
            # Phase 5: Down 2 (recoil squash)
            (6, 4.0,   -8, 32,  -8,    10, -18,  0,   10, -10, 0.96),
            # Phase 6: Pass 2 (apex stretch)
            (-6, -1.5, 16, -42,  18,    0,   0,  0,   -6,   5, 1.04),
        ]

    frames_right = []
    
    # Anatomical boundaries
    hip_y = int(h * 0.52)
    knee_y = int(h * 0.74)
    shoulder_y = int(h * 0.35)
    elbow_y = int(h * 0.48)
    head_y = int(h * 0.38)
    
    # Separate body layers:
    # Torso/Head, Left Leg, Right Leg, Left Arm, Right Arm
    
    for (torso_dy, pitch, n_hip, n_knee, n_foot, f_hip, f_knee, f_foot, n_arm, f_arm, sy) in phases:
        # Create coordinate map for non-linear mesh deformation
        # We construct a full transformed image
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        
        # We deform base_img using high quality piecewise grid transformation
        # Grid coordinates:
        y_grid, x_grid = np.indices((h, w), dtype=np.float32)
        
        map_y = np.copy(y_grid)
        map_x = np.copy(x_grid)
        
        # Center of character
        cx = w * 0.50
        
        # 1. Torso squash/stretch & vertical shift
        for y in range(h):
            rel_y = y / h
            # Lower body stays connected to feet, upper body scales
            if y < hip_y:
                map_y[y, :] = y / sy
                
        # 2. Left Leg (Far side / back leg: x < cx) vs Right Leg (Near side / front leg: x >= cx)
        # Apply hip rotation and knee flexion
        for y in range(hip_y, h):
            leg_frac = (y - hip_y) / (h - hip_y)
            
            # Near leg (right side of image when facing right)
            # Hip swing
            near_dx = math.sin(math.radians(n_hip)) * (y - hip_y) * 0.85
            if y > knee_y:
                knee_frac = (y - knee_y) / (h - knee_y)
                near_dx += math.sin(math.radians(n_knee)) * (y - knee_y) * 0.75
                # Foot flex
                near_dx += math.sin(math.radians(n_foot)) * knee_frac * 6.0
                
            # Far leg (left side of image when facing right)
            far_dx = math.sin(math.radians(f_hip)) * (y - hip_y) * 0.85
            if y > knee_y:
                knee_frac = (y - knee_y) / (h - knee_y)
                far_dx += math.sin(math.radians(f_knee)) * (y - knee_y) * 0.75
                far_dx += math.sin(math.radians(f_foot)) * knee_frac * 6.0
                
            # Apply to x coordinates
            # Smooth blend near center x
            x_weights = 1.0 / (1.0 + np.exp(-(x_grid[y, :] - cx) / 8.0)) # 0 for far leg, 1 for near leg
            combined_dx = (1.0 - x_weights) * far_dx + x_weights * near_dx
            
            map_x[y, :] -= combined_dx
            
        # 3. Arms swinging
        for y in range(shoulder_y, int(h * 0.70)):
            arm_frac = (y - shoulder_y) / (h * 0.35)
            near_arm_dx = math.sin(math.radians(n_arm)) * (y - shoulder_y) * 0.7
            far_arm_dx = math.sin(math.radians(f_arm)) * (y - shoulder_y) * 0.7
            
            # Near arm is on right side (x > w*0.65), Far arm is on left side (x < w*0.35)
            arm_mask_near = np.clip((x_grid[y, :] - w * 0.55) / (w * 0.25), 0, 1)
            arm_mask_far = np.clip((w * 0.45 - x_grid[y, :]) / (w * 0.25), 0, 1)
            
            map_x[y, :] -= arm_mask_near * near_arm_dx + arm_mask_far * far_arm_dx

        # Map RGBA channels
        deformed_channels = []
        for c in range(4):
            ch = ndi.map_coordinates(arr[:, :, c], [map_y, map_x], order=1, mode='constant', cval=0.0)
            deformed_channels.append(ch)
            
        deformed_arr = np.dstack(deformed_channels)
        
        # Shade far leg (x < cx and y > hip_y) to give authentic depth as in reference
        far_leg_mask = (x_grid < cx) & (y_grid > hip_y) & (deformed_arr[:, :, 3] > 20)
        # Apply 15% darkening to RGB on far leg
        for c in range(3):
            deformed_arr[:, :, c] = np.where(far_leg_mask, deformed_arr[:, :, c] * 0.85, deformed_arr[:, :, c])
            
        deformed_img = Image.fromarray(np.clip(deformed_arr, 0, 255).astype(np.uint8), "RGBA")
        
        # Rotate whole torso slightly according to pitch
        if abs(pitch) > 0.1:
            deformed_img = deformed_img.rotate(pitch, resample=RESAMPLE_BICUBIC, expand=True)
            
        # Position on canvas
        dw, dh = deformed_img.size
        ox = (FRAME_SIZE - dw) // 2
        oy = FRAME_SIZE - dh - 12 + torso_dy
        
        frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        frame.paste(deformed_img, (ox, oy), deformed_img)
        frames_right.append(frame)
        
    return frames_right

def run():
    goku_base = get_clean_cutout(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\goku_sources\goku_cutout.png", 140)
    venom_base = get_clean_cutout(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\venom_sources\venom_cutout.png", 145)
    
    goku_walk = create_articulated_walk_cycle(goku_base, is_venom=False)
    venom_walk = create_articulated_walk_cycle(venom_base, is_venom=True)
    
    # Save preview gifs
    out_dir = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc")
    goku_walk[0].save(out_dir / "test_goku_walk.gif", save_all=True, append_images=goku_walk[1:], duration=120, loop=0, disposal=2)
    venom_walk[0].save(out_dir / "test_venom_walk.gif", save_all=True, append_images=venom_walk[1:], duration=120, loop=0, disposal=2)
    print("Saved test_goku_walk.gif and test_venom_walk.gif successfully!")

if __name__ == "__main__":
    run()
